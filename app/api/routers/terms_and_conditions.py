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
from app.crud import terms_and_conditions as crud

router = APIRouter()


def _raise_conflict_if_dup(err: Exception, field_hint: Optional[str] = None):
    msg = str(err)
    if "E11000" in msg:
        detail = "Duplicate key." if not field_hint else f"Duplicate {field_hint}."
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=detail)
    # not a dup-key → bubble up
    raise err


@router.post(
    "/",
    response_model=TermsAndConditionsOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("terms_and_conditions", "Create"))],
    responses={
        201: {"description": "Terms & Conditions created"},
        400: {"description": "Validation error"},
        403: {"description": "Forbidden"},
        409: {"description": "Duplicate idx"},
        500: {"description": "Server error"},
    },
)
async def create_item(payload: TermsAndConditionsCreate):
    try:
        created = await crud.create(payload)
        return created
    except HTTPException:
        raise
    except Exception as e:
        try:
            _raise_conflict_if_dup(e, field_hint="idx")
        except Exception as e2:
            raise HTTPException(status_code=500, detail=f"Failed to create Terms & Conditions: {e2}")


@router.get(
    "/",
    response_model=List[TermsAndConditionsOut],
    dependencies=[Depends(require_permission("terms_and_conditions", "Read"))],
    responses={
        200: {"description": "List of Terms & Conditions"},
        403: {"description": "Forbidden"},
        500: {"description": "Server error"},
    },
)
async def list_items(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    sort_by_idx: bool = Query(True, description="Sort by idx asc; fallback createdAt desc"),
):
    try:
        return await crud.list_all(skip=skip, limit=limit, sort_by_idx=sort_by_idx)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list Terms & Conditions: {e}")


@router.get(
    "/{item_id}",
    response_model=TermsAndConditionsOut,
    dependencies=[Depends(require_permission("terms_and_conditions", "Read"))],
    responses={
        200: {"description": "Terms & Conditions"},
        403: {"description": "Forbidden"},
        404: {"description": "Not found"},
        500: {"description": "Server error"},
    },
)
async def get_item(item_id: PyObjectId):
    try:
        d = await crud.get_one(item_id)
        if not d:
            raise HTTPException(404, "Terms & Conditions not found")
        return d
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get Terms & Conditions: {e}")


@router.put(
    "/{item_id}",
    response_model=TermsAndConditionsOut,
    dependencies=[Depends(require_permission("terms_and_conditions", "Update"))],
    responses={
        200: {"description": "Updated Terms & Conditions"},
        400: {"description": "Validation error / no fields"},
        403: {"description": "Forbidden"},
        404: {"description": "Not found"},
        409: {"description": "Duplicate idx"},
        500: {"description": "Server error"},
    },
)
async def update_item(item_id: PyObjectId, payload: TermsAndConditionsUpdate):
    try:
        data = {k: v for k, v in payload.model_dump().items() if v is not None}
        if not data:
            raise HTTPException(status_code=400, detail="No fields provided for update")

        updated = await crud.update_one(item_id, payload)
        if not updated:
            raise HTTPException(404, "Terms & Conditions not found")
        return updated
    except HTTPException:
        raise
    except Exception as e:
        try:
            _raise_conflict_if_dup(e, field_hint="idx")
        except Exception as e2:
            raise HTTPException(status_code=500, detail=f"Failed to update Terms & Conditions: {e2}")


@router.delete(
    "/{item_id}",
    dependencies=[Depends(require_permission("terms_and_conditions", "Delete"))],
    responses={
        200: {"description": "Deleted"},
        400: {"description": "Invalid ID"},
        403: {"description": "Forbidden"},
        404: {"description": "Not found"},
        500: {"description": "Server error"},
    },
)
async def delete_item(item_id: PyObjectId):
    try:
        ok = await crud.delete_one(item_id)
        if ok is None:
            raise HTTPException(status_code=400, detail="Invalid Terms & Conditions ID.")
        if ok is False:
            raise HTTPException(status_code=404, detail="Terms & Conditions not found")
        return JSONResponse(status_code=200, content={"deleted": True})
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete Terms & Conditions: {e}")