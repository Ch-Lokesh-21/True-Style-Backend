"""
Service layer for Occasions.
- Owns business rules and coordinates CRUD + cascade deletes.
- Performs best-effort GridFS cleanup for image URLs returned by cascade.
"""

from __future__ import annotations
from typing import List, Optional, Dict, Any

from fastapi import HTTPException, status
from fastapi.responses import JSONResponse

from app.schemas.object_id import PyObjectId
from app.schemas.occasions import OccasionsCreate, OccasionsUpdate, OccasionsOut
from app.crud import occasions as crud
from app.utils.gridfs import delete_image, _extract_file_id_from_url


async def _cleanup_gridfs_urls(urls: list[str]) -> list[str]:
    """
    Best-effort deletion of GridFS files using their URLs.

    Args:
        urls: List of file URLs previously stored in documents.

    Returns:
        list[str]: Warnings for any non-fatal cleanup errors.
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


async def create_item_service(payload: OccasionsCreate) -> OccasionsOut:
    """
    Create a new occasion.

    Args:
        payload: OccasionsCreate

    Returns:
        OccasionsOut

    Raises:
        409 on duplicate (E11000).
    """
    try:
        created = await crud.create(payload)
        if not created:
            raise HTTPException(status_code=500, detail="Failed to persist occasion")
        return created
    except HTTPException:
        raise
    except Exception as e:
        if "E11000" in str(e):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Duplicate occasion")
        raise HTTPException(status_code=500, detail=f"Failed to create occasion: {e}")


async def list_items_service(
    skip: int,
    limit: int,
    occasion: Optional[str],
    q: Optional[str],
) -> List[OccasionsOut]:
    """
    List occasions with pagination and optional filtering.

    Args:
        skip: Offset.
        limit: Limit.
        occasion: Exact match.
        q: Fuzzy/regex search.

    Returns:
        List[OccasionsOut]
    """
    try:
        return await crud.list_all(skip=skip, limit=limit, occasion=occasion, q=q)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list occasions: {e}")


async def get_item_service(item_id: PyObjectId) -> OccasionsOut:
    """
    Get a single occasion by ID.

    Args:
        item_id: Occasion ObjectId.

    Returns:
        OccasionsOut

    Raises:
        404 if not found.
    """
    try:
        item = await crud.get_one(item_id)
        if not item:
            raise HTTPException(status_code=404, detail="Occasion not found")
        return item
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get occasion: {e}")


async def update_item_service(item_id: PyObjectId, payload: OccasionsUpdate) -> OccasionsOut:
    """
    Update an occasion.

    Args:
        item_id: Occasion ObjectId.
        payload: OccasionsUpdate (at least one field must be provided).

    Returns:
        OccasionsOut

    Raises:
        400 if no fields provided.
        404 if not found.
        409 on duplicate.
    """
    try:
        if not any(v is not None for v in payload.model_dump().values()):
            raise HTTPException(status_code=400, detail="No fields provided for update")
        updated = await crud.update_one(item_id, payload)
        if not updated:
            raise HTTPException(status_code=404, detail="Occasion not found")
        return updated
    except HTTPException:
        raise
    except Exception as e:
        if "E11000" in str(e):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Duplicate occasion")
        raise HTTPException(status_code=500, detail=f"Failed to update occasion: {e}")


async def delete_item_service(item_id: PyObjectId):
    """
    Transactionally delete an occasion and related documents; then best-effort cleanup GridFS files.

    Args:
        item_id: Occasion ObjectId.

    Returns:
        JSONResponse({"deleted": True, "stats": {...}, "file_cleanup_warnings": [...]?})
    """
    try:
        result = await crud.delete_one_cascade(item_id)
        if not result or result.get("status") == "not_found":
            raise HTTPException(status_code=404, detail="Occasion not found")
        if result.get("status") != "deleted":
            raise HTTPException(status_code=500, detail="Failed to delete occasion")

        warnings = await _cleanup_gridfs_urls(result.get("image_urls", []))
        payload: Dict[str, Any] = {"deleted": True, "stats": result.get("stats", {})}
        if warnings:
            payload["file_cleanup_warnings"] = warnings
        return JSONResponse(status_code=200, content=payload)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete occasion: {e}")