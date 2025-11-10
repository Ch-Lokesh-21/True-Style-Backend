"""
app/services/restore_logs_service.py

Service layer for Restore Logs.

Responsibilities:
- Orchestrate restore operations (latest full / by backup id) via CRUD.
- Provide CRUD wrappers with light validation.
- Raise HTTPExceptions with precise status codes/messages; the router is thin.

Notes:
- These functions return Pydantic models (RestoreLogsOut) or simple dicts.
"""

from __future__ import annotations
from typing import List, Optional, Dict, Any

from fastapi import HTTPException, status

from app.schemas.restore_logs import RestoreLogsCreate, RestoreLogsUpdate, RestoreLogsOut
from app.crud import restore_logs as crud


# ---------------- operational restores ----------------

async def restore_latest_full_service(
    drop: bool = True,
    gzip: bool = True,
) -> RestoreLogsOut:
    """
    Run mongorestore from the latest full backup and persist a restore log.

    Args:
        drop: Pass --drop to mongorestore.
        gzip: Pass --gzip to mongorestore.

    Returns:
        RestoreLogsOut

    Raises:
        HTTPException 400: Controlled runtime error (e.g., invalid state).
        HTTPException 500: mongorestore missing or unexpected failure.
    """
    try:
        doc = await crud.run_restore_latest_full(drop=drop, gzip=gzip)
        return RestoreLogsOut.model_validate(doc)
    except RuntimeError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except FileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="mongorestore not found. Install MongoDB Database Tools and ensure it's in PATH.",
        )
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Restore failed: {e}")


async def restore_by_backup_id_service(
    backup_id: str,
    drop: bool = True,
    gzip: bool = True,
) -> RestoreLogsOut:
    """
    Run mongorestore for a specific backup id and persist a restore log.

    Args:
        backup_id: Identifier of the backup to restore from.
        drop: Pass --drop to mongorestore.
        gzip: Pass --gzip to mongorestore.

    Returns:
        RestoreLogsOut

    Raises:
        HTTPException 400: Controlled runtime error (e.g., backup not found).
        HTTPException 500: mongorestore missing or unexpected failure.
    """
    try:
        doc = await crud.run_restore_by_backup_id(backup_id, drop=drop, gzip=gzip)
        return RestoreLogsOut.model_validate(doc)
    except RuntimeError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except FileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="mongorestore not found. Install MongoDB Database Tools and ensure it's in PATH.",
        )
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Restore failed: {e}")


# ---------------- standard CRUD ----------------

async def create_item_service(payload: RestoreLogsCreate) -> RestoreLogsOut:
    """
    Create a restore log entry (manual insertion).

    Args:
        payload: RestoreLogsCreate

    Returns:
        RestoreLogsOut
    """
    try:
        d = await crud.create(payload.model_dump(mode="python", exclude_none=True))
        return RestoreLogsOut.model_validate(d)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to create restore log: {e}")


async def list_items_service(
    skip: int = 0,
    limit: int = 50,
    status_: Optional[str] = None,
    backup_id: Optional[str] = None,
) -> List[RestoreLogsOut]:
    """
    List restore logs with optional filters.

    Args:
        skip: Offset.
        limit: Page size.
        status_: Exact match on status.
        backup_id: Exact match on backup id.

    Returns:
        List[RestoreLogsOut]
    """
    try:
        q: Dict[str, Any] = {}
        if status_:
            q["status"] = status_
        if backup_id:
            q["backup_id"] = backup_id
        docs = await crud.list_all(skip=skip, limit=limit, query=q or None)
        return [RestoreLogsOut.model_validate(x) for x in docs]
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to list restore logs: {e}")


async def get_item_service(item_id: str) -> RestoreLogsOut:
    """
    Get one restore log by id.

    Raises:
        404 if not found.
    """
    d = await crud.get_one(item_id)
    if not d:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Restore log not found")
    return RestoreLogsOut.model_validate(d)


async def update_item_service(item_id: str, payload: RestoreLogsUpdate) -> RestoreLogsOut:
    """
    Update an existing restore log.

    Raises:
        400 if no fields provided.
        404 if not found.
    """
    try:
        data = payload.model_dump(mode="python", exclude_none=True)
        if not data:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No fields to update")
        d = await crud.update_one(item_id, data)
        if not d:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Restore log not found")
        return RestoreLogsOut.model_validate(d)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to update restore log: {e}")


async def delete_item_service(item_id: str) -> Dict[str, bool]:
    """
    Delete a restore log.

    Raises:
        404 if not found.

    Returns:
        {"deleted": True}
    """
    ok = await crud.delete_one(item_id)
    if not ok:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Restore log not found")
    return {"deleted": True}
