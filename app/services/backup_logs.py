from __future__ import annotations
from typing import List, Optional, Dict, Any
from datetime import datetime

from fastapi import HTTPException
from fastapi.responses import JSONResponse

from app.schemas.backup_logs import BackupLogsUpdate, BackupLogsOut
from app.crud import backup_logs as crud


async def schedule_backup_service(
    scope: str,
    frequency: Optional[str],
    scheduled_at: Optional[datetime],
) -> BackupLogsOut:
    """
    Create a scheduled backup entry.

    Args:
        scope (str): Backup target scope (e.g., full/db/collections).
        frequency (str | None): Cron-like frequency definition.
        scheduled_at (datetime | None): When the backup should run.

    Returns:
        BackupLogsOut: Created backup log.

    Raises:
        HTTPException: On database or internal failure.
    """
    try:
        doc = await crud.schedule_backup_log(scope=scope, frequency=frequency, scheduled_at=scheduled_at)
        return BackupLogsOut.model_validate(doc)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to schedule backup: {e}")


async def run_backup_now_service(
    scope: Optional[str],
    gzip: bool,
) -> BackupLogsOut:
    """
    Trigger an immediate backup operation.

    Args:
        scope (str | None): What to back up (None = full DB).
        gzip (bool): Whether to compress the backup.

    Returns:
        BackupLogsOut: Backup execution result.

    Raises:
        HTTPException: On runtime errors, missing tools, or failure.
    """
    try:
        doc = await crud.run_instant_backup(scope=scope, gzip=gzip)
        return BackupLogsOut.model_validate(doc)
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except FileNotFoundError:
        raise HTTPException(
            status_code=500,
            detail="mongodump not found. Install MongoDB Database Tools and ensure it's in PATH.",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Backup failed: {e}")


async def list_backups_service(
    skip: int,
    limit: int,
    status_: Optional[str],
    scope: Optional[str],
    frequency: Optional[str],
    date_from: Optional[datetime],
    date_to: Optional[datetime],
) -> List[BackupLogsOut]:
    """
    List backup logs with advanced filtering.

    Args:
        skip (int): Pagination offset.
        limit (int): Max results.
        status_ (str | None): Filter by backup status.
        scope (str | None): Filter by scope.
        frequency (str | None): Filter by frequency.
        date_from, date_to (datetime | None): Optional time range filter.

    Returns:
        List[BackupLogsOut]: List of backup logs.

    Raises:
        HTTPException: When query or mapping fails.
    """
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


async def get_backup_service(backup_id: str) -> BackupLogsOut:
    """
    Get a single backup log by ID.

    Args:
        backup_id (str): Backup document ID.

    Returns:
        BackupLogsOut: Backup log data.

    Raises:
        HTTPException: If not found or on server failure.
    """
    try:
        d = await crud.get_one(backup_id)
        if not d:
            raise HTTPException(status_code=404, detail="Backup not found")
        return BackupLogsOut.model_validate(d)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get backup: {e}")


async def update_backup_service(backup_id: str, payload: BackupLogsUpdate) -> BackupLogsOut:
    """
    Update backup metadata (e.g., status or result).

    Args:
        backup_id (str): Backup log ID.
        payload (BackupLogsUpdate): Fields to update.

    Returns:
        BackupLogsOut: Updated backup log.

    Raises:
        HTTPException: If backup not found or no fields provided.
    """
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


async def delete_backup_service(backup_id: str):
    """
    Delete a backup log entry.

    Args:
        backup_id (str): Backup ID to delete.

    Returns:
        JSONResponse: {"deleted": True}

    Raises:
        HTTPException: If backup does not exist or delete fails.
    """
    try:
        ok = await crud.delete_one(backup_id)
        if not ok:
            raise HTTPException(status_code=404, detail="Backup not found")
        return JSONResponse(status_code=200, content={"deleted": True})
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete backup: {e}")