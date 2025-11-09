# app/crud/carts.py
from __future__ import annotations
from typing import List, Optional, Dict, Any
from bson import ObjectId

from app.core.database import db
from app.utils.mongo import stamp_create, stamp_update
from app.schemas.object_id import PyObjectId
from app.schemas.carts import CartsCreate, CartsUpdate, CartsOut

COLL = "carts"


def _to_out(doc: dict) -> CartsOut:
    return CartsOut.model_validate(doc)


def _maybe_oid(v):
    if isinstance(v, ObjectId):
        return v
    try:
        return ObjectId(str(v))
    except Exception:
        return v  # leave as-is if not coercible


async def create(payload: CartsCreate) -> CartsOut:
    # Preserve native types (ObjectId, datetime, etc.)
    doc = stamp_create(payload.model_dump(mode="python"))
    res = await db[COLL].insert_one(doc)
    saved = await db[COLL].find_one({"_id": res.inserted_id})
    return _to_out(saved)


async def list_all(skip: int = 0, limit: int = 50, query: Dict[str, Any] | None = None) -> List[CartsOut]:
    # If filters contain *_id fields or _id, coerce them to ObjectId when possible
    q: Dict[str, Any] = {}
    if query:
        q = {
            k: (_maybe_oid(v) if k == "_id" or k.endswith("_id") else v)
            for k, v in query.items()
        }

    cur = (
        db[COLL]
        .find(q)
        .skip(max(skip, 0))
        .limit(max(limit, 0))
        .sort("createdAt", -1)
    )
    docs = await cur.to_list(length=limit)
    return [_to_out(d) for d in docs]


async def get_one(_id: PyObjectId) -> Optional[CartsOut]:
    # _id is already a real ObjectId (PyObjectId)
    doc = await db[COLL].find_one({"_id": _id})
    return _to_out(doc) if doc else None


async def update_one(_id: PyObjectId, payload: CartsUpdate) -> Optional[CartsOut]:
    data = {k: v for k, v in payload.model_dump(mode="python",exclude_none=True).items() if v is not None}
    if not data:
        return None

    await db[COLL].update_one({"_id": _id}, {"$set": stamp_update(data)})
    doc = await db[COLL].find_one({"_id": _id})
    return _to_out(doc) if doc else None


async def delete_one(_id: PyObjectId) -> Optional[bool]:
    r = await db[COLL].delete_one({"_id": _id})
    return r.deleted_count == 1
