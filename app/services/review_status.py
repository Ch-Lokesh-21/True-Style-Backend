"""
Service layer for Review Status master.
Holds DB interactions, validations, and conflict handling.
"""

from __future__ import annotations
from typing import Optional, Dict, Any, List

from fastapi import HTTPException, status

from app.schemas.object_id import PyObjectId
from app.schemas.review_status import (
    ReviewStatusCreate,
    ReviewStatusUpdate,
    ReviewStatusOut,
)
from app.crud import review_status as crud


def _raise_conflict_if_dup(err: Exception, field_hint: Optional[str] = None):
    """
    Convert duplicate key errors into HTTP 409 with a helpful message.
    """
    msg = str(err)
    if "E11000" in msg:
        detail = "Duplicate key." if not field_hint else f"Duplicate {field_hint}."
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=detail)
    raise err


async def create_review_status(payload: ReviewStatusCreate) -> ReviewStatusOut:
    """
    Create a new review status.
    """
    try:
        return await crud.create(payload)
    except HTTPException:
        raise
    except Exception as e:
        try:
            _raise_conflict_if_dup(e, field_hint="idx or status")
        except Exception as e2:
            raise HTTPException(status_code=500, detail=f"Failed to create review status: {e2}")


async def list_review_statuses(
    skip: int,
    limit: int,
    status_q: Optional[str],
) -> List[ReviewStatusOut]:
    """
    List review statuses with optional exact status filter.
    """
    try:
        q: Dict[str, Any] = {}
        if status_q:
            q["status"] = status_q
        return await crud.list_all(skip=skip, limit=limit, query=q or None)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list review statuses: {e}")


async def get_review_status(item_id: PyObjectId) -> ReviewStatusOut:
    """
    Fetch one review status by id.
    """
    try:
        item = await crud.get_one(item_id)
        if not item:
            raise HTTPException(status_code=404, detail="Review status not found")
        return item
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get review status: {e}")


async def update_review_status(item_id: PyObjectId, payload: ReviewStatusUpdate) -> ReviewStatusOut:
    """
    Update fields in a review status. Requires at least one field in payload.
    """
    try:
        if not any(v is not None for v in payload.model_dump().values()):
            raise HTTPException(status_code=400, detail="No fields provided for update")

        updated = await crud.update_one(item_id, payload)
        if not updated:
            raise HTTPException(status_code=404, detail="Review status not found or not updated")
        return updated
    except HTTPException:
        raise
    except Exception as e:
        try:
            _raise_conflict_if_dup(e, field_hint="idx or status")
        except Exception as e2:
            raise HTTPException(status_code=500, detail=f"Failed to update review status: {e2}")


async def delete_review_status(item_id: PyObjectId) -> bool:
    """
    Delete one review status. Returns True if deleted.
    - Returns 400 if ID invalid or the status is referenced by reviews.
    - Returns 404 if not found.
    """
    try:
        ok = await crud.delete_one(item_id)

        if ok is None:
            raise HTTPException(status_code=400, detail="Invalid review status ID.")
        if ok is False:
            raise HTTPException(
                status_code=400,
                detail="Cannot delete this review status because one or more reviews are using it.",
            )

        return True
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete review status: {e}")