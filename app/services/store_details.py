"""
Service layer for Store Details.

Contains business logic only:
 - calls crud
 - handles duplicate errors
 - returns Pydantic models
"""

from __future__ import annotations
from fastapi import HTTPException, status
from fastapi.responses import JSONResponse
from typing import List, Optional, Dict, Any

from app.schemas.object_id import PyObjectId
from app.schemas.store_details import StoreDetailsCreate, StoreDetailsUpdate, StoreDetailsOut
from app.crud import store_details as crud


def _raise_conflict_if_dup(err: Exception, field_hint: Optional[str] = None):
    """Raise HTTP 409 if Mongo duplicate key error is detected."""
    msg = str(err)
    if "E11000" in msg:
        detail = "Duplicate key." if not field_hint else f"Duplicate {field_hint}."
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=detail)
    raise err


async def create_store_details(payload: StoreDetailsCreate) -> StoreDetailsOut:
    """Service: create store details."""
    try:
        return await crud.create(payload)
    except HTTPException:
        raise
    except Exception as e:
        try:
            _raise_conflict_if_dup(e, field_hint="PAN or GST")
        except Exception as e2:
            raise HTTPException(status_code=500, detail=f"Failed to create store details: {e2}")


async def list_store_details(skip: int, limit: int) -> List[StoreDetailsOut]:
    """Service: list store details."""
    try:
        return await crud.list_all(skip=skip, limit=limit)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list store details: {e}")


async def get_store_details(item_id: PyObjectId) -> StoreDetailsOut:
    """Service: get one store details."""
    try:
        item = await crud.get_one(item_id)
        if not item:
            raise HTTPException(status_code=404, detail="Store details not found")
        return item
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get store details: {e}")


async def update_store_details(item_id: PyObjectId, payload: StoreDetailsUpdate) -> StoreDetailsOut:
    """Service: update store details."""
    try:
        if not any(v is not None for v in payload.model_dump().values()):
            raise HTTPException(status_code=400, detail="No fields provided for update")

        updated = await crud.update_one(item_id, payload)
        if not updated:
            raise HTTPException(status_code=404, detail="Store details not found or not updated")
        return updated
    except HTTPException:
        raise
    except Exception as e:
        try:
            _raise_conflict_if_dup(e, field_hint="PAN or GST")
        except Exception as e2:
            raise HTTPException(status_code=500, detail=f"Failed to update store details: {e2}")


async def delete_store_details(item_id: PyObjectId):
    """Service: delete store details."""
    try:
        ok = await crud.delete_one(item_id)

        if ok is None:
            raise HTTPException(status_code=400, detail="Invalid store details ID.")
        if ok is False:
            raise HTTPException(status_code=404, detail="Store details not found")

        return JSONResponse(status_code=200, content={"deleted": True})
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete store details: {e}")