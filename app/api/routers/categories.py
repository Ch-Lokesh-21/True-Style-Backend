from __future__ import annotations
from typing import List, Optional, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import JSONResponse

from app.api.deps import require_permission
from app.schemas.object_id import PyObjectId
from app.schemas.categories import CategoriesCreate, CategoriesUpdate, CategoriesOut
from app.crud import categories as crud
from app.utils.gridfs import delete_image, _extract_file_id_from_url

router = APIRouter()  # mounted at /categories


async def _cleanup_gridfs_urls(urls: list[str]) -> list[str]:
    """Best-effort GridFS deletions; returns warnings."""
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
    response_model=CategoriesOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("categories", "Create"))],
    responses={
        201: {"description": "Category created"},
        400: {"description": "Validation error"},
        403: {"description": "Forbidden"},
        409: {"description": "Duplicate category"},
        500: {"description": "Server error"},
    },
)
async def create_item(payload: CategoriesCreate):
    try:
        created = await crud.create(payload)
        if not created:
            raise HTTPException(status_code=500, detail="Failed to persist category")
        return created
    except HTTPException:
        raise
    except Exception as e:
        if "E11000" in str(e):
            raise HTTPException(status_code=409, detail="Duplicate category")
        raise HTTPException(status_code=500, detail=f"Failed to create category: {e}")


@router.get(
    "/",
    response_model=List[CategoriesOut],
    responses={
        200: {"description": "List of categories"},
        400: {"description": "Validation error"},
        403: {"description": "Forbidden"},
        500: {"description": "Server error"},
    },
)
async def list_items(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    category: Optional[str] = Query(None, description="Exact match filter"),
    q: Optional[str] = Query(None, description="Case-insensitive fuzzy search"),
):
    try:
        return await crud.list_all(skip=skip, limit=limit, category=category, q=q)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list categories: {e}")


@router.get(
    "/{item_id}",
    response_model=CategoriesOut,
    responses={
        200: {"description": "Category"},
        403: {"description": "Forbidden"},
        404: {"description": "Not found"},
        500: {"description": "Server error"},
    },
)
async def get_item(item_id: PyObjectId):
    try:
        item = await crud.get_one(item_id)
        if not item:
            raise HTTPException(status_code=404, detail="Category not found")
        return item
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get category: {e}")


@router.put(
    "/{item_id}",
    response_model=CategoriesOut,
    dependencies=[Depends(require_permission("categories", "Update"))],
    responses={
        200: {"description": "Updated category"},
        400: {"description": "Validation error / no fields"},
        403: {"description": "Forbidden"},
        404: {"description": "Not found"},
        409: {"description": "Duplicate category"},
        500: {"description": "Server error"},
    },
)
async def update_item(item_id: PyObjectId, payload: CategoriesUpdate):
    try:
        if not any(v is not None for v in payload.model_dump().values()):
            raise HTTPException(status_code=400, detail="No fields provided for update")
        updated = await crud.update_one(item_id, payload)
        if not updated:
            raise HTTPException(status_code=404, detail="Category not found")
        return updated
    except HTTPException:
        raise
    except Exception as e:
        if "E11000" in str(e):
            raise HTTPException(status_code=409, detail="Duplicate category")
        raise HTTPException(status_code=500, detail=f"Failed to update category: {e}")


@router.delete(
    "/{item_id}",
    dependencies=[Depends(require_permission("categories", "Delete"))],
    responses={
        200: {"description": "Deleted"},
        403: {"description": "Forbidden"},
        404: {"description": "Not found"},
        500: {"description": "Server error"},
    },
)
async def delete_item(item_id: PyObjectId):
    """
    Transactionally delete a category and all its products + related documents.
    After commit, best-effort delete all related GridFS files (product thumbnails + product_images).
    """
    try:
        result = await crud.delete_one_cascade(item_id)
        if not result or result["status"] == "not_found":
            raise HTTPException(status_code=404, detail="Category not found")
        if result["status"] != "deleted":
            raise HTTPException(status_code=500, detail="Failed to delete category")

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
        raise HTTPException(status_code=500, detail=f"Failed to delete category: {e}")