from __future__ import annotations

from typing import Optional
from fastapi import HTTPException, UploadFile
from fastapi.responses import JSONResponse

from app.schemas.object_id import PyObjectId
from app.schemas.about import AboutCreate, AboutUpdate
from app.crud import about as crud
from app.utils.gridfs import (
    upload_image,
    replace_image,
    delete_image,
    _extract_file_id_from_url,
)


async def create_item_service(idx: int, description: str, image: UploadFile):
    """
    Create an About section entry with image upload to GridFS.

    Args:
        idx (int): Display index.
        description (str): About text content.
        image (UploadFile): Uploaded image file.

    Returns:
        AboutOut: Newly created record.

    Raises:
        HTTPException: 500 if upload or database operation fails.
    """
    try:
        _, url = await upload_image(image)
        payload = AboutCreate(idx=idx, description=description, image_url=url)
        return await crud.create(payload)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create About: {e}")


async def list_items_service(skip: int, limit: int):
    """
    List About entries in paginated form.

    Args:
        skip (int): Number of records to skip.
        limit (int): Max records to return.

    Returns:
        List[AboutOut]: Paginated About entries.

    Raises:
        HTTPException: 500 if listing fails.
    """
    try:
        return await crud.list_all(skip=skip, limit=limit)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list About: {e}")


async def get_item_service(item_id: PyObjectId):
    """
    Retrieve a single About entry by ID.

    Args:
        item_id (PyObjectId): The About record ID.

    Returns:
        AboutOut: The retrieved record.

    Raises:
        HTTPException:
            404 – If not found
            500 – DB failure
    """
    try:
        item = await crud.get_one(item_id)
        if not item:
            raise HTTPException(status_code=404, detail="About not found")
        return item
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get About: {e}")


async def update_item_service(
    item_id: PyObjectId,
    idx: Optional[int] = None,
    description: Optional[str] = None,
    image: UploadFile = None,
):
    """
    Update About entry data. Handles image replacement in GridFS if a new image is provided.

    Args:
        item_id (PyObjectId): Record ID to update.
        idx (Optional[int]): New index (optional).
        description (Optional[str]): Updated text (optional).
        image (UploadFile, optional): New image to replace existing one.

    Returns:
        AboutOut: Updated record.

    Raises:
        HTTPException:
            400 – No valid update fields
            404 – Record not found
            500 – DB or file failure
    """
    try:
        current = await crud.get_one(item_id)
        if not current:
            raise HTTPException(status_code=404, detail="About not found")

        patch_data: dict = {}
        if idx is not None:
            patch_data["idx"] = idx
        if description is not None:
            patch_data["description"] = description

        # Replace or add new image
        if image is not None:
            old_id = _extract_file_id_from_url(current.image_url)
            if old_id:
                _, new_url = await replace_image(old_id, image)
            else:
                _, new_url = await upload_image(image)
            patch_data["image_url"] = new_url

        patch = AboutUpdate(**patch_data)

        if not any(v is not None for v in patch.model_dump().values()):
            raise HTTPException(status_code=400, detail="No fields provided for update")

        updated = await crud.update_one(item_id, patch)
        if not updated:
            raise HTTPException(status_code=404, detail="About not found")
        return updated

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to update About: {e}"
        )


async def delete_item_service(item_id: PyObjectId):
    """
    Delete About entry and remove its GridFS image if present.

    Args:
        item_id (PyObjectId): ID of item to delete.

    Returns:
        JSONResponse: { deleted: True }

    Raises:
        HTTPException:
            404 – If record doesn't exist
            500 – DB or delete error
    """
    try:
        current = await crud.get_one(item_id)
        if not current:
            raise HTTPException(status_code=404, detail="About not found")

        file_id = _extract_file_id_from_url(current.image_url)
        if file_id:
            await delete_image(file_id)

        ok = await crud.delete_one(item_id)
        if not ok:
            raise HTTPException(status_code=404, detail="About not found")

        return JSONResponse(status_code=200, content={"deleted": True})

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to delete About: {e}"
        )