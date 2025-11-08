from __future__ import annotations
from typing import List, Optional, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import JSONResponse

from app.api.deps import require_permission
from app.schemas.object_id import PyObjectId
from app.schemas.occasions import OccasionsCreate, OccasionsUpdate, OccasionsOut
from app.crud import occasions as crud
from app.utils.gridfs import delete_image, _extract_file_id_from_url

router = APIRouter()  # mounted from main.py at /occasions


async def _cleanup_gridfs_urls(urls: list[str]) -> list[str]:
    """Best-effort deletion of GridFS files using their URLs. Returns warnings (non-fatal)."""
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
    response_model=OccasionsOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("occasions", "Create"))]
)
async def create_item(payload: OccasionsCreate):
    try:
        created = await crud.create(payload)
        if not created:
            raise HTTPException(status_code=500, detail="Failed to persist occasion")
        return created
    except HTTPException:
        raise
    except Exception as e:
        if "E11000" in str(e):
            raise HTTPException(status_code=409, detail="Duplicate occasion")
        raise HTTPException(status_code=500, detail=f"Failed to create occasion: {e}")


@router.get("/", response_model=List[OccasionsOut])
async def list_items(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    occasion: Optional[str] = Query(None, description="Filter by exact occasion"),
    q: Optional[str] = Query(None, description="Case-insensitive fuzzy search on occasion"),
):
    try:
        return await crud.list_all(skip=skip, limit=limit,occasion=occasion, q=q)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list occasions: {e}")


@router.get("/{item_id}", response_model=OccasionsOut)
async def get_item(item_id: PyObjectId):
    try:
        item = await crud.get_one(item_id)
        if not item:
            raise HTTPException(status_code=404, detail="Occasion not found")
        return item
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get occasion: {e}")


@router.put(
    "/{item_id}",
    response_model=OccasionsOut,
    dependencies=[Depends(require_permission("occasions", "Update"))]
)
async def update_item(item_id: PyObjectId, payload: OccasionsUpdate):
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
            raise HTTPException(status_code=409, detail="Duplicate occasion")
        raise HTTPException(status_code=500, detail=f"Failed to update occasion: {e}")


@router.delete(
    "/{item_id}",
    dependencies=[Depends(require_permission("occasions", "Delete"))]
)
async def delete_item(item_id: PyObjectId):
    """
    Transactionally delete an occasion and all its products + related documents.
    After commit, best-effort delete all related GridFS files (product thumbnails + product_images).
    """
    try:
        result = await crud.delete_one_cascade(item_id)
        if not result or result["status"] == "not_found":
            raise HTTPException(status_code=404, detail="Occasion not found")
        if result["status"] != "deleted":
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