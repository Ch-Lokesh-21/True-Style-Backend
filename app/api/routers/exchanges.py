"""
Routes for managing Exchanges.
- Handles request parsing, RBAC, and delegates business logic to services.
- Includes user endpoints and admin endpoints.
"""

from __future__ import annotations
from typing import List, Optional, Dict, Any
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status, UploadFile, File, Form
from fastapi.responses import JSONResponse

from app.api.deps import require_permission, get_current_user
from app.schemas.object_id import PyObjectId
from app.schemas.exchanges import ExchangesUpdate, ExchangesOut
from app.services.exchanges import (
    create_exchange_service,
    list_my_exchanges_service,
    get_my_exchange_service,
    admin_list_exchanges_service,
    admin_get_exchange_service,
    admin_update_exchange_status_service,
    admin_delete_exchange_service,
)

router = APIRouter()


@router.post(
    "/",
    response_model=ExchangesOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("exchanges", "Create"))],
)
async def create_exchange(
    order_item_id: PyObjectId = Form(...),
    reason: Optional[str] = Form(None),
    image: UploadFile = File(None),
    new_quantity: int = Form(...),
    new_size: Optional[str] = Form(None),
    current_user: Dict = Depends(get_current_user),
):
    """
    Create an exchange for a single order item.

    Notes:
    - Derives `order_id` and `product_id` from `order_items`.
    - Verifies the order belongs to the current user.
    - Forces `exchange_status` to "requested".
    - Enforces delivery window: delivery_date must be within the last 7 days (inclusive).

    Args:
        order_item_id: The order item to exchange.
        reason: Optional reason provided by the user.
        image: Optional image to upload to GridFS.
        new_quantity: Desired quantity for the exchange.
        new_size: Desired size for the exchange (if applicable).
        delivery_date: The date the order was delivered (YYYY-MM-DD).
        current_user: Injected current user.

    Returns:
        ExchangesOut: The created exchange.
    """
    return await create_exchange_service(
        order_item_id=order_item_id,
        reason=reason,
        image=image,
        new_quantity=new_quantity,
        new_size=new_size,
        current_user=current_user,
    )


@router.get(
    "/my",
    response_model=List[ExchangesOut],
    dependencies=[Depends(require_permission("exchanges", "Read"))],
)
async def list_my_exchanges(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    current_user: Dict = Depends(get_current_user),
):
    """
    List exchanges created by the current user.

    Args:
        skip: Pagination offset.
        limit: Page size.
        current_user: Injected current user.

    Returns:
        List[ExchangesOut]
    """
    return await list_my_exchanges_service(skip=skip, limit=limit, current_user=current_user)


@router.get(
    "/my/{item_id}",
    response_model=ExchangesOut,
    dependencies=[Depends(require_permission("exchanges", "Read"))],
)
async def get_my_exchange(item_id: PyObjectId, current_user: Dict = Depends(get_current_user)):
    """
    Get a single exchange created by the current user.

    Args:
        item_id: Exchange ObjectId.
        current_user: Injected current user.

    Returns:
        ExchangesOut

    Raises:
        403 if the exchange does not belong to the current user.
    """
    return await get_my_exchange_service(item_id=item_id, current_user=current_user)


# -------------------- Admin endpoints --------------------

@router.get(
    "/",
    response_model=List[ExchangesOut],
    dependencies=[Depends(require_permission("exchanges", "Read", "admin"))],
)
async def admin_list_exchanges(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    user_id: Optional[PyObjectId] = Query(None),
    order_id: Optional[PyObjectId] = Query(None),
    product_id: Optional[PyObjectId] = Query(None),
    exchange_status_id: Optional[PyObjectId] = Query(None),
):
    """
    Admin: List exchanges with optional filters.

    Args:
        skip: Pagination offset.
        limit: Page size.
        user_id: Filter by user.
        order_id: Filter by order.
        product_id: Filter by product.
        exchange_status_id: Filter by status id.

    Returns:
        List[ExchangesOut]
    """
    return await admin_list_exchanges_service(
        skip=skip,
        limit=limit,
        user_id=user_id,
        order_id=order_id,
        product_id=product_id,
        exchange_status_id=exchange_status_id,
    )


@router.get(
    "/{item_id}",
    response_model=ExchangesOut,
    dependencies=[Depends(require_permission("exchanges", "Read", "admin"))],
)
async def admin_get_exchange(item_id: PyObjectId):
    """
    Admin: Get a single exchange by ID.

    Args:
        item_id: Exchange ObjectId.

    Returns:
        ExchangesOut
    """
    return await admin_get_exchange_service(item_id)


@router.put(
    "/{item_id}/status",
    response_model=ExchangesOut,
    dependencies=[Depends(require_permission("exchanges", "Update", "admin"))],
)
async def admin_update_exchange_status(item_id: PyObjectId, payload: ExchangesUpdate):
    """
    Admin: Update exchange status only.

    Args:
        item_id: Exchange ObjectId.
        payload: ExchangesUpdate (expects exchange_status_id).

    Returns:
        ExchangesOut

    Raises:
        400 if exchange_status_id missing.
    """
    return await admin_update_exchange_status_service(item_id=item_id, payload=payload)


@router.delete(
    "/{item_id}",
    dependencies=[Depends(require_permission("exchanges", "Delete", "admin"))],
)
async def admin_delete_exchange(item_id: PyObjectId):
    """
    Admin: Delete an exchange and remove its GridFS-backed image if present.

    Args:
        item_id: Exchange ObjectId.

    Returns:
        JSONResponse({"deleted": True})
    """
    return await admin_delete_exchange_service(item_id)