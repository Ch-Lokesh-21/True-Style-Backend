from __future__ import annotations
from typing import List, Optional, Dict, Any

from fastapi import HTTPException, status

from app.schemas.object_id import PyObjectId
from app.schemas.user_ratings import UserRatingsCreate, UserRatingsUpdate, UserRatingsOut
from app.crud import user_ratings as crud


# Create
async def create_user_rating(payload: UserRatingsCreate, current_user: Dict) -> UserRatingsOut:
    try:
        if str(payload.user_id) != str(current_user["user_id"]):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
        return await crud.create_with_recalc(payload)
    except HTTPException:
        raise
    except Exception as e:
        if "E11000" in str(e):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="You already rated this product")
        raise HTTPException(status_code=500, detail=f"Failed to create user rating: {e}")


# Admin list
async def list_user_ratings_admin(
    skip: int,
    limit: int,
    product_id: Optional[PyObjectId],
    user_id: Optional[PyObjectId],
) -> List[UserRatingsOut]:
    try:
        q: Dict[str, Any] = {}
        if product_id is not None:
            q["product_id"] = product_id
        if user_id is not None:
            q["user_id"] = user_id
        return await crud.list_all(skip=skip, limit=limit, query=q or None)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list user ratings: {e}")


# Admin get by id
async def get_user_rating_admin(item_id: PyObjectId) -> UserRatingsOut:
    try:
        item = await crud.get_one(item_id)
        if not item:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User rating not found")
        return item
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get user rating: {e}")


# Me → by product
async def get_my_rating_for_product_service(product_id: PyObjectId, current_user: Dict) -> UserRatingsOut:
    try:
        item = await crud.get_by_user_and_product(
            user_id=current_user["user_id"],
            product_id=product_id,
        )
        if not item:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User rating not found")
        return item
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get user rating: {e}")


# Update + recalc
async def update_user_rating(item_id: PyObjectId, payload: UserRatingsUpdate, current_user: Dict) -> UserRatingsOut:
    try:
        if not any(v is not None for v in payload.model_dump().values()):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No fields provided for update")

        existing = await crud.get_one(item_id)
        if not existing:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User rating not found")
        if str(existing.user_id) != str(current_user["user_id"]):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

        updated = await crud.update_with_recalc(item_id, payload)
        if not updated:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User rating not found or not updated")
        return updated
    except HTTPException:
        raise
    except Exception as e:
        if "E11000" in str(e):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A rating for this product by this user already exists",
            )
        raise HTTPException(status_code=500, detail=f"Failed to update user rating: {e}")


# Delete + recalc
async def delete_user_rating(item_id: PyObjectId, current_user: Dict) -> bool:
    try:
        existing = await crud.get_one(item_id)
        if not existing:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User rating not found")
        if str(existing.user_id) != str(current_user["user_id"]):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

        ok = await crud.delete_with_recalc(item_id)
        if not ok:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User rating not found")
        return True
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete user rating: {e}")