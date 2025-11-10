from __future__ import annotations
from typing import List, Optional, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import JSONResponse

from app.api.deps import require_permission
from app.schemas.object_id import PyObjectId
from app.schemas.brands import BrandsCreate, BrandsUpdate, BrandsOut
from app.services.brands import (
    create_item_service,
    list_items_service,
    get_item_service,
    update_item_service,
    delete_item_service,
)

router = APIRouter()

@router.post(
    "/",
    response_model=BrandsOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("brands", "Create"))],
    responses={
        201: {"description": "Brand created"},
        400: {"description": "Validation error"},
        403: {"description": "Forbidden"},
        409: {"description": "Duplicate brand"},
        500: {"description": "Server error"},
    },
)
async def create_item(payload: BrandsCreate):
    return await create_item_service(payload)

@router.get(
    "/",
    response_model=List[BrandsOut],
    responses={
        200: {"description": "List of brands"},
        400: {"description": "Validation error"},
        500: {"description": "Server error"},
    },
)
async def list_items(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    name: Optional[str] = Query(None, description="Exact match filter for brand name"),
    q: Optional[str] = Query(None, description="Case-insensitive search on name"),
):
    return await list_items_service(skip=skip, limit=limit, name=name, q=q)

@router.get(
    "/{item_id}",
    response_model=BrandsOut,
    responses={
        200: {"description": "Brand"},
        404: {"description": "Not found"},
        500: {"description": "Server error"},
    },
)
async def get_item(item_id: PyObjectId):
    return await get_item_service(item_id)

@router.put(
    "/{item_id}",
    response_model=BrandsOut,
    dependencies=[Depends(require_permission("brands", "Update"))],
    responses={
        200: {"description": "Updated brand"},
        400: {"description": "Validation error / no fields"},
        404: {"description": "Not found"},
        409: {"description": "Duplicate brand"},
        500: {"description": "Server error"},
    },
)
async def update_item(item_id: PyObjectId, payload: BrandsUpdate):
    return await update_item_service(item_id, payload)

@router.delete(
    "/{item_id}",
    dependencies=[Depends(require_permission("brands", "Delete"))],
    responses={
        200: {"description": "Deleted"},
        404: {"description": "Not found"},
        500: {"description": "Server error"},
    },
)
async def delete_item(item_id: PyObjectId):
    return await delete_item_service(item_id)