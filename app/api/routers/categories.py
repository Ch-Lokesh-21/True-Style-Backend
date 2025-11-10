"""
Routes for managing Categories.
Handles request validation, permissions, and delegates business logic to the service layer.
Mounted at /categories
"""

from __future__ import annotations
from typing import List, Optional, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import JSONResponse

from app.api.deps import require_permission
from app.schemas.object_id import PyObjectId
from app.schemas.categories import CategoriesCreate, CategoriesUpdate, CategoriesOut
from app.services.categories import (
    create_item_service,
    list_items_service,
    get_item_service,
    update_item_service,
    delete_item_service,
)

router = APIRouter()


@router.post(
    "/",
    response_model=CategoriesOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("categories", "Create"))],
    responses={
        201: {"description": "Category created"},
        400: {"description": "Validation error"},
        403: {"description": "Forbidden"},
        409: {"description": "Duplicate category"},
        500: {"description": "Server error"},
    },
)
async def create_item(payload: CategoriesCreate):
    """
    Create a new category.

    Args:
        payload (CategoriesCreate): Schema containing category creation fields.

    Returns:
        CategoriesOut: The newly created category record.

    Raises:
        HTTPException: 409 if duplicate, 500 on server error.
    """
    return await create_item_service(payload)


@router.get(
    "/",
    response_model=List[CategoriesOut],
    responses={
        200: {"description": "List of categories"},
        400: {"description": "Validation error"},
        403: {"description": "Forbidden"},
        500: {"description": "Server error"},
    },
)
async def list_items(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    category: Optional[str] = Query(None, description="Exact match filter"),
    q: Optional[str] = Query(None, description="Case-insensitive fuzzy search"),
):
    """
    List categories with pagination and optional search filters.

    Args:
        skip (int): Pagination offset.
        limit (int): Number of records to return.
        category (str, optional): Exact match filter.
        q (str, optional): Regex fuzzy search.

    Returns:
        List[CategoriesOut]: Paginated list of categories.
    """
    return await list_items_service(skip, limit, category, q)


@router.get(
    "/{item_id}",
    response_model=CategoriesOut,
    responses={
        200: {"description": "Category"},
        403: {"description": "Forbidden"},
        404: {"description": "Not found"},
        500: {"description": "Server error"},
    },
)
async def get_item(item_id: PyObjectId):
    """
    Get a single category by ID.

    Args:
        item_id (PyObjectId): Category ID.

    Returns:
        CategoriesOut: Category record.

    Raises:
        HTTPException: 404 if not found.
    """
    return await get_item_service(item_id)


@router.put(
    "/{item_id}",
    response_model=CategoriesOut,
    dependencies=[Depends(require_permission("categories", "Update"))],
    responses={
        200: {"description": "Updated category"},
        400: {"description": "Validation error / no fields"},
        403: {"description": "Forbidden"},
        404: {"description": "Not found"},
        409: {"description": "Duplicate category"},
        500: {"description": "Server error"},
    },
)
async def update_item(item_id: PyObjectId, payload: CategoriesUpdate):
    """
    Update a category.

    Args:
        item_id (PyObjectId): ID of category to update.
        payload (CategoriesUpdate): Partial update fields.

    Returns:
        CategoriesOut: Updated record.
    """
    return await update_item_service(item_id, payload)


@router.delete(
    "/{item_id}",
    dependencies=[Depends(require_permission("categories", "Delete"))],
    responses={
        200: {"description": "Deleted"},
        403: {"description": "Forbidden"},
        404: {"description": "Not found"},
        500: {"description": "Server error"},
    },
)
async def delete_item(item_id: PyObjectId):
    """
    Delete a category and related products.
    After deleting DB docs, performs a best-effort cleanup of stored images in GridFS.

    Args:
        item_id (PyObjectId): Category ID.

    Returns:
        JSONResponse: deletion result with optional warnings.
    """
    return await delete_item_service(item_id)