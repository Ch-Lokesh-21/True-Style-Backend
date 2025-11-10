"""
Routes for Orders.
- User endpoints (place, list, get, self-status update) enforce ownership.
- Admin endpoints can read/update/delete any order.
- All heavy lifting is delegated to the service layer.
"""

from __future__ import annotations
from typing import List, Optional, Dict, Any

from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import JSONResponse

from app.api.deps import require_permission, get_current_user
from app.schemas.object_id import PyObjectId
from app.schemas.orders import OrdersUpdate, OrdersOut
from app.services.orders import (
    place_order_service,
    list_my_orders_service,
    get_my_order_service,
    admin_get_order_service,
    update_my_order_status_service,
    admin_update_order_status_service,
    admin_delete_order_service,
)

router = APIRouter()


@router.post(
    "/place-order",
    response_model=OrdersOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("orders", "Create"))],
)
async def place_order(
    user_id: PyObjectId,
    address_id: PyObjectId,
    payment_type_id: PyObjectId,
    # optional payment details (depending on payment type)
    card_name: Optional[str] = None,
    card_no: Optional[str] = None,
    upi_id: Optional[str] = None,
    current_user: Dict = Depends(get_current_user),
):
    """
    Create an order for the current user.

    Notes:
    - Validates payment type and required payment details.
    - Embeds address snapshot.
    - Checks and decrements product stock atomically.
    - Moves `cart_items` → `order_items`, creates payment (+ card/UPI details).
    - Clears cart items.
    - All writes occur in a single MongoDB transaction.

    Returns:
        OrdersOut
    """
    return await place_order_service(
        user_id=user_id,
        address_id=address_id,
        payment_type_id=payment_type_id,
        card_name=card_name,
        card_no=card_no,
        upi_id=upi_id,
        current_user=current_user,
    )


@router.get(
    "/my",
    response_model=List[OrdersOut],
    dependencies=[Depends(require_permission("orders", "Read"))],
)
async def list_my_orders(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    current_user: Dict = Depends(get_current_user),
):
    """List the current user's orders with pagination."""
    return await list_my_orders_service(skip=skip, limit=limit, current_user=current_user)


@router.get(
    "/my/{order_id}",
    response_model=OrdersOut,
    dependencies=[Depends(require_permission("orders", "Read"))],
)
async def get_my_order(order_id: PyObjectId, current_user: Dict = Depends(get_current_user)):
    """Get one order owned by the current user (ownership enforced)."""
    return await get_my_order_service(order_id=order_id, current_user=current_user)


@router.get(
    "/{order_id}",
    response_model=OrdersOut,
    dependencies=[Depends(require_permission("orders", "Read", "admin"))],
)
async def admin_get_order(order_id: PyObjectId):
    """Admin: get any order by id."""
    return await admin_get_order_service(order_id)


@router.put(
    "/my/{order_id}/status",
    response_model=OrdersOut,
    dependencies=[Depends(require_permission("orders", "Update"))],
)
async def update_my_order_status(
    order_id: PyObjectId,
    payload: OrdersUpdate,
    current_user: Dict = Depends(get_current_user),
):
    """
    User updates their own order status (if allowed by business policy).

    Requires:
        payload.status_id not None
    """
    return await update_my_order_status_service(order_id=order_id, payload=payload, current_user=current_user)


@router.put(
    "/{order_id}/status",
    response_model=OrdersOut,
    dependencies=[Depends(require_permission("orders", "Update", "admin"))],
)
async def admin_update_order_status(order_id: PyObjectId, payload: OrdersUpdate):
    """
    Admin: update `status_id`. Special handling:
      - If status is 'out for delivery' → generate and set a 6-digit OTP.
      - If status is 'delivered' → clear OTP.
    """
    return await admin_update_order_status_service(order_id=order_id, payload=payload)


@router.delete(
    "/{order_id}",
    dependencies=[Depends(require_permission("orders", "Delete"))],
)
async def admin_delete_order(order_id: PyObjectId):
    """
    Admin: transactionally delete one order and related documents:
      - order_items
      - payments
      - upi_details / card_details
    """
    return await admin_delete_order_service(order_id)