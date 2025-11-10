from __future__ import annotations
from typing import List, Optional, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import JSONResponse

from app.api.deps import require_permission, get_current_user
from app.schemas.object_id import PyObjectId
from app.schemas.wishlist_items import WishlistItemsCreate, WishlistItemsOut
from app.services.wishlist_items import (
    create_wishlist_item,
    list_wishlist_items,
    get_wishlist_item,
    move_wishlist_item_to_cart,
    delete_wishlist_item,
)

router = APIRouter()


@router.post(
    "/",
    response_model=WishlistItemsOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("wishlist_items", "Create"))],
)
async def create_item(
    product_id: PyObjectId,
    current_user: Dict = Depends(get_current_user),
):
    return await create_wishlist_item(product_id=product_id, current_user=current_user)


@router.get(
    "/",
    response_model=List[WishlistItemsOut],
    dependencies=[Depends(require_permission("wishlist_items", "Read"))],
)
async def list_items(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    product_id: Optional[PyObjectId] = Query(None, description="Filter by product_id"),
    current_user: Dict = Depends(get_current_user),
):
    return await list_wishlist_items(
        skip=skip, limit=limit, product_id=product_id, current_user=current_user
    )


@router.get(
    "/{item_id}",
    response_model=WishlistItemsOut,
    dependencies=[Depends(require_permission("wishlist_items", "Read"))],
)
async def get_item(
    item_id: PyObjectId,
    current_user: Dict = Depends(get_current_user),
):
    return await get_wishlist_item(item_id=item_id, current_user=current_user)


@router.post(
    "/move-to-cart/{item_id}",
    response_model=WishlistItemsOut,
    dependencies=[Depends(require_permission("wishlist_items", "Delete"))],
)
async def move_item(
    item_id: PyObjectId,
    size: Optional[str] = None,
    current_user: Dict = Depends(get_current_user),
):
    return await move_wishlist_item_to_cart(
        item_id=item_id, size=size, current_user=current_user
    )


@router.delete(
    "/{item_id}",
    dependencies=[Depends(require_permission("wishlist_items", "Delete"))],
)
async def delete_item(
    item_id: PyObjectId,
    current_user: Dict = Depends(get_current_user),
):
    ok = await delete_wishlist_item(item_id=item_id, current_user=current_user)
    if ok:
        return JSONResponse(status_code=200, content={"deleted": True})