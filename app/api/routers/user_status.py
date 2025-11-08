from __future__ import annotations
from typing import List, Optional, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import JSONResponse

from app.api.deps import require_permission
from app.schemas.object_id import PyObjectId
from app.schemas.user_status import UserStatusCreate, UserStatusUpdate, UserStatusOut
from app.crud import user_status as crud

router = APIRouter()  # mounted with prefix="/user-status"


def _raise_conflict_if_dup(err: Exception, field_hint: Optional[str] = None):
    msg = str(err)
    if "E11000" in msg:
        detail = "Duplicate key." if not field_hint else f"Duplicate {field_hint}."
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=detail)
    raise err


@router.post(
    "/",
    response_model=UserStatusOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("user_status", "Create"))],
)
async def create_item(payload: UserStatusCreate):
    try:
        return await crud.create(payload)
    except HTTPException:
        raise
    except Exception as e:
        try:
            _raise_conflict_if_dup(e, field_hint="idx or status")
        except Exception as e2:
            raise HTTPException(status_code=500, detail=f"Failed to create user status: {e2}")


@router.get(
    "/",
    response_model=List[UserStatusOut],
    dependencies=[Depends(require_permission("user_status", "Read"))],
)
async def list_items(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    status_eq: Optional[str] = Query(None, alias="status", description="Filter by status (exact match)"),
):
    try:
        q: Dict[str, Any] = {}
        if status_eq:
            q["status"] = status_eq
        return await crud.list_all(skip=skip, limit=limit, query=q or None)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list user status: {e}")


@router.get(
    "/{item_id}",
    response_model=UserStatusOut,
    dependencies=[Depends(require_permission("user_status", "Read"))],
)
async def get_item(item_id: PyObjectId):
    try:
        item = await crud.get_one(item_id)
        if not item:
            raise HTTPException(status_code=404, detail="User status not found")
        return item
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get user status: {e}")


@router.put(
    "/{item_id}",
    response_model=UserStatusOut,
    dependencies=[Depends(require_permission("user_status", "Update"))],
)
async def update_item(item_id: PyObjectId, payload: UserStatusUpdate):
    try:
        if not any(v is not None for v in payload.model_dump().values()):
            raise HTTPException(status_code=400, detail="No fields provided for update")
        updated = await crud.update_one(item_id, payload)
        if not updated:
            raise HTTPException(status_code=404, detail="User status not found or not updated")
        return updated
    except HTTPException:
        raise
    except Exception as e:
        try:
            _raise_conflict_if_dup(e, field_hint="idx or status")
        except Exception as e2:
            raise HTTPException(status_code=500, detail=f"Failed to update user status: {e2}")


@router.delete(
    "/{item_id}",
    dependencies=[Depends(require_permission("user_status", "Delete"))],
)
async def delete_item(item_id: PyObjectId):
    try:
        ok = await crud.delete_one(item_id)

        if ok is None:
            raise HTTPException(status_code=400, detail="Invalid user status ID.")

        if ok is False:
            raise HTTPException(
                status_code=400,
                detail="Cannot delete this user status because one or more users are using it.",
            )

        return JSONResponse(status_code=200, content={"deleted": True})

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete user status: {e}")