"""
Service layer for Product Images.
- Encapsulates business logic, GridFS handling, and error mapping for CRUD operations.
"""

from __future__ import annotations
from typing import List, Optional

from fastapi import HTTPException, UploadFile, status
from fastapi.responses import JSONResponse

from app.schemas.object_id import PyObjectId
from app.schemas.product_images import (
    ProductImagesCreate,
    ProductImagesUpdate,
    ProductImagesOut,
)
from app.crud import product_images as crud
from app.utils.gridfs import upload_image, replace_image, delete_image, _extract_file_id_from_url


async def create_item_service(product_id: PyObjectId, image: UploadFile) -> ProductImagesOut:
    """
    Create a ProductImages doc after uploading the file to GridFS.

    Args:
        product_id: Target product ObjectId.
        image: Image file (required).

    Returns:
        ProductImagesOut
    """
    try:
        if image is None or image.filename is None:
            raise HTTPException(status_code=400, detail="Image file is required")

        _, url = await upload_image(image)
        payload = ProductImagesCreate(product_id=product_id, image_url=url)
        created = await crud.create(payload)
        if not created:
            raise HTTPException(status_code=500, detail="Failed to persist ProductImages")
        return created
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create ProductImages: {e}")


async def list_items_service(
    skip: int,
    limit: int,
    product_id: Optional[PyObjectId],
) -> List[ProductImagesOut]:
    """
    List ProductImages with optional product filter.

    Args:
        skip: Offset.
        limit: Limit.
        product_id: Optional product id filter.

    Returns:
        List[ProductImagesOut]
    """
    try:
        return await crud.list_all(skip=skip, limit=limit, product_id=product_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list ProductImages: {e}")


async def get_item_service(item_id: PyObjectId) -> ProductImagesOut:
    """
    Get one ProductImages doc by id.

    Args:
        item_id: ProductImages ObjectId.

    Returns:
        ProductImagesOut

    Raises:
        404 if not found.
    """
    try:
        d = await crud.get_one(item_id)
        if not d:
            raise HTTPException(status_code=404, detail="ProductImages not found")
        return d
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get ProductImages: {e}")


async def update_item_service(
    item_id: PyObjectId,
    patch: ProductImagesUpdate,
    image: UploadFile = None,   # optional in service
) -> ProductImagesOut:
    """
    Update `product_id` and/or replace image in GridFS.

    Args:
        item_id: ProductImages ObjectId.
        patch: ProductImagesUpdate containing optional `product_id`.
        image: Optional new image file.

    Returns:
        ProductImagesOut

    Raises:
        400 if no fields provided.
        404 if not found.
    """
    try:
        current = await crud.get_one(item_id)
        if not current:
            raise HTTPException(status_code=404, detail="ProductImages not found")

        # If image provided, replace existing (or upload new if URL has no file id)
        if image is not None:
            old_id = _extract_file_id_from_url(current.image_url)
            if old_id:
                _, new_url = await replace_image(old_id, image)
            else:
                _, new_url = await upload_image(image)
            patch.image_url = new_url  # type: ignore[attr-defined]

        # Ensure something to update
        if not any(v is not None for v in patch.model_dump().values()):
            raise HTTPException(status_code=400, detail="No fields provided for update")

        updated = await crud.update_one(item_id, patch)
        if not updated:
            # (e.g., concurrent delete or optimistic failure path)
            raise HTTPException(status_code=409, detail="Update failed")
        return updated
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update ProductImages: {e}")


async def delete_item_service(item_id: PyObjectId):
    """
    Delete the ProductImages doc and best-effort remove its GridFS file.

    Args:
        item_id: ProductImages ObjectId.

    Returns:
        JSONResponse({"deleted": True})

    Raises:
        404 if not found.
    """
    try:
        current = await crud.get_one(item_id)
        if not current:
            raise HTTPException(status_code=404, detail="ProductImages not found")

        # Delete the doc first (so that if file cleanup fails, data is still removed)
        ok = await crud.delete_one(item_id)
        if not ok:
            raise HTTPException(status_code=400, detail="Unable to delete ProductImages")

        # Best-effort cleanup
        file_id = _extract_file_id_from_url(current.image_url)
        if file_id:
            await delete_image(file_id)

        return JSONResponse(status_code=200, content={"deleted": True})
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete ProductImages: {e}")