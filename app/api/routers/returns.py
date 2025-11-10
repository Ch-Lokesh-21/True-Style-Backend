"""
Routes for managing Returns.
- Handles request parsing, RBAC, and delegates business logic to the service layer.
- Auto-derives delivery_date from the order (via order_item_id → order_id).
"""

from __future__ import annotations
from typing import List, Optional, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status, UploadFile, File, Form
from fastapi.responses import JSONResponse

from app.api.deps import require_permission, get_current_user
from app.schemas.object_id import PyObjectId
from app.schemas.returns import ReturnsUpdate, ReturnsOut
from app.services.returns import (
    create_return_service,
    list_my_returns_service,
    get_my_return_service,
    admin_list_returns_service,
    admin_get_return_service,
    admin_update_return_status_service,
    admin_delete_return_service,
)

router = APIRouter()


@router.post(
    "/",
    response_model=ReturnsOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("returns", "Create"))],
)
async def create_return(
    order_item_id: PyObjectId = Form(...),
    quantity: int = Form(..., description="Quantity to return"),
    reason: Optional[str] = Form(None),
    image: UploadFile = File(None),
    current_user: Dict = Depends(get_current_user),
):
    """
    Create a return for an order item owned by the current user.

    Notes:
    - Validates ownership and available quantity (ordered - already returned).
    - Computes refund amount = unit_price * quantity.
    - Sets return_status to 'requested'.
    - If `image` is provided, uploads to GridFS and stores the URL.
    - **Delivery date is auto-fetched** from the order and must be within the last 7 days.

    Args:
        order_item_id: Target order item id.
        quantity: Number of units to return (must be > 0).
        reason: Optional user-provided reason.
        image: Optional photo evidence (stored in GridFS).
        current_user: Injected current user.

    Returns:
        ReturnsOut: Newly created return record.
    """
    return await create_return_service(
        order_item_id=order_item_id,
        quantity=quantity,
        reason=reason,
        image=image,
        current_user=current_user,
    )


# ---------- USER: list & get my returns ----------

@router.get(
    "/my",
    response_model=List[ReturnsOut],
    dependencies=[Depends(require_permission("returns", "Read"))],
)
async def list_my_returns(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    current_user: Dict = Depends(get_current_user),
):
    """
    List returns created by the current user.

    Args:
        skip: Pagination offset.
        limit: Page size.
        current_user: Injected user.

    Returns:
        List[ReturnsOut]
    """
    return await list_my_returns_service(skip=skip, limit=limit, current_user=current_user)


@router.get(
    "/my/{return_id}",
    response_model=ReturnsOut,
    dependencies=[Depends(require_permission("returns", "Read"))],
)
async def get_my_return(
    return_id: PyObjectId,
    current_user: Dict = Depends(get_current_user),
):
    """
    Get a single return that belongs to the current user.

    Args:
        return_id: Return ObjectId.
        current_user: Injected user.

    Returns:
        ReturnsOut

    Raises:
        403 if the return does not belong to the current user.
    """
    return await get_my_return_service(return_id=return_id, current_user=current_user)


# ---------- ADMIN: list/get/update/delete ----------

@router.get(
    "/",
    response_model=List[ReturnsOut],
    dependencies=[Depends(require_permission("returns", "Read", "admin"))],
)
async def admin_list_returns(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    user_id: Optional[PyObjectId] = Query(None),
    order_id: Optional[PyObjectId] = Query(None),
    product_id: Optional[PyObjectId] = Query(None),
    return_status_id: Optional[PyObjectId] = Query(None),
):
    """
    Admin: list returns with optional filters.

    Args:
        skip, limit: Pagination.
        user_id, order_id, product_id, return_status_id: Optional filters.

    Returns:
        List[ReturnsOut]
    """
    return await admin_list_returns_service(
        skip=skip,
        limit=limit,
        user_id=user_id,
        order_id=order_id,
        product_id=product_id,
        return_status_id=return_status_id,
    )


@router.get(
    "/{return_id}",
    response_model=ReturnsOut,
    dependencies=[Depends(require_permission("returns", "Read", "admin"))],
)
async def admin_get_return(return_id: PyObjectId):
    """
    Admin: get a return by ID.

    Args:
        return_id: Return ObjectId.

    Returns:
        ReturnsOut
    """
    return await admin_get_return_service(return_id)


@router.put(
    "/{return_id}/status",
    response_model=ReturnsOut,
    dependencies=[Depends(require_permission("returns", "Update", "admin"))],
)
async def admin_update_return_status(
    return_id: PyObjectId,
    payload: ReturnsUpdate,
):
    """
    Admin: update return status only.

    Args:
        return_id: Return ObjectId.
        payload: ReturnsUpdate (expects return_status_id).

    Returns:
        ReturnsOut

    Raises:
        400 if return_status_id missing.
    """
    return await admin_update_return_status_service(return_id=return_id, payload=payload)


@router.delete(
    "/{return_id}",
    dependencies=[Depends(require_permission("returns", "Delete"))]
)
async def admin_delete_return(return_id: PyObjectId):
    """
    Admin: delete a return.

    Args:
        return_id: Return ObjectId.

    Returns:
        JSONResponse({"deleted": True})
    """
    return await admin_delete_return_service(return_id)