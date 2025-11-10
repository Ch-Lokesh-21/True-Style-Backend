"""
Service layer for Payment Types.
- Centralizes business rules and error mapping for CRUD operations.
"""

from __future__ import annotations
from typing import List, Optional, Dict, Any

from fastapi import HTTPException, status
from fastapi.responses import JSONResponse

from app.schemas.object_id import PyObjectId
from app.schemas.payment_types import (
    PaymentTypesCreate,
    PaymentTypesUpdate,
    PaymentTypesOut,
)
from app.crud import payment_types as crud


def _raise_conflict_if_dup(err: Exception, field_hint: Optional[str] = None):
    """
    Map Mongo duplicate key errors to HTTP 409 Conflict.

    Args:
        err: Original exception.
        field_hint: Optional field name hint (e.g., "idx or type").

    Raises:
        HTTPException(409) when E11000 is detected, otherwise re-raises the original error.
    """
    msg = str(err)
    if "E11000" in msg:
        detail = "Duplicate key." if not field_hint else f"Duplicate {field_hint}."
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=detail)
    raise err


async def create_item_service(payload: PaymentTypesCreate) -> PaymentTypesOut:
    """
    Create a payment type.

    Args:
        payload: PaymentTypesCreate

    Returns:
        PaymentTypesOut

    Raises:
        409 on duplicate (idx or type).
    """
    try:
        return await crud.create(payload)
    except HTTPException:
        raise
    except Exception as e:
        try:
            _raise_conflict_if_dup(e, field_hint="idx or type")
        except Exception as e2:
            raise HTTPException(status_code=500, detail=f"Failed to create payment type: {e2}")


async def list_items_service(
    skip: int,
    limit: int,
    query: Optional[Dict[str, Any]],
) -> List[PaymentTypesOut]:
    """
    List payment types with optional filter.

    Args:
        skip: Offset.
        limit: Limit.
        query: Optional filter dict.

    Returns:
        List[PaymentTypesOut]
    """
    try:
        return await crud.list_all(skip=skip, limit=limit, query=query or None)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list payment types: {e}")


async def get_item_service(item_id: PyObjectId) -> PaymentTypesOut:
    """
    Get a single payment type by id.

    Args:
        item_id: Payment type ObjectId.

    Returns:
        PaymentTypesOut

    Raises:
        404 if not found.
    """
    try:
        item = await crud.get_one(item_id)
        if not item:
            raise HTTPException(status_code=404, detail="Payment type not found")
        return item
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get payment type: {e}")


async def update_item_service(item_id: PyObjectId, payload: PaymentTypesUpdate) -> PaymentTypesOut:
    """
    Update a payment type.

    Args:
        item_id: Payment type ObjectId.
        payload: PaymentTypesUpdate (at least one field must be provided).

    Returns:
        PaymentTypesOut

    Raises:
        400 if no fields provided.
        404 if not found.
        409 on duplicate (idx or type).
    """
    try:
        if not any(v is not None for v in payload.model_dump().values()):
            raise HTTPException(status_code=400, detail="No fields provided for update")
        updated = await crud.update_one(item_id, payload)
        if not updated:
            raise HTTPException(status_code=404, detail="Payment type not found or not updated")
        return updated
    except HTTPException:
        raise
    except Exception as e:
        try:
            _raise_conflict_if_dup(e, field_hint="idx or type")
        except Exception as e2:
            raise HTTPException(status_code=500, detail=f"Failed to update payment type: {e2}")


async def delete_item_service(item_id: PyObjectId):
    """
    Delete a payment type.

    Delete semantics:
      - Returns 400 if ID is invalid (`ok is None`).
      - Returns 400 if the type is being used by one or more payments (`ok is False`).
      - Returns 200 with {"deleted": True} on success.

    Args:
        item_id: Payment type ObjectId.

    Returns:
        JSONResponse({"deleted": True})
    """
    try:
        ok = await crud.delete_one(item_id)

        if ok is None:
            raise HTTPException(status_code=400, detail="Invalid payment type ID.")

        if ok is False:
            raise HTTPException(
                status_code=400,
                detail="Cannot delete this payment type because one or more payments are using it.",
            )

        return JSONResponse(status_code=200, content={"deleted": True})
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete payment type: {e}")