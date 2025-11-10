from __future__ import annotations
from typing import List, Optional, Dict, Any
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import JSONResponse

from app.api.deps import require_permission
from app.schemas.backup_logs import BackupLogsUpdate, BackupLogsOut
from app.services.backup_logs import (
    schedule_backup_service,
    run_backup_now_service,
    list_backups_service,
    get_backup_service,
    update_backup_service,
    delete_backup_service,
)

router = APIRouter()

# -------- schedule (create a "pending" log with a target path) --------
@router.post(
    "/schedule",
    response_model=BackupLogsOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("backup_logs", "Create"))],
)
async def schedule_backup(
    scope: Optional[str] = Query("full", description="full | users | products | orders | content | payments | returns | exchanges"),
    frequency: Optional[str] = Query("once"),
    scheduled_at: Optional[datetime] = Query(None),
):
    return await schedule_backup_service(scope=scope or "full", frequency=frequency, scheduled_at=scheduled_at)

# -------- run backup now (mongodump) --------
@router.post(
    "/run",
    response_model=BackupLogsOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("backup_logs", "Create"))],
)
async def run_backup_now(
    scope: Optional[str] = Query("full", description="Label to store with the log. Backup always dumps the DB."),
    gzip: bool = Query(True, description="Use mongodump --gzip"),
):
    return await run_backup_now_service(scope=scope, gzip=gzip)

# -------- read / list / get --------
@router.get(
    "/",
    response_model=List[BackupLogsOut],
    dependencies=[Depends(require_permission("backup_logs", "Read"))],
)
async def list_backups(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    status_: Optional[str] = Query(None, alias="status"),
    scope: Optional[str] = Query(None),
    frequency: Optional[str] = Query(None),
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
):
    return await list_backups_service(
        skip=skip,
        limit=limit,
        status_=status_,
        scope=scope,
        frequency=frequency,
        date_from=date_from,
        date_to=date_to,
    )

@router.get(
    "/{backup_id}",
    response_model=BackupLogsOut,
    dependencies=[Depends(require_permission("backup_logs", "Read"))],
)
async def get_backup(backup_id: str):
    return await get_backup_service(backup_id)

# -------- update / delete --------
@router.put(
    "/{backup_id}",
    response_model=BackupLogsOut,
    dependencies=[Depends(require_permission("backup_logs", "Update"))],
)
async def update_backup(backup_id: str, payload: BackupLogsUpdate):
    return await update_backup_service(backup_id, payload)

@router.delete(
    "/{backup_id}",
    dependencies=[Depends(require_permission("backup_logs", "Delete"))],
)
async def delete_backup(backup_id: str):
    return await delete_backup_service(backup_id)