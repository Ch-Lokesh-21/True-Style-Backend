"""
Service layer for Policies.
- Centralizes business logic, GridFS handling, and error mapping for CRUD operations.
"""

from __future__ import annotations
from typing import List, Optional

from fastapi import HTTPException, status, UploadFile
from fastapi.responses import JSONResponse

from app.schemas.object_id import PyObjectId
from app.schemas.policies import PoliciesCreate, PoliciesUpdate, PoliciesOut
from app.crud import policies as crud
from app.utils.gridfs import upload_image, replace_image, delete_image, _extract_file_id_from_url


async def create_item_service(
    idx: int,
    title: str,
    description: str,
    image: UploadFile,
) -> PoliciesOut:
    """
    Create a policy: upload image to GridFS and store image_url.

    Args:
        idx: Display/order index.
        title: Policy title.
        description: Policy description.
        image: File to upload to GridFS.

    Returns:
        PoliciesOut

    Raises:
        409 on duplicate idx (if unique index is enforced).
    """
    try:
        _, url = await upload_image(image)
        payload = PoliciesCreate(idx=idx, image_url=url, description=description, title=title)
        return await crud.create(payload)
    except HTTPException:
        raise
    except Exception as e:
        msg = str(e)
        if "E11000" in msg and "idx" in msg:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Duplicate idx.")
        raise HTTPException(status_code=500, detail=f"Failed to create Policies: {e}")


async def list_items_service(skip: int, limit: int, sort_by_idx: bool) -> List[PoliciesOut]:
    """
    List policies with pagination and sorting.

    Args:
        skip: Offset.
        limit: Limit.
        sort_by_idx: If True, sort by idx ascending; otherwise fallback to createdAt desc.

    Returns:
        List[PoliciesOut]
    """
    try:
        return await crud.list_all(skip=skip, limit=limit, sort_by_idx=sort_by_idx)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list Policies: {e}")


async def get_item_service(item_id: PyObjectId) -> PoliciesOut:
    """
    Get a single policy by id.

    Args:
        item_id: Policy ObjectId.

    Returns:
        PoliciesOut

    Raises:
        404 if not found.
    """
    try:
        d = await crud.get_one(item_id)
        if not d:
            raise HTTPException(status_code=404, detail="Policies not found")
        return d
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get Policies: {e}")


async def update_item_service(
    item_id: PyObjectId,
    idx: Optional[int] = None,
    title: Optional[str] = None,
    description: Optional[str] = None,
    image: UploadFile = None,  # optional in service to show file upload control in docs
) -> PoliciesOut:
    """
    Update idx/title/description; if a new image is provided, replace/upload in GridFS and update image_url.

    Args:
        item_id: Policy ObjectId.
        idx: Optional new idx.
        title: Optional new title.
        description: Optional new description.
        image: Optional new image file.

    Returns:
        PoliciesOut

    Raises:
        400 if no fields provided.
        404 if not found.
        409 on duplicate idx (if unique index).
    """
    try:
        current = await crud.get_one(item_id)
        if not current:
            raise HTTPException(status_code=404, detail="Policies not found")

        patch = PoliciesUpdate()

        if image is not None:
            # Try replacing existing file; if no old file id, upload new
            old_id = _extract_file_id_from_url(current.image_url)
            if old_id:
                _, new_url = await replace_image(old_id, image)
            else:
                _, new_url = await upload_image(image)
            patch.image_url = new_url  # type: ignore[attr-defined]

        if idx is not None:
            patch.idx = idx
        if title is not None:
            patch.title = title
        if description is not None:
            patch.description = description

        if not any(v is not None for v in patch.model_dump().values()):
            raise HTTPException(status_code=400, detail="No fields provided for update")

        updated = await crud.update_one(item_id, patch)
        if not updated:
            # Could be not found or duplicate idx error surfaced as None in CRUD
            raise HTTPException(status_code=409, detail="Update failed (possibly duplicate idx).")
        return updated
    except HTTPException:
        raise
    except Exception as e:
        msg = str(e)
        if "E11000" in msg and "idx" in msg:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Duplicate idx.")
        raise HTTPException(status_code=500, detail=f"Failed to update Policies: {e}")


async def delete_item_service(item_id: PyObjectId):
    """
    Delete a policy; also deletes its GridFS image if present.

    Args:
        item_id: Policy ObjectId.

    Returns:
        JSONResponse({"deleted": True})

    Raises:
        404 if not found.
    """
    try:
        current = await crud.get_one(item_id)
        if not current:
            raise HTTPException(status_code=404, detail="Policies not found")

        file_id = _extract_file_id_from_url(current.image_url)
        if file_id:
            await delete_image(file_id)

        ok = await crud.delete_one(item_id)
        if not ok:
            raise HTTPException(status_code=404, detail="Policies not found")
        return JSONResponse(status_code=200, content={"deleted": True})
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete Policies: {e}")