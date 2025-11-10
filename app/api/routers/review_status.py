"""
Routes for Review Status master CRUD.
Delegates business logic to the service layer.
"""

from __future__ import annotations
from typing import List, Optional, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import JSONResponse

from app.api.deps import require_permission
from app.schemas.object_id import PyObjectId
from app.schemas.review_status import (
    ReviewStatusCreate,
    ReviewStatusUpdate,
    ReviewStatusOut,
)
from app.services.review_status import (
    create_review_status,
    list_review_statuses,
    get_review_status,
    update_review_status,
    delete_review_status,
)

router = APIRouter()  # mount at /review-status


@router.post(
    "/",
    response_model=ReviewStatusOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("review_status", "Create"))],
    responses={
        201: {"description": "Review status created"},
        400: {"description": "Validation error"},
        403: {"description": "Forbidden"},
        409: {"description": "Duplicate"},
        500: {"description": "Server error"},
    },
)
async def create_item(payload: ReviewStatusCreate):
    """Create a new review status."""
    return await create_review_status(payload)


@router.get(
    "/",
    response_model=List[ReviewStatusOut],
    dependencies=[Depends(require_permission("review_status", "Read"))],
    responses={
        200: {"description": "List of review statuses"},
        400: {"description": "Validation error"},
        403: {"description": "Forbidden"},
        500: {"description": "Server error"},
    },
)
async def list_items(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    status_q: Optional[str] = Query(None, description="Filter by status (exact match)"),
):
    """List review statuses with optional exact-status filter."""
    return await list_review_statuses(skip, limit, status_q)


@router.get(
    "/{item_id}",
    response_model=ReviewStatusOut,
    dependencies=[Depends(require_permission("review_status", "Read"))],
    responses={
        200: {"description": "Review status"},
        403: {"description": "Forbidden"},
        404: {"description": "Not found"},
        500: {"description": "Server error"},
    },
)
async def get_item(item_id: PyObjectId):
    """Get a single review status by id."""
    return await get_review_status(item_id)


@router.put(
    "/{item_id}",
    response_model=ReviewStatusOut,
    dependencies=[Depends(require_permission("review_status", "Update"))],
    responses={
        200: {"description": "Updated review status"},
        400: {"description": "Validation error / no fields"},
        403: {"description": "Forbidden"},
        404: {"description": "Not found"},
        409: {"description": "Duplicate"},
        500: {"description": "Server error"},
    },
)
async def update_item(item_id: PyObjectId, payload: ReviewStatusUpdate):
    """Update fields of a review status."""
    return await update_review_status(item_id, payload)


@router.delete(
    "/{item_id}",
    dependencies=[Depends(require_permission("review_status", "Delete"))],
    responses={
        200: {"description": "Deleted"},
        400: {"description": "In use / invalid ID"},
        403: {"description": "Forbidden"},
        404: {"description": "Not found"},
        500: {"description": "Server error"},
    },
)
async def delete_item(item_id: PyObjectId):
    """Delete a review status (blocked if referenced by reviews)."""
    await delete_review_status(item_id)
    return JSONResponse(status_code=200, content={"deleted": True})