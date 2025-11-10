"""
Routes for managing Exchange Status records.
Provides CRUD endpoints and delegates actual business logic to the service layer.
Mounted at /exchange-status
"""

from __future__ import annotations
from typing import List, Optional, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import JSONResponse

from app.api.deps import require_permission
from app.schemas.object_id import PyObjectId
from app.schemas.exchange_status import (
    ExchangeStatusCreate,
    ExchangeStatusUpdate,
    ExchangeStatusOut,
)
from app.services.exchange_status import (
    create_item_service,
    list_items_service,
    get_item_service,
    update_item_service,
    delete_item_service,
)

router = APIRouter()  # mounted in main.py at /exchange-status


@router.post(
    "/",
    response_model=ExchangeStatusOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("exchange_status", "Create"))]
)
async def create_item(payload: ExchangeStatusCreate):
    """
    Create a new exchange status.

    Args:
        payload: Fields for the exchange status.

    Returns:
        ExchangeStatusOut: Newly created record.

    Raises:
        HTTPException: 409 if duplicate, 500 otherwise.
    """
    return await create_item_service(payload)


@router.get(
    "/",
    response_model=List[ExchangeStatusOut],
    dependencies=[Depends(require_permission("exchange_status", "Read"))]
)
async def list_items(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    status_q: Optional[str] = Query(None, description="Filter by exact status"),
):
    """
    List all exchange statuses with pagination and optional filtering.

    Args:
        skip: Offset for pagination.
        limit: Number of records to return.
        status_q: Exact match on status string.

    Returns:
        List[ExchangeStatusOut]
    """
    return await list_items_service(skip=skip, limit=limit, status_q=status_q)


@router.get(
    "/{item_id}",
    response_model=ExchangeStatusOut,
    dependencies=[Depends(require_permission("exchange_status", "Read"))]
)
async def get_item(item_id: PyObjectId):
    """
    Retrieve a single exchange status by ID.

    Args:
        item_id: ObjectId of the status.

    Returns:
        ExchangeStatusOut

    Raises:
        404 if not found
    """
    return await get_item_service(item_id)


@router.put(
    "/{item_id}",
    response_model=ExchangeStatusOut,
    dependencies=[Depends(require_permission("exchange_status", "Update"))]
)
async def update_item(item_id: PyObjectId, payload: ExchangeStatusUpdate):
    """
    Update a status record.

    Args:
        item_id: Record ID.
        payload: Fields to update.

    Returns:
        ExchangeStatusOut

    Raises:
        400 No fields
        404 Not found
        409 Duplicate idx or status
    """
    return await update_item_service(item_id=item_id, payload=payload)


@router.delete(
    "/{item_id}",
    dependencies=[Depends(require_permission("exchange_status", "Delete"))]
)
async def delete_item(item_id: PyObjectId):
    """
    Delete a status.

    CRUD contract:
      - None => not found
      - False => status is in use (cannot delete)
      - True => deleted

    Returns:
        JSONResponse({"deleted": True}) on success.
    """
    return await delete_item_service(item_id)