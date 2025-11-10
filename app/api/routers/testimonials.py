"""
API Router for Testimonials.

Responsibilities:
- Enforce permissions
- Parse form/file inputs
- Delegate to the testimonials service
"""

from __future__ import annotations
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status, UploadFile, File, Form
from fastapi.responses import JSONResponse

from app.api.deps import require_permission
from app.schemas.object_id import PyObjectId
from app.schemas.testimonials import TestimonialsCreate, TestimonialsUpdate, TestimonialsOut
from app.services.testimonials import (
    create_testimonial,
    list_testimonials,
    get_testimonial,
    update_testimonial,
    delete_testimonial,
)

router = APIRouter()


@router.post(
    "/",
    response_model=TestimonialsOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("testimonials", "Create"))],
)
async def create_item(
    idx: int = Form(...),
    description: str = Form(...),
    image: UploadFile = File(...),
):
    """Route: create testimonial (handles file upload via service)."""
    return await create_testimonial(idx=idx, description=description, image=image)


@router.get(
    "/",
    response_model=List[TestimonialsOut],
)
async def list_items(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    sort_by_idx: bool = Query(True, description="Sort by idx asc; fallback createdAt desc"),
):
    """Route: list testimonials with optional sorting."""
    return await list_testimonials(skip=skip, limit=limit, sort_by_idx=sort_by_idx)


@router.get(
    "/{item_id}",
    response_model=TestimonialsOut,
)
async def get_item(item_id: PyObjectId):
    """Route: fetch single testimonial by id."""
    return await get_testimonial(item_id)


@router.put(
    "/{item_id}",
    response_model=TestimonialsOut,
    dependencies=[Depends(require_permission("testimonials", "Update"))],
)
async def update_item(
    item_id: PyObjectId,
    idx: Optional[int] = Form(None),
    description: Optional[str] = Form(None),
    image: UploadFile = File(None),
):
    """Route: update testimonial fields and/or image."""
    return await update_testimonial(
        item_id=item_id,
        idx=idx,
        description=description,
        image=image,
    )


@router.delete(
    "/{item_id}",
    dependencies=[Depends(require_permission("testimonials", "Delete"))],
)
async def delete_item(item_id: PyObjectId):
    """
    Route: delete testimonial and best-effort remove the GridFS file afterwards.
    """
    return await delete_testimonial(item_id)