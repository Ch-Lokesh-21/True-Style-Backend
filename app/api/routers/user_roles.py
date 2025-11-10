from __future__ import annotations
from typing import List, Optional, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import JSONResponse

from app.api.deps import require_permission
from app.schemas.object_id import PyObjectId
from app.schemas.user_roles import UserRolesCreate, UserRolesUpdate, UserRolesOut
from app.services.user_roles import (
    create_user_role,
    list_user_roles,
    get_user_role,
    update_user_role,
    delete_user_role,
)

router = APIRouter()  # main.py: app.include_router(router, prefix="/user-roles")


@router.post(
    "/",
    response_model=UserRolesOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("user_roles", "Create"))],
)
async def create_item(payload: UserRolesCreate):
    return await create_user_role(payload)


@router.get(
    "/",
    response_model=List[UserRolesOut],
    dependencies=[Depends(require_permission("user_roles", "Read"))],
)
async def list_items(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    role: Optional[str] = Query(None, description="Filter by role (exact match)"),
):
    return await list_user_roles(skip=skip, limit=limit, role=role)


@router.get(
    "/{item_id}",
    response_model=UserRolesOut,
    dependencies=[Depends(require_permission("user_roles", "Read"))],
)
async def get_item(item_id: PyObjectId):
    return await get_user_role(item_id)


@router.put(
    "/{item_id}",
    response_model=UserRolesOut,
    dependencies=[Depends(require_permission("user_roles", "Update"))],
)
async def update_item(item_id: PyObjectId, payload: UserRolesUpdate):
    return await update_user_role(item_id=item_id, payload=payload)


@router.delete(
    "/{item_id}",
    dependencies=[Depends(require_permission("user_roles", "Delete"))],
)
async def delete_item(item_id: PyObjectId):
    ok = await delete_user_role(item_id)
    if ok:
        return JSONResponse(status_code=200, content={"deleted": True})