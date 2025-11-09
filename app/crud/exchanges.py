# app/crud/exchanges.py
from __future__ import annotations
from typing import List, Optional, Dict, Any
from bson import ObjectId

from app.core.database import db
from app.utils.mongo import stamp_create, stamp_update
from app.schemas.object_id import PyObjectId
from app.schemas.exchanges import ExchangesCreate, ExchangesUpdate, ExchangesOut

COLL = "exchanges"

def _to_out(doc: dict) -> ExchangesOut:
    return ExchangesOut.model_validate(doc)

def _to_oid(v: Any) -> ObjectId:
    if isinstance(v, ObjectId):
        return v
    try:
        return ObjectId(str(v))
    except Exception:
        raise ValueError("Invalid ObjectId")

def _normalize_query(query: Dict[str, Any] | None) -> Dict[str, Any]:
    """
    Normalize filters likely to be ObjectId; support $in.
    """
    if not query:
        return {}
    q: Dict[str, Any] = {}
    oid_fields = {"_id", "user_id", "order_id", "product_id", "exchange_status_id"}
    for k, v in query.items():
        if v is None:
            continue
        if k in oid_fields:
            if isinstance(v, dict) and "$in" in v and isinstance(v["$in"], list):
                q[k] = {"$in": [_to_oid(x) for x in v["$in"]]}
            else:
                q[k] = _to_oid(v)
        else:
            q[k] = v
    return q

async def create(payload: ExchangesCreate) -> ExchangesOut:
    # Ensure real ObjectIds are persisted
    doc = stamp_create(payload.model_dump(mode="python"))
    res = await db[COLL].insert_one(doc)
    saved = await db[COLL].find_one({"_id": res.inserted_id})
    return _to_out(saved)

async def list_all(
    skip: int = 0,
    limit: int = 50,
    query: Dict[str, Any] | None = None,
) -> List[ExchangesOut]:
    q = _normalize_query(query)
    cur = (
        db[COLL]
        .find(q)
        .skip(max(0, int(skip)))
        .limit(max(0, int(limit)))
        .sort("createdAt", -1)
    )
    docs = await cur.to_list(length=limit)
    return [_to_out(d) for d in docs]

async def get_one(_id: PyObjectId) -> Optional[ExchangesOut]:
    try:
        oid = _to_oid(_id)
    except ValueError:
        return None
    doc = await db[COLL].find_one({"_id": oid})
    return _to_out(doc) if doc else None

async def update_one(_id: PyObjectId, payload: ExchangesUpdate) -> Optional[ExchangesOut]:
    try:
        oid = _to_oid(_id)
    except ValueError:
        return None

    data = payload.model_dump(mode="python", exclude_none=True)
    if not data:
        return None

    await db[COLL].update_one({"_id": oid}, {"$set": stamp_update(data)})
    doc = await db[COLL].find_one({"_id": oid})
    return _to_out(doc) if doc else None

async def delete_one(_id: PyObjectId) -> Optional[bool]:
    try:
        oid = _to_oid(_id)
    except ValueError:
        return None
    r = await db[COLL].delete_one({"_id": oid})
    return r.deleted_count == 1