from __future__ import annotations
from typing import List, Dict, Any

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import JSONResponse

from app.api.deps import require_permission, get_current_user
from app.schemas.object_id import PyObjectId
from app.schemas.user_address import (
    UserAddressCreate,
    UserAddressUpdate,
    UserAddressOut,
)
from app.crud import user_address as crud

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
    try:
        item_user_id = str(payload.user_id)
        current_user_id = str(current_user.get("user_id", ""))

        if not current_user_id:
            raise HTTPException(status_code=401, detail="Unauthorized")
        if current_user_id != item_user_id:
            raise HTTPException(status_code=403, detail="Forbidden")

        return await crud.create(payload)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to create user address: {e}"
        )


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
    try:
        # enforce scoping to the current user (stored as ObjectId in DB)
        user_oid = ObjectId(str(current_user["user_id"]))
        q: Dict[str, Any] = {"user_id": user_oid}
        return await crud.list_all(skip=skip, limit=limit, query=q)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to list user addresses: {e}"
        )


@router.get(
    "/{item_id}",
    response_model=UserAddressOut,
    dependencies=[Depends(require_permission("user_address", "Read"))],
)
async def get_item(
    item_id: PyObjectId,
    current_user: Dict = Depends(get_current_user),
):
    try:
        item = await crud.get_one(item_id)
        if not item:
            raise HTTPException(status_code=404, detail="User address not found")

        if str(item.user_id) != str(current_user["user_id"]):
            raise HTTPException(status_code=403, detail="Forbidden")

        return item
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get user address: {e}"
        )


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
    try:
        if not any(v is not None for v in payload.model_dump().values()):
            raise HTTPException(status_code=400, detail="No fields provided for update")

        item = await crud.get_one(item_id)
        if not item:
            raise HTTPException(status_code=404, detail="User address not found")

        if str(item.user_id) != str(current_user["user_id"]):
            raise HTTPException(status_code=403, detail="Forbidden")

        updated = await crud.update_one(item_id, payload)
        if not updated:
            raise HTTPException(
                status_code=404, detail="User address not found or not updated"
            )
        return updated
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to update user address: {e}"
        )


@router.delete(
    "/{item_id}",
    dependencies=[Depends(require_permission("user_address", "Delete"))],
)
async def delete_item(
    item_id: PyObjectId,
    current_user: Dict = Depends(get_current_user),
):
    try:
        item = await crud.get_one(item_id)
        if not item:
            raise HTTPException(status_code=404, detail="User address not found")

        if str(item.user_id) != str(current_user["user_id"]):
            raise HTTPException(status_code=403, detail="Forbidden")

        ok = await crud.delete_one(item_id)
        if ok is None or ok is False:
            raise HTTPException(status_code=400, detail="Unable to delete")

        return JSONResponse(status_code=200, content={"deleted": True})
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to delete user address: {e}"
        )