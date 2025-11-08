from __future__ import annotations
from typing import List, Optional, Dict, Any
from bson import ObjectId

from app.core.database import db
from app.utils.mongo import stamp_create, stamp_update
from app.schemas.object_id import PyObjectId
from app.schemas.payments import PaymentsCreate, PaymentsUpdate, PaymentsOut

COLL = "payments"

def _to_out(doc: dict) -> PaymentsOut:
    return PaymentsOut.model_validate(doc)

async def create(payload: PaymentsCreate) -> PaymentsOut:
    doc = stamp_create(payload.model_dump())
    res = await db[COLL].insert_one(doc)
    saved = await db[COLL].find_one({"_id": res.inserted_id})
    return _to_out(saved)

async def list_all(
    skip: int = 0,
    limit: int = 50,
    query: Dict[str, Any] | None = None,
) -> List[PaymentsOut]:
    cur = (
        db[COLL]
        .find(query or {})
        .skip(max(skip, 0))
        .limit(max(limit, 0))
        .sort("createdAt", -1)
    )
    docs = await cur.to_list(length=limit)
    return [_to_out(d) for d in docs]

async def get_one(_id: PyObjectId) -> Optional[PaymentsOut]:
    try:
        oid = ObjectId(str(_id))
    except Exception:
        return None
    doc = await db[COLL].find_one({"_id": oid})
    return _to_out(doc) if doc else None

async def update_one(_id: PyObjectId, payload: PaymentsUpdate) -> Optional[PaymentsOut]:
    try:
        oid = ObjectId(str(_id))
    except Exception:
        return None

    data = {k: v for k, v in payload.model_dump().items() if v is not None}
    if not data:
        return None

    await db[COLL].update_one({"_id": oid}, {"$set": stamp_update(data)})
    doc = await db[COLL].find_one({"_id": oid})
    return _to_out(doc) if doc else None

async def delete_one(_id: PyObjectId) -> Optional[bool]:
    try:
        oid = ObjectId(str(_id))
    except Exception:
        return None
    r = await db[COLL].delete_one({"_id": oid})
    return r.deleted_count == 1