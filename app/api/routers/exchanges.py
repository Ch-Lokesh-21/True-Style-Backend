# app/api/routes/exchanges.py
from __future__ import annotations
from typing import List, Optional, Dict, Any

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Query, status, UploadFile, File, Form
from fastapi.responses import JSONResponse

from app.api.deps import require_permission, get_current_user
from app.core.database import db
from app.schemas.object_id import PyObjectId
from app.schemas.exchanges import ExchangesCreate, ExchangesUpdate, ExchangesOut
from app.crud import exchanges as crud
from app.utils.gridfs import upload_image, replace_image, delete_image, _extract_file_id_from_url

router = APIRouter()

from typing import Any  # make sure Any is imported

def _to_oid(v: Any, field: str) -> ObjectId:
    try:
        return ObjectId(str(v))
    except Exception:
        raise HTTPException(status_code=400, detail=f"Invalid {field}")

async def _get_order_item(order_item_id: PyObjectId) -> dict:
    oi = await db["order_items"].find_one({"_id": _to_oid(order_item_id, "order_item_id")})
    if not oi:
        raise HTTPException(status_code=404, detail="Order item not found")
    return oi

async def _assert_order_belongs_to_user(order_id: ObjectId, user_id: ObjectId) -> dict:
    doc = await db["orders"].find_one({"_id": order_id, "user_id": user_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Order not found for user")
    return doc

async def _get_exchange_status_id_by_label(label: str) -> ObjectId:
    doc = await db["exchange_status"].find_one({"status": label})
    if not doc:
        raise HTTPException(status_code=500, detail=f"Exchange status '{label}' not found")
    return doc["_id"]


@router.post(
    "/",
    response_model=ExchangesOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("exchanges", "Create"))],
)
async def create_exchange(
    order_item_id: PyObjectId = Form(...),
    reason: Optional[str] = Form(None),
    image: UploadFile = File(None),
    new_quantity: int = Form(...),
    new_size: Optional[str] = Form(None),
    current_user: Dict = Depends(get_current_user),
):
    """
    User creates an exchange by referencing a single order_item.
    - Derives order_id and product_id from order_items.
    - Enforces ownership.
    - Forces exchange_status to 'requested' (looked up from exchange_status collection).
    """
    user_oid = _to_oid(current_user["user_id"], "user_id")

    # 1) load order_item and derive order_id + product_id
    oi = await _get_order_item(order_item_id)
    order_id = oi["order_id"]
    product_id = oi["product_id"]

    # 2) ensure the order belongs to this user
    await _assert_order_belongs_to_user(order_id, user_oid)

    # 3) resolve exchange_status = "requested"
    requested_status_id = await _get_exchange_status_id_by_label("requested")

    # 4) handle image (GridFS or direct URL)
    if image is not None:
        _, final_url = await upload_image(image)

    # 5) build payload using derived ids + forced status
    payload = ExchangesCreate(
        order_id=PyObjectId(str(order_id)),
        product_id=PyObjectId(str(product_id)),
        exchange_status_id=PyObjectId(str(requested_status_id)),
        user_id=PyObjectId(str(user_oid)),
        reason=reason,
        image_url=final_url,
        new_quantity=new_quantity,
        new_size=new_size,
    )

    try:
        return await crud.create(payload)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create exchange: {e}")


@router.get(
    "/my",
    response_model=List[ExchangesOut],
    dependencies=[Depends(require_permission("exchanges", "Read"))],
)
async def list_my_exchanges(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    current_user: Dict = Depends(get_current_user),
):
    try:
        return await crud.list_all(
            skip=skip,
            limit=limit,
            query={"user_id": current_user["user_id"]},
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list exchanges: {e}")


@router.get(
    "/my/{item_id}",
    response_model=ExchangesOut,
    dependencies=[Depends(require_permission("exchanges", "Read"))],
)
async def get_my_exchange(item_id: PyObjectId, current_user: Dict = Depends(get_current_user)):
    try:
        item = await crud.get_one(item_id)
        if not item:
            raise HTTPException(status_code=404, detail="Exchange not found")
        if str(item.user_id) != str(current_user["user_id"]):
            raise HTTPException(status_code=403, detail="Forbidden")
        return item
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get exchange: {e}")


# -------------------- Admin endpoints --------------------

@router.get(
    "/",
    response_model=List[ExchangesOut],
    dependencies=[Depends(require_permission("exchanges", "Read", "admin"))],
)
async def admin_list_exchanges(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    user_id: Optional[PyObjectId] = Query(None),
    order_id: Optional[PyObjectId] = Query(None),
    product_id: Optional[PyObjectId] = Query(None),
    exchange_status_id: Optional[PyObjectId] = Query(None),
):
    try:
        q: Dict[str, Any] = {}
        if user_id: q["user_id"] = user_id
        if order_id: q["order_id"] = order_id
        if product_id: q["product_id"] = product_id
        if exchange_status_id: q["exchange_status_id"] = exchange_status_id
        return await crud.list_all(skip=skip, limit=limit, query=q or None)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list exchanges: {e}")


@router.get(
    "/{item_id}",
    response_model=ExchangesOut,
    dependencies=[Depends(require_permission("exchanges", "Read", "admin"))],
)
async def admin_get_exchange(item_id: PyObjectId):
    try:
        item = await crud.get_one(item_id)
        if not item:
            raise HTTPException(status_code=404, detail="Exchange not found")
        return item
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get exchange: {e}")


@router.put(
    "/{item_id}/status",
    response_model=ExchangesOut,
    dependencies=[Depends(require_permission("exchanges", "Update", "admin"))],
)
async def admin_update_exchange_status(item_id: PyObjectId, payload: ExchangesUpdate):
    """
    Admin can only update exchange_status_id (as per schema).
    """
    try:
        if payload.exchange_status_id is None:
            raise HTTPException(status_code=400, detail="exchange_status_id is required")
        updated = await crud.update_one(item_id, payload)
        if not updated:
            raise HTTPException(status_code=404, detail="Exchange not found or not updated")
        return updated
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update exchange: {e}")


@router.delete(
    "/{item_id}",
    dependencies=[Depends(require_permission("exchanges", "Delete", "admin"))],
)
async def admin_delete_exchange(item_id: PyObjectId):
    """
    Admin delete; if the exchange has a GridFS-backed image, remove it too.
    """
    try:
        current = await crud.get_one(item_id)
        if not current:
            raise HTTPException(status_code=404, detail="Exchange not found")

        file_id = _extract_file_id_from_url(current.image_url)
        if file_id:
            await delete_image(file_id)

        ok = await crud.delete_one(item_id)
        if not ok:
            raise HTTPException(status_code=404, detail="Exchange not found")
        return JSONResponse(status_code=200, content={"deleted": True})
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete exchange: {e}")