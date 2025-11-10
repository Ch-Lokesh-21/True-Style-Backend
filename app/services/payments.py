"""
Service layer for Payments.
- Owns business rules, ownership checks, and error mapping for CRUD operations.
"""

from __future__ import annotations
from typing import List, Optional, Dict, Any

from fastapi import HTTPException
from app.schemas.object_id import PyObjectId
from app.schemas.payments import PaymentsUpdate, PaymentsOut
from app.crud import payments as crud


async def list_my_payments_service(
    skip: int,
    limit: int,
    order_id: Optional[PyObjectId],
    invoice_no: Optional[str],
    current_user: Dict[str, Any],
) -> List[PaymentsOut]:
    """
    List payments owned by the current user with optional filters.

    Args:
        skip: Offset.
        limit: Limit.
        order_id: Optional filter by order.
        invoice_no: Optional exact invoice number.
        current_user: Auth context (expects 'user_id').

    Returns:
        List[PaymentsOut]
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


async def get_my_payment_service(payment_id: PyObjectId, current_user: Dict[str, Any]) -> PaymentsOut:
    """
    Get one payment if owned by the current user.

    Args:
        payment_id: Payment ObjectId.
        current_user: Auth context (expects 'user_id').

    Returns:
        PaymentsOut

    Raises:
        404 if not found.
        403 if not owned by user.
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


async def list_payments_admin_service(
    skip: int,
    limit: int,
    user_id: Optional[PyObjectId],
    order_id: Optional[PyObjectId],
    payment_types_id: Optional[PyObjectId],
    payment_status_id: Optional[PyObjectId],
    invoice_no: Optional[str],
) -> List[PaymentsOut]:
    """
    Admin: list payments with rich filters.

    Args:
        skip: Offset.
        limit: Limit.
        user_id: Optional filter by user id.
        order_id: Optional filter by order id.
        payment_types_id: Optional filter by payment type id.
        payment_status_id: Optional filter by payment status id.
        invoice_no: Optional exact invoice number.

    Returns:
        List[PaymentsOut]
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


async def get_payment_admin_service(payment_id: PyObjectId) -> PaymentsOut:
    """
    Admin: get any payment by id.

    Args:
        payment_id: Payment ObjectId.

    Returns:
        PaymentsOut

    Raises:
        404 if not found.
    """
    try:
        item = await crud.get_one(payment_id)
        if not item:
            raise HTTPException(status_code=404, detail="Payment not found")
        return item
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get payment: {e}")


async def update_payment_status_admin_service(payment_id: PyObjectId, payload: PaymentsUpdate) -> PaymentsOut:
    """
    Admin: update a payment's status (status id only).

    Args:
        payment_id: Payment ObjectId.
        payload: PaymentsUpdate (expects `payment_status_id`).

    Returns:
        PaymentsOut

    Raises:
        400 if `payment_status_id` is missing.
        404 if not found.
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