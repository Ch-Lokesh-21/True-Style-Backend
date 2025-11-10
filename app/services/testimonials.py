"""
Testimonials service layer.

Contains business logic only:
- Validations
- GridFS upload/replace/delete
- CRUD orchestration
- Clean error mapping (dup key → 409)
"""

from __future__ import annotations
from typing import Optional

from fastapi import HTTPException, UploadFile, status
from fastapi.responses import JSONResponse

from app.schemas.object_id import PyObjectId
from app.schemas.testimonials import TestimonialsCreate, TestimonialsUpdate, TestimonialsOut
from app.crud import testimonials as crud
from app.utils.gridfs import upload_image, replace_image, delete_image, _extract_file_id_from_url


def _dup_guard(err: Exception, hint: str = "idx") -> None:
    """
    Map MongoDB duplicate key errors to HTTP 409 (conflict).
    """
    msg = str(err)
    if "E11000" in msg:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Duplicate {hint}.")


async def create_testimonial(idx: int, description: str, image: UploadFile) -> TestimonialsOut:
    """
    Service: create a testimonial.
    Steps:
      - Validate file input
      - Upload image to GridFS
      - Persist document
    """
    try:
        if not image or not image.filename:
            raise HTTPException(status_code=400, detail="Image file is required")

        _, url = await upload_image(image)
        payload = TestimonialsCreate(idx=idx, image_url=url, description=description)
        created = await crud.create(payload)
        if not created:
            raise HTTPException(status_code=500, detail="Failed to persist Testimonial")
        return created
    except HTTPException:
        raise
    except Exception as e:
        _dup_guard(e, "idx")
        raise HTTPException(status_code=500, detail=f"Failed to create Testimonial: {e}")


async def list_testimonials(skip: int, limit: int, sort_by_idx: bool) -> list[TestimonialsOut]:
    """
    Service: list testimonials with optional idx sorting.
    """
    try:
        return await crud.list_all(skip=skip, limit=limit, sort_by_idx=sort_by_idx)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list Testimonials: {e}")


async def get_testimonial(item_id: PyObjectId) -> TestimonialsOut:
    """
    Service: fetch single testimonial.
    """
    try:
        d = await crud.get_one(item_id)
        if not d:
            raise HTTPException(status_code=404, detail="Testimonial not found")
        return d
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get Testimonial: {e}")


async def update_testimonial(
    item_id: PyObjectId,
    idx: Optional[int],
    description: Optional[str],
    image: Optional[UploadFile],
) -> TestimonialsOut:
    """
    Service: update fields and/or replace image in GridFS.
    """
    try:
        current = await crud.get_one(item_id)
        if not current:
            raise HTTPException(status_code=404, detail="Testimonial not found")

        patch = TestimonialsUpdate()

        if image is not None:
            old_id = _extract_file_id_from_url(current.image_url)
            if old_id:
                _, new_url = await replace_image(old_id, image)
            else:
                _, new_url = await upload_image(image)
            patch.image_url = new_url
        if idx is not None:
            patch.idx = idx
        if description is not None:
            patch.description = description

        if not any(v is not None for v in patch.model_dump().values()):
            raise HTTPException(status_code=400, detail="No fields provided for update")

        updated = await crud.update_one(item_id, patch)
        if not updated:
            # (e.g., concurrent delete or conflicting unique idx)
            raise HTTPException(status_code=409, detail="Update failed (possibly duplicate idx).")
        return updated
    except HTTPException:
        raise
    except Exception as e:
        _dup_guard(e, "idx")
        raise HTTPException(status_code=500, detail=f"Failed to update Testimonial: {e}")


async def delete_testimonial(item_id: PyObjectId):
    """
    Service: delete doc first; on success, best-effort delete the GridFS file.
    """
    try:
        current = await crud.get_one(item_id)
        if not current:
            raise HTTPException(status_code=404, detail="Testimonial not found")

        ok = await crud.delete_one(item_id)
        if not ok:
            raise HTTPException(status_code=404, detail="Testimonial not found")

        # Post-commit cleanup; ignore failures
        file_id = _extract_file_id_from_url(current.image_url)
        if file_id:
            try:
                await delete_image(file_id)
            except Exception:
                pass

        return JSONResponse(status_code=200, content={"deleted": True})
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete Testimonial: {e}")