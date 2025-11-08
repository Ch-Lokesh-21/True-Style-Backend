from __future__ import annotations
from typing import List, Optional, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import JSONResponse

from app.api.deps import require_permission
from app.schemas.object_id import PyObjectId
from app.schemas.return_status import (
    ReturnStatusCreate,
    ReturnStatusUpdate,
    ReturnStatusOut,
)
from app.crud import return_status as crud

router = APIRouter()  # mounted in main.py at /return-status


def _raise_conflict_if_dup(err: Exception, field_hint: Optional[str] = None):
    msg = str(err)
    if "E11000" in msg:
        detail = "Duplicate key." if not field_hint else f"Duplicate {field_hint}."
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=detail)
    raise err


@router.post(
    "/",
    response_model=ReturnStatusOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("return_status", "Create"))],
    responses={
        201: {"description": "Return status created"},
        400: {"description": "Validation error"},
        403: {"description": "Forbidden"},
        409: {"description": "Duplicate"},
        500: {"description": "Server error"},
    },
)
async def create_item(payload: ReturnStatusCreate):
    try:
        return await crud.create(payload)
    except HTTPException:
        raise
    except Exception as e:
        try:
            _raise_conflict_if_dup(e, field_hint="idx or status")
        except Exception as e2:
            raise HTTPException(status_code=500, detail=f"Failed to create return status: {e2}")


@router.get(
    "/",
    response_model=List[ReturnStatusOut],
    dependencies=[Depends(require_permission("return_status", "Read"))],
    responses={
        200: {"description": "List of return statuses"},
        400: {"description": "Validation error"},
        403: {"description": "Forbidden"},
        500: {"description": "Server error"},
    },
)
async def list_items(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    status_q: Optional[str] = Query(None, description="Filter by status"),
):
    try:
        q: Dict[str, Any] = {}
        if status_q:
            q["status"] = status_q
        return await crud.list_all(skip=skip, limit=limit, query=q or None)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list return statuses: {e}")


@router.get(
    "/{item_id}",
    response_model=ReturnStatusOut,
    dependencies=[Depends(require_permission("return_status", "Read"))],
    responses={
        200: {"description": "Return status"},
        403: {"description": "Forbidden"},
        404: {"description": "Not found"},
        500: {"description": "Server error"},
    },
)
async def get_item(item_id: PyObjectId):
    try:
        item = await crud.get_one(item_id)
        if not item:
            raise HTTPException(status_code=404, detail="Return status not found")
        return item
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get return status: {e}")


@router.put(
    "/{item_id}",
    response_model=ReturnStatusOut,
    dependencies=[Depends(require_permission("return_status", "Update"))],
    responses={
        200: {"description": "Updated return status"},
        400: {"description": "Validation error / no fields"},
        403: {"description": "Forbidden"},
        404: {"description": "Not found"},
        409: {"description": "Duplicate"},
        500: {"description": "Server error"},
    },
)
async def update_item(item_id: PyObjectId, payload: ReturnStatusUpdate):
    try:
        if not any(v is not None for v in payload.model_dump().values()):
            raise HTTPException(status_code=400, detail="No fields provided for update")
        updated = await crud.update_one(item_id, payload)
        if not updated:
            raise HTTPException(status_code=404, detail="Return status not found or not updated")
        return updated
    except HTTPException:
        raise
    except Exception as e:
        try:
            _raise_conflict_if_dup(e, field_hint="idx or status")
        except Exception as e2:
            raise HTTPException(status_code=500, detail=f"Failed to update return status: {e2}")


@router.delete(
    "/{item_id}",
    dependencies=[Depends(require_permission("return_status", "Delete"))],
    responses={
        200: {"description": "Deleted"},
        400: {"description": "In use / invalid ID"},
        403: {"description": "Forbidden"},
        404: {"description": "Not found"},
        500: {"description": "Server error"},
    },
)
async def delete_item(item_id: PyObjectId):
    try:
        ok = await crud.delete_one(item_id)

        if ok is None:
            raise HTTPException(status_code=400, detail="Invalid return status ID.")

        if ok is False:
            raise HTTPException(
                status_code=400,
                detail="Cannot delete this return status because one or more returns are using it.",
            )

        return JSONResponse(status_code=200, content={"deleted": True})
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete return status: {e}")