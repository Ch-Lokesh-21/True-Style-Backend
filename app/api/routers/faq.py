from __future__ import annotations
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status, UploadFile, File, Form
from fastapi.responses import JSONResponse

from app.api.deps import require_permission
from app.schemas.object_id import PyObjectId
from app.schemas.faq import FaqCreate, FaqUpdate, FaqOut
from app.crud import faq as crud
from app.utils.gridfs import upload_image, replace_image, delete_image, _extract_file_id_from_url

router = APIRouter()


@router.post(
    "/",
    response_model=FaqOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("faq","Create"))],
)
async def create_item(
    idx: int = Form(...),
    question: str = Form(...),
    answer: str = Form(...),
    image: UploadFile = File(...),
):
    """Create FAQ: stream image to GridFS, store image_url."""
    try:
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


@router.get("/", response_model=List[FaqOut])
async def list_items(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    sort_by_idx: bool = Query(True, description="Sort by idx asc; fallback createdAt desc"),
):
    try:
        return await crud.list_all(skip=skip, limit=limit, sort_by_idx=sort_by_idx)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list FAQ: {e}")


@router.get("/{item_id}", response_model=FaqOut)
async def get_item(item_id: PyObjectId):
    try:
        d = await crud.get_one(item_id)
        if not d:
            raise HTTPException(status_code=404, detail="FAQ not found")
        return d
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get FAQ: {e}")


@router.put(
    "/{item_id}",
    response_model=FaqOut,
    dependencies=[Depends(require_permission("faq","Update"))],
)
async def update_item(
    item_id: PyObjectId,
    idx: Optional[int] = Form(None),
    question: Optional[str] = Form(None),
    answer: Optional[str] = Form(None),
    image: UploadFile = File(None),
):
    """Update FAQ fields; if image is provided, replace in GridFS and update image_url."""
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
            raise HTTPException(status_code=409, detail="Update failed (possibly duplicate idx).")
        return updated
    except HTTPException:
        raise
    except Exception as e:
        msg = str(e)
        if "E11000" in msg and "idx" in msg:
            raise HTTPException(status_code=409, detail="Duplicate idx.")
        raise HTTPException(status_code=500, detail=f"Failed to update FAQ: {e}")


@router.delete(
    "/{item_id}",
    dependencies=[Depends(require_permission("faq","Delete"))],
)
async def delete_item(item_id: PyObjectId):
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