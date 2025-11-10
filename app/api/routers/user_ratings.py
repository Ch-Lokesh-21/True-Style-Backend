from __future__ import annotations
from typing import List, Optional, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import JSONResponse

from app.api.deps import require_permission, get_current_user
from app.schemas.object_id import PyObjectId
from app.schemas.user_ratings import UserRatingsCreate, UserRatingsUpdate, UserRatingsOut
from app.services.user_ratings import (
    create_user_rating,
    list_user_ratings_admin,
    get_user_rating_admin,
    get_my_rating_for_product_service,
    update_user_rating,
    delete_user_rating,
)

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
    return await create_user_rating(payload=payload, current_user=current_user)


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
    return await list_user_ratings_admin(skip=skip, limit=limit, product_id=product_id, user_id=user_id)


# -------------------------------------------
# Get by rating _id
# -------------------------------------------
@router.get(
    "/{item_id}",
    response_model=UserRatingsOut,
    dependencies=[Depends(require_permission("user_ratings", "Read","admin"))],
)
async def get_item(item_id: PyObjectId):
    return await get_user_rating_admin(item_id=item_id)


# -------------------------------------------------------
# Get the current user's rating for a product (me)
# -------------------------------------------------------
@router.get(
    "/by-product/{product_id}/me",
    response_model=UserRatingsOut,
    dependencies=[Depends(require_permission("user_ratings", "Read"))],
)
async def get_my_rating_for_product(product_id: PyObjectId, current_user: Dict = Depends(get_current_user)):
    return await get_my_rating_for_product_service(product_id=product_id, current_user=current_user)


# -----------------------------------------------
# Update (owner guard) with transactional recalc
# -----------------------------------------------
@router.put(
    "/{item_id}",
    response_model=UserRatingsOut,
    dependencies=[Depends(require_permission("user_ratings", "Update"))],
)
async def update_item(item_id: PyObjectId, payload: UserRatingsUpdate, current_user: Dict = Depends(get_current_user)):
    return await update_user_rating(item_id=item_id, payload=payload, current_user=current_user)


# -----------------------------------------------
# Delete (owner guard) with transactional recalc
# -----------------------------------------------
@router.delete(
    "/{item_id}",
    dependencies=[Depends(require_permission("user_ratings", "Delete"))],
)
async def delete_item(item_id: PyObjectId, current_user: Dict = Depends(get_current_user)):
    ok = await delete_user_rating(item_id=item_id, current_user=current_user)
    if ok:
        return JSONResponse(status_code=200, content={"deleted": True})