"""
Service layer for Product Types.
- Centralizes business logic, GridFS handling, and error mapping for CRUD ops.
"""

from __future__ import annotations
from typing import List, Optional

from fastapi import HTTPException, status, UploadFile
from fastapi.responses import JSONResponse

from app.schemas.object_id import PyObjectId
from app.schemas.product_types import (
    ProductTypesCreate,
    ProductTypesUpdate,
    ProductTypesOut,
)
from app.crud import product_types as crud
from app.utils.gridfs import upload_image, replace_image, delete_image, _extract_file_id_from_url


async def create_item_service(
    type: str,
    size_chart: UploadFile,
    thumbnail: UploadFile,
) -> ProductTypesOut:
    """
    Create ProductType after uploading required files to GridFS.

    Args:
        type: Product type label.
        size_chart: Required size chart file.
        thumbnail: Required thumbnail image.

    Returns:
        ProductTypesOut

    Raises:
        400 if any required file missing.
        409 on duplicate product type.
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
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Duplicate product type")
        raise HTTPException(status_code=500, detail=f"Failed to create ProductType: {e}")


async def list_items_service(skip: int, limit: int) -> List[ProductTypesOut]:
    """
    List product types with pagination.

    Args:
        skip: Offset.
        limit: Limit.

    Returns:
        List[ProductTypesOut]
    """
    try:
        return await crud.list_all(skip=skip, limit=limit)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list ProductTypes: {e}")


async def get_item_service(item_id: PyObjectId) -> ProductTypesOut:
    """
    Get one ProductType by id.

    Args:
        item_id: ProductTypes ObjectId.

    Returns:
        ProductTypesOut

    Raises:
        404 if not found.
    """
    try:
        d = await crud.get_one(item_id)
        if not d:
            raise HTTPException(status_code=404, detail="ProductType not found")
        return d
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get ProductType: {e}")


async def update_item_service(
    item_id: PyObjectId,
    type: Optional[str] = None,
    size_chart: UploadFile = None,   # optional in service to show upload control in docs
    thumbnail: UploadFile = None,    # optional in service to show upload control in docs
) -> ProductTypesOut:
    """
    Update a ProductType; optionally replace size chart and/or thumbnail in GridFS.

    Args:
        item_id: ProductTypes ObjectId.
        type: Optional new type label.
        size_chart: Optional new size chart file.
        thumbnail: Optional new thumbnail file.

    Returns:
        ProductTypesOut

    Raises:
        400 if no fields provided.
        404 if not found.
        409 on duplicate type.
    """
    try:
        current = await crud.get_one(item_id)
        if not current:
            raise HTTPException(status_code=404, detail="ProductType not found")

        patch = ProductTypesUpdate()

        # Replace size_chart if provided
        if size_chart is not None:
            old_sc_id = _extract_file_id_from_url(current.size_chart_url)
            if old_sc_id:
                _, new_sc_url = await replace_image(old_sc_id, size_chart)
            else:
                _, new_sc_url = await upload_image(size_chart)
            patch.size_chart_url = new_sc_url  # type: ignore[attr-defined]

        # Replace thumbnail if provided
        if thumbnail is not None:
            old_th_id = _extract_file_id_from_url(current.thumbnail_url)
            if old_th_id:
                _, new_th_url = await replace_image(old_th_id, thumbnail)
            else:
                _, new_th_url = await upload_image(thumbnail)
            patch.thumbnail_url = new_th_url  # type: ignore[attr-defined]

        if type is not None:
            patch.type = type

        # Ensure something to update
        if not any(v is not None for v in patch.model_dump().values()):
            raise HTTPException(status_code=400, detail="No fields provided for update")

        updated = await crud.update_one(item_id, patch)
        if not updated:
            # Generic failure path (e.g., concurrent delete)
            raise HTTPException(status_code=409, detail="Update failed")
        return updated
    except HTTPException:
        raise
    except Exception as e:
        msg = str(e)
        if "E11000" in msg:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Duplicate product type")
        raise HTTPException(status_code=500, detail=f"Failed to update ProductType: {e}")


async def delete_item_service(item_id: PyObjectId):
    """
    Delete ProductType if unused; then best-effort cleanup its GridFS files.

    Args:
        item_id: ProductTypes ObjectId.

    Returns:
        JSONResponse({"deleted": True})

    Raises:
        400 if invalid / in-use.
        404 if not found.
    """
    try:
        current = await crud.get_one(item_id)
        if not current:
            raise HTTPException(status_code=404, detail="ProductType not found")

        ok = await crud.delete_one(item_id)
        if ok is None:
            raise HTTPException(status_code=400, detail="Invalid ProductType ID.")
        if ok is False:
            raise HTTPException(
                status_code=400,
                detail="Cannot delete this ProductType because one or more products are using it.",
            )

        # Cleanup files after successful delete
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