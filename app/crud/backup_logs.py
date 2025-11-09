from __future__ import annotations
import os
import shutil
import time
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional

from bson import ObjectId
from app.core.database import db
from app.core.config import settings
from app.utils.mongo import stamp_create, stamp_update
from app.schemas.backup_logs import (
    BackupLogsCreate,
    BackupScope,
)

COLL = "backup_logs"

# ---------------- helpers ----------------

def _utc_now() -> datetime:
    return datetime.now(timezone.utc)

def _ensure_dir(path: str | Path) -> Path:
    p = Path(path).expanduser().resolve()
    p.mkdir(parents=True, exist_ok=True)
    return p

def _folder_size_bytes(root: Path) -> int:
    total = 0
    for dirpath, _, filenames in os.walk(root):
        for f in filenames:
            try:
                total += os.path.getsize(os.path.join(dirpath, f))
            except OSError:
                pass
    return total

def _bytes_to_gb(b: int) -> float:
    return round(b / (1024**3), 4)

def _run(cmd: List[str]) -> tuple[int, str, str]:
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    return proc.returncode, proc.stdout, proc.stderr

# Allowed scopes -> used only to label logs and optionally map future behavior
_ALLOWED_SCOPES = {s.value for s in BackupScope} | {"full"}

# ---------------- CRUD core ----------------

async def create_log(payload: BackupLogsCreate) -> Dict[str, Any]:
    doc = stamp_create(payload.model_dump(mode="python", exclude_none=True))
    res = await db[COLL].insert_one(doc)
    return await db[COLL].find_one({"_id": res.inserted_id})

async def list_all(skip: int = 0, limit: int = 50, query: Dict[str, Any] | None = None) -> List[Dict[str, Any]]:
    cur = (
        db[COLL]
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
    return await db[COLL].find_one({"_id": oid})

async def update_one(_id: ObjectId | str, data: Dict[str, Any]) -> Dict[str, Any] | None:
    try:
        oid = ObjectId(str(_id))
    except Exception:
        return None
    await db[COLL].update_one({"_id": oid}, {"$set": stamp_update(data)})
    return await get_one(oid)

async def delete_one(_id: ObjectId | str) -> bool:
    try:
        oid = ObjectId(str(_id))
    except Exception:
        return False
    r = await db[COLL].delete_one({"_id": oid})
    return r.deleted_count == 1

# ---------------- scheduling helper ----------------

async def schedule_backup_log(
    *,
    scope: str = "full",
    frequency: Optional[str] = None,
    scheduled_at: Optional[datetime] = None,
) -> Dict[str, Any]:
    # sanitize scope
    scope_val = scope if scope in _ALLOWED_SCOPES else "full"

    # build a consistent future path where a scheduler could write later
    dbn = settings.MONGO_DB
    base = settings.BACKUP_BASE_PATH or "./backups"
    base_out = _ensure_dir(base)
    ts = time.strftime("%Y/%m/%d/%H%M%S")
    out_dir = base_out / dbn / "scheduled" / scope_val / ts

    payload = BackupLogsCreate(
        status="pending",
        size=0.0,
        scope=scope_val,              # enum string is fine; Pydantic validates
        frequency=frequency or "once",
        path=str(out_dir),
        scheduled_at=scheduled_at,
        started_at=None,
        finished_at=None,
    )
    return await create_log(payload)

# ---------------- run-now backup (mongodump) ----------------

async def run_instant_backup(
    *,
    scope: Optional[str] = "full",
    gzip: bool = True,
) -> Dict[str, Any]:
    """
    Run `mongodump` immediately, auto-pick a new folder, and persist a log
    (using BackupLogsCreate) that includes the path for future restore.
    """
    uri = settings.MONGO_URI
    if not uri:
        raise RuntimeError("MONGO_URI not configured.")
    dbn = settings.MONGO_DB
    if not dbn:
        raise RuntimeError("MONGO_DB not configured.")

    # output folder structure: <BASE>/<db>/<yyyy>/<mm>/<dd>/<HHMMSS>/
    base = settings.BACKUP_BASE_PATH or "./backups"
    base_out = _ensure_dir(base)
    ts = time.strftime("%Y/%m/%d/%H%M%S")
    out_dir = base_out / dbn / ts
    out_dir.mkdir(parents=True, exist_ok=True)

    started_at = _utc_now()
    gzip_flag: List[str] = ["--gzip"] if gzip else []

    # We dump the whole DB for simplicity and reliability
    cmd = ["mongodump", "--uri", uri, "--db", dbn, "--out", str(out_dir), *gzip_flag]
    rc, so, se = _run(cmd)

    finished_at = _utc_now()

    if rc != 0:
        # cleanup partial output
        try:
            shutil.rmtree(out_dir, ignore_errors=True)
        except Exception:
            pass

        payload = BackupLogsCreate(
            status="failed",
            size=0.0,
            scope=(scope if (scope in _ALLOWED_SCOPES) else "full"),
            frequency="once",
            path=str(out_dir),
            started_at=started_at,
            finished_at=finished_at,
        )
        return await create_log(payload)

    # success → measure size (mongodump usually creates <out_dir>/<dbn>)
    measure_root = out_dir / dbn
    if not measure_root.exists():
        measure_root = out_dir
    size_gb = _bytes_to_gb(_folder_size_bytes(measure_root))

    payload = BackupLogsCreate(
        status="success",
        size=size_gb,
        scope=(scope if (scope in _ALLOWED_SCOPES) else "full"),
        frequency="once",
        path=str(out_dir),
        started_at=started_at,
        finished_at=finished_at,
    )
    return await create_log(payload)