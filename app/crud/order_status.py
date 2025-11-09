from __future__ import annotations
from typing import List, Optional, Dict, Any

from app.core.database import db
from app.utils.mongo import stamp_create, stamp_update
from app.schemas.object_id import PyObjectId
from app.schemas.order_status import OrderStatusCreate, OrderStatusUpdate, OrderStatusOut

COLL = "order_status"


def _to_out(doc: dict) -> OrderStatusOut:
    return OrderStatusOut.model_validate(doc)


async def create(payload: OrderStatusCreate) -> OrderStatusOut:
    doc = stamp_create(payload.model_dump(mode="python"))
    res = await db[COLL].insert_one(doc)
    saved = await db[COLL].find_one({"_id": res.inserted_id})
    return _to_out(saved)


async def list_all(
    skip: int = 0,
    limit: int = 50,
    query: Dict[str, Any] | None = None,
) -> List[OrderStatusOut]:
    cur = (
        db[COLL]
        .find(query or {})
        .skip(max(skip, 0))
        .limit(max(limit, 0))
        .sort("createdAt", -1)
    )
    docs = await cur.to_list(length=limit)
    return [_to_out(d) for d in docs]


async def get_one(_id: PyObjectId) -> Optional[OrderStatusOut]:
    doc = await db[COLL].find_one({"_id": _id})
    return _to_out(doc) if doc else None


async def update_one(_id: PyObjectId, payload: OrderStatusUpdate) -> Optional[OrderStatusOut]:
    data = {k: v for k, v in payload.model_dump(mode="python",exclude_none=True).items() if v is not None}
    if not data:
        return None

    await db[COLL].update_one({"_id": _id}, {"$set": stamp_update(data)})
    doc = await db[COLL].find_one({"_id": _id})
    return _to_out(doc) if doc else None


async def delete_one(_id: PyObjectId) -> Optional[bool]:
    # Guard: if any order references this status, block deletion
    used = await db["orders"].find_one({"status_id": _id})
    if used:
        return False

    r = await db[COLL].delete_one({"_id": _id})
    return r.deleted_count == 1