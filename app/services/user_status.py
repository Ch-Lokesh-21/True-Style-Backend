from __future__ import annotations
from typing import List, Optional, Dict, Any

from fastapi import HTTPException, status

from app.schemas.object_id import PyObjectId
from app.schemas.user_status import UserStatusCreate, UserStatusUpdate, UserStatusOut
from app.crud import user_status as crud


def _raise_conflict_if_dup(err: Exception, field_hint: Optional[str] = None):
    msg = str(err)
    if "E11000" in msg:
        detail = "Duplicate key." if not field_hint else f"Duplicate {field_hint}."
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=detail)
    # not a dup-key → bubble up
    raise err


async def create_user_status(payload: UserStatusCreate) -> UserStatusOut:
    try:
        return await crud.create(payload)
    except HTTPException:
        raise
    except Exception as e:
        try:
            _raise_conflict_if_dup(e, field_hint="idx or status")
        except Exception as e2:
            raise HTTPException(status_code=500, detail=f"Failed to create user status: {e2}")


async def list_user_status(
    skip: int,
    limit: int,
    status_eq: Optional[str],
) -> List[UserStatusOut]:
    try:
        q: Dict[str, Any] = {}
        if status_eq:
            q["status"] = status_eq
        return await crud.list_all(skip=skip, limit=limit, query=q or None)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list user status: {e}")


async def get_user_status(item_id: PyObjectId) -> UserStatusOut:
    try:
        item = await crud.get_one(item_id)
        if not item:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User status not found")
        return item
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get user status: {e}")


async def update_user_status(item_id: PyObjectId, payload: UserStatusUpdate) -> UserStatusOut:
    try:
        if not any(v is not None for v in payload.model_dump().values()):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No fields provided for update")
        updated = await crud.update_one(item_id, payload)
        if not updated:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User status not found or not updated")
        return updated
    except HTTPException:
        raise
    except Exception as e:
        try:
            _raise_conflict_if_dup(e, field_hint="idx or status")
        except Exception as e2:
            raise HTTPException(status_code=500, detail=f"Failed to update user status: {e2}")


async def delete_user_status(item_id: PyObjectId) -> bool:
    try:
        ok = await crud.delete_one(item_id)

        if ok is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid user status ID.")

        if ok is False:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot delete this user status because one or more users are using it.",
            )

        return True
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete user status: {e}")