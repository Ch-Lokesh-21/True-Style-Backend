# app/crud/upi_details.py
from __future__ import annotations
from typing import List, Optional, Dict, Any
from bson import ObjectId

from app.core.database import db
from app.utils.mongo import stamp_create, stamp_update
from app.schemas.object_id import PyObjectId
from app.schemas.upi_details import UpiDetailsCreate, UpiDetailsUpdate, UpiDetailsOut

COLL = "upi_details"

def _to_out(doc: dict) -> UpiDetailsOut:
    return UpiDetailsOut.model_validate(doc)

def _to_oid(v: Any) -> Optional[ObjectId]:
    try:
        return ObjectId(str(v))
    except Exception:
        return None

async def create(payload: UpiDetailsCreate) -> UpiDetailsOut:
    """
    INTERNAL: used by Orders transaction to save UPI details.
    """
    doc = stamp_create(payload.model_dump(mode="python"))
    res = await db[COLL].insert_one(doc)
    saved = await db[COLL].find_one({"_id": res.inserted_id})
    return _to_out(saved)

async def list_all(skip: int = 0, limit: int = 50, query: Dict[str, Any] | None = None) -> List[UpiDetailsOut]:
    cur = (
        db[COLL]
        .find(query or {})
        .skip(max(skip, 0))
        .limit(max(limit, 0))
        .sort("createdAt", -1)
    )
    docs = await cur.to_list(length=limit)
    return [_to_out(d) for d in docs]

async def get_one(_id: PyObjectId) -> Optional[UpiDetailsOut]:
    oid = _to_oid(_id)
    if not oid:
        return None
    doc = await db[COLL].find_one({"_id": oid})
    return _to_out(doc) if doc else None

async def get_by_payment_id(payment_id: PyObjectId) -> Optional[UpiDetailsOut]:
    pid = _to_oid(payment_id)
    if not pid:
        return None
    doc = await db[COLL].find_one({"payment_id": pid})
    return _to_out(doc) if doc else None

async def update_one(_id: PyObjectId, payload: UpiDetailsUpdate) -> Optional[UpiDetailsOut]:
    """
    INTERNAL: generally not exposed via routes; prefer Orders-owned lifecycle.
    """
    oid = _to_oid(_id)
    if not oid:
        return None

    data = payload.model_dump(mode="python", exclude_none=True)
    if not data:
        return None

    await db[COLL].update_one({"_id": oid}, {"$set": stamp_update(data)})
    doc = await db[COLL].find_one({"_id": oid})
    return _to_out(doc) if doc else None

async def delete_one(_id: PyObjectId) -> Optional[bool]:
    """
    INTERNAL: generally not exposed via routes; prefer Orders-owned lifecycle.
    """
    oid = _to_oid(_id)
    if not oid:
        return None
    r = await db[COLL].delete_one({"_id": oid})
    return r.deleted_count == 1