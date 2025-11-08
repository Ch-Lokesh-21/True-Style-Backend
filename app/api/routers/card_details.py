from __future__ import annotations
from typing import List, Optional, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import JSONResponse

from app.api.deps import admin_required
from app.schemas.object_id import PyObjectId
from app.schemas.card_details import CardDetailsCreate, CardDetailsUpdate, CardDetailsOut
from app.crud import card_details as crud

router = APIRouter()
@router.post(
    "/",
    response_model=CardDetailsOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_item(payload: CardDetailsCreate):
    try:
        created = await crud.create(payload)
        return created
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create card details: {e}")

@router.get(
    "/",
    response_model=List[CardDetailsOut],
)
async def list_items(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    name: Optional[str] = Query(None, description="Filter by card holder name (exact match)"),
):
    try:
        q: Dict[str, Any] | None = {"name": name} if name else None
        return await crud.list_all(skip=skip, limit=limit, query=q)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list card details: {e}")

@router.get(
    "/{item_id}",
    response_model=CardDetailsOut,
)
async def get_item(item_id: PyObjectId):
    try:
        d = await crud.get_one(item_id)
        if not d:
            raise HTTPException(status_code=404, detail="Card details not found")
        return d
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get card details: {e}")

@router.put(
    "/{item_id}",
    response_model=CardDetailsOut,
)
async def update_item(item_id: PyObjectId, payload: CardDetailsUpdate):
    try:
        if not any(v is not None for v in payload.model_dump().values()):
            raise HTTPException(status_code=400, detail="No fields provided for update")
        d = await crud.update_one(item_id, payload)
        if not d:
            raise HTTPException(status_code=404, detail="Card details not found or not updated")
        return d
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update card details: {e}")

@router.delete(
    "/{item_id}",
)
async def delete_item(item_id: PyObjectId):
    try:
        ok = await crud.delete_one(item_id)
        if not ok:
            raise HTTPException(status_code=404, detail="Card details not found")
        return JSONResponse(status_code=200, content={"deleted": True})
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete card details: {e}")