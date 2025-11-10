"""
Service layer for Return Status master.
Contains DB logic, validation, and conflict handling.
"""

from __future__ import annotations
from typing import Optional, Dict, Any, List

from fastapi import HTTPException, status
from fastapi.responses import JSONResponse

from app.schemas.object_id import PyObjectId
from app.schemas.return_status import (
    ReturnStatusCreate,
    ReturnStatusUpdate,
    ReturnStatusOut,
)
from app.crud import return_status as crud


def _raise_conflict_if_dup(err: Exception, field_hint: Optional[str] = None):
    """Convert duplicate key errors into HTTP 409."""
    msg = str(err)
    if "E11000" in msg:
        detail = "Duplicate key." if not field_hint else f"Duplicate {field_hint}."
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=detail)
    raise err


async def create_return_status(payload: ReturnStatusCreate) -> ReturnStatusOut:
    """Create a new return status."""
    try:
        return await crud.create(payload)
    except HTTPException:
        raise
    except Exception as e:
        try:
            _raise_conflict_if_dup(e, field_hint="idx or status")
        except Exception as e2:
            raise HTTPException(status_code=500, detail=f"Failed to create return status: {e2}")


async def list_return_statuses(
    skip: int,
    limit: int,
    status_q: Optional[str]
) -> List[ReturnStatusOut]:
    """List return statuses with optional exact status filter."""
    try:
        q: Dict[str, Any] = {}
        if status_q:
            q["status"] = status_q
        return await crud.list_all(skip=skip, limit=limit, query=q or None)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list return statuses: {e}")


async def get_return_status(item_id: PyObjectId) -> ReturnStatusOut:
    """Fetch one return status by id."""
    try:
        item = await crud.get_one(item_id)
        if not item:
            raise HTTPException(status_code=404, detail="Return status not found")
        return item
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get return status: {e}")


async def update_return_status(item_id: PyObjectId, payload: ReturnStatusUpdate) -> ReturnStatusOut:
    """Update fields in a return status."""
    try:
        if not any(v is not None for v in payload.model_dump().values()):
            raise HTTPException(status_code=400, detail="No fields provided for update")

        updated = await crud.update_one(item_id, payload)
        if not updated:
            raise HTTPException(status_code=404, detail="Return status not found or not updated")
        return updated
    except HTTPException:
        raise
    except Exception as e:
        try:
            _raise_conflict_if_dup(e, field_hint="idx or status")
        except Exception as e2:
            raise HTTPException(status_code=500, detail=f"Failed to update return status: {e2}")


async def delete_return_status(item_id: PyObjectId) -> bool:
    """Delete one return status if not in use."""
    try:
        ok = await crud.delete_one(item_id)

        if ok is None:
            raise HTTPException(status_code=400, detail="Invalid return status ID.")
        if ok is False:
            raise HTTPException(
                status_code=400,
                detail="Cannot delete: return status is used by existing returns.",
            )
        return True
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete return status: {e}")