"""
app/api/routes/restore_logs.py

Restore Logs API Router.

Exposes:
- POST /run/latest-full
- POST /run/by-backup/{backup_id}
- Standard CRUD: POST /, GET /, GET /{id}, PUT /{id}, DELETE /{id}

RBAC:
- All endpoints protected with `require_permission` according to action.
"""

from __future__ import annotations
from typing import List, Optional, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import JSONResponse

from app.api.deps import require_permission
from app.schemas.restore_logs import RestoreLogsCreate, RestoreLogsUpdate, RestoreLogsOut
from app.services.restore_logs import (
    restore_latest_full_service,
    restore_by_backup_id_service,
    create_item_service,
    list_items_service,
    get_item_service,
    update_item_service,
    delete_item_service,
)

router = APIRouter()

# ---------------- run restore ops ----------------

@router.post(
    "/run/latest-full",
    response_model=RestoreLogsOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("restore_logs", "Create"))],
)
async def restore_latest_full(
    drop: bool = Query(True, description="Pass --drop to mongorestore"),
    gzip: bool = Query(True, description="Pass --gzip to mongorestore"),
):
    """Trigger a restore from the **latest full backup** and persist a log."""
    return await restore_latest_full_service(drop=drop, gzip=gzip)


@router.post(
    "/run/by-backup/{backup_id}",
    response_model=RestoreLogsOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("restore_logs", "Create"))],
)
async def restore_by_backup_id(
    backup_id: str,
    drop: bool = Query(True, description="Pass --drop to mongorestore"),
    gzip: bool = Query(True, description="Pass --gzip to mongorestore"),
):
    """Trigger a restore for a specific `backup_id` and persist a log."""
    return await restore_by_backup_id_service(backup_id, drop=drop, gzip=gzip)

# ---------------- standard CRUD ----------------

@router.post(
    "/",
    response_model=RestoreLogsOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("restore_logs", "Create"))],
)
async def create_item(payload: RestoreLogsCreate):
    """Create a restore log document (manual record)."""
    return await create_item_service(payload)


@router.get(
    "/",
    response_model=List[RestoreLogsOut],
    dependencies=[Depends(require_permission("restore_logs", "Read"))],
)
async def list_items(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(50, ge=1, le=200, description="Page size (max 200)"),
    status_: Optional[str] = Query(None, alias="status", description="Filter by exact status"),
    backup_id: Optional[str] = Query(None, description="Filter by exact backup_id"),
):
    """List restore logs with optional filters."""
    return await list_items_service(skip=skip, limit=limit, status_=status_, backup_id=backup_id)


@router.get(
    "/{item_id}",
    response_model=RestoreLogsOut,
    dependencies=[Depends(require_permission("restore_logs", "Read"))],
)
async def get_item(item_id: str):
    """Fetch a single restore log by its id."""
    return await get_item_service(item_id)


@router.put(
    "/{item_id}",
    response_model=RestoreLogsOut,
    dependencies=[Depends(require_permission("restore_logs", "Update"))],
)
async def update_item(item_id: str, payload: RestoreLogsUpdate):
    """Update fields of an existing restore log."""
    return await update_item_service(item_id, payload)


@router.delete(
    "/{item_id}",
    dependencies=[Depends(require_permission("restore_logs", "Delete"))],
)
async def delete_item(item_id: str):
    """Delete a restore log and return {'deleted': True} on success."""
    result = await delete_item_service(item_id)
    return JSONResponse(status_code=200, content=result)