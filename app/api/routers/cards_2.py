from __future__ import annotations
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status, UploadFile, File, Form
from fastapi.responses import JSONResponse

from app.api.deps import require_permission
from app.schemas.object_id import PyObjectId
from app.schemas.cards_2 import Cards2Out
from app.services.cards_2 import (
    create_item_service,
    list_items_service,
    get_item_service,
    update_item_service,
    delete_item_service,
)

router = APIRouter()

@router.post(
    "/",
    response_model=Cards2Out,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("cards_2","Create"))]
)
async def create_item(
    idx: int = Form(...),
    title: str = Form(...),
    image: UploadFile = File(...),
):
    """
    Create a new Cards2 item. Streams the image to GridFS and stores the resulting image_url.
    """
    return await create_item_service(idx=idx, title=title, image=image)

@router.get("/", response_model=List[Cards2Out])
async def list_items(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    sort_by_idx: bool = Query(True, description="Sort by idx asc; fallback createdAt desc"),
):
    return await list_items_service(skip=skip, limit=limit, sort_by_idx=sort_by_idx)

@router.get("/{item_id}", response_model=Cards2Out)
async def get_item(item_id: PyObjectId):
    return await get_item_service(item_id)

@router.put(
    "/{item_id}",
    response_model=Cards2Out,
    dependencies=[Depends(require_permission("cards_2","Update"))],
)
async def update_item(
    item_id: PyObjectId,
    idx: Optional[int] = Form(None),
    title: Optional[str] = Form(None),
    image: UploadFile = File(None),  # optional upload visible in Swagger
):
    """
    Update mutable fields; if a new image is provided, replace it in GridFS and update image_url.
    """
    return await update_item_service(item_id=item_id, idx=idx, title=title, image=image)

@router.delete(
    "/{item_id}",
    dependencies=[Depends(require_permission("cards_2","Delete"))],
)
async def delete_item(item_id: PyObjectId):
    return await delete_item_service(item_id)