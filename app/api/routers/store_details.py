"""
API Router for Store Details.

Handles HTTP layer:
 - permissions
 - request/response validation
 - calling service functions
"""

from __future__ import annotations
from typing import List, Optional, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import JSONResponse

from app.api.deps import require_permission
from app.schemas.object_id import PyObjectId
from app.schemas.store_details import (
    StoreDetailsCreate,
    StoreDetailsUpdate,
    StoreDetailsOut,
)
from app.services.store_details import (
    create_store_details,
    list_store_details,
    get_store_details,
    update_store_details,
    delete_store_details,
)

router = APIRouter()  # mounted at /store-details


@router.post(
    "/",
    response_model=StoreDetailsOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("store_details", "Create"))],
    responses={
        201: {"description": "Store details created"},
        400: {"description": "Validation error"},
        403: {"description": "Forbidden"},
        409: {"description": "Duplicate (PAN/GST)"},
        500: {"description": "Server error"},
    },
)
async def create_item(payload: StoreDetailsCreate):
    """Route: create store details."""
    return await create_store_details(payload)


@router.get(
    "/",
    response_model=List[StoreDetailsOut],
    responses={
        200: {"description": "List of store details"},
        403: {"description": "Forbidden"},
        500: {"description": "Server error"},
    },
)
async def list_items(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
):
    """Route: list store details with pagination."""
    return await list_store_details(skip, limit)


@router.get(
    "/{item_id}",
    response_model=StoreDetailsOut,
    responses={
        200: {"description": "Store details"},
        403: {"description": "Forbidden"},
        404: {"description": "Not found"},
        500: {"description": "Server error"},
    },
)
async def get_item(item_id: PyObjectId):
    """Route: get a single store details doc."""
    return await get_store_details(item_id)


@router.put(
    "/{item_id}",
    response_model=StoreDetailsOut,
    dependencies=[Depends(require_permission("store_details", "Update"))],
    responses={
        200: {"description": "Updated store details"},
        400: {"description": "Validation error / no fields"},
        403: {"description": "Forbidden"},
        404: {"description": "Not found"},
        409: {"description": "Duplicate (PAN/GST)"},
        500: {"description": "Server error"},
    },
)
async def update_item(item_id: PyObjectId, payload: StoreDetailsUpdate):
    """Route: update store details."""
    return await update_store_details(item_id, payload)


@router.delete(
    "/{item_id}",
    dependencies=[Depends(require_permission("store_details", "Delete"))],
    responses={
        200: {"description": "Deleted"},
        400: {"description": "Invalid ID"},
        403: {"description": "Forbidden"},
        404: {"description": "Not found"},
        500: {"description": "Server error"},
    },
)
async def delete_item(item_id: PyObjectId):
    """Route: delete store details."""
    return await delete_store_details(item_id)