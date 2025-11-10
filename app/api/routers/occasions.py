"""
Routes for managing Occasions.
- Parses requests, applies RBAC, and delegates business logic to the service layer.
"""

from __future__ import annotations
from typing import List, Optional, Dict, Any

from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import JSONResponse

from app.api.deps import require_permission
from app.schemas.object_id import PyObjectId
from app.schemas.occasions import OccasionsCreate, OccasionsUpdate, OccasionsOut
from app.services.occasions import (
    create_item_service,
    list_items_service,
    get_item_service,
    update_item_service,
    delete_item_service,
)

router = APIRouter()  # mounted from main.py at /occasions


@router.post(
    "/",
    response_model=OccasionsOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("occasions", "Create"))]
)
async def create_item(payload: OccasionsCreate):
    """
    Create a new occasion.

    Args:
        payload: OccasionsCreate schema.

    Returns:
        OccasionsOut
    """
    return await create_item_service(payload)


@router.get("/", response_model=List[OccasionsOut])
async def list_items(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    occasion: Optional[str] = Query(None, description="Filter by exact occasion"),
    q: Optional[str] = Query(None, description="Case-insensitive fuzzy search on occasion"),
):
    """
    List occasions with pagination and optional filters.

    Args:
        skip: Pagination offset.
        limit: Page size.
        occasion: Exact match filter.
        q: Fuzzy (regex) search on `occasion`.

    Returns:
        List[OccasionsOut]
    """
    return await list_items_service(skip=skip, limit=limit, occasion=occasion, q=q)


@router.get("/{item_id}", response_model=OccasionsOut)
async def get_item(item_id: PyObjectId):
    """
    Get a single occasion by ID.

    Args:
        item_id: Occasion ObjectId.

    Returns:
        OccasionsOut

    Raises:
        404 if not found.
    """
    return await get_item_service(item_id)


@router.put(
    "/{item_id}",
    response_model=OccasionsOut,
    dependencies=[Depends(require_permission("occasions", "Update"))]
)
async def update_item(item_id: PyObjectId, payload: OccasionsUpdate):
    """
    Update an occasion.

    Args:
        item_id: Occasion ObjectId.
        payload: OccasionsUpdate schema (must contain at least one field).

    Returns:
        OccasionsOut

    Raises:
        400 if no fields provided.
        404 if not found.
        409 on duplicate occasion.
    """
    return await update_item_service(item_id=item_id, payload=payload)


@router.delete(
    "/{item_id}",
    dependencies=[Depends(require_permission("occasions", "Delete"))]
)
async def delete_item(item_id: PyObjectId):
    """
    Transactionally delete an occasion and all its products + related documents.
    After commit, best-effort delete all related GridFS files (product thumbnails + product_images).

    Args:
        item_id: Occasion ObjectId.

    Returns:
        JSONResponse: {"deleted": True, "stats": {...}, "file_cleanup_warnings": [...]?}
    """
    return await delete_item_service(item_id)