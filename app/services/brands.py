from __future__ import annotations
from typing import List, Optional, Dict, Any

from fastapi import HTTPException
from fastapi.responses import JSONResponse

from app.schemas.object_id import PyObjectId
from app.schemas.brands import BrandsCreate, BrandsUpdate, BrandsOut
from app.crud import brands as crud
from app.utils.gridfs import delete_image, _extract_file_id_from_url

# -------- helpers --------

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

# -------- services --------

async def create_item_service(payload: BrandsCreate) -> BrandsOut:
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

async def list_items_service(
    skip: int,
    limit: int,
    name: Optional[str],
    q: Optional[str],
) -> List[BrandsOut]:
    try:
        return await crud.list_all(skip=skip, limit=limit, name=name, q=q)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list brands: {e}")

async def get_item_service(item_id: PyObjectId) -> BrandsOut:
    try:
        item = await crud.get_one(item_id)
        if not item:
            raise HTTPException(status_code=404, detail="Brand not found")
        return item
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get brand: {e}")

async def update_item_service(item_id: PyObjectId, payload: BrandsUpdate) -> BrandsOut:
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

async def delete_item_service(item_id: PyObjectId):
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