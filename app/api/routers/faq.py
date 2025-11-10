"""
Routes for managing FAQ entries.
- Handles request parsing, RBAC, and delegates all logic to the service layer.
"""

from __future__ import annotations
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status, UploadFile, File, Form
from fastapi.responses import JSONResponse

from app.api.deps import require_permission
from app.schemas.object_id import PyObjectId
from app.schemas.faq import FaqUpdate, FaqOut
from app.services.faq import (
    create_item_service,
    list_items_service,
    get_item_service,
    update_item_service,
    delete_item_service,
)

router = APIRouter()


@router.post(
    "/",
    response_model=FaqOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("faq","Create"))],
)
async def create_item(
    idx: int = Form(...),
    question: str = Form(...),
    answer: str = Form(...),
    image: UploadFile = File(None),
):
    """
    Create an FAQ entry.

    Notes:
    - If `image` is provided, it will be streamed to GridFS and the `image_url` stored.
    - Current schema expects an image; we enforce presence with a 400 if `image` is omitted.

    Args:
        idx: Display/index order.
        question: Question text.
        answer: Answer text.
        image: Optional file upload; required by business rules.

    Returns:
        FaqOut: Newly created FAQ.
    """
    return await create_item_service(idx=idx, question=question, answer=answer, image=image)


@router.get("/", response_model=List[FaqOut])
async def list_items(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    sort_by_idx: bool = Query(True, description="Sort by idx asc; fallback createdAt desc"),
):
    """
    List FAQs with pagination.

    Args:
        skip: Offset for pagination.
        limit: Page size.
        sort_by_idx: Whether to sort by idx ascending.

    Returns:
        List[FaqOut]
    """
    return await list_items_service(skip=skip, limit=limit, sort_by_idx=sort_by_idx)


@router.get("/{item_id}", response_model=FaqOut)
async def get_item(item_id: PyObjectId):
    """
    Get a single FAQ by its ID.

    Args:
        item_id: FAQ ObjectId.

    Returns:
        FaqOut

    Raises:
        404 if not found.
    """
    return await get_item_service(item_id)


@router.put(
    "/{item_id}",
    response_model=FaqOut,
    dependencies=[Depends(require_permission("faq","Update"))],
)
async def update_item(
    item_id: PyObjectId,
    idx: Optional[int] = Form(None),
    question: Optional[str] = Form(None),
    answer: Optional[str] = Form(None),
    image: UploadFile = File(None),
):
    """
    Update FAQ fields. If `image` is provided, the old GridFS image is replaced and `image_url` updated.

    Args:
        item_id: FAQ ObjectId.
        idx: New display order.
        question: New question text.
        answer: New answer text.
        image: Optional new image file to replace the existing one.

    Returns:
        FaqOut

    Raises:
        400 if no fields provided.
        404 if not found.
        409 on duplicate idx.
    """
    return await update_item_service(
        item_id=item_id,
        idx=idx,
        question=question,
        answer=answer,
        image=image,
    )


@router.delete(
    "/{item_id}",
    dependencies=[Depends(require_permission("faq","Delete"))],
)
async def delete_item(item_id: PyObjectId):
    """
    Delete an FAQ and its GridFS image if present.

    Args:
        item_id: FAQ ObjectId.

    Returns:
        JSONResponse: {"deleted": True}
    """
    return await delete_item_service(item_id)