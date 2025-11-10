"""
Service layer for Exchange Status.
Contains validation, duplicate handling, and CRUD coordination.
"""

from __future__ import annotations
from typing import List, Optional, Dict, Any

from fastapi import HTTPException, status
from fastapi.responses import JSONResponse

from app.schemas.object_id import PyObjectId
from app.schemas.exchange_status import (
    ExchangeStatusCreate,
    ExchangeStatusUpdate,
    ExchangeStatusOut,
)
from app.crud import exchange_status as crud


def _raise_conflict_if_dup(err: Exception, field_hint: Optional[str] = None):
    """
    Detect Mongo duplicate key errors (E11000) and raise a 409.
    Otherwise rethrow original error.

    Args:
        err: Original exception
        field_hint: Optional field name to refine detail message

    Raises:
        HTTPException 409 if duplicate; otherwise original exception
    """
    msg = str(err)
    if "E11000" in msg:
        detail = "Duplicate key."
        if field_hint:
            detail = f"Duplicate {field_hint}."
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=detail)
    raise err


async def create_item_service(payload: ExchangeStatusCreate) -> ExchangeStatusOut:
    """
    Create a new exchange status.

    Args:
        payload: Creation fields

    Returns:
        ExchangeStatusOut

    Raises:
        HTTPException: 409 on duplicate, 500 otherwise
    """
    try:
        return await crud.create(payload)
    except HTTPException:
        raise
    except Exception as e:
        try:
            _raise_conflict_if_dup(e, field_hint="idx or status")
        except HTTPException:
            raise
        except Exception as e2:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to create exchange status: {e2}",
            )


async def list_items_service(
    skip: int,
    limit: int,
    status_q: Optional[str],
) -> List[ExchangeStatusOut]:
    """
    List exchange statuses with optional exact status filter.

    Args:
        skip: Offset
        limit: Number of items
        status_q: Exact status filter

    Returns:
        List[ExchangeStatusOut]
    """
    try:
        q: Dict[str, Any] = {}
        if status_q:
            q["status"] = status_q
        return await crud.list_all(skip=skip, limit=limit, query=q or None)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list exchange status: {e}")


async def get_item_service(item_id: PyObjectId) -> ExchangeStatusOut:
    """
    Get an exchange status by ID.

    Args:
        item_id: ObjectId

    Returns:
        ExchangeStatusOut

    Raises:
        404 if not found
    """
    try:
        item = await crud.get_one(item_id)
        if not item:
            raise HTTPException(status_code=404, detail="Exchange status not found")
        return item
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get exchange status: {e}")


async def update_item_service(item_id: PyObjectId, payload: ExchangeStatusUpdate) -> ExchangeStatusOut:
    """
    Update an exchange status.

    Args:
        item_id: ObjectId
        payload: Partial fields to update

    Returns:
        ExchangeStatusOut

    Raises:
        400 if no fields
        404 if not found
        409 duplicate
    """
    try:
        if not any(v is not None for v in payload.model_dump().values()):
            raise HTTPException(status_code=400, detail="No fields provided for update")

        updated = await crud.update_one(item_id, payload)
        if not updated:
            raise HTTPException(status_code=404, detail="Exchange status not found or not updated")
        return updated
    except HTTPException:
        raise
    except Exception as e:
        try:
            _raise_conflict_if_dup(e, field_hint="idx or status")
        except HTTPException:
            raise
        except Exception as e2:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to update exchange status: {e2}",
            )


async def delete_item_service(item_id: PyObjectId):
    """
    Delete an exchange status.

    CRUD meanings:
      - None: Not found
      - False: Status is in use (cannot delete)
      - True: Deleted

    Args:
        item_id: ObjectId

    Returns:
        JSONResponse {"deleted": True}
    """
    try:
        ok = await crud.delete_one(item_id)
        if ok is None:
            raise HTTPException(status_code=404, detail="Exchange status not found")
        if ok is False:
            raise HTTPException(status_code=400, detail="Exchange status is being used")
        return JSONResponse(status_code=200, content={"deleted": True})
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete exchange status: {e}",
        )