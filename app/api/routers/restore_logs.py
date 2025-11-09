from __future__ import annotations
from typing import List, Optional, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import JSONResponse

from app.api.deps import require_permission
from app.schemas.restore_logs import RestoreLogsCreate, RestoreLogsUpdate, RestoreLogsOut
from app.crud import restore_logs as crud

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
    try:
        doc = await crud.run_restore_latest_full(drop=drop, gzip=gzip)
        return RestoreLogsOut.model_validate(doc)
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except FileNotFoundError:
        raise HTTPException(
            status_code=500,
            detail="mongorestore not found. Install MongoDB Database Tools and ensure it's in PATH."
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Restore failed: {e}")

@router.post(
    "/run/by-backup/{backup_id}",
    response_model=RestoreLogsOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("restore_logs", "Create"))],
)
async def restore_by_backup_id(
    backup_id: str,
    drop: bool = Query(True),
    gzip: bool = Query(True),
):
    try:
        doc = await crud.run_restore_by_backup_id(backup_id, drop=drop, gzip=gzip)
        return RestoreLogsOut.model_validate(doc)
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except FileNotFoundError:
        raise HTTPException(
            status_code=500,
            detail="mongorestore not found. Install MongoDB Database Tools and ensure it's in PATH."
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Restore failed: {e}")

# ---------------- standard CRUD ----------------

@router.post(
    "/",
    response_model=RestoreLogsOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("restore_logs", "Create"))],
)
async def create_item(payload: RestoreLogsCreate):
    try:
        d = await crud.create(payload.model_dump(mode="python", exclude_none=True))
        return RestoreLogsOut.model_validate(d)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create restore log: {e}")

@router.get(
    "/",
    response_model=List[RestoreLogsOut],
    dependencies=[Depends(require_permission("restore_logs", "Read"))],
)
async def list_items(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    status_: Optional[str] = Query(None, alias="status"),
    backup_id: Optional[str] = Query(None),
):
    try:
        q: Dict[str, Any] = {}
        if status_:
            q["status"] = status_
        if backup_id:
            q["backup_id"] = backup_id
        docs = await crud.list_all(skip=skip, limit=limit, query=q or None)
        return [RestoreLogsOut.model_validate(x) for x in docs]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list restore logs: {e}")

@router.get(
    "/{item_id}",
    response_model=RestoreLogsOut,
    dependencies=[Depends(require_permission("restore_logs", "Read"))],
)
async def get_item(item_id: str):
    d = await crud.get_one(item_id)
    if not d:
        raise HTTPException(status_code=404, detail="Restore log not found")
    return RestoreLogsOut.model_validate(d)

@router.put(
    "/{item_id}",
    response_model=RestoreLogsOut,
    dependencies=[Depends(require_permission("restore_logs", "Update"))],
)
async def update_item(item_id: str, payload: RestoreLogsUpdate):
    try:
        data = payload.model_dump(mode="python", exclude_none=True)
        if not data:
            raise HTTPException(status_code=400, detail="No fields to update")
        d = await crud.update_one(item_id, data)
        if not d:
            raise HTTPException(status_code=404, detail="Restore log not found")
        return RestoreLogsOut.model_validate(d)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update restore log: {e}")

@router.delete(
    "/{item_id}",
    dependencies=[Depends(require_permission("restore_logs", "Delete"))],
)
async def delete_item(item_id: str):
    ok = await crud.delete_one(item_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Restore log not found")
    return JSONResponse(status_code=200, content={"deleted": True})