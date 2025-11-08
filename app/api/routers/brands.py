from __future__ import annotations
from typing import List, Optional, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import JSONResponse

from app.api.deps import require_permission
from app.schemas.object_id import PyObjectId
from app.schemas.brands import BrandsCreate, BrandsUpdate, BrandsOut
from app.crud import brands as crud
from app.utils.gridfs import delete_image, _extract_file_id_from_url

router = APIRouter()


async def _cleanup_gridfs_urls(urls: list[str]) -> list[str]:
    """
    Best-effort deletion of GridFS files using their URLs.
    Returns a list of warnings (non-fatal errors).
    """
    warnings: list[str] = []
    for url in urls or []:
        try:
            fid = _extract_file_id_from_url(url)
            if not fid:
                continue
            await delete_image(fid)
        except Exception as ex:
            warnings.append(f"{url}: {ex}")
    return warnings


@router.post(
    "/",
    response_model=BrandsOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("brands", "Create"))],
    responses={
        201: {"description": "Brand created"},
        400: {"description": "Validation error"},
        403: {"description": "Forbidden"},
        409: {"description": "Duplicate brand"},
        500: {"description": "Server error"},
    },
)
async def create_item(payload: BrandsCreate):
    try:
        created = await crud.create(payload)
        if not created:
            raise HTTPException(status_code=500, detail="Failed to persist brand")
        return created
    except HTTPException:
        raise
    except Exception as e:
        msg = str(e)
        if "E11000" in msg:
            raise HTTPException(status_code=409, detail="Duplicate brand")
        raise HTTPException(status_code=500, detail=f"Failed to create brand: {e}")


@router.get(
    "/",
    response_model=List[BrandsOut],
    responses={
        200: {"description": "List of brands"},
        400: {"description": "Validation error"},
        500: {"description": "Server error"},
    },
)
async def list_items(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    name: Optional[str] = Query(None, description="Exact match filter for brand name"),
    q: Optional[str] = Query(None, description="Case-insensitive search on name"),
):
    """List brands with pagination, supports either exact `name` or fuzzy `q` (regex) search."""
    try:
        return await crud.list_all(skip=skip, limit=limit, name=name, q=q)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list brands: {e}")


@router.get(
    "/{item_id}",
    response_model=BrandsOut,
    responses={
        200: {"description": "Brand"},
        404: {"description": "Not found"},
        500: {"description": "Server error"},
    },
)
async def get_item(item_id: PyObjectId):
    try:
        item = await crud.get_one(item_id)
        if not item:
            raise HTTPException(status_code=404, detail="Brand not found")
        return item
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get brand: {e}")


@router.put(
    "/{item_id}",
    response_model=BrandsOut,
    dependencies=[Depends(require_permission("brands", "Update"))],
    responses={
        200: {"description": "Updated brand"},
        400: {"description": "Validation error / no fields"},
        404: {"description": "Not found"},
        409: {"description": "Duplicate brand"},
        500: {"description": "Server error"},
    },
)
async def update_item(item_id: PyObjectId, payload: BrandsUpdate):
    try:
        if not any(v is not None for v in payload.model_dump().values()):
            raise HTTPException(status_code=400, detail="No fields provided for update")

        updated = await crud.update_one(item_id, payload)
        if updated is None:
            raise HTTPException(status_code=404, detail="Brand not found")
        return updated
    except HTTPException:
        raise
    except Exception as e:
        msg = str(e)
        if "E11000" in msg:
            raise HTTPException(status_code=409, detail="Duplicate brand")
        raise HTTPException(status_code=500, detail=f"Failed to update brand: {e}")


@router.delete(
    "/{item_id}",
    dependencies=[Depends(require_permission("brands", "Delete"))],
    responses={
        200: {"description": "Deleted"},
        404: {"description": "Not found"},
        500: {"description": "Server error"},
    },
)
async def delete_item(item_id: PyObjectId):
    """
    Transactionally delete a brand and all its products + related documents.
    After commit, best-effort delete all related GridFS files (product thumbnails + product_images).
    """
    try:
        result = await crud.delete_one_cascade(item_id)
        if not result or result["status"] == "not_found":
            raise HTTPException(status_code=404, detail="Brand not found")
        if result["status"] != "deleted":
            raise HTTPException(status_code=500, detail="Failed to delete brand")

        warnings = await _cleanup_gridfs_urls(result.get("image_urls", []))
        payload: Dict[str, Any] = {
            "deleted": True,
            "stats": result.get("stats", {}),
        }
        if warnings:
            payload["file_cleanup_warnings"] = warnings
        return JSONResponse(status_code=200, content=payload)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete brand: {e}")