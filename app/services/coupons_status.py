"""
Service layer for Coupons Status.
Encapsulates business logic, CRUD coordination, and error normalization.
"""

from __future__ import annotations
from typing import List, Optional, Dict, Any

from fastapi import HTTPException, status
from fastapi.responses import JSONResponse

from app.schemas.object_id import PyObjectId
from app.schemas.coupons_status import (
    CouponsStatusCreate,
    CouponsStatusUpdate,
    CouponsStatusOut,
)
from app.crud import coupons_status as crud


def _raise_conflict_if_dup(err: Exception, field_hint: Optional[str] = None) -> None:
    """
    Re-raises HTTP 409 on Mongo duplicate key errors; otherwise re-raises original error.

    Args:
        err: The original exception.
        field_hint: Optional field name to include in the error detail.

    Raises:
        HTTPException: With 409 status if duplicate key detected.
        Exception: The original exception if not a duplicate key error.
    """
    msg = str(err)
    if "E11000" in msg:
        detail = "Duplicate key."
        if field_hint:
            detail = f"Duplicate {field_hint}."
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=detail)
    raise err


async def create_item_service(payload: CouponsStatusCreate) -> CouponsStatusOut:
    """
    Create a coupons status record.

    Args:
        payload: Creation fields.

    Returns:
        CouponsStatusOut: Created record.

    Raises:
        HTTPException:
            - 409 on duplicate.
            - 500 on server error.
    """
    try:
        return await crud.create(payload)
    except HTTPException:
        raise
    except Exception as e:
        try:
            _raise_conflict_if_dup(e, field_hint="status")
        except HTTPException:
            raise
        except Exception as e2:
            raise HTTPException(status_code=500, detail=f"Failed to create coupons status: {e2}")


async def list_items_service(
    skip: int,
    limit: int,
    status_q: Optional[str],
) -> List[CouponsStatusOut]:
    """
    List coupons status records with optional exact status filter.

    Args:
        skip: Pagination offset.
        limit: Page size.
        status_q: Exact status string to filter by.

    Returns:
        List[CouponsStatusOut]
    """
    try:
        q: Dict[str, Any] = {}
        if status_q:
            q["status"] = status_q
        return await crud.list_all(skip=skip, limit=limit, query=q or None)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list coupons status: {e}")


async def get_item_service(item_id: PyObjectId) -> CouponsStatusOut:
    """
    Get a single coupons status record by ID.

    Args:
        item_id: Record ObjectId.

    Returns:
        CouponsStatusOut

    Raises:
        HTTPException:
            - 404 if not found
            - 500 on server error
    """
    try:
        item = await crud.get_one(item_id)
        if not item:
            raise HTTPException(status_code=404, detail="Coupons status not found")
        return item
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get coupons status: {e}")


async def update_item_service(item_id: PyObjectId, payload: CouponsStatusUpdate) -> CouponsStatusOut:
    """
    Update a coupons status record.

    Args:
        item_id: Record ID.
        payload: Partial update fields.

    Returns:
        CouponsStatusOut

    Raises:
        HTTPException:
            - 400 if no fields provided.
            - 404 if not found.
            - 409 on duplicate (idx or status).
            - 500 on server error.
    """
    try:
        if not any(v is not None for v in payload.model_dump().values()):
            raise HTTPException(status_code=400, detail="No fields provided for update")

        updated = await crud.update_one(item_id, payload)
        if not updated:
            raise HTTPException(status_code=404, detail="Coupons status not found or not updated")
        return updated
    except HTTPException:
        raise
    except Exception as e:
        try:
            _raise_conflict_if_dup(e, field_hint="idx or status")
        except HTTPException:
            raise
        except Exception as e2:
            raise HTTPException(status_code=500, detail=f"Failed to update coupons status: {e2}")


async def delete_item_service(item_id: PyObjectId):
    """
    Delete a coupons status record.

    CRUD contract:
      - returns True if deleted
      - returns False if status is referenced by one or more coupons (prevent deletion)
      - returns None for invalid ID (e.g., cast/format issue)

    Args:
        item_id: Record ID.

    Returns:
        JSONResponse: {"deleted": True} on success.

    Raises:
        HTTPException:
            - 400 if invalid ID or status is in use.
            - 500 on server error.
    """
    try:
        ok = await crud.delete_one(item_id)

        if ok is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid coupon status ID.",
            )

        if ok is False:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot delete this status because one or more coupons are using it.",
            )

        return JSONResponse(status_code=200, content={"deleted": True})

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete coupons status: {e}",
        )