from __future__ import annotations

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status, UploadFile, File, Form
from fastapi.responses import JSONResponse

from app.schemas.object_id import PyObjectId
from app.schemas.about import AboutCreate, AboutUpdate, AboutOut
from app.crud import about as crud
from app.utils.gridfs import upload_image, replace_image, delete_image, _extract_file_id_from_url
from app.api.deps import require_permission

router = APIRouter()

@router.post(
    "/",
    response_model=AboutOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("about", "Create"))]
)
async def create_item(
    idx: int = Form(...),
    description: str = Form(...),
    image: UploadFile = File(...),
):
    try:
        _, url = await upload_image(image)
        payload = AboutCreate(idx=idx, description=description, image_url=url)
        return await crud.create(payload)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create About: {e}")


@router.get("/", response_model=List[AboutOut])
async def list_items(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
):
    try:
        return await crud.list_all(skip=skip, limit=limit)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list About: {e}")


@router.get("/{item_id}", response_model=AboutOut)
async def get_item(item_id: PyObjectId):
    try:
        item = await crud.get_one(item_id)
        if not item:
            raise HTTPException(status_code=404, detail="About not found")
        return item
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get About: {e}")


@router.put(
    "/{item_id}",
    response_model=AboutOut,
    dependencies=[Depends(require_permission("about", "Update"))],
)
async def update_item(
    item_id: PyObjectId,
    idx: Optional[int] = Form(None),
    description: Optional[str] = Form(None),
    image: UploadFile= File(None),
):
    try:
        current = await crud.get_one(item_id)
        if not current:
            raise HTTPException(status_code=404, detail="About not found")

        # Build the patch only with provided fields
        patch_data = {}
        if idx is not None:
            patch_data["idx"] = idx
        if description is not None:
            patch_data["description"] = description

        # Image handling: replace if new image provided; fallback to upload if old id missing
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
        raise HTTPException(status_code=500, detail=f"Failed to update About: {e}")


@router.delete(
    "/{item_id}",
    dependencies=[Depends(require_permission("about", "Delete"))],
)
async def delete_item(item_id: PyObjectId):
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
        raise HTTPException(status_code=500, detail=f"Failed to delete About: {e}")