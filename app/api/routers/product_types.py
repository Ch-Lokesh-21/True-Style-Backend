from __future__ import annotations
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status, UploadFile, File, Form
from fastapi.responses import JSONResponse

from app.api.deps import require_permission
from app.schemas.object_id import PyObjectId
from app.schemas.product_types import ProductTypesCreate, ProductTypesUpdate, ProductTypesOut
from app.crud import product_types as crud
from app.utils.gridfs import upload_image, replace_image, delete_image, _extract_file_id_from_url

router = APIRouter()


@router.post(
    "/",
    response_model=ProductTypesOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("product_types","Create"))],
)
async def create_item(
    type: str = Form(...),
    size_chart: UploadFile = File(...),
    thumbnail: UploadFile = File(...),
):
    """
    Create ProductType. Upload both `size_chart` and `thumbnail` to GridFS,
    persist their URLs.
    """
    try:
        if not size_chart or not size_chart.filename:
            raise HTTPException(status_code=400, detail="Size chart file is required")
        if not thumbnail or not thumbnail.filename:
            raise HTTPException(status_code=400, detail="Thumbnail file is required")

        _, size_chart_url = await upload_image(size_chart)
        _, thumbnail_url = await upload_image(thumbnail)

        payload = ProductTypesCreate(
            type=type,
            size_chart_url=size_chart_url,
            thumbnail_url=thumbnail_url,
        )
        created = await crud.create(payload)
        return created
    except HTTPException:
        raise
    except Exception as e:
        msg = str(e)
        if "E11000" in msg:
            # if unique index on type or idx is added later
            raise HTTPException(status_code=409, detail="Duplicate product type")
        raise HTTPException(status_code=500, detail=f"Failed to create ProductType: {e}")


@router.get("/", response_model=List[ProductTypesOut])
async def list_items(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
):
    try:
        return await crud.list_all(skip=skip, limit=limit)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list ProductTypes: {e}")


@router.get("/{item_id}", response_model=ProductTypesOut)
async def get_item(item_id: PyObjectId):
    try:
        d = await crud.get_one(item_id)
        if not d:
            raise HTTPException(404, "ProductType not found")
        return d
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get ProductType: {e}")


@router.put(
    "/{item_id}",
    response_model=ProductTypesOut,
    dependencies=[Depends(require_permission("product_types","Update"))],
)
async def update_item(
    item_id: PyObjectId,
    type: Optional[str] = Form(None),
    size_chart: UploadFile = File(None),
    thumbnail: UploadFile = File(None),
):
    """
    Update ProductType. If new files are provided, replace existing GridFS files and update URLs.
    """
    try:
        current = await crud.get_one(item_id)
        if not current:
            raise HTTPException(404, "ProductType not found")

        patch = ProductTypesUpdate()

        # size_chart replacement
        if size_chart is not None:
            old_id = _extract_file_id_from_url(current.size_chart_url)
            _, new_url = await replace_image(old_id, size_chart) if old_id else await upload_image(size_chart)
            patch.size_chart_url = new_url

        # thumbnail replacement
        if thumbnail is not None:
            old_id = _extract_file_id_from_url(current.thumbnail_url)
            _, new_url = await replace_image(old_id, thumbnail) if old_id else await upload_image(thumbnail)
            patch.thumbnail_url = new_url

        if type is not None:
            patch.type = type

        if not any(v is not None for v in patch.model_dump().values()):
            raise HTTPException(status_code=400, detail="No fields provided for update")

        updated = await crud.update_one(item_id, patch)
        if not updated:
            raise HTTPException(status_code=409, detail="Update failed")
        return updated
    except HTTPException:
        raise
    except Exception as e:
        msg = str(e)
        if "E11000" in msg:
            raise HTTPException(status_code=409, detail="Duplicate product type")
        raise HTTPException(status_code=500, detail=f"Failed to update ProductType: {e}")


@router.delete(
    "/{item_id}",
    dependencies=[Depends(require_permission("product_types","Delete"))]
)
async def delete_item(item_id: PyObjectId):
    """
    Delete ProductType if unused. After delete, best-effort cleanup of GridFS files.
    """
    try:
        current = await crud.get_one(item_id)
        if not current:
            raise HTTPException(404, "ProductType not found")

        ok = await crud.delete_one(item_id)

        if ok is None:
            raise HTTPException(status_code=400, detail="Invalid ProductType ID.")
        if ok is False:
            raise HTTPException(
                status_code=400,
                detail="Cannot delete this ProductType because one or more products are using it."
            )

        # Safe to cleanup files now
        sc_id = _extract_file_id_from_url(current.size_chart_url)
        th_id = _extract_file_id_from_url(current.thumbnail_url)
        if sc_id:
            await delete_image(sc_id)
        if th_id:
            await delete_image(th_id)

        return JSONResponse(status_code=200, content={"deleted": True})
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete ProductType: {e}")