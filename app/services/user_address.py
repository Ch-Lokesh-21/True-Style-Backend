from __future__ import annotations
from typing import List, Dict, Any

from bson import ObjectId
from fastapi import HTTPException, status

from app.schemas.object_id import PyObjectId
from app.schemas.user_address import UserAddressCreate, UserAddressUpdate, UserAddressOut
from app.crud import user_address as crud


async def create_user_address(payload: UserAddressCreate, current_user: Dict) -> UserAddressOut:
    try:
        item_user_id = str(payload.user_id)
        current_user_id = str(current_user.get("user_id", ""))

        if not current_user_id:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")
        if current_user_id != item_user_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

        return await crud.create(payload)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create user address: {e}")


async def list_user_addresses(skip: int, limit: int, current_user: Dict) -> List[UserAddressOut]:
    try:
        user_oid = ObjectId(str(current_user["user_id"]))
        q: Dict[str, Any] = {"user_id": user_oid}
        return await crud.list_all(skip=skip, limit=limit, query=q)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list user addresses: {e}")


async def get_user_address(item_id: PyObjectId, current_user: Dict) -> UserAddressOut:
    try:
        item = await crud.get_one(item_id)
        if not item:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User address not found")

        if str(item.user_id) != str(current_user["user_id"]):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

        return item
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get user address: {e}")


async def update_user_address(item_id: PyObjectId, payload: UserAddressUpdate, current_user: Dict) -> UserAddressOut:
    try:
        if not any(v is not None for v in payload.model_dump().values()):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No fields provided for update")

        item = await crud.get_one(item_id)
        if not item:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User address not found")

        if str(item.user_id) != str(current_user["user_id"]):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

        updated = await crud.update_one(item_id, payload)
        if not updated:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User address not found or not updated")
        return updated
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update user address: {e}")


async def delete_user_address(item_id: PyObjectId, current_user: Dict) -> bool:
    try:
        item = await crud.get_one(item_id)
        if not item:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User address not found")

        if str(item.user_id) != str(current_user["user_id"]):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

        ok = await crud.delete_one(item_id)
        if ok is None or ok is False:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unable to delete")
        return True
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete user address: {e}")