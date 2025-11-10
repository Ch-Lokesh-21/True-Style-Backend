"""
Service layer for Exchanges.
- Owns the business rules, DB access orchestration, and GridFS handling.
- Enforces the 7-day delivery window on creation.
"""

from __future__ import annotations
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone, timedelta, date

from bson import ObjectId
from fastapi import HTTPException, UploadFile, status
from fastapi.responses import JSONResponse

from app.api.deps import get_current_user  # only for typing/context if needed elsewhere
from app.core.database import db
from app.schemas.object_id import PyObjectId
from app.schemas.exchanges import ExchangesCreate, ExchangesUpdate, ExchangesOut
from app.crud import exchanges as crud
from app.utils.gridfs import upload_image, replace_image, delete_image, _extract_file_id_from_url


def _to_oid(v: Any, field: str) -> ObjectId:
    """
    Safely cast a value to ObjectId or raise 400 with a helpful message.

    Args:
        v: Any value that should represent an ObjectId.
        field: Field name for error context.

    Returns:
        ObjectId

    Raises:
        HTTPException 400 if cast fails.
    """
    try:
        return ObjectId(str(v))
    except Exception:
        raise HTTPException(status_code=400, detail=f"Invalid {field}")


async def _get_order_item(order_item_id: PyObjectId) -> dict:
    """
    Load the order_item document or raise 404.

    Args:
        order_item_id: Order item id.

    Returns:
        dict: order_item document.

    Raises:
        HTTPException 404 if not found.
    """
    oi = await db["order_items"].find_one({"_id": _to_oid(order_item_id, "order_item_id")})
    if not oi:
        raise HTTPException(status_code=404, detail="Order item not found")
    return oi


