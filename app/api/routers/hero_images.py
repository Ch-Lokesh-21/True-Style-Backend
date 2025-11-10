"""
Routes for managing Hero Images.
- Handles request parsing, RBAC, and delegates all logic to the service layer.
"""

from __future__ import annotations
from typing import List, Optional

from fastapi import APIRouter, Depends, Query, status, UploadFile, File, Form
from fastapi.responses import JSONResponse

from app.api.deps import require_permission
from app.schemas.object_id import PyObjectId
from app.schemas.hero_images import HeroImagesUpdate, HeroImagesOut
from app.services.hero_images import (
    create_item_service,
    list_items_service,
    get_item_service,
    update_item_service,
    delete_item_service,
)

router = APIRouter()


@router.post(
    "/",
    response_model=HeroImagesOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("hero_images", "Create"))]
)
async def create_item(
    idx: int = Form(...),
    image: UploadFile = File(None),
):
    """
    Create a hero image.

    Notes:
    - Image (if provided) is streamed to GridFS; resulting `image_url` is stored.
    - Business rule: image is required; service returns 400 if omitted.

    Args:
        idx: Display order.
        image: Image file to upload (required by business rule).

    Returns:
        HeroImagesOut: Newly created hero image.
    """
    return await create_item_service(idx=idx, image=image)


@router.get("/", response_model=List[HeroImagesOut])
async def list_items(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    sort_by_idx: bool = Query(True, description="Sort by idx asc; fallback createdAt desc"),
):
    """
    List hero images with pagination.

    Args:
        skip: Offset for pagination.
        limit: Page size.
        sort_by_idx: Whether to sort by ascending `idx`.

    Returns:
        List[HeroImagesOut]
    """
    return await list_items_service(skip=skip, limit=limit, sort_by_idx=sort_by_idx)


@router.get("/{item_id}", response_model=HeroImagesOut)
async def get_item(item_id: PyObjectId):
    """
    Get a hero image by ID.

    Args:
        item_id: Hero image ObjectId.

    Returns:
        HeroImagesOut

    Raises:
        404 if not found.
    """
    return await get_item_service(item_id)


@router.put(
    "/{item_id}",
    response_model=HeroImagesOut,
    dependencies=[Depends(require_permission("hero_images", "Update"))]
)
async def update_item(
    item_id: PyObjectId,
    idx: Optional[int] = Form(None),
    image: UploadFile = File(None),
):
    """
    Update `idx` and/or replace image.

    If `image` is provided, the old GridFS image is replaced and `image_url` updated.

    Args:
        item_id: Hero image ObjectId.
        idx: Optional new index.
        image: Optional new image file.

    Returns:
        HeroImagesOut

    Raises:
        400 if no fields provided.
        404 if not found.
        409 on duplicate idx (if unique index exists).
    """
    return await update_item_service(item_id=item_id, idx=idx, image=image)


@router.delete(
    "/{item_id}",
    dependencies=[Depends(require_permission("hero_images", "Delete"))]
)
async def delete_item(item_id: PyObjectId):
    """
    Delete a hero image and its GridFS file if present.

    Args:
        item_id: Hero image ObjectId.

    Returns:
        JSONResponse: {"deleted": True}
    """
    return await delete_item_service(item_id)