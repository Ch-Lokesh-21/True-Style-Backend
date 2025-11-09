# app/api/routes/payments.py
from __future__ import annotations
from typing import List, Optional, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from app.api.deps import require_permission, get_current_user
from app.schemas.object_id import PyObjectId
from app.schemas.payments import PaymentsUpdate, PaymentsOut
from app.crud import payments as crud

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
    Optional filters: order_id, invoice_no.
    """
    try:
        q: Dict[str, Any] = {"user_id": current_user["user_id"]}
        if order_id is not None:
            q["order_id"] = order_id
        if invoice_no:
            q["invoice_no"] = invoice_no.strip()
        return await crud.list_all(skip=skip, limit=limit, query=q)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list my payments: {e}")


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
    """
    try:
        item = await crud.get_one(payment_id)
        if not item:
            raise HTTPException(status_code=404, detail="Payment not found")
        if str(item.user_id) != str(current_user["user_id"]):
            raise HTTPException(status_code=403, detail="Forbidden")
        return item
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get payment: {e}")


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
    Admin: list payments with rich filters:
    user_id, order_id, payment_types_id, payment_status_id, invoice_no.
    """
    try:
        q: Dict[str, Any] = {}
        if user_id is not None:
            q["user_id"] = user_id
        if order_id is not None:
            q["order_id"] = order_id
        if payment_types_id is not None:
            q["payment_types_id"] = payment_types_id
        if payment_status_id is not None:
            q["payment_status_id"] = payment_status_id
        if invoice_no:
            q["invoice_no"] = invoice_no.strip()
        return await crud.list_all(skip=skip, limit=limit, query=q or None)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list payments: {e}")


@router.get(
    "/{payment_id}",
    response_model=PaymentsOut,
    dependencies=[Depends(require_permission("payments", "Read", "admin"))],
)
async def get_payment_admin(payment_id: PyObjectId):
    """Admin: get any payment by id."""
    try:
        item = await crud.get_one(payment_id)
        if not item:
            raise HTTPException(status_code=404, detail="Payment not found")
        return item
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get payment: {e}")


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
    """
    try:
        if payload.payment_status_id is None:
            raise HTTPException(status_code=400, detail="payment_status_id is required")
        updated = await crud.update_one(payment_id, payload)
        if not updated:
            raise HTTPException(status_code=404, detail="Payment not found or not updated")
        return updated
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update payment: {e}")