async def _assert_order_belongs_to_user(order_id: ObjectId, user_id: ObjectId) -> dict:
    """
    Ensure the order belongs to the given user.

    Args:
        order_id: Order ObjectId.
        user_id: User ObjectId.

    Returns:
        dict: order document.

    Raises:
        HTTPException 404 if not found for user.
    """
    doc = await db["orders"].find_one({"_id": order_id, "user_id": user_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Order not found for user")
    return doc


async def _get_exchange_status_id_by_label(label: str) -> ObjectId:
    """
    Resolve an exchange_status by its label (e.g., 'requested').

    Args:
        label: Status label.

    Returns:
        ObjectId: The status id.

    Raises:
        HTTPException 500 if not configured/present.
    """
    doc = await db["exchange_status"].find_one({"status": label})
    if not doc:
        raise HTTPException(status_code=500, detail=f"Exchange status '{label}' not found")
    return doc["_id"]


def _ensure_within_7_days(delivery_date: date) -> None:
    """
    Ensure the provided delivery_date is within the last 7 days inclusive.

    Args:
        delivery_date: Date of delivery.

    Raises:
        HTTPException 400 if exchange window has expired.
    """
    today = datetime.now(timezone.utc).date()
    delta_days = (today - delivery_date).days
    if delta_days < 0:
        # Future delivery date is invalid in this context
        raise HTTPException(status_code=400, detail="Delivery date cannot be in the future")
    if delta_days > 7:
        raise HTTPException(status_code=400, detail="Exchange window expired (delivery + 7 days)")


# -------------------- User services --------------------

async def create_exchange_service(
    order_item_id: PyObjectId,
    reason: Optional[str],
    image: UploadFile = None,
    new_quantity: int = 1,
    new_size: Optional[str] = None,
    current_user: Dict[str, Any] = None,
) -> ExchangesOut:
    """
    Create an exchange for a single order item.
    - delivery_date is automatically fetched from orders collection.
    - Enforces delivery_date within the last 7 days.
    """

    # Prepare user ObjectId
    user_oid = _to_oid(current_user["user_id"], "user_id")

    # 1) Load order_item → derive order_id + product_id
    oi = await _get_order_item(order_item_id)
    order_id = oi["order_id"]
    product_id = oi["product_id"]

    # 2) Ensure ownership
    order_doc = await _assert_order_belongs_to_user(order_id, user_oid)

    # ✅ 3) Read delivery_date from order document
    delivery_date = order_doc.get("delivery_date")
    if not delivery_date:
        raise HTTPException(
            status_code=400,
            detail="Order does not contain delivery_date; exchange cannot be created.",
        )

    # If stored as string, convert to date
    if isinstance(delivery_date, str):
        try:
            delivery_date = datetime.fromisoformat(delivery_date).date()
        except Exception:
            raise HTTPException(
                status_code=500,
                detail="delivery_date in DB is not a valid ISO date format",
            )
    elif isinstance(delivery_date, datetime):
        delivery_date = delivery_date.date()
    elif not isinstance(delivery_date, date):
        raise HTTPException(
            status_code=500,
            detail="delivery_date format in DB is invalid",
        )

    # ✅ 4) Enforce 7-day rule
    _ensure_within_7_days(delivery_date)

    # 5) Resolve exchange_status = "requested"
    requested_status_id = await _get_exchange_status_id_by_label("requested")

    # 6) Handle image
    final_url: Optional[str] = None
    if image is not None:
        _, final_url = await upload_image(image)

    # 7) Build payload
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


async def list_my_exchanges_service(
    skip: int,
    limit: int,
    current_user: Dict[str, Any],
) -> List[ExchangesOut]:
    """
    List exchanges created by the current user.

    Args:
        skip: Offset.
        limit: Limit.
        current_user: Current user dict (expects 'user_id').

    Returns:
        List[ExchangesOut]
    """
    try:
        return await crud.list_all(
            skip=skip,
            limit=limit,
            query={"user_id": current_user["user_id"]},
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list exchanges: {e}")


async def get_my_exchange_service(item_id: PyObjectId, current_user: Dict[str, Any]) -> ExchangesOut:
    """
    Get a single exchange that belongs to the current user.

    Args:
        item_id: Exchange ObjectId.
        current_user: Current user context.

    Returns:
        ExchangesOut

    Raises:
        403 if user does not own the exchange.
    """
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


# -------------------- Admin services --------------------

async def admin_list_exchanges_service(
    skip: int,
    limit: int,
    user_id: Optional[PyObjectId],
    order_id: Optional[PyObjectId],
    product_id: Optional[PyObjectId],
    exchange_status_id: Optional[PyObjectId],
) -> List[ExchangesOut]:
    """
    Admin: list exchanges with optional filters.

    Args:
        skip, limit: Pagination controls.
        user_id, order_id, product_id, exchange_status_id: Optional filters.

    Returns:
        List[ExchangesOut]
    """
    try:
        q: Dict[str, Any] = {}
        if user_id: q["user_id"] = user_id
        if order_id: q["order_id"] = order_id
        if product_id: q["product_id"] = product_id
        if exchange_status_id: q["exchange_status_id"] = exchange_status_id
        return await crud.list_all(skip=skip, limit=limit, query=q or None)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list exchanges: {e}")


async def admin_get_exchange_service(item_id: PyObjectId) -> ExchangesOut:
    """
    Admin: get a single exchange by ID.

    Args:
        item_id: Exchange ObjectId.

    Returns:
        ExchangesOut
    """
    try:
        item = await crud.get_one(item_id)
        if not item:
            raise HTTPException(status_code=404, detail="Exchange not found")
        return item
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get exchange: {e}")


async def admin_update_exchange_status_service(item_id: PyObjectId, payload: ExchangesUpdate) -> ExchangesOut:
    """
    Admin: update only the exchange_status_id.

    Args:
        item_id: Exchange ObjectId.
        payload: ExchangesUpdate (expects exchange_status_id).

    Returns:
        ExchangesOut

    Raises:
        400 if exchange_status_id is missing.
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


async def admin_delete_exchange_service(item_id: PyObjectId):
    """
    Admin: delete an exchange and remove GridFS file if present.

    Args:
        item_id: Exchange ObjectId.

    Returns:
        JSONResponse({"deleted": True})
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