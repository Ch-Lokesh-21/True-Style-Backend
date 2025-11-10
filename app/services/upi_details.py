"""
UPI Details service layer.

Encapsulates business logic for:
- Ownership checks against payments
- Admin lookups by payment
- Admin listings with cross-collection joins (via `payments`)
"""

from __future__ import annotations
from typing import List, Optional, Dict, Any

from bson import ObjectId
from fastapi import HTTPException, status

from app.schemas.object_id import PyObjectId
from app.schemas.upi_details import UpiDetailsOut
from app.crud import upi_details as upi_crud
from app.crud import payments as payments_crud
from app.core.database import db


def _to_oid(v: Any, field: str) -> ObjectId:
    """
    Coerce a value to ObjectId or raise 400 with a clear field name.
    """
    try:
        return ObjectId(str(v))
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid {field}")


async def get_my_upi_by_payment_svc(payment_id: PyObjectId, current_user: Dict) -> UpiDetailsOut:
    """
    Service: return UPI details for a payment that belongs to the current user.

    Steps:
    1) Load the payment by id
    2) Verify `payment.user_id` matches the current user's id
    3) Load & return UPI details row linked by `payment_id`
    """
    pay = await payments_crud.get_one(payment_id)
    if not pay:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment not found")

    if str(pay.user_id) != str(current_user["user_id"]):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

    item = await upi_crud.get_by_payment_id(payment_id)
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="UPI details not found")
    return item


async def get_upi_by_payment_admin_svc(payment_id: PyObjectId) -> UpiDetailsOut:
    """
    Service (admin): fetch UPI details by payment id.
    """
    item = await upi_crud.get_by_payment_id(payment_id)
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="UPI details not found")
    return item


async def list_upi_details_admin_svc(
    skip: int,
    limit: int,
    payment_id: Optional[PyObjectId],
    upi_id: Optional[str],
    user_id: Optional[PyObjectId],
    order_id: Optional[PyObjectId],
) -> List[UpiDetailsOut]:
    """
    Service (admin): list UPI details with optional filters.

    Filter logic:
      - Direct: `payment_id`, `upi_id`
      - Join via `payments` on (`user_id`, `order_id`) to resolve matching payment ids
      - If both a direct `payment_id` and join-derived ids are present, enforce intersection
    """
    q: Dict[str, Any] = {}

    if payment_id is not None:
        q["payment_id"] = _to_oid(payment_id, "payment_id")

    if upi_id:
        q["upi_id"] = upi_id.strip()

    # Build join filters for payments
    join_filters: Dict[str, Any] = {}
    if user_id is not None:
        join_filters["user_id"] = _to_oid(user_id, "user_id")
    if order_id is not None:
        join_filters["order_id"] = _to_oid(order_id, "order_id")

    # Resolve payment ids via join if needed
    if join_filters:
        cur = db["payments"].find(join_filters, projection={"_id": 1})
        pids_from_join = [doc["_id"] async for doc in cur]

        if not pids_from_join:
            return []

        if "payment_id" in q:
            # intersect a specific payment_id with join results
            if q["payment_id"] not in pids_from_join:
                return []
            # keep q["payment_id"] as is (single match)
        else:
            q["payment_id"] = {"$in": pids_from_join}

    return await upi_crud.list_all(skip=skip, limit=limit, query=q or None)