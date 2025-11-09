# app/api/routes/upi_details.py
from __future__ import annotations
from typing import List, Optional, Dict, Any

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.deps import require_permission, get_current_user
from app.schemas.object_id import PyObjectId
from app.schemas.upi_details import UpiDetailsOut
from app.crud import upi_details as upi_crud
from app.crud import payments as payments_crud
from app.core.database import db

router = APIRouter()

def _to_oid(v: Any, field: str) -> ObjectId:
    try:
        return ObjectId(str(v))
    except Exception:
        raise HTTPException(status_code=400, detail=f"Invalid {field}")

# ---------------------------
# USER: read own UPI details
# ---------------------------
@router.get(
    "/my/by-payment/{payment_id}",
    response_model=UpiDetailsOut,
    dependencies=[Depends(require_permission("upi_details", "Read"))],
)
async def get_my_upi_by_payment(
    payment_id: PyObjectId,
    current_user: Dict = Depends(get_current_user),
):
    """
    Return the raw UPI ID for the caller's own payment.
    """
    pay = await payments_crud.get_one(payment_id)
    if not pay:
        raise HTTPException(status_code=404, detail="Payment not found")

    if str(pay.user_id) != str(current_user["user_id"]):
        raise HTTPException(status_code=403, detail="Forbidden")

    item = await upi_crud.get_by_payment_id(payment_id)
    if not item:
        raise HTTPException(status_code=404, detail="UPI details not found")
    return item

# ---------------------------
# ADMIN: by payment id
# ---------------------------
@router.get(
    "/by-payment/{payment_id}",
    response_model=UpiDetailsOut,
    dependencies=[Depends(require_permission("upi_details", "Read", "admin"))]
)
async def get_upi_by_payment_admin(payment_id: PyObjectId):
    item = await upi_crud.get_by_payment_id(payment_id)
    if not item:
        raise HTTPException(status_code=404, detail="UPI details not found")
    return item

# ---------------------------
# ADMIN: list with filters
# ---------------------------
@router.get(
    "/",
    response_model=List[UpiDetailsOut],
    dependencies=[Depends(require_permission("upi_details", "Read", "admin"))]
)
async def list_upi_details_admin(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    payment_id: Optional[PyObjectId] = Query(None, description="Filter by payment_id"),
    upi_id: Optional[str] = Query(None, description="Exact UPI ID match"),
    user_id: Optional[PyObjectId] = Query(None, description="Filter by user_id (via payments join)"),
    order_id: Optional[PyObjectId] = Query(None, description="Filter by order_id (via payments join)"),
):
    """
    Admin listing:
      - Direct filters: payment_id, upi_id
      - Indirect (join via payments): user_id, order_id
    """
    q: Dict[str, Any] = {}

    if payment_id is not None:
        q["payment_id"] = _to_oid(payment_id, "payment_id")

    if upi_id:
        q["upi_id"] = upi_id.strip()

    # Resolve user_id/order_id via payments → collect matching payment_ids
    pids_from_join: Optional[List[ObjectId]] = None
    join_filters: Dict[str, Any] = {}
    if user_id is not None:
        join_filters["user_id"] = _to_oid(user_id, "user_id")
    if order_id is not None:
        join_filters["order_id"] = _to_oid(order_id, "order_id")

    if join_filters:
        # Find payments matching join filters, grab their _ids
        cur = db["payments"].find(join_filters, projection={"_id": 1})
        pids_from_join = [doc["_id"] async for doc in cur]
        if not pids_from_join:
            return []  # nothing matches; early exit
        # merge with any existing payment_id filter
        if "payment_id" in q:
            if q["payment_id"] not in pids_from_join:
                return []
            # otherwise keep the single id
        else:
            q["payment_id"] = {"$in": pids_from_join}

    return await upi_crud.list_all(skip=skip, limit=limit, query=q or None)