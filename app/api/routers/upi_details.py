from __future__ import annotations
from typing import List, Optional, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import JSONResponse

from app.api.deps import user_required, admin_required
from app.schemas.object_id import PyObjectId
from app.schemas.upi_details import UpiDetailsCreate, UpiDetailsUpdate, UpiDetailsOut
from app.crud import upi_details as crud

router = APIRouter()

@router.post(
    "/",
    response_model=UpiDetailsOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_item(payload: UpiDetailsCreate):
    try:
        return await crud.create(payload)
    except Exception as e:
        msg = str(e)
        if "E11000" in msg:
            raise HTTPException(status_code=409, detail="Duplicate UPI details")
        raise HTTPException(status_code=500, detail=f"Failed to create UPI details: {e}")

@router.get(
    "/",
    response_model=List[UpiDetailsOut],
)
async def list_items(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    user_id: Optional[str] = Query(None, description="Filter by user_id"),
    upi_id: Optional[str] = Query(None, description="Filter by UPI ID (exact match)"),
):
    try:
        q: Dict[str, Any] = {}
        if user_id:
            q["user_id"] = user_id
        if upi_id:
            q["upi_id"] = upi_id
        items = await crud.list_all(skip=skip, limit=limit, query=q or None)
        return items
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list UPI details: {e}")

@router.get(
    "/{item_id}",
    response_model=UpiDetailsOut,
)
async def get_item(item_id: PyObjectId):
    try:
        item = await crud.get_one(item_id)
        if not item:
            raise HTTPException(status_code=404, detail="UPI details not found")
        return item
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get UPI details: {e}")

@router.put(
    "/{item_id}",
    response_model=UpiDetailsOut,
)
async def update_item(item_id: PyObjectId, payload: UpiDetailsUpdate):
    try:
        if not any(v is not None for v in payload.model_dump().values()):
            raise HTTPException(status_code=400, detail="No fields provided for update")
        updated = await crud.update_one(item_id, payload)
        if not updated:
            raise HTTPException(status_code=404, detail="UPI details not found or not updated")
        return updated
    except HTTPException:
        raise
    except Exception as e:
        msg = str(e)
        if "E11000" in msg:
            raise HTTPException(status_code=409, detail="Duplicate UPI details")
        raise HTTPException(status_code=500, detail=f"Failed to update UPI details: {e}")

@router.delete(
    "/{item_id}",
)
async def delete_item(item_id: PyObjectId):
    try:
        ok = await crud.delete_one(item_id)
        if not ok:
            raise HTTPException(status_code=404, detail="UPI details not found")
        return JSONResponse(status_code=200, content={"deleted": True})
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete UPI details: {e}")