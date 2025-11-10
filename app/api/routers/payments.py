"""
Routes for Payments.
- Thin HTTP layer: parses/validates inputs, applies RBAC, and delegates to services.
"""

from __future__ import annotations
from typing import List, Optional, Dict, Any

from fastapi import APIRouter, Depends, Query, status
from app.api.deps import require_permission, get_current_user
from app.schemas.object_id import PyObjectId
from app.schemas.payments import PaymentsUpdate, PaymentsOut
from app.services.payments import (
    list_my_payments_service,
    get_my_payment_service,
    list_payments_admin_service,
    get_payment_admin_service,
    update_payment_status_admin_service,
)

router = APIRouter()  # mounted at /payments


# --------------------------
# USER: read my payments
# --------------------------
@router.get(
    "/my",
    response_model=List[PaymentsOut],
    dependencies=[Depends(require_permission("payments", "Read"))],
)
async def list_my_payments(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    order_id: Optional[PyObjectId] = Query(None, description="Filter by my specific order"),
    invoice_no: Optional[str] = Query(None, description="Exact invoice number"),
    current_user: Dict = Depends(get_current_user),
):
    """
    List payments that belong to the **current user**.

    Args:
        skip: Pagination offset.
        limit: Page size.
        order_id: Optional filter for a specific order.
        invoice_no: Optional exact invoice number.
        current_user: Injected current user context.

    Returns:
        List[PaymentsOut]
    """
    return await list_my_payments_service(
        skip=skip, limit=limit, order_id=order_id, invoice_no=invoice_no, current_user=current_user
    )


@router.get(
    "/my/{payment_id}",
    response_model=PaymentsOut,
    dependencies=[Depends(require_permission("payments", "Read"))],
)
async def get_my_payment(
    payment_id: PyObjectId,
    current_user: Dict = Depends(get_current_user),
):
    """
    Get a single payment if it belongs to the current user.

    Args:
        payment_id: Payment ObjectId.
        current_user: Injected current user context.

    Returns:
        PaymentsOut

    Raises:
        404 if not found.
        403 if the payment is not owned by the user.
    """
    return await get_my_payment_service(payment_id=payment_id, current_user=current_user)


# --------------------------
# ADMIN: read any payments
# --------------------------
@router.get(
    "/",
    response_model=List[PaymentsOut],
    dependencies=[Depends(require_permission("payments", "Read", "admin"))],
)
async def list_payments_admin(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    user_id: Optional[PyObjectId] = Query(None),
    order_id: Optional[PyObjectId] = Query(None),
    payment_types_id: Optional[PyObjectId] = Query(None),
    payment_status_id: Optional[PyObjectId] = Query(None),
    invoice_no: Optional[str] = Query(None),
):
    """
    Admin: list payments with rich filters.

    Args:
        skip: Pagination offset.
        limit: Page size.
        user_id: Optional filter.
        order_id: Optional filter.
        payment_types_id: Optional filter.
        payment_status_id: Optional filter.
        invoice_no: Optional exact invoice number.

    Returns:
        List[PaymentsOut]
    """
    return await list_payments_admin_service(
        skip=skip,
        limit=limit,
        user_id=user_id,
        order_id=order_id,
        payment_types_id=payment_types_id,
        payment_status_id=payment_status_id,
        invoice_no=invoice_no,
    )


@router.get(
    "/{payment_id}",
    response_model=PaymentsOut,
    dependencies=[Depends(require_permission("payments", "Read", "admin"))],
)
async def get_payment_admin(payment_id: PyObjectId):
    """
    Admin: get any payment by id.

    Args:
        payment_id: Payment ObjectId.

    Returns:
        PaymentsOut

    Raises:
        404 if not found.
    """
    return await get_payment_admin_service(payment_id)


# --------------------------
# ADMIN: update status only
# --------------------------
@router.put(
    "/{payment_id}/status",
    response_model=PaymentsOut,
    dependencies=[Depends(require_permission("payments", "Update", "admin"))],
)
async def update_payment_status_admin(payment_id: PyObjectId, payload: PaymentsUpdate):
    """
    Admin: update a payment's status (e.g., pending → success/failed).

    Only `payment_status_id` is expected in the payload.

    Args:
        payment_id: Payment ObjectId.
        payload: PaymentsUpdate with `payment_status_id`.

    Returns:
        PaymentsOut

    Raises:
        400 if `payment_status_id` missing.
        404 if not found.
    """
    return await update_payment_status_admin_service(payment_id=payment_id, payload=payload)