from __future__ import annotations
from typing import List, Optional, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import JSONResponse

from app.api.deps import require_permission
from app.schemas.object_id import PyObjectId
from app.schemas.exchange_status import (
    ExchangeStatusCreate,
    ExchangeStatusUpdate,
    ExchangeStatusOut,
)
from app.crud import exchange_status as crud

router = APIRouter()  # mounted in main.py at /exchange-status


def _raise_conflict_if_dup(err: Exception, field_hint: Optional[str] = None):
    msg = str(err)
    if "E11000" in msg:
        detail = "Duplicate key."
        if field_hint:
            detail = f"Duplicate {field_hint}."
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=detail)
    raise err


@router.post(
    "/",
    response_model=ExchangeStatusOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("exchange_status", "Create"))]
)
async def create_item(payload: ExchangeStatusCreate):
    try:
        return await crud.create(payload)
    except HTTPException:
        raise
    except Exception as e:
        try:
            _raise_conflict_if_dup(e, field_hint="idx or status")
        except Exception as e2:
            raise HTTPException(status_code=500, detail=f"Failed to create exchange status: {e2}")


@router.get(
    "/",
    response_model=List[ExchangeStatusOut],
    dependencies=[Depends(require_permission("exchange_status", "Read"))]
)
async def list_items(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    status_q: Optional[str] = Query(None, description="Filter by exact status"),
):
    try:
        q: Dict[str, Any] = {}
        if status_q:
            q["status"] = status_q
        return await crud.list_all(skip=skip, limit=limit, query=q or None)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list exchange status: {e}")


@router.get(
    "/{item_id}",
    response_model=ExchangeStatusOut,
    dependencies=[Depends(require_permission("exchange_status", "Read"))]
)
async def get_item(item_id: PyObjectId):
    try:
        item = await crud.get_one(item_id)
        if not item:
            raise HTTPException(status_code=404, detail="Exchange status not found")
        return item
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get exchange status: {e}")


@router.put(
    "/{item_id}",
    response_model=ExchangeStatusOut,
    dependencies=[Depends(require_permission("exchange_status", "Update"))]
)
async def update_item(item_id: PyObjectId, payload: ExchangeStatusUpdate):
    try:
        if not any(v is not None for v in payload.model_dump().values()):
            raise HTTPException(status_code=400, detail="No fields provided for update")

        updated = await crud.update_one(item_id, payload)
        if not updated:
            raise HTTPException(status_code=404, detail="Exchange status not found or not updated")
        return updated
    except HTTPException:
        raise
    except Exception as e:
        try:
            _raise_conflict_if_dup(e, field_hint="idx or status")
        except Exception as e2:
            raise HTTPException(status_code=500, detail=f"Failed to update exchange status: {e2}")


@router.delete(
    "/{item_id}",
    dependencies=[Depends(require_permission("exchange_status", "Delete"))]
)
async def delete_item(item_id: PyObjectId):
    try:
        ok = await crud.delete_one(item_id)
        if ok is None:
            raise HTTPException(status_code=404, detail="Exchange status not found")
        if ok is False:
            raise HTTPException(status_code=400, detail="Exchange status is being used")
        return JSONResponse(status_code=200, content={"deleted": True})
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete exchange status: {e}")