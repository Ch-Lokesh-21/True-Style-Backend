"""
API Router for Terms & Conditions.

Handles:
 - permissions
 - request/response parsing
 - delegates to service layer
"""

from __future__ import annotations
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import JSONResponse

from app.api.deps import require_permission
from app.schemas.object_id import PyObjectId
from app.schemas.terms_and_conditions import (
    TermsAndConditionsCreate,
    TermsAndConditionsUpdate,
    TermsAndConditionsOut,
)
from app.services.terms_and_conditions import (
    create_terms,
    list_terms,
    get_terms,
    update_terms,
    delete_terms,
)

router = APIRouter()  # mounted at /terms-and-conditions


@router.post(
    "/",
    response_model=TermsAndConditionsOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("terms_and_conditions", "Create"))],
)
async def create_item(payload: TermsAndConditionsCreate):
    """Route: create Terms & Conditions."""
    return await create_terms(payload)


@router.get(
    "/",
    response_model=List[TermsAndConditionsOut],
    dependencies=[Depends(require_permission("terms_and_conditions", "Read"))],
)
async def list_items(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    sort_by_idx: bool = Query(True),
):
    """Route: list Terms & Conditions with optional sorting."""
    return await list_terms(skip, limit, sort_by_idx)


@router.get(
    "/{item_id}",
    response_model=TermsAndConditionsOut,
    dependencies=[Depends(require_permission("terms_and_conditions", "Read"))],
)
async def get_item(item_id: PyObjectId):
    """Route: get a single Terms & Conditions document."""
    return await get_terms(item_id)


@router.put(
    "/{item_id}",
    response_model=TermsAndConditionsOut,
    dependencies=[Depends(require_permission("terms_and_conditions", "Update"))],
)
async def update_item(item_id: PyObjectId, payload: TermsAndConditionsUpdate):
    """Route: update Terms & Conditions."""
    return await update_terms(item_id, payload)


@router.delete(
    "/{item_id}",
    dependencies=[Depends(require_permission("terms_and_conditions", "Delete"))],
)
async def delete_item(item_id: PyObjectId):
    """Route: delete Terms & Conditions."""
    return await delete_terms(item_id)