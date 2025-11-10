from __future__ import annotations
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import JSONResponse

from app.api.deps import require_permission, get_current_user
from app.schemas.object_id import PyObjectId
from app.schemas.cart_items import CartItemsUpdate, CartItemsOut
from app.services.cart_items import (
    create_item_service,
    list_items_service,
    get_item_service,
    update_item_service,
    delete_item_service,
    move_to_wishlist_service,
)

router = APIRouter()  # mounted at /cart-items


@router.post(
    "/",
    response_model=CartItemsOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("cart_items", "Create"))]
)
async def create_item(
    product_id: PyObjectId,
    size: str,
    quantity: Optional[int] = 1,
    current_user: Dict = Depends(get_current_user),
):
    """
    Create-or-merge:
      - If (cart_id, product_id, size) exists → increment quantity.
      - Else create a new line.
    """
    return await create_item_service(product_id=product_id, size=size, quantity=quantity, current_user=current_user)


@router.get(
    "/",
    response_model=List[CartItemsOut],
    dependencies=[Depends(require_permission("cart_items", "Read"))]
)
async def list_items(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    product_id: Optional[PyObjectId] = Query(None, description="Filter by product_id"),
    current_user: Dict = Depends(get_current_user),
):
    return await list_items_service(skip=skip, limit=limit, product_id=product_id, current_user=current_user)


@router.get(
    "/{item_id}",
    response_model=CartItemsOut,
    dependencies=[Depends(require_permission("cart_items", "Read"))],
)
async def get_item(item_id: PyObjectId, current_user: Dict = Depends(get_current_user)):
    return await get_item_service(item_id=item_id, current_user=current_user)


@router.put(
    "/{item_id}",
    response_model=CartItemsOut,
    dependencies=[Depends(require_permission("cart_items", "Update"))],
)
async def update_item(
    item_id: PyObjectId,
    payload: CartItemsUpdate,
    current_user: Dict = Depends(get_current_user),
):
    return await update_item_service(item_id=item_id, payload=payload, current_user=current_user)


@router.delete(
    "/{item_id}",
    dependencies=[Depends(require_permission("cart_items", "Delete"))]
)
async def delete_item(item_id: PyObjectId, current_user: Dict = Depends(get_current_user)):
    return await delete_item_service(item_id=item_id, current_user=current_user)


# ----------------------------
# Transactional: Move to Wishlist
# ----------------------------
@router.post(
    "/move-to-wishlist/{item_id}",
    response_model=CartItemsOut,  # return the deleted cart snapshot
    dependencies=[Depends(require_permission("cart_items", "Delete"))],
)
async def move_to_wishlist(
    item_id: PyObjectId,
    current_user: Dict = Depends(get_current_user),
):
    """
    Moves a cart line into wishlist_items atomically:
      - Upsert wishlist_items by (wishlist_id, product_id)
      - Delete the cart line
    Assumptions:
      - current_user contains "wishlist_id"
      - wishlist_items schema stores wishlist_id & product_id as ObjectId
    """
    return await move_to_wishlist_service(item_id=item_id, current_user=current_user)