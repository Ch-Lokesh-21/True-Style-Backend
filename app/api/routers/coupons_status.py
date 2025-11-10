"""
Routes for managing Coupons Status.
Handles HTTP request parsing, RBAC, validation, and delegates business logic to services.
Mounted at /coupons-status
"""

from __future__ import annotations
from typing import List, Optional, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import JSONResponse

from app.api.deps import require_permission
from app.schemas.object_id import PyObjectId
from app.schemas.coupons_status import (
    CouponsStatusCreate,
    CouponsStatusUpdate,
    CouponsStatusOut,
)
from app.services.coupons_status import (
    create_item_service,
    list_items_service,
    get_item_service,
    update_item_service,
    delete_item_service,
)

router = APIRouter()  # mounted at /coupons-status


@router.post(
    "/",
    response_model=CouponsStatusOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("coupons_status", "Create"))]
)
async def create_item(payload: CouponsStatusCreate):
    """
    Create a coupons status record.

    Args:
        payload: Fields for the coupons status (e.g., idx, status).

    Returns:
        CouponsStatusOut: The newly created record.

    Raises:
        HTTPException:
            - 409 if a duplicate key (e.g., status) exists.
            - 500 on server error.
    """
    return await create_item_service(payload)


@router.get(
    "/",
    response_model=List[CouponsStatusOut],
    dependencies=[Depends(require_permission("coupons_status", "Read"))]
)
async def list_items(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    status_q: Optional[str] = Query(None, description="Filter by exact status"),
):
    """
    List coupons status records with optional exact status filter.

    Args:
        skip: Pagination offset.
        limit: Page size.
        status_q: Exact status string to filter by.

    Returns:
        List[CouponsStatusOut]: Paginated list of status records.

    Raises:
        HTTPException: 500 on server error.
    """
    return await list_items_service(skip=skip, limit=limit, status_q=status_q)


@router.get(
    "/{item_id}",
    response_model=CouponsStatusOut,
    dependencies=[Depends(require_permission("coupons_status", "Read"))]
)
async def get_item(item_id: PyObjectId):
    """
    Get a single coupons status record by its ID.

    Args:
        item_id: Coupons status ObjectId.

    Returns:
        CouponsStatusOut: The matching record.

    Raises:
        HTTPException:
            - 404 if not found.
            - 500 on server error.
    """
    return await get_item_service(item_id)


@router.put(
    "/{item_id}",
    response_model=CouponsStatusOut,
    dependencies=[Depends(require_permission("coupons_status", "Update"))],
)
async def update_item(item_id: PyObjectId, payload: CouponsStatusUpdate):
    """
    Update fields of a coupons status record.

    Args:
        item_id: Record ID.
        payload: Partial update fields.

    Returns:
        CouponsStatusOut: Updated record.

    Raises:
        HTTPException:
            - 400 if no fields provided.
            - 404 if not found.
            - 409 on duplicate (idx or status).
            - 500 on server error.
    """
    return await update_item_service(item_id=item_id, payload=payload)


@router.delete(
    "/{item_id}",
    dependencies=[Depends(require_permission("coupons_status", "Delete"))],
)
async def delete_item(item_id: PyObjectId):
    """
    Delete a coupons status record.

    Deletion outcomes from CRUD:
      - None: invalid ID → 400
      - False: in-use by one or more coupons → 400
      - True: deleted → 200

    Args:
        item_id: Record ID.

    Returns:
        JSONResponse: {"deleted": True} on success.

    Raises:
        HTTPException:
            - 400 for invalid ID or when status is in use.
            - 500 on server error.
    """
    return await delete_item_service(item_id=item_id)