"""
Routes for managing Coupons.
Handles request parsing, RBAC, and delegates all business logic to the service layer.
Mounted at /coupons
"""

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
from app.services.coupons import (
    create_item_service,
    list_items_service,
    get_item_service,
    update_item_service,
    delete_item_service,
    validate_coupon_service,
)

router = APIRouter()  # mounted in main.py at /coupons


@router.post(
    "/",
    response_model=CouponsOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("coupons", "Create"))]
)
async def create_item(payload: CouponsCreate):
    """
    Create a new coupon.

    Args:
        payload: Coupon creation schema.

    Returns:
        CouponsOut: Newly created coupon.

    Raises:
        HTTPException:
            - 409 if duplicate coupon.
            - 500 on server error.
    """
    return await create_item_service(payload)


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
    """
    List coupons with optional filters.

    Args:
        skip: Pagination offset.
        limit: Page size.
        code: Exact code filter.
        type: Coupon type filter.
        coupons_status_id: Status ObjectId filter.

    Returns:
        List[CouponsOut]
    """
    return await list_items_service(skip=skip, limit=limit, code=code, type=type, coupons_status_id=coupons_status_id)


@router.get(
    "/{item_id}",
    response_model=CouponsOut,
    dependencies=[Depends(require_permission("coupons", "Read"))]
)
async def get_item(item_id: PyObjectId):
    """
    Get a coupon by its ID.

    Args:
        item_id: Coupon ObjectId.

    Returns:
        CouponsOut

    Raises:
        HTTPException:
            - 404 if not found.
            - 500 on server error.
    """
    return await get_item_service(item_id)


@router.put(
    "/{item_id}",
    response_model=CouponsOut,
    dependencies=[Depends(require_permission("coupons", "Update"))]
)
async def update_item(item_id: PyObjectId, payload: CouponsUpdate):
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
    return await update_item_service(item_id=item_id, payload=payload)


@router.delete(
    "/{item_id}",
    dependencies=[Depends(require_permission("coupons", "Delete"))],
)
async def delete_item(item_id: PyObjectId):
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
    return await delete_item_service(item_id)


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
    Validate a coupon against a provided amount.
    Returns 200 with CouponCheckOut when valid, else 400 JSON with a structured reason.

    Args:
        payload: CouponCheckIn (code, amount).

    Returns:
        CouponCheckOut on 200 OK, or JSONResponse on 400.

    Raises:
        HTTPException: 500 on server error.
    """
    return await validate_coupon_service(payload)