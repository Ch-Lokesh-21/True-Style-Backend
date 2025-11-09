from __future__ import annotations
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional

from bson import ObjectId
from app.core.database import db
from app.core.config import settings
from app.utils.mongo import stamp_create, stamp_update
from app.schemas.restore_logs import RestoreLogsCreate, RestoreLogsUpdate

RESTORE_COLL = "restore_logs"
BACKUP_COLL = "backup_logs"

# ---------------- helpers ----------------

def _utc_now() -> datetime:
    return datetime.now(timezone.utc)

def _run(cmd: List[str]) -> tuple[int, str, str]:
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    return proc.returncode, proc.stdout, proc.stderr

def _resolve_dump_dir(backup_path: str) -> Path:
    """
    Returns the folder path that mongorestore’s --dir should point to.
    Our backups are created at <base>/<db>/<yyyy>/<mm>/<dd>/<HHMMSS>,
    and mongodump writes files under that folder, usually in a <db> subfolder.
    """
    p = Path(backup_path).expanduser().resolve()
    dbn = settings.MONGO_DB
    # Prefer the <backup>/<db> subfolder if it exists; else use the root.
    candidate = p / dbn
    return candidate if candidate.exists() else p

async def _insert_restore_log(backup_id: ObjectId | str, status: str) -> Dict[str, Any]:
    payload = RestoreLogsCreate(
        backup_id=ObjectId(str(backup_id)),
        status=status,
    )
    doc = stamp_create(payload.model_dump(mode="python", exclude_none=True))
    res = await db[RESTORE_COLL].insert_one(doc)
    return await db[RESTORE_COLL].find_one({"_id": res.inserted_id})

async def _update_restore_log(_id: ObjectId, update: RestoreLogsUpdate) -> Dict[str, Any] | None:
    data = update.model_dump(mode="python", exclude_none=True)
    if not data:
        return await db[RESTORE_COLL].find_one({"_id": _id})
    await db[RESTORE_COLL].update_one({"_id": _id}, {"$set": stamp_update(data)})
    return await db[RESTORE_COLL].find_one({"_id": _id})

async def _get_backup_doc_by_id(backup_id: ObjectId | str) -> Dict[str, Any] | None:
    try:
        oid = ObjectId(str(backup_id))
    except Exception:
        return None
    return await db[BACKUP_COLL].find_one({"_id": oid})

async def _get_latest_full_backup_success() -> Dict[str, Any] | None:
    cur = (
        db[BACKUP_COLL]
        .find({"status": "success", "scope": "full"})
        .sort("createdAt", -1)
        .limit(1)
    )
    docs = await cur.to_list(length=1)
    return docs[0] if docs else None

# ---------------- public CRUD ----------------

async def create(data: Dict[str, Any]) -> Dict[str, Any]:
    # Expect caller to pass only fields valid for RestoreLogsCreate (backup_id, status?)
    payload = RestoreLogsCreate(**data)  # validates via Pydantic
    doc = stamp_create(payload.model_dump(mode="python", exclude_none=True))
    res = await db[RESTORE_COLL].insert_one(doc)
    return await db[RESTORE_COLL].find_one({"_id": res.inserted_id})

async def list_all(skip: int = 0, limit: int = 50, query: Dict[str, Any] | None = None) -> List[Dict[str, Any]]:
    cur = (
        db[RESTORE_COLL]
        .find(query or {})
        .skip(max(0, skip))
        .limit(max(1, limit))
        .sort("createdAt", -1)
    )
    return await cur.to_list(length=limit)

async def get_one(_id: ObjectId | str) -> Dict[str, Any] | None:
    try:
        oid = ObjectId(str(_id))
    except Exception:
        return None
    return await db[RESTORE_COLL].find_one({"_id": oid})

async def update_one(_id: ObjectId | str, data: Dict[str, Any]) -> Dict[str, Any] | None:
    try:
        oid = ObjectId(str(_id))
    except Exception:
        return None
    payload = RestoreLogsUpdate(**data)
    await db[RESTORE_COLL].update_one({"_id": oid}, {"$set": stamp_update(payload.model_dump(mode="python", exclude_none=True))})
    return await get_one(oid)

async def delete_one(_id: ObjectId | str) -> bool:
    try:
        oid = ObjectId(str(_id))
    except Exception:
        return False
    r = await db[RESTORE_COLL].delete_one({"_id": oid})
    return r.deleted_count == 1

# ---------------- run restore operations ----------------

async def run_restore_latest_full(*, drop: bool = True, gzip: bool = True) -> Dict[str, Any]:
    """
    Find the most recent successful FULL backup in backup_logs,
    run mongorestore, and write a restore_log using Pydantic models.
    """
    bk = await _get_latest_full_backup_success()
    if not bk:
        raise RuntimeError("No successful FULL backup found.")

    backup_id = bk["_id"]
    dump_dir = _resolve_dump_dir(bk["path"])
    uri = settings.MONGO_URI
    dbn = settings.MONGO_DB
    if not uri or not dbn:
        raise RuntimeError("MONGO_URI / MONGO_DB not configured.")
    if not dump_dir.exists():
        raise RuntimeError("Backup path does not exist on disk.")

    # 1) insert pending restore log
    pending = await _insert_restore_log(backup_id=backup_id, status="pending")
    restore_id = pending["_id"]

    # 2) run mongorestore
    flags = ["--uri", uri, "--db", dbn, "--dir", str(dump_dir)]
    if drop:
        flags.append("--drop")
    if gzip:
        flags.append("--gzip")

    rc, so, se = _run(["mongorestore", *flags])

    # 3) finalize log
    if rc == 0:
        updated = await _update_restore_log(
            restore_id,
            RestoreLogsUpdate(status="success")
        )
    else:
        reason = (se or so).strip() or "restore failed"
        updated = await _update_restore_log(
            restore_id,
            RestoreLogsUpdate(status="failed", reason=reason)
        )

    # Always return the final log doc
    return updated or await get_one(restore_id)  # type: ignore[return-value]

async def run_restore_by_backup_id(backup_id: ObjectId | str, *, drop: bool = True, gzip: bool = True) -> Dict[str, Any]:
    """
    Run mongorestore using an explicit backup log id.
    """
    bk = await _get_backup_doc_by_id(backup_id)
    if not bk:
        raise RuntimeError("Backup not found.")
    if str(bk.get("status")) != "success":
        raise RuntimeError("Backup is not in 'success' status.")
    if not bk.get("path"):
        raise RuntimeError("Backup path missing in log.")

    dump_dir = _resolve_dump_dir(bk["path"])
    uri = settings.MONGO_URI
    dbn = settings.MONGO_DB
    if not uri or not dbn:
        raise RuntimeError("MONGO_URI / MONGO_DB not configured.")
    if not dump_dir.exists():
        raise RuntimeError("Backup path does not exist on disk.")

    # 1) pending
    pending = await _insert_restore_log(backup_id=bk["_id"], status="pending")
    restore_id = pending["_id"]

    # 2) restore
    flags = ["--uri", uri, "--db", dbn, "--dir", str(dump_dir)]
    if drop:
        flags.append("--drop")
    if gzip:
        flags.append("--gzip")

    rc, so, se = _run(["mongorestore", *flags])

    # 3) finalize
    if rc == 0:
        updated = await _update_restore_log(
            restore_id,
            RestoreLogsUpdate(status="success")
        )
    else:
        reason = (se or so).strip() or "restore failed"
        updated = await _update_restore_log(
            restore_id,
            RestoreLogsUpdate(status="failed", reason=reason)
        )

    return updated or await get_one(restore_id)