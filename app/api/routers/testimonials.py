from __future__ import annotations
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status, UploadFile, File, Form
from fastapi.responses import JSONResponse

from app.api.deps import require_permission
from app.schemas.object_id import PyObjectId
from app.schemas.testimonials import TestimonialsCreate, TestimonialsUpdate, TestimonialsOut
from app.crud import testimonials as crud
from app.utils.gridfs import upload_image, replace_image, delete_image, _extract_file_id_from_url

router = APIRouter()


def _dup_guard(e: Exception, hint: str = "idx"):
    msg = str(e)
    if "E11000" in msg:
        raise HTTPException(status_code=409, detail=f"Duplicate {hint}.")


@router.post(
    "/",
    response_model=TestimonialsOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("testimonials","Create"))],
)
async def create_item(
    idx: int = Form(...),
    description: str = Form(...),
    image: UploadFile = File(...),
):
    """Create testimonial: upload image to GridFS and store image_url."""
    try:
        if not image or not image.filename:
            raise HTTPException(status_code=400, detail="Image file is required")

        _, url = await upload_image(image)
        payload = TestimonialsCreate(idx=idx, image_url=url, description=description)
        created = await crud.create(payload)
        return created
    except HTTPException:
        raise
    except Exception as e:
        _dup_guard(e, "idx")
        raise HTTPException(status_code=500, detail=f"Failed to create Testimonial: {e}")


@router.get(
    "/",
    response_model=List[TestimonialsOut],
)
async def list_items(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    sort_by_idx: bool = Query(True, description="Sort by idx asc; fallback createdAt desc"),
):
    try:
        return await crud.list_all(skip=skip, limit=limit, sort_by_idx=sort_by_idx)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list Testimonials: {e}")


@router.get(
    "/{item_id}",
    response_model=TestimonialsOut,
)
async def get_item(item_id: PyObjectId):
    try:
        d = await crud.get_one(item_id)
        if not d:
            raise HTTPException(404, "Testimonial not found")
        return d
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get Testimonial: {e}")


@router.put(
    "/{item_id}",
    response_model=TestimonialsOut,
    dependencies=[Depends(require_permission("testimonials","Update"))],
)
async def update_item(
    item_id: PyObjectId,
    idx: Optional[int] = Form(None),
    description: Optional[str] = Form(None),
    image: UploadFile = File(None),
):
    """
    Update idx/description; if image provided, replace in GridFS and update image_url.
    """
    try:
        current = await crud.get_one(item_id)
        if not current:
            raise HTTPException(404, "Testimonial not found")

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
            raise HTTPException(status_code=409, detail="Update failed (possibly duplicate idx).")
        return updated
    except HTTPException:
        raise
    except Exception as e:
        _dup_guard(e, "idx")
        raise HTTPException(status_code=500, detail=f"Failed to update Testimonial: {e}")


@router.delete(
    "/{item_id}",
    dependencies=[Depends(require_permission("testimonials","Delete"))],
)
async def delete_item(item_id: PyObjectId):
    """
    Delete document first; if successful, best-effort delete the GridFS file.
    """
    try:
        current = await crud.get_one(item_id)
        if not current:
            raise HTTPException(404, "Testimonial not found")

        ok = await crud.delete_one(item_id)
        if not ok:
            raise HTTPException(404, "Testimonial not found")

        # best-effort cleanup (post-commit)
        file_id = _extract_file_id_from_url(current.image_url)
        if file_id:
            try:
                await delete_image(file_id)
            except Exception:
                # swallow cleanup errors
                pass

        return JSONResponse(status_code=200, content={"deleted": True})
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete Testimonial: {e}")