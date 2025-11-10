"""
Routes for Payment Status.
- Thin HTTP layer: parses requests, applies RBAC, delegates to service.
"""

from __future__ import annotations
from typing import List, Optional, Dict, Any

from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import JSONResponse

from app.api.deps import require_permission
from app.schemas.object_id import PyObjectId
from app.schemas.payment_status import (
    PaymentStatusCreate,
    PaymentStatusUpdate,
    PaymentStatusOut,
)
from app.services.payment_status import (
    create_item_service,
    list_items_service,
    get_item_service,
    update_item_service,
    delete_item_service,
)

router = APIRouter()  # mounted in main.py at /payment-status


@router.post(
    "/",
    response_model=PaymentStatusOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("payment_status", "Create"))]
)
async def create_item(payload: PaymentStatusCreate):
    """
    Create a payment status.

    Args:
        payload: PaymentStatusCreate.

    Returns:
        PaymentStatusOut

    Raises:
        409 on duplicate key (idx or status), if unique index exists.
    """
    return await create_item_service(payload)


@router.get(
    "/",
    response_model=List[PaymentStatusOut],
    dependencies=[Depends(require_permission("payment_status", "Read"))]
)
async def list_items(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    status_q: Optional[str] = Query(None, description="Filter by exact status"),
):
    """
    List payment statuses with optional exact `status` filter.

    Args:
        skip: Offset.
        limit: Limit.
        status_q: Optional exact status match.

    Returns:
        List[PaymentStatusOut]
    """
    q: Dict[str, Any] = {}
    if status_q:
        q["status"] = status_q
    return await list_items_service(skip=skip, limit=limit, query=q or None)


@router.get(
    "/{item_id}",
    response_model=PaymentStatusOut,
    dependencies=[Depends(require_permission("payment_status", "Read"))]
)
async def get_item(item_id: PyObjectId):
    """
    Get a single payment status by id.

    Args:
        item_id: Payment status ObjectId.

    Returns:
        PaymentStatusOut

    Raises:
        404 if not found.
    """
    return await get_item_service(item_id)


@router.put(
    "/{item_id}",
    response_model=PaymentStatusOut,
    dependencies=[Depends(require_permission("payment_status", "Update"))]
)
async def update_item(item_id: PyObjectId, payload: PaymentStatusUpdate):
    """
    Update a payment status.

    Args:
        item_id: Payment status ObjectId.
        payload: PaymentStatusUpdate (must contain at least one field).

    Returns:
        PaymentStatusOut

    Raises:
        400 if no fields provided.
        404 if not found.
        409 on duplicate (idx or status).
    """
    return await update_item_service(item_id=item_id, payload=payload)


@router.delete(
    "/{item_id}",
    dependencies=[Depends(require_permission("payment_status", "Delete"))]
)
async def delete_item(item_id: PyObjectId):
    """
    Delete a payment status.

    Delete semantics (per CRUD contract):
      - If `ok is None`: ID invalid → 400.
      - If `ok is False`: status in use by payments → 400.
      - If `ok is True`: return 200 with {"deleted": True}.

    Args:
        item_id: Payment status ObjectId.

    Returns:
        JSONResponse({"deleted": True})
    """
    return await delete_item_service(item_id)