from __future__ import annotations
from typing import List, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import JSONResponse

from app.api.deps import require_permission, get_current_user
from app.schemas.object_id import PyObjectId
from app.schemas.user_address import UserAddressCreate, UserAddressUpdate, UserAddressOut
from app.services.user_address import (
    create_user_address,
    list_user_addresses,
    get_user_address,
    update_user_address,
    delete_user_address,
)

router = APIRouter()  # main.py mounts with: app.include_router(router, prefix="/user-address")


@router.post(
    "/",
    response_model=UserAddressOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("user_address", "Create"))],
)
async def create_item(
    payload: UserAddressCreate,
    current_user: Dict = Depends(get_current_user),
):
    return await create_user_address(payload=payload, current_user=current_user)


@router.get(
    "/",
    response_model=List[UserAddressOut],
    dependencies=[Depends(require_permission("user_address", "Read"))],
)
async def list_items(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    current_user: Dict = Depends(get_current_user),
):
    return await list_user_addresses(skip=skip, limit=limit, current_user=current_user)


@router.get(
    "/{item_id}",
    response_model=UserAddressOut,
    dependencies=[Depends(require_permission("user_address", "Read"))],
)
async def get_item(
    item_id: PyObjectId,
    current_user: Dict = Depends(get_current_user),
):
    return await get_user_address(item_id=item_id, current_user=current_user)


@router.put(
    "/{item_id}",
    response_model=UserAddressOut,
    dependencies=[Depends(require_permission("user_address", "Update"))],
)
async def update_item(
    item_id: PyObjectId,
    payload: UserAddressUpdate,
    current_user: Dict = Depends(get_current_user),
):
    return await update_user_address(item_id=item_id, payload=payload, current_user=current_user)


@router.delete(
    "/{item_id}",
    dependencies=[Depends(require_permission("user_address", "Delete"))],
)
async def delete_item(
    item_id: PyObjectId,
    current_user: Dict = Depends(get_current_user),
):
    ok = await delete_user_address(item_id=item_id, current_user=current_user)
    if ok:
        return JSONResponse(status_code=200, content={"deleted": True})