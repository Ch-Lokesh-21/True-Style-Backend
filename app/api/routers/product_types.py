"""
Routes for Product Types.
- Thin HTTP layer: parses inputs, applies RBAC, and delegates to the service layer.
"""

from __future__ import annotations
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status, UploadFile, File, Form
from fastapi.responses import JSONResponse

from app.api.deps import require_permission
from app.schemas.object_id import PyObjectId
from app.schemas.product_types import ProductTypesOut
from app.services.product_types import (
    create_item_service,
    list_items_service,
    get_item_service,
    update_item_service,
    delete_item_service,
)

router = APIRouter()


@router.post(
    "/",
    response_model=ProductTypesOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("product_types","Create"))],
)
async def create_item(
    type: str = Form(...),
    size_chart: UploadFile = File(...),
    thumbnail: UploadFile = File(...),
):
    """
    Create a ProductType.

    - Uploads both `size_chart` and `thumbnail` to GridFS.
    - Persists their URLs in the ProductType document.

    Args:
        type: Product type label (e.g., "t-shirt").
        size_chart: Required size chart file.
        thumbnail: Required thumbnail image.

    Returns:
        ProductTypesOut
    """
    return await create_item_service(type=type, size_chart=size_chart, thumbnail=thumbnail)


@router.get("/", response_model=List[ProductTypesOut])
async def list_items(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
):
    """
    List product types with pagination.

    Args:
        skip: Pagination offset.
        limit: Page size.

    Returns:
        List[ProductTypesOut]
    """
    return await list_items_service(skip=skip, limit=limit)


@router.get("/{item_id}", response_model=ProductTypesOut)
async def get_item(item_id: PyObjectId):
    """
    Get a single ProductType by id.

    Args:
        item_id: ProductTypes ObjectId.

    Returns:
        ProductTypesOut

    Raises:
        404 if not found.
    """
    return await get_item_service(item_id)


@router.put(
    "/{item_id}",
    response_model=ProductTypesOut,
    dependencies=[Depends(require_permission("product_types","Update"))],
)
async def update_item(
    item_id: PyObjectId,
    type: Optional[str] = Form(None),
    size_chart: UploadFile = File(None),   # optional in router to show upload control
    thumbnail: UploadFile = File(None),    # optional in router to show upload control
):
    """
    Update a ProductType.

    - Optionally replaces `size_chart` and/or `thumbnail` in GridFS and updates URLs.
    - Updates `type` label if provided.

    Args:
        item_id: ProductTypes ObjectId.
        type: Optional new type label.
        size_chart: Optional new size chart file.
        thumbnail: Optional new thumbnail file.

    Returns:
        ProductTypesOut

    Raises:
        400 if no fields provided.
        404 if not found.
        409 on duplicate key (e.g., type).
    """
    return await update_item_service(
        item_id=item_id,
        type=type,
        size_chart=size_chart,
        thumbnail=thumbnail,
    )


@router.delete(
    "/{item_id}",
    dependencies=[Depends(require_permission("product_types","Delete"))]
)
async def delete_item(item_id: PyObjectId):
    """
    Delete a ProductType if unused; then best-effort cleanup its GridFS files.

    Args:
        item_id: ProductTypes ObjectId.

    Returns:
        JSONResponse({"deleted": True})

    Raises:
        400 if invalid / in-use.
        404 if not found.
    """
    return await delete_item_service(item_id)