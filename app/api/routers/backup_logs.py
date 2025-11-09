from __future__ import annotations
from typing import List, Optional, Dict, Any
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import JSONResponse

from app.api.deps import require_permission
from app.schemas.backup_logs import BackupLogsUpdate, BackupLogsOut
from app.crud import backup_logs as crud

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
    try:
        doc = await crud.schedule_backup_log(scope=scope or "full", frequency=frequency, scheduled_at=scheduled_at)
        return BackupLogsOut.model_validate(doc)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to schedule backup: {e}")

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
    try:
        doc = await crud.run_instant_backup(scope=scope, gzip=gzip)
        return BackupLogsOut.model_validate(doc)
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except FileNotFoundError:
        raise HTTPException(
            status_code=500,
            detail="mongodump not found. Install MongoDB Database Tools and ensure it's in PATH."
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Backup failed: {e}")

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
    try:
        q: Dict[str, Any] = {}
        if status_:
            q["status"] = status_
        if scope:
            q["scope"] = scope
        if frequency:
            q["frequency"] = frequency
        if date_from or date_to:
            q["createdAt"] = {}
            if date_from:
                q["createdAt"]["$gte"] = date_from
            if date_to:
                q["createdAt"]["$lt"] = date_to

        docs = await crud.list_all(skip=skip, limit=limit, query=q or None)
        return [BackupLogsOut.model_validate(d) for d in docs]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list backups: {e}")

@router.get(
    "/{backup_id}",
    response_model=BackupLogsOut,
    dependencies=[Depends(require_permission("backup_logs", "Read"))],
)
async def get_backup(backup_id: str):
    try:
        d = await crud.get_one(backup_id)
        if not d:
            raise HTTPException(status_code=404, detail="Backup not found")
        return BackupLogsOut.model_validate(d)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get backup: {e}")

# -------- update / delete --------

@router.put(
    "/{backup_id}",
    response_model=BackupLogsOut,
    dependencies=[Depends(require_permission("backup_logs", "Update"))],
)
async def update_backup(backup_id: str, payload: BackupLogsUpdate):
    try:
        data = payload.model_dump(mode="python", exclude_none=True)
        if not data:
            raise HTTPException(status_code=400, detail="No fields to update")
        d = await crud.update_one(backup_id, data)
        if not d:
            raise HTTPException(status_code=404, detail="Backup not found")
        return BackupLogsOut.model_validate(d)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update backup: {e}")

@router.delete(
    "/{backup_id}",
    dependencies=[Depends(require_permission("backup_logs", "Delete"))],
)
async def delete_backup(backup_id: str):
    try:
        ok = await crud.delete_one(backup_id)
        if not ok:
            raise HTTPException(status_code=404, detail="Backup not found")
        return JSONResponse(status_code=200, content={"deleted": True})
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete backup: {e}")