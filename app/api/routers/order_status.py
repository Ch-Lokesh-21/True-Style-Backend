from __future__ import annotations
from typing import List, Optional, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import JSONResponse

from app.api.deps import require_permission
from app.schemas.object_id import PyObjectId
from app.schemas.order_status import OrderStatusCreate, OrderStatusUpdate, OrderStatusOut
from app.crud import order_status as crud

router = APIRouter()  # mounted in main.py at /order-status


@router.post(
    "/",
    response_model=OrderStatusOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("order_status", "Create"))]
)
async def create_item(payload: OrderStatusCreate):
    try:
        return await crud.create(payload)
    except Exception as e:
        msg = str(e)
        if "E11000" in msg:
            # if you later add a unique index on idx or status
            raise HTTPException(status_code=409, detail="Duplicate order status")
        raise HTTPException(status_code=500, detail=f"Failed to create order status: {e}")


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
    try:
        q: Dict[str, Any] = {}
        if status_q:
            q["status"] = status_q
        return await crud.list_all(skip=skip, limit=limit, query=q or None)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list order status: {e}")


@router.get(
    "/{item_id}",
    response_model=OrderStatusOut,
    dependencies=[Depends(require_permission("order_status", "Read"))]
)
async def get_item(item_id: PyObjectId):
    try:
        item = await crud.get_one(item_id)
        if not item:
            raise HTTPException(status_code=404, detail="Order status not found")
        return item
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get order status: {e}")


@router.put(
    "/{item_id}",
    response_model=OrderStatusOut,
    dependencies=[Depends(require_permission("order_status", "Update"))]
)
async def update_item(item_id: PyObjectId, payload: OrderStatusUpdate):
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
            raise HTTPException(status_code=409, detail="Duplicate order status")
        raise HTTPException(status_code=500, detail=f"Failed to update order status: {e}")


@router.delete(
    "/{item_id}",
    dependencies=[Depends(require_permission("order_status", "Delete"))]
)
async def delete_item(item_id: PyObjectId):
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