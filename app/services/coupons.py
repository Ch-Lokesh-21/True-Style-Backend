"""
Service layer for Coupons.
Encapsulates all business rules, data access orchestration, and error normalization.
"""

from __future__ import annotations
from typing import List, Optional, Dict, Any

from fastapi import HTTPException, status
from fastapi.responses import JSONResponse

from app.schemas.object_id import PyObjectId
from app.schemas.coupons import (
    CouponsCreate, CouponsUpdate, CouponsOut,
    CouponCheckIn, CouponCheckOut,
)
from app.crud import coupons as crud
from app.core.database import db  # used by validation for status lookup


async def create_item_service(payload: CouponsCreate) -> CouponsOut:
    """
    Create a coupon.

    Args:
        payload: Coupon creation schema.

    Returns:
        CouponsOut

    Raises:
        HTTPException:
            - 409 for duplicate coupon.
            - 500 for other errors.
    """
    try:
        return await crud.create(payload)
    except HTTPException:
        raise
    except Exception as e:
        if "E11000" in str(e):
            raise HTTPException(status_code=409, detail="Duplicate coupon")
        raise HTTPException(status_code=500, detail=f"Failed to create coupon: {e}")


async def list_items_service(
    skip: int,
    limit: int,
    code: Optional[str],
    type: Optional[str],
    coupons_status_id: Optional[PyObjectId],
) -> List[CouponsOut]:
    """
    List coupons with optional filters.

    Args:
        skip: Pagination offset.
        limit: Page size.
        code: Exact code filter.
        type: Type filter.
        coupons_status_id: Status ObjectId filter.

    Returns:
        List[CouponsOut]
    """
    try:
        q: Dict[str, Any] = {}
        if code:
            q["code"] = code
        if type:
            q["type"] = type
        if coupons_status_id is not None:
            q["coupons_status_id"] = coupons_status_id
        return await crud.list_all(skip=skip, limit=limit, query=q or None)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list coupons: {e}")


async def get_item_service(item_id: PyObjectId) -> CouponsOut:
    """
    Get coupon by ID.

    Args:
        item_id: Coupon ObjectId.

    Returns:
        CouponsOut

    Raises:
        HTTPException:
            - 404 if not found.
            - 500 on server error.
    """
    try:
        item = await crud.get_one(item_id)
        if not item:
            raise HTTPException(status_code=404, detail="Coupon not found")
        return item
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get coupon: {e}")


async def update_item_service(item_id: PyObjectId, payload: CouponsUpdate) -> CouponsOut:
    """
    Update a coupon.

    Args:
        item_id: Coupon ObjectId.
        payload: Partial update fields.

    Returns:
        CouponsOut

    Raises:
        HTTPException:
            - 400 if no fields provided.
            - 404 if not found.
            - 409 if duplicate coupon.
            - 500 on server error.
    """
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


async def delete_item_service(item_id: PyObjectId):
    """
    Delete a coupon.

    Args:
        item_id: Coupon ObjectId.

    Returns:
        JSONResponse: {"deleted": True} on success.

    Raises:
        HTTPException:
            - 404 if not found.
            - 500 on server error.
    """
    try:
        ok = await crud.delete_one(item_id)
        if not ok:
            raise HTTPException(status_code=404, detail="Coupon not found")
        return JSONResponse(status_code=200, content={"deleted": True})
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete coupon: {e}")


async def validate_coupon_service(payload: CouponCheckIn):
    """
    Validate a coupon against a given amount.
    Returns 200 with CouponCheckOut if valid; otherwise 400 JSON with a structured reason.

    Args:
        payload: CouponCheckIn containing 'code' and 'amount'.

    Returns:
        CouponCheckOut on success (valid coupon), or JSONResponse (400) on failure.

    Raises:
        HTTPException: 500 on unexpected server error.
    """

    def bad(reason: str, amount_val: float, coupon_obj=None):
        """
        Build a 400 JSON response for invalid coupon cases.

        Args:
            reason: Human-readable failure reason.
            amount_val: Original amount.
            coupon_obj: Optional coupon to pick type/discount from.

        Returns:
            JSONResponse with the expected invalid coupon shape.
        """
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
            # Unknown types treated as flat numeric fallback
            discount_amount = max(0.0, float(coupon.discount or 0))

        # Cap to amount and compute final
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