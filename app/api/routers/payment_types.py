"""
Routes for Payment Types.
- Thin HTTP layer: parses/validates inputs, applies RBAC, and delegates to the service layer.
"""

from __future__ import annotations
from typing import List, Optional, Dict, Any

from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import JSONResponse

from app.api.deps import require_permission
from app.schemas.object_id import PyObjectId
from app.schemas.payment_types import (
    PaymentTypesCreate,
    PaymentTypesUpdate,
    PaymentTypesOut,
)
from app.services.payment_types import (
    create_item_service,
    list_items_service,
    get_item_service,
    update_item_service,
    delete_item_service,
)

router = APIRouter()  # mount in main.py with prefix="/payment-types"


@router.post(
    "/",
    response_model=PaymentTypesOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("payment_types", "Create"))],
)
async def create_item(payload: PaymentTypesCreate):
    """
    Create a payment type.

    Args:
        payload: PaymentTypesCreate.

    Returns:
        PaymentTypesOut

    Raises:
        409 on duplicate (idx or type), if unique index exists.
    """
    return await create_item_service(payload)


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
    """
    List payment types with optional exact `type` filter.

    Args:
        skip: Pagination offset.
        limit: Page size.
        type_q: Optional exact match on the `type` field.

    Returns:
        List[PaymentTypesOut]
    """
    q: Dict[str, Any] = {}
    if type_q:
        q["type"] = type_q
    return await list_items_service(skip=skip, limit=limit, query=q or None)


@router.get(
    "/{item_id}",
    response_model=PaymentTypesOut,
    dependencies=[Depends(require_permission("payment_types", "Read"))],
)
async def get_item(item_id: PyObjectId):
    """
    Get a single payment type by id.

    Args:
        item_id: Payment type ObjectId.

    Returns:
        PaymentTypesOut

    Raises:
        404 if not found.
    """
    return await get_item_service(item_id)


@router.put(
    "/{item_id}",
    response_model=PaymentTypesOut,
    dependencies=[Depends(require_permission("payment_types", "Update"))],
)
async def update_item(item_id: PyObjectId, payload: PaymentTypesUpdate):
    """
    Update a payment type.

    Args:
        item_id: Payment type ObjectId.
        payload: PaymentTypesUpdate (must include at least one field).

    Returns:
        PaymentTypesOut

    Raises:
        400 if no fields provided.
        404 if not found.
        409 on duplicate (idx or type).
    """
    return await update_item_service(item_id=item_id, payload=payload)


@router.delete(
    "/{item_id}",
    dependencies=[Depends(require_permission("payment_types", "Delete"))],
)
async def delete_item(item_id: PyObjectId):
    """
    Delete a payment type.

    Delete semantics (per CRUD contract):
      - If `ok is None`: ID invalid → 400.
      - If `ok is False`: type in use by payments → 400.
      - If `ok is True`: return 200 with {"deleted": True}.

    Args:
        item_id: Payment type ObjectId.

    Returns:
        JSONResponse({"deleted": True})
    """
    return await delete_item_service(item_id)