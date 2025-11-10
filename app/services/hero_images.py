"""
Service layer for Hero Images.
- Handles GridFS image upload/replace/delete and coordinates CRUD operations.
"""

from __future__ import annotations
from typing import List, Optional

from fastapi import HTTPException, UploadFile
from fastapi.responses import JSONResponse

from app.schemas.object_id import PyObjectId
from app.schemas.hero_images import HeroImagesCreate, HeroImagesUpdate, HeroImagesOut
from app.crud import hero_images as crud
from app.utils.gridfs import upload_image, replace_image, delete_image, _extract_file_id_from_url


async def create_item_service(idx: int, image: UploadFile = None) -> HeroImagesOut:
    """
    Create a hero image.

    Rules:
      - Business rule requires an image; if omitted, raises 400.
      - Streams image to GridFS and stores the resulting `image_url`.

    Args:
        idx: Display order.
        image: File to upload (required by business rule).

    Returns:
        HeroImagesOut
    """
    try:
        if image is None:
            raise HTTPException(status_code=400, detail="image is required")

        _, url = await upload_image(image)
        payload = HeroImagesCreate(idx=idx, image_url=url)
        created = await crud.create(payload)
        return created
    except HTTPException:
        raise
    except Exception as e:
        if "E11000" in str(e) and "idx" in str(e):
            raise HTTPException(status_code=409, detail="Duplicate idx.")
        raise HTTPException(status_code=500, detail=f"Failed to create HeroImages: {e}")


async def list_items_service(skip: int, limit: int, sort_by_idx: bool) -> List[HeroImagesOut]:
    """
    List hero images with pagination and optional idx sorting.

    Args:
        skip: Offset.
        limit: Page size.
        sort_by_idx: Whether to sort by idx asc; fallback createdAt desc.

    Returns:
        List[HeroImagesOut]
    """
    try:
        return await crud.list_all(skip=skip, limit=limit, sort_by_idx=sort_by_idx)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list HeroImages: {e}")


async def get_item_service(item_id: PyObjectId) -> HeroImagesOut:
    """
    Get a single hero image by ID.

    Args:
        item_id: ObjectId

    Returns:
        HeroImagesOut

    Raises:
        404 if not found
    """
    try:
        d = await crud.get_one(item_id)
        if not d:
            raise HTTPException(status_code=404, detail="HeroImages not found")
        return d
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get HeroImages: {e}")


async def update_item_service(
    item_id: PyObjectId,
    idx: Optional[int],
    image: UploadFile = None,
) -> HeroImagesOut:
    """
    Update `idx` and/or replace image. If `image` is provided, replace the existing GridFS file.

    Args:
        item_id: Hero image ObjectId
        idx: Optional new idx
        image: Optional new image file

    Returns:
        HeroImagesOut

    Raises:
        400 if no fields provided
        404 if not found
        409 on duplicate idx
    """
    try:
        current = await crud.get_one(item_id)
        if not current:
            raise HTTPException(status_code=404, detail="HeroImages not found")

        patch = HeroImagesUpdate()
        if image is not None:
            old_id = _extract_file_id_from_url(current.image_url)
            if old_id:
                _, new_url = await replace_image(old_id, image)
            else:
                _, new_url = await upload_image(image)
            patch.image_url = new_url  # type: ignore[attr-defined]

        if idx is not None:
            patch.idx = idx

        if not any(v is not None for v in patch.model_dump().values()):
            raise HTTPException(status_code=400, detail="No fields provided for update")

        updated = await crud.update_one(item_id, patch)
        if not updated:
            # either not found or duplicate idx constraint violation surfaced at DB
            raise HTTPException(status_code=409, detail="Update failed (possibly duplicate idx).")
        return updated
    except HTTPException:
        raise
    except Exception as e:
        if "E11000" in str(e) and "idx" in str(e):
            raise HTTPException(status_code=409, detail="Duplicate idx.")
        raise HTTPException(status_code=500, detail=f"Failed to update HeroImages: {e}")


async def delete_item_service(item_id: PyObjectId):
    """
    Delete a hero image and its GridFS file if present.

    Args:
        item_id: Hero image ObjectId

    Returns:
        JSONResponse({"deleted": True})
    """
    try:
        current = await crud.get_one(item_id)
        if not current:
            raise HTTPException(status_code=404, detail="HeroImages not found")

        file_id = _extract_file_id_from_url(current.image_url)
        if file_id:
            await delete_image(file_id)

        ok = await crud.delete_one(item_id)
        if not ok:
            raise HTTPException(status_code=404, detail="HeroImages not found")
        return JSONResponse(status_code=200, content={"deleted": True})
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete HeroImages: {e}")