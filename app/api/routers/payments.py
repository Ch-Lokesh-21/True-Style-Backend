from __future__ import annotations
from typing import List, Optional, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import JSONResponse

from app.api.deps import user_required, admin_required
from app.schemas.object_id import PyObjectId
from app.schemas.payments import PaymentsCreate, PaymentsUpdate, PaymentsOut
from app.crud import payments as crud

router = APIRouter()  # mounted in main.py at /payments

@router.post(
    "/",
    response_model=PaymentsOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(admin_required)],
)
async def create_item(payload: PaymentsCreate):
    try:
        return await crud.create(payload)
    except Exception as e:
        msg = str(e)
        if "E11000" in msg:
            # if later you add a unique index on invoice_no, etc.
            raise HTTPException(status_code=409, detail="Duplicate payment")
        raise HTTPException(status_code=500, detail=f"Failed to create payment: {e}")

@router.get(
    "/",
    response_model=List[PaymentsOut],
    dependencies=[Depends(user_required)],
)
async def list_items(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    user_id: Optional[str] = Query(None, description="Filter by user_id"),
    order_id: Optional[str] = Query(None, description="Filter by order_id"),
    payment_types_id: Optional[int] = Query(None, description="Filter by payment_types_id"),
    payment_status_id: Optional[int] = Query(None, description="Filter by payment_status_id"),
    invoice_no: Optional[str] = Query(None, description="Filter by exact invoice_no"),
):
    try:
        q: Dict[str, Any] = {}
        if user_id:
            q["user_id"] = user_id
        if order_id:
            q["order_id"] = order_id
        if payment_types_id is not None:
            q["payment_types_id"] = payment_types_id
        if payment_status_id is not None:
            q["payment_status_id"] = payment_status_id
        if invoice_no:
            q["invoice_no"] = invoice_no
        return await crud.list_all(skip=skip, limit=limit, query=q or None)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list payments: {e}")

@router.get(
    "/{item_id}",
    response_model=PaymentsOut,
    dependencies=[Depends(user_required)],
)
async def get_item(item_id: PyObjectId):
    try:
        item = await crud.get_one(item_id)
        if not item:
            raise HTTPException(status_code=404, detail="Payment not found")
        return item
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get payment: {e}")

@router.put(
    "/{item_id}",
    response_model=PaymentsOut,
    dependencies=[Depends(admin_required)],
)
async def update_item(item_id: PyObjectId, payload: PaymentsUpdate):
    try:
        if not any(v is not None for v in payload.model_dump().values()):
            raise HTTPException(status_code=400, detail="No fields provided for update")
        updated = await crud.update_one(item_id, payload)
        if not updated:
            raise HTTPException(status_code=404, detail="Payment not found or not updated")
        return updated
    except HTTPException:
        raise
    except Exception as e:
        msg = str(e)
        if "E11000" in msg:
            raise HTTPException(status_code=409, detail="Duplicate payment")
        raise HTTPException(status_code=500, detail=f"Failed to update payment: {e}")

@router.delete(
    "/{item_id}",
    dependencies=[Depends(admin_required)],
)
async def delete_item(item_id: PyObjectId):
    try:
        ok = await crud.delete_one(item_id)
        if not ok:
            raise HTTPException(status_code=404, detail="Payment not found")
        return JSONResponse(status_code=200, content={"deleted": True})
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete payment: {e}")