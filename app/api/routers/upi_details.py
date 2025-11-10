"""
API Router for UPI Details.

Responsibilities:
- Enforce permissions
- Accept/validate query & path params
- Delegate to the UPI details service
"""

from __future__ import annotations
from typing import List, Optional, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, Query
from app.api.deps import require_permission, get_current_user
from app.schemas.object_id import PyObjectId
from app.schemas.upi_details import UpiDetailsOut
from app.services.upi_details import (
    get_my_upi_by_payment_svc,
    get_upi_by_payment_admin_svc,
    list_upi_details_admin_svc,
)

router = APIRouter()


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
    Return the caller's own UPI details for the given payment.
    Ownership is enforced against the payment's `user_id`.
    """
    return await get_my_upi_by_payment_svc(payment_id=payment_id, current_user=current_user)


@router.get(
    "/by-payment/{payment_id}",
    response_model=UpiDetailsOut,
    dependencies=[Depends(require_permission("upi_details", "Read", "admin"))],
)
async def get_upi_by_payment_admin(payment_id: PyObjectId):
    """
    Admin: fetch UPI details associated with a specific payment.
    """
    return await get_upi_by_payment_admin_svc(payment_id=payment_id)


@router.get(
    "/",
    response_model=List[UpiDetailsOut],
    dependencies=[Depends(require_permission("upi_details", "Read", "admin"))],
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
    Admin listing with both direct and join-based filters:
    - Direct: `payment_id`, `upi_id`
    - Join via `payments`: `user_id`, `order_id`
    """
    return await list_upi_details_admin_svc(
        skip=skip,
        limit=limit,
        payment_id=payment_id,
        upi_id=upi_id,
        user_id=user_id,
        order_id=order_id,
    )