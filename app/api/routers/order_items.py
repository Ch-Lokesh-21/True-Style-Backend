from __future__ import annotations
from typing import List, Optional, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import JSONResponse

from app.api.deps import user_required, admin_required
from app.schemas.object_id import PyObjectId
from app.schemas.order_items import OrderItemsCreate, OrderItemsUpdate, OrderItemsOut
from app.crud import order_items as crud

router = APIRouter()  # mounted in main.py at /order-items

@router.post(
    "/",
    response_model=OrderItemsOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(admin_required)],
)
async def create_item(payload: OrderItemsCreate):
    try:
        return await crud.create(payload)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create order item: {e}")

@router.get(
    "/",
    response_model=List[OrderItemsOut],
    dependencies=[Depends(user_required)],
)
async def list_items(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    order_id: Optional[str] = Query(None, description="Filter by order_id"),
    user_id: Optional[str] = Query(None, description="Filter by user_id"),
    product_id: Optional[str] = Query(None, description="Filter by product_id"),
):
    try:
        q: Dict[str, Any] = {}
        if order_id:
            q["order_id"] = order_id
        if user_id:
            q["user_id"] = user_id
        if product_id:
            q["product_id"] = product_id
        return await crud.list_all(skip=skip, limit=limit, query=q or None)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list order items: {e}")

@router.get(
    "/{item_id}",
    response_model=OrderItemsOut,
    dependencies=[Depends(user_required)],
)
async def get_item(item_id: PyObjectId):
    try:
        item = await crud.get_one(item_id)
        if not item:
            raise HTTPException(status_code=404, detail="Order item not found")
        return item
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get order item: {e}")

@router.put(
    "/{item_id}",
    response_model=OrderItemsOut,
    dependencies=[Depends(admin_required)],
)
async def update_item(item_id: PyObjectId, payload: OrderItemsUpdate):
    try:
        if not any(v is not None for v in payload.model_dump().values()):
            raise HTTPException(status_code=400, detail="No fields provided for update")
        updated = await crud.update_one(item_id, payload)
        if not updated:
            raise HTTPException(status_code=404, detail="Order item not found or not updated")
        return updated
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update order item: {e}")

@router.delete(
    "/{item_id}",
    dependencies=[Depends(admin_required)],
)
async def delete_item(item_id: PyObjectId):
    try:
        ok = await crud.delete_one(item_id)
        if not ok:
            raise HTTPException(status_code=404, detail="Order item not found")
        return JSONResponse(status_code=200, content={"deleted": True})
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete order item: {e}")