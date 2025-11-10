"""
Service layer for category management.
Contains all business logic, database interaction, and cleanup operations.
"""

from __future__ import annotations
from typing import List, Optional, Dict, Any

from fastapi import HTTPException
from fastapi.responses import JSONResponse

from app.schemas.object_id import PyObjectId
from app.schemas.categories import CategoriesCreate, CategoriesUpdate, CategoriesOut
from app.crud import categories as crud
from app.utils.gridfs import delete_image, _extract_file_id_from_url


async def _cleanup_gridfs_urls(urls: list[str]) -> list[str]:
    """
    Best-effort GridFS deletions; non-crashing operation.

    Args:
        urls (list[str]): List of image URLs to remove.

    Returns:
        list[str]: Warnings for failed deletions.
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


async def create_item_service(payload: CategoriesCreate) -> CategoriesOut:
    """
    Create a category.

    Args:
        payload (CategoriesCreate): Schema containing new category data.

    Returns:
        CategoriesOut: Newly created category.

    Raises:
        HTTPException: 409 for duplicate, 500 on DB error.
    """
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


async def list_items_service(
    skip: int,
    limit: int,
    category: Optional[str],
    q: Optional[str],
) -> List[CategoriesOut]:
    """
    List categories with optional search parameters.

    Args:
        skip (int): Offset
        limit (int): Max items
        category (str): Exact filter
        q (str): Regex search

    Returns:
        List[CategoriesOut]
    """
    try:
        return await crud.list_all(skip=skip, limit=limit, category=category, q=q)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list categories: {e}")


async def get_item_service(item_id: PyObjectId) -> CategoriesOut:
    """
    Get a single category by ID.

    Args:
        item_id (PyObjectId)

    Returns:
        CategoriesOut

    Raises:
        HTTPException: 404 if not found
    """
    try:
        item = await crud.get_one(item_id)
        if not item:
            raise HTTPException(status_code=404, detail="Category not found")
        return item
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get category: {e}")


async def update_item_service(item_id: PyObjectId, payload: CategoriesUpdate) -> CategoriesOut:
    """
    Update a category.

    Args:
        item_id (PyObjectId)
        payload (CategoriesUpdate): Partial update fields.

    Returns:
        CategoriesOut
    """
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


async def delete_item_service(item_id: PyObjectId):
    """
    Delete a category and cascade deletion of dependent products.
    Then perform non-fatal GridFS cleanup of images.

    Args:
        item_id (PyObjectId)

    Returns:
        JSONResponse with deletion status, stats, and optional file cleanup warnings.
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