"""
Routes for Product Images.
- Thin HTTP layer that parses inputs, applies RBAC, and delegates to service functions.
"""

from __future__ import annotations
from typing import List, Optional

from fastapi import APIRouter, Depends, Query, status, UploadFile, File, Form
from fastapi.responses import JSONResponse

from app.api.deps import require_permission
from app.schemas.object_id import PyObjectId
from app.schemas.product_images import ProductImagesOut, ProductImagesUpdate
from app.services.product_images import (
    create_item_service,
    list_items_service,
    get_item_service,
    update_item_service,
    delete_item_service,
)

router = APIRouter()


@router.post(
    "/",
    response_model=ProductImagesOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("product_images", "Create"))],
)
async def create_item(
    product_id: PyObjectId = Form(...),
    image: UploadFile = File(...),
):
    """
    Create a ProductImages document.

    - Streams the file into GridFS and stores `image_url`.
    - `product_id` is validated as an ObjectId by PyObjectId.

    Args:
        product_id: Target product's ObjectId.
        image: Image file to upload (required).

    Returns:
        ProductImagesOut
    """
    return await create_item_service(product_id=product_id, image=image)


@router.get("/", response_model=List[ProductImagesOut])
async def list_items(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    product_id: Optional[PyObjectId] = Query(None, description="Filter by product ObjectId"),
):
    """
    List product images with optional filter by product.

    Args:
        skip: Pagination offset.
        limit: Page size.
        product_id: Optional product filter.

    Returns:
        List[ProductImagesOut]
    """
    return await list_items_service(skip=skip, limit=limit, product_id=product_id)


@router.get("/{item_id}", response_model=ProductImagesOut)
async def get_item(item_id: PyObjectId):
    """
    Get a single ProductImages doc by id.

    Args:
        item_id: ProductImages ObjectId.

    Returns:
        ProductImagesOut

    Raises:
        404 if not found.
    """
    return await get_item_service(item_id)


@router.put(
    "/{item_id}",
    response_model=ProductImagesOut,
    dependencies=[Depends(require_permission("product_images", "Update"))],
)
async def update_item(
    item_id: PyObjectId,
    product_id: Optional[PyObjectId] = Form(None),
    image: UploadFile = File(None),  # show upload control in docs; optional here
):
    """
    Update `product_id` and/or replace the image in GridFS.

    Args:
        item_id: ProductImages ObjectId.
        product_id: Optional new product id.
        image: Optional new image file.

    Returns:
        ProductImagesOut

    Raises:
        400 if no fields provided.
        404 if not found.
        409 on generic update conflict.
    """
    patch = ProductImagesUpdate(product_id=product_id)
    return await update_item_service(item_id=item_id, patch=patch, image=image)


@router.delete(
    "/{item_id}",
    dependencies=[Depends(require_permission("product_images", "Delete"))],
)
async def delete_item(item_id: PyObjectId):
    """
    Delete the ProductImages document and best-effort remove its GridFS file.

    Args:
        item_id: ProductImages ObjectId.

    Returns:
        JSONResponse({"deleted": True})

    Raises:
        404 if not found.
    """
    return await delete_item_service(item_id)