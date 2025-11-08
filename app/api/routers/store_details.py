from __future__ import annotations
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import JSONResponse

from app.api.deps import require_permission
from app.schemas.object_id import PyObjectId
from app.schemas.store_details import (
    StoreDetailsCreate,
    StoreDetailsUpdate,
    StoreDetailsOut,
)
from app.crud import store_details as crud

router = APIRouter()  # mounted at /store-details


def _raise_conflict_if_dup(err: Exception, field_hint: Optional[str] = None):
    msg = str(err)
    if "E11000" in msg:
        detail = "Duplicate key." if not field_hint else f"Duplicate {field_hint}."
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=detail)
    # not a dup-key → rethrow
    raise err


@router.post(
    "/",
    response_model=StoreDetailsOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("store_details", "Create"))],
    responses={
        201: {"description": "Store details created"},
        400: {"description": "Validation error"},
        403: {"description": "Forbidden"},
        409: {"description": "Duplicate (PAN/GST)"},
        500: {"description": "Server error"},
    },
)
async def create_item(payload: StoreDetailsCreate):
    try:
        return await crud.create(payload)
    except HTTPException:
        raise
    except Exception as e:
        try:
            # if you add unique indexes on pan_no/gst_no, this maps dup errors
            _raise_conflict_if_dup(e, field_hint="PAN or GST")
        except Exception as e2:
            raise HTTPException(status_code=500, detail=f"Failed to create store details: {e2}")


@router.get(
    "/",
    response_model=List[StoreDetailsOut],
    responses={
        200: {"description": "List of store details"},
        403: {"description": "Forbidden"},
        500: {"description": "Server error"},
    },
)
async def list_items(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
):
    try:
        return await crud.list_all(skip=skip, limit=limit)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list store details: {e}")


@router.get(
    "/{item_id}",
    response_model=StoreDetailsOut,
    responses={
        200: {"description": "Store details"},
        403: {"description": "Forbidden"},
        404: {"description": "Not found"},
        500: {"description": "Server error"},
    },
)
async def get_item(item_id: PyObjectId):
    try:
        item = await crud.get_one(item_id)
        if not item:
            raise HTTPException(status_code=404, detail="Store details not found")
        return item
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get store details: {e}")


@router.put(
    "/{item_id}",
    response_model=StoreDetailsOut,
    dependencies=[Depends(require_permission("store_details", "Update"))],
    responses={
        200: {"description": "Updated store details"},
        400: {"description": "Validation error / no fields"},
        403: {"description": "Forbidden"},
        404: {"description": "Not found"},
        409: {"description": "Duplicate (PAN/GST)"},
        500: {"description": "Server error"},
    },
)
async def update_item(item_id: PyObjectId, payload: StoreDetailsUpdate):
    try:
        # guard: reject no-op updates
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


@router.delete(
    "/{item_id}",
    dependencies=[Depends(require_permission("store_details", "Delete"))],
    responses={
        200: {"description": "Deleted"},
        400: {"description": "Invalid ID"},
        403: {"description": "Forbidden"},
        404: {"description": "Not found"},
        500: {"description": "Server error"},
    },
)
async def delete_item(item_id: PyObjectId):
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