"""
Service layer for Order Status.
- Encapsulates business rules and error mapping for CRUD operations.
"""

from __future__ import annotations
from typing import List, Optional, Dict, Any

from fastapi import HTTPException, status
from fastapi.responses import JSONResponse

from app.schemas.object_id import PyObjectId
from app.schemas.order_status import OrderStatusCreate, OrderStatusUpdate, OrderStatusOut
from app.crud import order_status as crud


async def create_item_service(payload: OrderStatusCreate) -> OrderStatusOut:
    """
    Create an order status.

    Args:
        payload: OrderStatusCreate

    Returns:
        OrderStatusOut

    Raises:
        409 on duplicate (E11000).
    """
    try:
        return await crud.create(payload)
    except Exception as e:
        msg = str(e)
        if "E11000" in msg:
            # if a unique index exists on idx or status
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Duplicate order status")
        raise HTTPException(status_code=500, detail=f"Failed to create order status: {e}")


async def list_items_service(skip: int, limit: int, query: Optional[Dict[str, Any]]) -> List[OrderStatusOut]:
    """
    List order statuses with optional filter.

    Args:
        skip: Offset.
        limit: Limit.
        query: Optional filter dict.

    Returns:
        List[OrderStatusOut]
    """
    try:
        return await crud.list_all(skip=skip, limit=limit, query=query or None)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list order status: {e}")


async def get_item_service(item_id: PyObjectId) -> OrderStatusOut:
    """
    Get a single order status by id.

    Args:
        item_id: Order status ObjectId.

    Returns:
        OrderStatusOut

    Raises:
        404 if not found.
    """
    try:
        item = await crud.get_one(item_id)
        if not item:
            raise HTTPException(status_code=404, detail="Order status not found")
        return item
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get order status: {e}")


async def update_item_service(item_id: PyObjectId, payload: OrderStatusUpdate) -> OrderStatusOut:
    """
    Update an order status.

    Args:
        item_id: Order status ObjectId.
        payload: OrderStatusUpdate (must include at least one field).

    Returns:
        OrderStatusOut

    Raises:
        400 if no fields provided.
        404 if not found.
        409 on duplicate (E11000).
    """
    try:
        if not any(v is not None for v in payload.model_dump().values()):
            raise HTTPException(status_code=400, detail="No fields provided for update")
        updated = await crud.update_one(item_id, payload)
        if not updated:
            raise HTTPException(status_code=404, detail="Order status not found or not updated")
        return updated
    except HTTPException:
        raise
    except Exception as e:
        msg = str(e)
        if "E11000" in msg:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Duplicate order status")
        raise HTTPException(status_code=500, detail=f"Failed to update order status: {e}")


async def delete_item_service(item_id: PyObjectId):
    """
    Delete an order status.

    Delete semantics (as per CRUD contract):
      - If `ok is None`: ID invalid → raise 400.
      - If `ok is False`: status in use → raise 400.
      - If `ok is True`: return {"deleted": True}.

    Args:
        item_id: Order status ObjectId.

    Returns:
        JSONResponse({"deleted": True})
    """
    try:
        ok = await crud.delete_one(item_id)

        if ok is None:
            raise HTTPException(status_code=400, detail="Invalid order status ID.")

        if ok is False:
            raise HTTPException(
                status_code=400,
                detail="Cannot delete this order status because one or more orders are using it.",
            )

        return JSONResponse(status_code=200, content={"deleted": True})
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete order status: {e}")