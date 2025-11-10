"""
Routes for Order Status.
- Parses requests, applies RBAC, and delegates business logic to the service layer.
"""

from __future__ import annotations
from typing import List, Optional, Dict, Any

from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import JSONResponse

from app.api.deps import require_permission
from app.schemas.object_id import PyObjectId
from app.schemas.order_status import OrderStatusCreate, OrderStatusUpdate, OrderStatusOut
from app.services.order_status import (
    create_item_service,
    list_items_service,
    get_item_service,
    update_item_service,
    delete_item_service,
)

router = APIRouter()  # mounted in main.py at /order-status


@router.post(
    "/",
    response_model=OrderStatusOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("order_status", "Create"))]
)
async def create_item(payload: OrderStatusCreate):
    """
    Create an order status.

    Args:
        payload: OrderStatusCreate schema.

    Returns:
        OrderStatusOut

    Raises:
        409 on duplicate status (if a unique index exists).
    """
    return await create_item_service(payload)


@router.get(
    "/",
    response_model=List[OrderStatusOut],
    dependencies=[Depends(require_permission("order_status", "Read"))]
)
async def list_items(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    status_q: Optional[str] = Query(None, description="Filter by exact status"),
):
    """
    List order statuses with optional exact `status` filter.

    Args:
        skip: Pagination offset.
        limit: Page size.
        status_q: Optional exact match on status field.

    Returns:
        List[OrderStatusOut]
    """
    q: Dict[str, Any] = {}
    if status_q:
        q["status"] = status_q
    return await list_items_service(skip=skip, limit=limit, query=q or None)


@router.get(
    "/{item_id}",
    response_model=OrderStatusOut,
    dependencies=[Depends(require_permission("order_status", "Read"))]
)
async def get_item(item_id: PyObjectId):
    """
    Get a single order status by id.

    Args:
        item_id: Order status ObjectId.

    Returns:
        OrderStatusOut

    Raises:
        404 if not found.
    """
    return await get_item_service(item_id)


@router.put(
    "/{item_id}",
    response_model=OrderStatusOut,
    dependencies=[Depends(require_permission("order_status", "Update"))]
)
async def update_item(item_id: PyObjectId, payload: OrderStatusUpdate):
    """
    Update an order status.

    Args:
        item_id: Order status ObjectId.
        payload: OrderStatusUpdate schema (must include at least one field).

    Returns:
        OrderStatusOut

    Raises:
        400 if no fields provided.
        404 if not found.
        409 on duplicate status/index.
    """
    return await update_item_service(item_id=item_id, payload=payload)


@router.delete(
    "/{item_id}",
    dependencies=[Depends(require_permission("order_status", "Delete"))]
)
async def delete_item(item_id: PyObjectId):
    """
    Delete an order status.

    Delete semantics (as per CRUD contract):
      - Returns 400 if ID is invalid (ok is None).
      - Returns 400 if the status is in use by one or more orders (ok is False).
      - Returns 200 with {"deleted": True} on success.

    Args:
        item_id: Order status ObjectId.

    Returns:
        JSONResponse({"deleted": True})
    """
    return await delete_item_service(item_id)