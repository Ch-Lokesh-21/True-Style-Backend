"""
Routes for Return Status master CRUD.
Delegates business logic to return_status_service.
"""

from __future__ import annotations
from typing import List, Optional, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import JSONResponse

from app.api.deps import require_permission
from app.schemas.object_id import PyObjectId
from app.schemas.return_status import (
    ReturnStatusCreate,
    ReturnStatusUpdate,
    ReturnStatusOut
)
from app.services.return_status import (
    create_return_status,
    list_return_statuses,
    get_return_status,
    update_return_status,
    delete_return_status,
)

router = APIRouter()  # mounted at /return-status


@router.post(
    "/",
    response_model=ReturnStatusOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("return_status", "Create"))],
)
async def create_item(payload: ReturnStatusCreate):
    """Create new return status."""
    return await create_return_status(payload)


@router.get(
    "/",
    response_model=List[ReturnStatusOut],
    dependencies=[Depends(require_permission("return_status", "Read"))],
)
async def list_items(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    status_q: Optional[str] = Query(None)
):
    """List return statuses with optional filter."""
    return await list_return_statuses(skip, limit, status_q)


@router.get(
    "/{item_id}",
    response_model=ReturnStatusOut,
    dependencies=[Depends(require_permission("return_status", "Read"))],
)
async def get_item(item_id: PyObjectId):
    """Get a single return status by id."""
    return await get_return_status(item_id)


@router.put(
    "/{item_id}",
    response_model=ReturnStatusOut,
    dependencies=[Depends(require_permission("return_status", "Update"))],
)
async def update_item(item_id: PyObjectId, payload: ReturnStatusUpdate):
    """Update a return status."""
    return await update_return_status(item_id, payload)


@router.delete(
    "/{item_id}",
    dependencies=[Depends(require_permission("return_status", "Delete"))],
)
async def delete_item(item_id: PyObjectId):
    """Delete a return status (protected if in use)."""
    ok = await delete_return_status(item_id)
    return JSONResponse(status_code=200, content={"deleted": True})