"""
Service layer for FAQ management.
- Handles GridFS image upload/replace/delete and coordinates CRUD operations.
"""

from __future__ import annotations
from typing import List, Optional

from fastapi import HTTPException, UploadFile, status
from fastapi.responses import JSONResponse

from app.schemas.object_id import PyObjectId
from app.schemas.faq import FaqCreate, FaqUpdate, FaqOut
from app.crud import faq as crud
from app.utils.gridfs import upload_image, replace_image, delete_image, _extract_file_id_from_url


async def create_item_service(
    idx: int,
    question: str,
    answer: str,
    image: UploadFile = None,
) -> FaqOut:
    """
    Create an FAQ entry.

    Rules:
      - Business rule requires an image; if omitted, raises 400.
      - Streams image to GridFS and stores the resulting URL.

    Args:
        idx: Display order.
        question: Question text.
        answer: Answer text.
        image: File to upload (required by business rule).

    Returns:
        FaqOut
    """
    try:
        if image is None:
            raise HTTPException(status_code=400, detail="image is required")

        _, url = await upload_image(image)
        payload = FaqCreate(idx=idx, image_url=url, question=question, answer=answer)
        return await crud.create(payload)
    except HTTPException:
        raise
    except Exception as e:
        msg = str(e)
        if "E11000" in msg and "idx" in msg:
            raise HTTPException(status_code=409, detail="Duplicate idx.")
        raise HTTPException(status_code=500, detail=f"Failed to create FAQ: {e}")


async def list_items_service(skip: int, limit: int, sort_by_idx: bool) -> List[FaqOut]:
    """
    List FAQs with pagination and sorting.

    Args:
        skip: Offset
        limit: Page size
        sort_by_idx: Sort by idx asc; fallback createdAt desc

    Returns:
        List[FaqOut]
    """
    try:
        return await crud.list_all(skip=skip, limit=limit, sort_by_idx=sort_by_idx)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list FAQ: {e}")


async def get_item_service(item_id: PyObjectId) -> FaqOut:
    """
    Get a single FAQ by ID.

    Args:
        item_id: FAQ ObjectId

    Returns:
        FaqOut

    Raises:
        404 if not found
    """
    try:
        d = await crud.get_one(item_id)
        if not d:
            raise HTTPException(status_code=404, detail="FAQ not found")
        return d
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get FAQ: {e}")


async def update_item_service(
    item_id: PyObjectId,
    idx: Optional[int],
    question: Optional[str],
    answer: Optional[str],
    image: UploadFile = None,
) -> FaqOut:
    """
    Update FAQ fields; if image is provided, replace in GridFS and update image_url.

    Args:
        item_id: FAQ ObjectId
        idx: Optional new idx
        question: Optional new question
        answer: Optional new answer
        image: Optional new image file

    Returns:
        FaqOut

    Raises:
        400 if no fields provided
        404 if not found
        409 on duplicate idx
    """
    try:
        current = await crud.get_one(item_id)
        if not current:
            raise HTTPException(status_code=404, detail="FAQ not found")

        patch = FaqUpdate()
        if image is not None:
            old_id = _extract_file_id_from_url(current.image_url)
            if old_id:
                _, new_url = await replace_image(old_id, image)
            else:
                _, new_url = await upload_image(image)
            patch.image_url = new_url  # type: ignore[attr-defined]
        if idx is not None:
            patch.idx = idx
        if question is not None:
            patch.question = question
        if answer is not None:
            patch.answer = answer

        if not any(v is not None for v in patch.model_dump().values()):
            raise HTTPException(status_code=400, detail="No fields provided for update")

        updated = await crud.update_one(item_id, patch)
        if not updated:
            # either not found or duplicate idx unique violation surfaced at DB
            raise HTTPException(status_code=409, detail="Update failed (possibly duplicate idx).")
        return updated
    except HTTPException:
        raise
    except Exception as e:
        msg = str(e)
        if "E11000" in msg and "idx" in msg:
            raise HTTPException(status_code=409, detail="Duplicate idx.")
        raise HTTPException(status_code=500, detail=f"Failed to update FAQ: {e}")


async def delete_item_service(item_id: PyObjectId):
    """
    Delete an FAQ and its GridFS image if present.

    Args:
        item_id: FAQ ObjectId

    Returns:
        JSONResponse({"deleted": True})
    """
    try:
        current = await crud.get_one(item_id)
        if not current:
            raise HTTPException(status_code=404, detail="FAQ not found")

        file_id = _extract_file_id_from_url(current.image_url)
        if file_id:
            await delete_image(file_id)

        ok = await crud.delete_one(item_id)
        if not ok:
            raise HTTPException(status_code=404, detail="FAQ not found")
        return JSONResponse(status_code=200, content={"deleted": True})
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete FAQ: {e}")