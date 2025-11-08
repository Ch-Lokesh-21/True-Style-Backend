from __future__ import annotations
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status, UploadFile, File, Form
from fastapi.responses import JSONResponse

from app.api.deps import require_permission
from app.schemas.object_id import PyObjectId
from app.schemas.product_images import (
    ProductImagesCreate,
    ProductImagesUpdate,
    ProductImagesOut,
)
from app.crud import product_images as crud
from app.utils.gridfs import upload_image, replace_image, delete_image, _extract_file_id_from_url

router = APIRouter()


@router.post(
    "/",
    response_model=ProductImagesOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("product_images", "Create"))],
)
async def create_item(
    product_id: PyObjectId = Form(...),
    image: UploadFile = File(...),
):
    """
    Create a ProductImages doc:
      - file is uploaded to GridFS
      - `product_id` is a real ObjectId via PyObjectId
    """
    try:
        if image is None or image.filename is None:
            raise HTTPException(status_code=400, detail="Image file is required")

        _, url = await upload_image(image)
        payload = ProductImagesCreate(product_id=product_id, image_url=url)
        created = await crud.create(payload)
        if not created:
            raise HTTPException(status_code=500, detail="Failed to persist ProductImages")
        return created
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create ProductImages: {e}")


@router.get("/", response_model=List[ProductImagesOut])
async def list_items(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    product_id: Optional[PyObjectId] = Query(None, description="Filter by product ObjectId"),
):
    try:
        return await crud.list_all(skip=skip, limit=limit, product_id=product_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list ProductImages: {e}")


@router.get("/{item_id}", response_model=ProductImagesOut)
async def get_item(item_id: PyObjectId):
    try:
        d = await crud.get_one(item_id)
        if not d:
            raise HTTPException(status_code=404, detail="ProductImages not found")
        return d
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get ProductImages: {e}")


@router.put(
    "/{item_id}",
    response_model=ProductImagesOut,
    dependencies=[Depends(require_permission("product_images", "Update"))],
)
async def update_item(
    item_id: PyObjectId,
    product_id: Optional[PyObjectId] = Form(None),
    image: UploadFile = File(None),
):
    """
    Update `product_id` (real ObjectId) and/or replace image in GridFS.
    """
    try:
        current = await crud.get_one(item_id)
        if not current:
            raise HTTPException(status_code=404, detail="ProductImages not found")

        patch = ProductImagesUpdate()

        if product_id is not None:
            patch.product_id = product_id

        if image is not None:
            old_id = _extract_file_id_from_url(current.image_url)
            if old_id:
                _, new_url = await replace_image(old_id, image)
            else:
                _, new_url = await upload_image(image)
            patch.image_url = new_url

        if not any(v is not None for v in patch.model_dump().values()):
            raise HTTPException(status_code=400, detail="No fields provided for update")

        updated = await crud.update_one(item_id, patch)
        if not updated:
            # (e.g., concurrent delete)
            raise HTTPException(status_code=409, detail="Update failed")
        return updated
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update ProductImages: {e}")


@router.delete(
    "/{item_id}",
    dependencies=[Depends(require_permission("product_images", "Delete"))],
)
async def delete_item(item_id: PyObjectId):
    """
    Delete the document and best-effort remove the GridFS file afterwards.
    """
    try:
        current = await crud.get_one(item_id)
        if not current:
            raise HTTPException(status_code=404, detail="ProductImages not found")

        ok = await crud.delete_one(item_id)
        if not ok:
            raise HTTPException(status_code=400, detail="Unable to delete ProductImages")

        file_id = _extract_file_id_from_url(current.image_url)
        if file_id:
            await delete_image(file_id)

        return JSONResponse(status_code=200, content={"deleted": True})
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete ProductImages: {e}")