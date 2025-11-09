from __future__ import annotations
from typing import List, Optional, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import JSONResponse

from app.api.deps import require_permission, get_current_user
from app.schemas.object_id import PyObjectId
from app.schemas.user_ratings import (
    UserRatingsCreate,
    UserRatingsUpdate,
    UserRatingsOut,
)
from app.crud import user_ratings as crud

router = APIRouter()  # mounted in main.py at prefix="/user-ratings"

# ---------------------------
# Create: user can rate self
# ---------------------------
@router.post(
    "/",
    response_model=UserRatingsOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("user_ratings", "Create"))],
)
async def create_item(payload: UserRatingsCreate, current_user: Dict = Depends(get_current_user)):
    try:
        if str(payload.user_id) != str(current_user["user_id"]):
            raise HTTPException(status_code=403, detail="Forbidden")

        return await crud.create_with_recalc(payload)
    except HTTPException:
        raise
    except Exception as e:
        if "E11000" in str(e):
            raise HTTPException(status_code=409, detail="You already rated this product")
        raise HTTPException(status_code=500, detail=f"Failed to create user rating: {e}")

# ---------------------------------------
# List all (admin / anyone with Read perm)
# ---------------------------------------
@router.get(
    "/",
    response_model=List[UserRatingsOut],
    dependencies=[Depends(require_permission("user_ratings", "Read","admin"))],
)
async def list_items(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    product_id: Optional[PyObjectId] = Query(None, description="Filter by product_id"),
    user_id: Optional[PyObjectId] = Query(None, description="Filter by user_id"),
):
    try:
        q: Dict[str, Any] = {}
        if product_id is not None:
            q["product_id"] = product_id
        if user_id is not None:
            q["user_id"] = user_id
        return await crud.list_all(skip=skip, limit=limit, query=q or None)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list user ratings: {e}")

# -------------------------------------------
# Get by rating _id
# -------------------------------------------
@router.get(
    "/{item_id}",
    response_model=UserRatingsOut,
    dependencies=[Depends(require_permission("user_ratings", "Read","admin"))],
)
async def get_item(item_id: PyObjectId):
    try:
        item = await crud.get_one(item_id)
        if not item:
            raise HTTPException(status_code=404, detail="User rating not found")
        return item
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get user rating: {e}")

# -------------------------------------------------------
# Get the current user's rating for a product (me)
# -------------------------------------------------------
@router.get(
    "/by-product/{product_id}/me",
    response_model=UserRatingsOut,
    dependencies=[Depends(require_permission("user_ratings", "Read"))],
)
async def get_my_rating_for_product(product_id: PyObjectId, current_user: Dict = Depends(get_current_user)):
    try:
        item = await crud.get_by_user_and_product(
            user_id=current_user["user_id"],
            product_id=product_id,
        )
        if not item:
            raise HTTPException(status_code=404, detail="User rating not found")
        return item
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get user rating: {e}")

# -----------------------------------------------
# Update (owner guard) with transactional recalc
# -----------------------------------------------
@router.put(
    "/{item_id}",
    response_model=UserRatingsOut,
    dependencies=[Depends(require_permission("user_ratings", "Update"))],
)
async def update_item(item_id: PyObjectId, payload: UserRatingsUpdate, current_user: Dict = Depends(get_current_user)):
    try:
        if not any(v is not None for v in payload.model_dump().values()):
            raise HTTPException(status_code=400, detail="No fields provided for update")

        existing = await crud.get_one(item_id)
        if not existing:
            raise HTTPException(status_code=404, detail="User rating not found")
        if str(existing.user_id) != str(current_user["user_id"]):
            raise HTTPException(status_code=403, detail="Forbidden")

        updated = await crud.update_with_recalc(item_id, payload)
        if not updated:
            raise HTTPException(status_code=404, detail="User rating not found or not updated")
        return updated
    except HTTPException:
        raise
    except Exception as e:
        if "E11000" in str(e):
            raise HTTPException(status_code=409, detail="A rating for this product by this user already exists")
        raise HTTPException(status_code=500, detail=f"Failed to update user rating: {e}")

# -----------------------------------------------
# Delete (owner guard) with transactional recalc
# -----------------------------------------------
@router.delete(
    "/{item_id}",
    dependencies=[Depends(require_permission("user_ratings", "Delete"))],
)
async def delete_item(item_id: PyObjectId, current_user: Dict = Depends(get_current_user)):
    try:
        existing = await crud.get_one(item_id)
        if not existing:
            raise HTTPException(status_code=404, detail="User rating not found")
        if str(existing.user_id) != str(current_user["user_id"]):
            raise HTTPException(status_code=403, detail="Forbidden")

        ok = await crud.delete_with_recalc(item_id)
        if not ok:
            raise HTTPException(status_code=404, detail="User rating not found")
        return JSONResponse(status_code=200, content={"deleted": True})
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete user rating: {e}")