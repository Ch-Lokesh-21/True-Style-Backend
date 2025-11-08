from __future__ import annotations
from typing import List, Optional, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import JSONResponse

from app.api.deps import require_permission
from app.schemas.object_id import PyObjectId
from app.schemas.coupons import (
    CouponsCreate, CouponsUpdate, CouponsOut,
    CouponCheckIn, CouponCheckOut,
)
from app.crud import coupons as crud
from app.core.database import db  # used only by /validate for status lookup

router = APIRouter()  # mounted in main.py at /coupons


@router.post(
    "/",
    response_model=CouponsOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("coupons", "Create"))]
)
async def create_item(payload: CouponsCreate):
    try:
        return await crud.create(payload)
    except HTTPException:
        raise
    except Exception as e:
        if "E11000" in str(e):
            raise HTTPException(status_code=409, detail="Duplicate coupon")
        raise HTTPException(status_code=500, detail=f"Failed to create coupon: {e}")


@router.get(
    "/",
    response_model=List[CouponsOut],
    dependencies=[Depends(require_permission("coupons", "Read"))],
)
async def list_items(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    code: Optional[str] = Query(None, description="Filter by exact code"),
    type: Optional[str] = Query(None, description="Filter by type"),
    coupons_status_id: Optional[PyObjectId] = Query(None, description="Filter by status id"),
):
    try:
        q: Dict[str, Any] = {}
        if code:
            q["code"] = code
        if type:
            q["type"] = type
        if coupons_status_id is not None:
            q["coupons_status_id"] = coupons_status_id  # already ObjectId
        return await crud.list_all(skip=skip, limit=limit, query=q or None)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list coupons: {e}")


@router.get(
    "/{item_id}",
    response_model=CouponsOut,
    dependencies=[Depends(require_permission("coupons", "Read"))]
)
async def get_item(item_id: PyObjectId):
    try:
        item = await crud.get_one(item_id)
        if not item:
            raise HTTPException(status_code=404, detail="Coupon not found")
        return item
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get coupon: {e}")


@router.put(
    "/{item_id}",
    response_model=CouponsOut,
    dependencies=[Depends(require_permission("coupons", "Update"))]
)
async def update_item(item_id: PyObjectId, payload: CouponsUpdate):
    try:
        if not any(v is not None for v in payload.model_dump().values()):
            raise HTTPException(status_code=400, detail="No fields provided for update")
        updated = await crud.update_one(item_id, payload)
        if not updated:
            raise HTTPException(status_code=404, detail="Coupon not found or not updated")
        return updated
    except HTTPException:
        raise
    except Exception as e:
        if "E11000" in str(e):
            raise HTTPException(status_code=409, detail="Duplicate coupon")
        raise HTTPException(status_code=500, detail=f"Failed to update coupon: {e}")


@router.delete(
    "/{item_id}",
    dependencies=[Depends(require_permission("coupons", "Delete"))],
)
async def delete_item(item_id: PyObjectId):
    try:
        ok = await crud.delete_one(item_id)
        if not ok:
            raise HTTPException(status_code=404, detail="Coupon not found")
        return JSONResponse(status_code=200, content={"deleted": True})
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete coupon: {e}")


# --------- Validate coupon ---------

@router.post(
    "/validate",
    response_model=CouponCheckOut,  # applies to 200 OK only
    dependencies=[Depends(require_permission("coupons", "Read"))],
    responses={
        400: {
            "description": "Invalid coupon",
            "content": {
                "application/json": {
                    "example": {
                        "code": "WELCOME10",
                        "valid": False,
                        "discount_type": "percent",
                        "discount_value": 10,
                        "discount_amount": 0.0,
                        "final_amount": 499.0,
                        "reason": "Minimum price 500.0 not met",
                    }
                }
            },
        }
    },
)
async def validate_coupon(payload: CouponCheckIn):
    """
    200 OK only if valid; otherwise 400 with a structured reason.
    """
    def bad(reason: str, amount_val: float, coupon_obj=None):
        return JSONResponse(
            status_code=400,
            content={
                "code": payload.code,
                "valid": False,
                "discount_type": getattr(coupon_obj, "type", None),
                "discount_value": getattr(coupon_obj, "discount", None),
                "discount_amount": 0.0,
                "final_amount": amount_val,
                "reason": reason,
            },
        )

    try:
        amount = float(payload.amount)
        if amount < 0:
            return bad("Amount must be non-negative", amount)

        coupon = await crud.get_by_code(payload.code)
        if not coupon:
            return bad("Coupon not found", amount)

        # Status check (coupons_status_id is ObjectId)
        status_doc = await db["coupons_status"].find_one({"_id": coupon.coupons_status_id})
        if not status_doc or str(status_doc.get("status", "")).lower() != "active":
            return bad("Coupon is inactive or expired", amount, coupon)

        # Minimum price
        if coupon.minimum_price is not None and amount < coupon.minimum_price:
            return bad(f"Minimum price {coupon.minimum_price} not met", amount, coupon)

        # Usage
        if coupon.usage is not None and coupon.usage <= 0:
            return bad("Coupon usage limit reached", amount, coupon)

        # Compute discount
        discount_amount = 0.0
        if coupon.type == "percent":
            rate = float(coupon.discount or 0)
            rate = max(0.0, min(rate, 100.0))
            discount_amount = round(amount * (rate / 100.0), 2)
        elif coupon.type == "flat":
            discount_amount = max(0.0, float(coupon.discount or 0))
        else:
            discount_amount = max(0.0, float(coupon.discount or 0))

        # Cap to amount
        discount_amount = min(discount_amount, amount)
        final_amount = round(amount - discount_amount, 2)

        return CouponCheckOut(
            code=payload.code,
            valid=True,
            discount_type=coupon.type,
            discount_value=coupon.discount,
            discount_amount=float(discount_amount),
            final_amount=float(final_amount),
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to validate coupon: {e}")