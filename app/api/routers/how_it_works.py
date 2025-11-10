"""
Routes for managing How-It-Works entries.
- Parses requests, applies RBAC, and delegates business logic to the service layer.
"""

from __future__ import annotations
from typing import List, Optional

from fastapi import APIRouter, Depends, Query, status, UploadFile, File, Form
from fastapi.responses import JSONResponse

from app.api.deps import require_permission
from app.schemas.object_id import PyObjectId
from app.schemas.how_it_works import HowItWorksUpdate, HowItWorksOut
from app.services.how_it_works import (
    create_item_service,
    list_items_service,
    get_item_service,
    update_item_service,
    delete_item_service,
)

router = APIRouter()


@router.post(
    "/",
    response_model=HowItWorksOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("how_it_works", "Create"))]
)
async def create_item(
    idx: int = Form(...),
    title: str = Form(...),
    image: UploadFile = File(None),
):
    """
    Create a How-It-Works entry.

    Notes:
    - If `image` is provided, it will be streamed to GridFS and `image_url` stored.
    - Business rule: image is required; the service returns 400 if omitted.

    Args:
        idx: Display/index order.
        title: Card title.
        image: Image file to upload (required by business rule).

    Returns:
        HowItWorksOut
    """
    return await create_item_service(idx=idx, title=title, image=image)


@router.get("/", response_model=List[HowItWorksOut])
async def list_items(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    sort_by_idx: bool = Query(True, description="Sort by idx asc; fallback createdAt desc"),
):
    """
    List How-It-Works entries with pagination.

    Args:
        skip: Offset for pagination.
        limit: Page size.
        sort_by_idx: Whether to sort by idx ascending.

    Returns:
        List[HowItWorksOut]
    """
    return await list_items_service(skip=skip, limit=limit, sort_by_idx=sort_by_idx)


@router.get("/{item_id}", response_model=HowItWorksOut)
async def get_item(item_id: PyObjectId):
    """
    Get a single How-It-Works entry by ID.

    Args:
        item_id: ObjectId of the entry.

    Returns:
        HowItWorksOut

    Raises:
        404 if not found.
    """
    return await get_item_service(item_id)


@router.put(
    "/{item_id}",
    response_model=HowItWorksOut,
    dependencies=[Depends(require_permission("how_it_works", "Update"))]
)
async def update_item(
    item_id: PyObjectId,
    idx: Optional[int] = Form(None),
    title: Optional[str] = Form(None),
    image: UploadFile = File(None),
):
    """
    Update `idx`/`title`; if `image` is provided, the old GridFS file is replaced and `image_url` updated.

    Args:
        item_id: Entry ObjectId.
        idx: Optional new display order.
        title: Optional new title.
        image: Optional new image file.

    Returns:
        HowItWorksOut

    Raises:
        400 if no fields provided.
        404 if not found.
        409 on duplicate idx (if unique).
    """
    return await update_item_service(item_id=item_id, idx=idx, title=title, image=image)


@router.delete(
    "/{item_id}",
    dependencies=[Depends(require_permission("how_it_works", "Delete"))]
)
async def delete_item(item_id: PyObjectId):
    """
    Delete an entry and its GridFS image if present.

    Args:
        item_id: Entry ObjectId.

    Returns:
        JSONResponse: {"deleted": True}
    """
    return await delete_item_service(item_id)