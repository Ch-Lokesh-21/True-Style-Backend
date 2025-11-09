# app/api/routes/returns.py
from __future__ import annotations
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, timezone

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Query, status, UploadFile, File, Form
from fastapi.responses import JSONResponse

from app.api.deps import require_permission, get_current_user
from app.core.database import db
from app.schemas.object_id import PyObjectId
from app.schemas.returns import ReturnsCreate, ReturnsUpdate, ReturnsOut
from app.crud import returns as crud
from app.utils.gridfs import upload_image

router = APIRouter()

# -------------- helpers --------------

def _to_oid(v: Any, field: str) -> ObjectId:
    try:
        return ObjectId(str(v))
    except Exception:
        raise HTTPException(status_code=400, detail=f"Invalid {field}")

async def _get_status_id(label: str) -> ObjectId:
    doc = await db["return_status"].find_one({"status": label})
    if not doc:
        raise HTTPException(status_code=500, detail=f"Return status '{label}' not found")
    return doc["_id"]

async def _load_order_item(oi_id: PyObjectId) -> dict:
    oi = await db["order_items"].find_one({"_id": _to_oid(oi_id, "order_item_id")})
    if not oi:
        raise HTTPException(status_code=404, detail="Order item not found")
    return oi

async def _load_order(order_id: ObjectId) -> dict:
    order = await db["orders"].find_one({"_id": order_id})
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order

async def _load_product(product_id: ObjectId) -> dict:
    prod = await db["products"].find_one({"_id": product_id})
    if not prod:
        raise HTTPException(status_code=404, detail="Product not found")
    return prod

async def _already_returned_qty(order_id: ObjectId, product_id: ObjectId) -> int:
    pipeline = [
        {"$match": {"order_id": order_id, "product_id": product_id}},
        {"$group": {"__id": None, "q": {"$sum": {"$ifNull": ["$quantity", 0]}}}},
    ]
    total = 0
    async for row in db["returns"].aggregate(pipeline):
        total = int(row.get("q", 0))
    return total

def _price_of(prod: dict) -> float:
    # prefer total_price if present, else price, else 0.0
    val = prod.get("total_price", prod.get("price", 0.0))
    try:
        return float(val)
    except Exception:
        return 0.0

# -------------- routes --------------

@router.post(
    "/",
    response_model=ReturnsOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("returns", "Create"))],
)
async def create_return(
    order_item_id: PyObjectId = Form(...),
    quantity: int = Form(..., description="Quantity to return"),
    reason: Optional[str] = Form(None),
    image: UploadFile = File(None),
    current_user: Dict = Depends(get_current_user),
):
    """
    User creates a return for an order item they own.
    - Validates ownership and available quantity (ordered - already returned).
    - Computes amount from product price * quantity.
    - Sets return_status to 'requested'.
    - Accepts either file upload (stored via GridFS) or direct image_url (string).
    """
    if quantity <= 0:
        raise HTTPException(status_code=400, detail="quantity must be greater than 0")

    # Load order_item + linked order/product
    oi = await _load_order_item(order_item_id)
    order_id: ObjectId = oi["order_id"]
    product_id: ObjectId = oi["product_id"]
    ordered_qty: int = int(oi.get("quantity", 0))

    order = await _load_order(order_id)
    # ownership guard
    if str(order.get("user_id")) != str(current_user.get("user_id")):
        raise HTTPException(status_code=403, detail="Forbidden")

    # ensure quantity is available considering previously created returns
    prior = await _already_returned_qty(order_id, product_id)
    available = max(0, ordered_qty - prior)
    if quantity > available:
        raise HTTPException(
            status_code=400,
            detail=f"Only {available} items can be returned for this order item",
        )

    prod = await _load_product(product_id)
    unit_price = _price_of(prod)
    amount = round(unit_price * quantity, 2)

    # image handling
    if image is not None:
        _, final_url = await upload_image(image)

    status_id = await _get_status_id("requested")

    payload = ReturnsCreate(
        order_id=order_id,
        product_id=product_id,
        return_status_id=status_id,
        user_id=_to_oid(current_user["user_id"], "user_id"),
        reason=reason,
        image_url=final_url,
        quantity=quantity,
        amount=amount,
    )

    try:
        return await crud.create(payload)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create return: {e}")

# ---------- USER: list & get my returns ----------

@router.get(
    "/my",
    response_model=List[ReturnsOut],
    dependencies=[Depends(require_permission("returns", "Read"))],
)
async def list_my_returns(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    current_user: Dict = Depends(get_current_user),
):
    try:
        q = {"user_id": _to_oid(current_user["user_id"], "user_id")}
        return await crud.list_all(skip=skip, limit=limit, query=q)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list returns: {e}")

@router.get(
    "/my/{return_id}",
    response_model=ReturnsOut,
    dependencies=[Depends(require_permission("returns", "Read"))],
)
async def get_my_return(
    return_id: PyObjectId,
    current_user: Dict = Depends(get_current_user),
):
    try:
        item = await crud.get_one(return_id)
        if not item:
            raise HTTPException(status_code=404, detail="Return not found")
        if str(item.user_id) != str(current_user["user_id"]):
            raise HTTPException(status_code=403, detail="Forbidden")
        return item
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get return: {e}")

# ---------- ADMIN: list/get/update/delete ----------

@router.get(
    "/",
    response_model=List[ReturnsOut],
    dependencies=[Depends(require_permission("returns", "Read", "admin"))],
)
async def admin_list_returns(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    user_id: Optional[PyObjectId] = Query(None),
    order_id: Optional[PyObjectId] = Query(None),
    product_id: Optional[PyObjectId] = Query(None),
    return_status_id: Optional[PyObjectId] = Query(None),
):
    try:
        q: Dict[str, Any] = {}
        if user_id is not None:
            q["user_id"] = _to_oid(user_id, "user_id")
        if order_id is not None:
            q["order_id"] = _to_oid(order_id, "order_id")
        if product_id is not None:
            q["product_id"] = _to_oid(product_id, "product_id")
        if return_status_id is not None:
            q["return_status_id"] = _to_oid(return_status_id, "return_status_id")
        return await crud.list_all(skip=skip, limit=limit, query=q or None)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list returns: {e}")

@router.get(
    "/{return_id}",
    response_model=ReturnsOut,
    dependencies=[Depends(require_permission("returns", "Read", "admin"))],
)
async def admin_get_return(return_id: PyObjectId):
    try:
        item = await crud.get_one(return_id)
        if not item:
            raise HTTPException(status_code=404, detail="Return not found")
        return item
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get return: {e}")

@router.put(
    "/{return_id}/status",
    response_model=ReturnsOut,
    dependencies=[Depends(require_permission("returns", "Update", "admin"))],
)
async def admin_update_return_status(
    return_id: PyObjectId,
    payload: ReturnsUpdate,
):
    """
    Admin can update only the status (per your ReturnsUpdate schema).
    """
    try:
        if payload.return_status_id is None:
            raise HTTPException(status_code=400, detail="return_status_id is required")
        updated = await crud.update_one(return_id, payload)
        if not updated:
            raise HTTPException(status_code=404, detail="Return not found or not updated")
        return updated
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update return: {e}")

@router.delete(
    "/{return_id}",
    dependencies=[Depends(require_permission("returns", "Delete"))]
)
async def admin_delete_return(return_id: PyObjectId):
    try:
        ok = await crud.delete_one(return_id)
        if not ok:
            raise HTTPException(status_code=404, detail="Return not found")
        return JSONResponse(status_code=200, content={"deleted": True})
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete return: {e}")