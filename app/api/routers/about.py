from __future__ import annotations

from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status, UploadFile, File, Form

from app.schemas.object_id import PyObjectId
from app.schemas.about import AboutOut
from app.api.deps import require_permission
from app.services.about import (
    create_item_service,
    list_items_service,
    get_item_service,
    update_item_service,
    delete_item_service,
)

router = APIRouter()

@router.post(
    "/",
    response_model=AboutOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("about", "Create"))],
)
async def create_item(
    idx: int = Form(...),
    description: str = Form(...),
    image: UploadFile = File(...),
):
    return await create_item_service(idx, description, image)

@router.get("/", response_model=List[AboutOut])
async def list_items(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
):
    return await list_items_service(skip, limit)

@router.get("/{item_id}", response_model=AboutOut)
async def get_item(item_id: PyObjectId):
    return await get_item_service(item_id)

@router.put(
    "/{item_id}",
    response_model=AboutOut,
    dependencies=[Depends(require_permission("about", "Update"))],
)
async def update_item(
    item_id: PyObjectId,
    idx: Optional[int] = Form(None),
    description: Optional[str] = Form(None),
    image: Optional[UploadFile] = File(None),
):
    return await update_item_service(item_id, idx, description, image)

@router.delete(
    "/{item_id}",
    dependencies=[Depends(require_permission("about", "Delete"))],
)
async def delete_item(item_id: PyObjectId):
    return await delete_item_service(item_id)