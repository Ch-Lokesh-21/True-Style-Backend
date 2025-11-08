from __future__ import annotations
from typing import List, Optional
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException, Query, status, UploadFile, File, Form
from fastapi.responses import JSONResponse

from app.api.deps import user_required, admin_required
from app.schemas.object_id import PyObjectId
from app.schemas.returns import ReturnsCreate, ReturnsUpdate, ReturnsOut
from app.crud import returns as crud
from app.utils.gridfs import upload_image, replace_image, delete_image

router = APIRouter()


def _extract_file_id_from_url(url: Optional[str]) -> Optional[str]:
    """Extract GridFS file_id from URLs like .../files/<id>[?...]."""
    if not url:
        return None
    p = urlparse(url)
    path = p.path or ""
    parts = path.split("/files/", 1)
    if len(parts) != 2 or not parts[1]:
        return None
    return parts[1].split("/")[0]


@router.post(
    "/",
    response_model=ReturnsOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(admin_required)],
)
async def create_item(
    order_id: str = Form(...),
    product_id: str = Form(...),
    return_status_id: int = Form(...),
    user_id: str = Form(...),
    reason: Optional[str] = Form(None),
    amount: Optional[float] = Form(None),
    image: Optional[UploadFile] = File(None),   # optional file upload
    image_url: Optional[str] = Form(None),      # or direct URL
):
    """
    Create return. If an image file is provided, store in GridFS and set image_url accordingly.
    """
    try:
        final_url = image_url
        if image is not None:
            _, final_url = await upload_image(image)

        payload = ReturnsCreate(
            order_id=order_id,
            product_id=product_id,
            return_status_id=return_status_id,
            user_id=user_id,
            reason=reason,
            image_url=final_url,
            amount=amount,
        )
        return await crud.create(payload)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create Return: {e}")


@router.get("/", response_model=List[ReturnsOut], dependencies=[Depends(user_required)])
async def list_items(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
):
    try:
        return await crud.list_all(skip=skip, limit=limit)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list Returns: {e}")


@router.get("/{item_id}", response_model=ReturnsOut, dependencies=[Depends(user_required)])
async def get_item(item_id: PyObjectId):
    try:
        d = await crud.get_one(item_id)
        if not d:
            raise HTTPException(404, "Return not found")
        return d
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get Return: {e}")


@router.put("/{item_id}", response_model=ReturnsOut, dependencies=[Depends(admin_required)])
async def update_item(
    item_id: PyObjectId,
    order_id: Optional[str] = Form(None),
    product_id: Optional[str] = Form(None),
    return_status_id: Optional[int] = Form(None),
    user_id: Optional[str] = Form(None),
    reason: Optional[str] = Form(None),
    amount: Optional[float] = Form(None),
    image: Optional[UploadFile] = File(None),   # optional new file
    image_url: Optional[str] = Form(None),      # or direct URL override
):
    """
    Update return. File upload (if provided) replaces the old GridFS file and updates image_url.
    If only image_url is given, we just update the URL (no GridFS operation).
    """
    try:
        current = await crud.get_one(item_id)
        if not current:
            raise HTTPException(404, "Return not found")

        patch = ReturnsUpdate()

        if image is not None:
            old_id = _extract_file_id_from_url(current.image_url)
            _, new_url = await replace_image(old_id, image)
            patch.image_url = new_url
        elif image_url is not None:
            patch.image_url = image_url

        if order_id is not None:
            patch.order_id = order_id
        if product_id is not None:
            patch.product_id = product_id
        if return_status_id is not None:
            patch.return_status_id = return_status_id
        if user_id is not None:
            patch.user_id = user_id
        if reason is not None:
            patch.reason = reason
        if amount is not None:
            patch.amount = amount

        if not any(v is not None for v in patch.model_dump().values()):
            raise HTTPException(status_code=400, detail="No fields provided for update")

        updated = await crud.update_one(item_id, patch)
        if not updated:
            raise HTTPException(status_code=409, detail="Update failed")
        return updated
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update Return: {e}")


@router.delete("/{item_id}", dependencies=[Depends(admin_required)])
async def delete_item(item_id: PyObjectId):
    try:
        current = await crud.get_one(item_id)
        if not current:
            raise HTTPException(404, "Return not found")

        file_id = _extract_file_id_from_url(current.image_url)
        if file_id:
            await delete_image(file_id)

        ok = await crud.delete_one(item_id)
        if not ok:
            raise HTTPException(404, "Return not found")
        return JSONResponse(status_code=200, content={"deleted": True})
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete Return: {e}")