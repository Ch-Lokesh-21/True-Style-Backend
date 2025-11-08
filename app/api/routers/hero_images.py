from __future__ import annotations
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status, UploadFile, File, Form
from fastapi.responses import JSONResponse

from app.api.deps import require_permission
from app.schemas.object_id import PyObjectId
from app.schemas.hero_images import HeroImagesCreate, HeroImagesUpdate, HeroImagesOut
from app.crud import hero_images as crud
from app.utils.gridfs import upload_image, replace_image, delete_image, _extract_file_id_from_url

router = APIRouter()


@router.post(
    "/",
    response_model=HeroImagesOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("hero_images", "Create"))]
)
async def create_item(
    idx: int = Form(...),
    image: UploadFile = File(...),
):
    """Create hero image: stream file to GridFS and store its image_url."""
    try:
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


@router.get("/", response_model=List[HeroImagesOut])
async def list_items(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    sort_by_idx: bool = Query(True, description="Sort by idx asc; fallback createdAt desc"),
):
    try:
        return await crud.list_all(skip=skip, limit=limit, sort_by_idx=sort_by_idx)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list HeroImages: {e}")


@router.get("/{item_id}", response_model=HeroImagesOut)
async def get_item(item_id: PyObjectId):
    try:
        d = await crud.get_one(item_id)
        if not d:
            raise HTTPException(status_code=404, detail="HeroImages not found")
        return d
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get HeroImages: {e}")


@router.put(
    "/{item_id}",
    response_model=HeroImagesOut,
    dependencies=[Depends(require_permission("hero_images", "Update"))]
)
async def update_item(
    item_id: PyObjectId,
    idx: Optional[int] = Form(None),
    image: UploadFile = File(None),
):
    """
    Update idx and/or replace image. If image provided, upload to GridFS and update image_url.
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
            raise HTTPException(status_code=409, detail="Update failed (possibly duplicate idx).")
        return updated
    except HTTPException:
        raise
    except Exception as e:
        if "E11000" in str(e) and "idx" in str(e):
            raise HTTPException(status_code=409, detail="Duplicate idx.")
        raise HTTPException(status_code=500, detail=f"Failed to update HeroImages: {e}")


@router.delete(
    "/{item_id}",
    dependencies=[Depends(require_permission("hero_images", "Delete"))]
)
async def delete_item(item_id: PyObjectId):
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