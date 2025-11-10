"""
Service layer for Order Items.
- Encapsulates business rules for user- and admin-facing queries.
"""

from __future__ import annotations
from typing import List, Optional, Dict, Any

from fastapi import HTTPException

from app.schemas.object_id import PyObjectId
from app.schemas.order_items import OrderItemsOut
from app.crud import order_items as crud


async def list_my_items_service(
    skip: int,
    limit: int,
    order_id: Optional[PyObjectId],
    product_id: Optional[PyObjectId],
    current_user: Dict[str, Any],
) -> List[OrderItemsOut]:
    """
    List order-items that belong to the current user, with optional order/product filters.
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


async def get_my_item_service(item_id: PyObjectId, current_user: Dict[str, Any]) -> OrderItemsOut:
    """
    Get a single order-item if it belongs to the current user.
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


async def list_items_admin_service(
    skip: int,
    limit: int,
    order_id: Optional[PyObjectId],
    user_id: Optional[PyObjectId],
    product_id: Optional[PyObjectId],
) -> List[OrderItemsOut]:
    """
    Admin: list order-items with optional filters.
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


async def get_item_admin_service(item_id: PyObjectId) -> OrderItemsOut:
    """
    Admin: get a single order-item by id.
    """
    try:
        item = await crud.get_one(item_id)
        if not item:
            raise HTTPException(status_code=404, detail="Order item not found")
        return item
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get order item: {e}")