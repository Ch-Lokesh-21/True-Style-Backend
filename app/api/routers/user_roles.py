from __future__ import annotations
from typing import List, Optional, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import JSONResponse

from app.api.deps import require_permission
from app.schemas.object_id import PyObjectId
from app.schemas.user_roles import UserRolesCreate, UserRolesUpdate, UserRolesOut
from app.crud import user_roles as crud

router = APIRouter()  # main.py: app.include_router(user_roles.router, prefix="/user-roles")


@router.post(
    "/",
    response_model=UserRolesOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("user_roles", "Create"))],
)
async def create_item(payload: UserRolesCreate):
    try:
        return await crud.create(payload)
    except Exception as e:
        msg = str(e)
        if "E11000" in msg:
            # if you add a unique index on role later
            raise HTTPException(status_code=409, detail="Duplicate role")
        raise HTTPException(status_code=500, detail=f"Failed to create role: {e}")


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
    try:
        q: Dict[str, Any] = {}
        if role:
            q["role"] = role
        return await crud.list_all(skip=skip, limit=limit, query=q or None)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list roles: {e}")


@router.get(
    "/{item_id}",
    response_model=UserRolesOut,
    dependencies=[Depends(require_permission("user_roles", "Read"))],
)
async def get_item(item_id: PyObjectId):
    try:
        item = await crud.get_one(item_id)
        if not item:
            raise HTTPException(status_code=404, detail="Role not found")
        return item
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get role: {e}")


@router.put(
    "/{item_id}",
    response_model=UserRolesOut,
    dependencies=[Depends(require_permission("user_roles", "Update"))],
)
async def update_item(item_id: PyObjectId, payload: UserRolesUpdate):
    try:
        if not any(v is not None for v in payload.model_dump().values()):
            raise HTTPException(status_code=400, detail="No fields provided for update")
        updated = await crud.update_one(item_id, payload)
        if not updated:
            raise HTTPException(status_code=404, detail="Role not found or not updated")
        return updated
    except HTTPException:
        raise
    except Exception as e:
        msg = str(e)
        if "E11000" in msg:
            raise HTTPException(status_code=409, detail="Duplicate role")
        raise HTTPException(status_code=500, detail=f"Failed to update role: {e}")


@router.delete(
    "/{item_id}",
    dependencies=[Depends(require_permission("user_roles", "Delete"))],
)
async def delete_item(item_id: PyObjectId):
    try:
        ok = await crud.delete_one(item_id)

        if ok is None:
            raise HTTPException(status_code=400, detail="Invalid user role ID.")

        if ok is False:
            raise HTTPException(
                status_code=400,
                detail="Cannot delete this user role because one or more users are using it.",
            )

        return JSONResponse(status_code=200, content={"deleted": True})
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete role: {e}")