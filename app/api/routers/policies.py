from __future__ import annotations
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status, UploadFile, File, Form
from fastapi.responses import JSONResponse

from app.api.deps import require_permission
from app.schemas.object_id import PyObjectId
from app.schemas.policies import PoliciesCreate, PoliciesUpdate, PoliciesOut
from app.crud import policies as crud
from app.utils.gridfs import upload_image, replace_image, delete_image, _extract_file_id_from_url

router = APIRouter()

@router.post(
    "/",
    response_model=PoliciesOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("policies","Create"))],
)
async def create_item(
    idx: int = Form(...),
    title: str = Form(...),
    description: str = Form(...),
    image: UploadFile = File(...),
):
    """Create policy: upload image to GridFS and store image_url."""
    try:
        _, url = await upload_image(image)
        payload = PoliciesCreate(idx=idx, image_url=url, description=description, title=title)
        return await crud.create(payload)
    except HTTPException:
        raise
    except Exception as e:
        msg = str(e)
        if "E11000" in msg and "idx" in msg:
            raise HTTPException(status_code=409, detail="Duplicate idx.")
        raise HTTPException(status_code=500, detail=f"Failed to create Policies: {e}")

@router.get("/", response_model=List[PoliciesOut])
async def list_items(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    sort_by_idx: bool = Query(True, description="Sort by idx asc; fallback createdAt desc"),
):
    try:
        return await crud.list_all(skip=skip, limit=limit, sort_by_idx=sort_by_idx)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list Policies: {e}")

@router.get("/{item_id}", response_model=PoliciesOut)
async def get_item(item_id: PyObjectId):
    try:
        d = await crud.get_one(item_id)
        if not d:
            raise HTTPException(404, "Policies not found")
        return d
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get Policies: {e}")

@router.put(
    "/{item_id}",
    response_model=PoliciesOut,
    dependencies=[Depends(require_permission("policies","Update"))],
)
async def update_item(
    item_id: PyObjectId,
    idx: Optional[int] = Form(None),
    title: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    image: UploadFile = File(None),
):
    """
    Update idx/title/description; if image provided, replace it in GridFS and update image_url.
    """
    try:
        current = await crud.get_one(item_id)
        if not current:
            raise HTTPException(404, "Policies not found")

        patch = PoliciesUpdate()
        if image is not None:
            old_id = _extract_file_id_from_url(current.image_url)
            _, new_url = await replace_image(old_id, image)
            patch.image_url = new_url
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
            raise HTTPException(status_code=409, detail="Update failed (possibly duplicate idx).")
        return updated
    except HTTPException:
        raise
    except Exception as e:
        msg = str(e)
        if "E11000" in msg and "idx" in msg:
            raise HTTPException(status_code=409, detail="Duplicate idx.")
        raise HTTPException(status_code=500, detail=f"Failed to update Policies: {e}")

@router.delete("/{item_id}", dependencies=[Depends(require_permission("policies","Delete"))])
async def delete_item(item_id: PyObjectId):
    try:
        current = await crud.get_one(item_id)
        if not current:
            raise HTTPException(404, "Policies not found")

        file_id = _extract_file_id_from_url(current.image_url)
        if file_id:
            await delete_image(file_id)

        ok = await crud.delete_one(item_id)
        if not ok:
            raise HTTPException(404, "Policies not found")
        return JSONResponse(status_code=200, content={"deleted": True})
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete Policies: {e}")