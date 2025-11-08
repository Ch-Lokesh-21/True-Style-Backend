# app/api/routes/cards_1.py
from __future__ import annotations
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status, UploadFile, File, Form
from fastapi.responses import JSONResponse

from app.api.deps import require_permission
from app.schemas.object_id import PyObjectId
from app.schemas.cards_1 import Cards1Create, Cards1Update, Cards1Out
from app.crud import cards_1 as crud
from app.utils.gridfs import upload_image, replace_image, delete_image, _extract_file_id_from_url

router = APIRouter()


@router.post(
    "/",
    response_model=Cards1Out,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("cards_1", "Create"))]
)
async def create_item(
    idx: int = Form(...),
    title: str = Form(...),
    image: UploadFile = File(...),
):
    """
    Create a new Cards1 item. Image is streamed into GridFS; image_url is stored.
    """
    try:
        _, url = await upload_image(image)
        payload = Cards1Create(idx=idx, title=title, image_url=url)
        return await crud.create(payload)
    except HTTPException:
        raise
    except Exception as e:
        msg = str(e)
        if "E11000" in msg and "idx" in msg:
            raise HTTPException(status_code=409, detail="Duplicate idx.")
        raise HTTPException(status_code=500, detail=f"Failed to create Cards1: {e}")


@router.get("/", response_model=List[Cards1Out])
async def list_items(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    sort_by_idx: bool = Query(True, description="Sort by idx asc; fallback createdAt desc"),
):
    try:
        return await crud.list_all(skip=skip, limit=limit, sort_by_idx=sort_by_idx)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list Cards1: {e}")


@router.get("/{item_id}", response_model=Cards1Out)
async def get_item(item_id: PyObjectId):
    try:
        d = await crud.get_one(item_id)
        if not d:
            raise HTTPException(status_code=404, detail="Cards1 not found")
        return d
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get Cards1: {e}")


@router.put(
    "/{item_id}",
    response_model=Cards1Out,
    dependencies=[Depends(require_permission("cards_1", "Update"))]
)
async def update_item(
    item_id: PyObjectId,
    idx: Optional[int] = Form(None),
    title: Optional[str] = Form(None),
    image: UploadFile = File(None),
):
    """
    Update fields; if image is provided, replace it in GridFS and update image_url.
    """
    try:
        current = await crud.get_one(item_id)
        if not current:
            raise HTTPException(status_code=404, detail="Cards1 not found")

        patch = Cards1Update()
        if image is not None:
            old_id = _extract_file_id_from_url(current.image_url)
            if old_id:
                _, new_url = await replace_image(old_id, image)
            else:
                # fallback: if old file id not parseable, just upload
                _, new_url = await upload_image(image)
            patch.image_url = new_url  # type: ignore[attr-defined]

        if idx is not None:
            patch.idx = idx
        if title is not None:
            patch.title = title

        if not any(v is not None for v in patch.model_dump().values()):
            raise HTTPException(status_code=400, detail="No fields provided for update")

        updated = await crud.update_one(item_id, patch)
        if not updated:
            # could be not found or duplicate idx in unique index
            raise HTTPException(status_code=409, detail="Update failed (possibly duplicate idx).")
        return updated
    except HTTPException:
        raise
    except Exception as e:
        msg = str(e)
        if "E11000" in msg and "idx" in msg:
            raise HTTPException(status_code=409, detail="Duplicate idx.")
        raise HTTPException(status_code=500, detail=f"Failed to update Cards1: {e}")


@router.delete(
    "/{item_id}",
    dependencies=[Depends(require_permission("cards_1", "Delete"))]
)
async def delete_item(item_id: PyObjectId):
    try:
        current = await crud.get_one(item_id)
        if not current:
            raise HTTPException(status_code=404, detail="Cards1 not found")

        file_id = _extract_file_id_from_url(current.image_url)
        if file_id:
            await delete_image(file_id)

        ok = await crud.delete_one(item_id)
        if not ok:
            raise HTTPException(status_code=404, detail="Cards1 not found")
        return JSONResponse(status_code=200, content={"deleted": True})
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete Cards1: {e}")