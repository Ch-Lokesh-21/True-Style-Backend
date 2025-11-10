"""
Routes for Policies.
- Thin HTTP layer: parses/validates inputs, applies RBAC, and delegates to the service layer.
"""

from __future__ import annotations
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status, UploadFile, File, Form
from fastapi.responses import JSONResponse

from app.api.deps import require_permission
from app.schemas.object_id import PyObjectId
from app.schemas.policies import PoliciesCreate, PoliciesUpdate, PoliciesOut
from app.services.policies import (
    create_item_service,
    list_items_service,
    get_item_service,
    update_item_service,
    delete_item_service,
)

router = APIRouter()


@router.post(
    "/",
    response_model=PoliciesOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("policies","Create"))],
)
async def create_item(
    idx: int = Form(...),
    title: str = Form(...),
    description: str = Form(...),
    image: UploadFile = File(...),
):
    """
    Create a policy: upload image to GridFS and store the resulting image_url.

    Args:
        idx: Display/order index.
        title: Policy title.
        description: Policy description.
        image: Image file to store in GridFS.

    Returns:
        PoliciesOut
    """
    return await create_item_service(idx=idx, title=title, description=description, image=image)


@router.get("/", response_model=List[PoliciesOut])
async def list_items(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    sort_by_idx: bool = Query(True, description="Sort by idx asc; fallback createdAt desc"),
):
    """
    List policies with pagination.

    Args:
        skip: Pagination offset.
        limit: Page size.
        sort_by_idx: If True, sort by idx ascending; otherwise fallback to createdAt desc.

    Returns:
        List[PoliciesOut]
    """
    return await list_items_service(skip=skip, limit=limit, sort_by_idx=sort_by_idx)


@router.get("/{item_id}", response_model=PoliciesOut)
async def get_item(item_id: PyObjectId):
    """
    Get a single policy by id.

    Args:
        item_id: Policy ObjectId.

    Returns:
        PoliciesOut

    Raises:
        404 if not found.
    """
    return await get_item_service(item_id)


@router.put(
    "/{item_id}",
    response_model=PoliciesOut,
    dependencies=[Depends(require_permission("policies","Update"))],
)
async def update_item(
    item_id: PyObjectId,
    idx: Optional[int] = Form(None),
    title: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    image: UploadFile = File(None),
):
    """
    Update idx/title/description; if an image is provided, replace it in GridFS and update image_url.

    Args:
        item_id: Policy ObjectId.
        idx: Optional new idx.
        title: Optional new title.
        description: Optional new description.
        image: Optional new image file (GridFS). Use File(None) to show upload control in docs.

    Returns:
        PoliciesOut

    Raises:
        400 if no fields provided.
        404 if not found.
        409 on duplicate idx (if unique index).
    """
    return await update_item_service(
        item_id=item_id,
        idx=idx,
        title=title,
        description=description,
        image=image,  # optional in router
    )


@router.delete("/{item_id}", dependencies=[Depends(require_permission("policies","Delete"))])
async def delete_item(item_id: PyObjectId):
    """
    Delete a policy; if it has a GridFS image, delete the file too.

    Args:
        item_id: Policy ObjectId.

    Returns:
        JSONResponse({"deleted": True})

    Raises:
        404 if not found.
    """
    return await delete_item_service(item_id)