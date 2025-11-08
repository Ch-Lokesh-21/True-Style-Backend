from __future__ import annotations
from typing import List, Optional, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import JSONResponse

from app.api.deps import require_permission
from app.schemas.object_id import PyObjectId
from app.schemas.payment_types import (
    PaymentTypesCreate,
    PaymentTypesUpdate,
    PaymentTypesOut,
)
from app.crud import payment_types as crud

router = APIRouter()  # mount in main.py with prefix="/payment-types"


def _raise_conflict_if_dup(err: Exception, field_hint: Optional[str] = None):
    msg = str(err)
    if "E11000" in msg:
        detail = "Duplicate key." if not field_hint else f"Duplicate {field_hint}."
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=detail)
    raise err


@router.post(
    "/",
    response_model=PaymentTypesOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("payment_types", "Create"))],
)
async def create_item(payload: PaymentTypesCreate):
    try:
        return await crud.create(payload)
    except HTTPException:
        raise
    except Exception as e:
        try:
            _raise_conflict_if_dup(e, field_hint="idx or type")
        except Exception as e2:
            raise HTTPException(status_code=500, detail=f"Failed to create payment type: {e2}")


@router.get(
    "/",
    response_model=List[PaymentTypesOut],
    dependencies=[Depends(require_permission("payment_types", "Read"))],
)
async def list_items(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    type_q: Optional[str] = Query(None, description="Filter by exact type"),
):
    try:
        q: Dict[str, Any] = {}
        if type_q:
            q["type"] = type_q
        return await crud.list_all(skip=skip, limit=limit, query=q or None)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list payment types: {e}")


@router.get(
    "/{item_id}",
    response_model=PaymentTypesOut,
    dependencies=[Depends(require_permission("payment_types", "Read"))],
)
async def get_item(item_id: PyObjectId):
    try:
        item = await crud.get_one(item_id)
        if not item:
            raise HTTPException(status_code=404, detail="Payment type not found")
        return item
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get payment type: {e}")


@router.put(
    "/{item_id}",
    response_model=PaymentTypesOut,
    dependencies=[Depends(require_permission("payment_types", "Update"))],
)
async def update_item(item_id: PyObjectId, payload: PaymentTypesUpdate):
    try:
        if not any(v is not None for v in payload.model_dump().values()):
            raise HTTPException(status_code=400, detail="No fields provided for update")
        updated = await crud.update_one(item_id, payload)
        if not updated:
            raise HTTPException(status_code=404, detail="Payment type not found or not updated")
        return updated
    except HTTPException:
        raise
    except Exception as e:
        try:
            _raise_conflict_if_dup(e, field_hint="idx or type")
        except Exception as e2:
            raise HTTPException(status_code=500, detail=f"Failed to update payment type: {e2}")


@router.delete(
    "/{item_id}",
    dependencies=[Depends(require_permission("payment_types", "Delete"))],
)
async def delete_item(item_id: PyObjectId):
    try:
        ok = await crud.delete_one(item_id)

        if ok is None:
            raise HTTPException(status_code=400, detail="Invalid payment type ID.")

        if ok is False:
            raise HTTPException(
                status_code=400,
                detail="Cannot delete this payment type because one or more payments are using it.",
            )

        return JSONResponse(status_code=200, content={"deleted": True})

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete payment type: {e}")