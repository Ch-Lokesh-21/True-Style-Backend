from __future__ import annotations
from typing import List, Optional, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import JSONResponse

from app.api.deps import require_permission
from app.schemas.object_id import PyObjectId
from app.schemas.user_status import UserStatusCreate, UserStatusUpdate, UserStatusOut
from app.services.user_status import (
    create_user_status,
    list_user_status,
    get_user_status,
    update_user_status,
    delete_user_status,
)

router = APIRouter()  # mounted with prefix="/user-status"


@router.post(
    "/",
    response_model=UserStatusOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("user_status", "Create"))],
)
async def create_item(payload: UserStatusCreate):
    return await create_user_status(payload)


@router.get(
    "/",
    response_model=List[UserStatusOut],
    dependencies=[Depends(require_permission("user_status", "Read"))],
)
async def list_items(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    status_eq: Optional[str] = Query(None, alias="status", description="Filter by status (exact match)"),
):
    return await list_user_status(skip=skip, limit=limit, status_eq=status_eq)


@router.get(
    "/{item_id}",
    response_model=UserStatusOut,
    dependencies=[Depends(require_permission("user_status", "Read"))],
)
async def get_item(item_id: PyObjectId):
    return await get_user_status(item_id)


@router.put(
    "/{item_id}",
    response_model=UserStatusOut,
    dependencies=[Depends(require_permission("user_status", "Update"))],
)
async def update_item(item_id: PyObjectId, payload: UserStatusUpdate):
    return await update_user_status(item_id=item_id, payload=payload)


@router.delete(
    "/{item_id}",
    dependencies=[Depends(require_permission("user_status", "Delete"))],
)
async def delete_item(item_id: PyObjectId):
    ok = await delete_user_status(item_id)
    if ok:
        return JSONResponse(status_code=200, content={"deleted": True})