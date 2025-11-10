from __future__ import annotations
from typing import List, Optional, Dict, Any

from fastapi import HTTPException, status

from app.schemas.object_id import PyObjectId
from app.schemas.user_roles import UserRolesCreate, UserRolesUpdate, UserRolesOut
from app.crud import user_roles as crud


def _dup_guard(err: Exception, hint: str = "role") -> None:
    msg = str(err)
    if "E11000" in msg:
        # maps dup key errors if you add unique index on role in future
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Duplicate {hint}")


async def create_user_role(payload: UserRolesCreate) -> UserRolesOut:
    try:
        return await crud.create(payload)
    except HTTPException:
        raise
    except Exception as e:
        _dup_guard(e, "role")
        raise HTTPException(status_code=500, detail=f"Failed to create role: {e}")


async def list_user_roles(
    skip: int,
    limit: int,
    role: Optional[str],
) -> List[UserRolesOut]:
    try:
        q: Dict[str, Any] = {}
        if role:
            q["role"] = role
        return await crud.list_all(skip=skip, limit=limit, query=q or None)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list roles: {e}")


async def get_user_role(item_id: PyObjectId) -> UserRolesOut:
    try:
        item = await crud.get_one(item_id)
        if not item:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")
        return item
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get role: {e}")


async def update_user_role(item_id: PyObjectId, payload: UserRolesUpdate) -> UserRolesOut:
    try:
        if not any(v is not None for v in payload.model_dump().values()):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No fields provided for update")
        updated = await crud.update_one(item_id, payload)
        if not updated:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found or not updated")
        return updated
    except HTTPException:
        raise
    except Exception as e:
        _dup_guard(e, "role")
        raise HTTPException(status_code=500, detail=f"Failed to update role: {e}")


async def delete_user_role(item_id: PyObjectId) -> bool:
    try:
        ok = await crud.delete_one(item_id)

        if ok is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid user role ID.")

        if ok is False:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot delete this user role because one or more users are using it.",
            )

        return True
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete role: {e}")