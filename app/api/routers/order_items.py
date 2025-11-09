# app/api/routes/order_items.py
from __future__ import annotations
from typing import List, Optional, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from app.api.deps import require_permission, get_current_user
from app.schemas.object_id import PyObjectId
from app.schemas.order_items import OrderItemsOut
from app.crud import order_items as crud

router = APIRouter()  # mounted at /order-items


# --------------------------
# USER: my order items
# --------------------------
@router.get(
    "/my",
    response_model=List[OrderItemsOut],
    dependencies=[Depends(require_permission("order_items", "Read"))],
)
async def list_my_items(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    order_id: Optional[PyObjectId] = Query(None, description="Filter by a specific order"),
    product_id: Optional[PyObjectId] = Query(None, description="Filter by a specific product"),
    current_user: Dict = Depends(get_current_user),
):
    """
    List order-items that belong to the **current user**.
    Optional filters: order_id, product_id.
    """
    try:
        q: Dict[str, Any] = {"user_id": current_user["user_id"]}
        if order_id is not None:
            q["order_id"] = order_id
        if product_id is not None:
            q["product_id"] = product_id
        return await crud.list_all(skip=skip, limit=limit, query=q)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list my order items: {e}")


@router.get(
    "/my/{item_id}",
    response_model=OrderItemsOut,
    dependencies=[Depends(require_permission("order_items", "Read"))],
)
async def get_my_item(
    item_id: PyObjectId,
    current_user: Dict = Depends(get_current_user),
):
    """
    Get a single order-item **only if** it belongs to the current user.
    """
    try:
        item = await crud.get_one(item_id)
        if not item:
            raise HTTPException(status_code=404, detail="Order item not found")
        if str(item.user_id) != str(current_user["user_id"]):
            raise HTTPException(status_code=403, detail="Forbidden")
        return item
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get order item: {e}")


# --------------------------
# ADMIN: read any order items
# --------------------------
@router.get(
    "/",
    response_model=List[OrderItemsOut],
    dependencies=[Depends(require_permission("order_items", "Read", "admin"))],
)
async def list_items_admin(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    order_id: Optional[PyObjectId] = Query(None),
    user_id: Optional[PyObjectId] = Query(None),
    product_id: Optional[PyObjectId] = Query(None),
):
    """
    Admin: list order-items with optional filters: order_id, user_id, product_id.
    """
    try:
        q: Dict[str, Any] = {}
        if order_id is not None:
            q["order_id"] = order_id
        if user_id is not None:
            q["user_id"] = user_id
        if product_id is not None:
            q["product_id"] = product_id
        return await crud.list_all(skip=skip, limit=limit, query=q or None)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list order items: {e}")


@router.get(
    "/{item_id}",
    response_model=OrderItemsOut,
    dependencies=[Depends(require_permission("order_items", "Read", "admin"))],
)
async def get_item_admin(item_id: PyObjectId):
    """Admin: get any single order-item by id."""
    try:
        item = await crud.get_one(item_id)
        if not item:
            raise HTTPException(status_code=404, detail="Order item not found")
        return item
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get order item: {e}")