"""
Service layer for Terms & Conditions.

Contains business logic only:
 - CRUD operations via crud layer
 - duplicate handling
 - raises clean HTTP exceptions
"""

from __future__ import annotations
from typing import Optional, List
from fastapi import HTTPException, status
from fastapi.responses import JSONResponse

from app.schemas.object_id import PyObjectId
from app.schemas.terms_and_conditions import (
    TermsAndConditionsCreate,
    TermsAndConditionsUpdate,
    TermsAndConditionsOut,
)
from app.crud import terms_and_conditions as crud


def _raise_conflict_if_dup(err: Exception, field_hint: Optional[str] = None):
    """Map MongoDB duplicate key errors to HTTP 409."""
    msg = str(err)
    if "E11000" in msg:
        detail = "Duplicate key." if not field_hint else f"Duplicate {field_hint}."
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=detail)
    raise err


async def create_terms(payload: TermsAndConditionsCreate) -> TermsAndConditionsOut:
    """Service: create Terms & Conditions."""
    try:
        return await crud.create(payload)
    except HTTPException:
        raise
    except Exception as e:
        try:
            _raise_conflict_if_dup(e, field_hint="idx")
        except Exception as e2:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to create Terms & Conditions: {e2}"
            )


async def list_terms(skip: int, limit: int, sort_by_idx: bool) -> List[TermsAndConditionsOut]:
    """Service: list Terms & Conditions."""
    try:
        return await crud.list_all(skip=skip, limit=limit, sort_by_idx=sort_by_idx)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list Terms & Conditions: {e}")


async def get_terms(item_id: PyObjectId) -> TermsAndConditionsOut:
    """Service: fetch single T&C."""
    try:
        d = await crud.get_one(item_id)
        if not d:
            raise HTTPException(status_code=404, detail="Terms & Conditions not found")
        return d
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get Terms & Conditions: {e}")


async def update_terms(item_id: PyObjectId, payload: TermsAndConditionsUpdate) -> TermsAndConditionsOut:
    """Service: update T&C."""
    try:
        data = {k: v for k, v in payload.model_dump().items() if v is not None}
        if not data:
            raise HTTPException(status_code=400, detail="No fields provided for update")

        updated = await crud.update_one(item_id, payload)
        if not updated:
            raise HTTPException(status_code=404, detail="Terms & Conditions not found")
        return updated
    except HTTPException:
        raise
    except Exception as e:
        try:
            _raise_conflict_if_dup(e, field_hint="idx")
        except Exception as e2:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to update Terms & Conditions: {e2}"
            )


async def delete_terms(item_id: PyObjectId):
    """Service: delete T&C."""
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