"""
Routes for Order Items.
- User endpoints return only items owned by the current user.
- Admin endpoints can query any items with optional filters.
"""

from __future__ import annotations
from typing import List, Optional, Dict, Any

from fastapi import APIRouter, Depends, Query, status
from app.api.deps import require_permission, get_current_user
from app.schemas.object_id import PyObjectId
from app.schemas.order_items import OrderItemsOut
from app.services.order_items import (
    list_my_items_service,
    get_my_item_service,
    list_items_admin_service,
    get_item_admin_service,
)

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
    List order-items that belong to the current user, with optional filters.

    Args:
        skip: Pagination offset.
        limit: Page size.
        order_id: Optional order filter.
        product_id: Optional product filter.
        current_user: Injected user context.

    Returns:
        List[OrderItemsOut]
    """
    return await list_my_items_service(
        skip=skip, limit=limit, order_id=order_id, product_id=product_id, current_user=current_user
    )


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
    Get a single order-item if (and only if) it belongs to the current user.

    Args:
        item_id: Order item ObjectId.
        current_user: Injected user context.

    Returns:
        OrderItemsOut

    Raises:
        404 if not found.
        403 if not owned by user.
    """
    return await get_my_item_service(item_id=item_id, current_user=current_user)


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
    Admin: list order-items with optional filters.

    Args:
        skip: Pagination offset.
        limit: Page size.
        order_id: Optional order filter.
        user_id: Optional user filter.
        product_id: Optional product filter.

    Returns:
        List[OrderItemsOut]
    """
    return await list_items_admin_service(
        skip=skip, limit=limit, order_id=order_id, user_id=user_id, product_id=product_id
    )


@router.get(
    "/{item_id}",
    response_model=OrderItemsOut,
    dependencies=[Depends(require_permission("order_items", "Read", "admin"))],
)
async def get_item_admin(item_id: PyObjectId):
    """
    Admin: get any single order-item by id.

    Args:
        item_id: Order item ObjectId.

    Returns:
        OrderItemsOut

    Raises:
        404 if not found.
    """
    return await get_item_admin_service(item_id)