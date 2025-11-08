from __future__ import annotations
from typing import List, Optional, Dict, Any

from app.core.database import db
from app.utils.mongo import stamp_create, stamp_update
from app.schemas.object_id import PyObjectId
from app.schemas.payment_status import (
    PaymentStatusCreate,
    PaymentStatusUpdate,
    PaymentStatusOut,
)

COLL = "payment_status"
PAYMENTS_COLL = "payments"   # collection where this status may be referenced


def _to_out(doc: dict) -> PaymentStatusOut:
    return PaymentStatusOut.model_validate(doc)


async def create(payload: PaymentStatusCreate) -> PaymentStatusOut:
    doc = stamp_create(payload.model_dump(mode="python"))
    res = await db[COLL].insert_one(doc)
    saved = await db[COLL].find_one({"_id": res.inserted_id})
    return _to_out(saved)


async def list_all(
    skip: int = 0,
    limit: int = 50,
    query: Dict[str, Any] | None = None,
) -> List[PaymentStatusOut]:
    skip = max(0, int(skip))
    limit = max(0, int(limit))
    cur = (
        db[COLL]
        .find(query or {})
        .skip(skip)
        .limit(limit)
        .sort([("idx", 1), ("createdAt", -1)])
    )
    docs = await cur.to_list(length=limit)
    return [_to_out(d) for d in docs]


async def get_one(_id: PyObjectId) -> Optional[PaymentStatusOut]:
    doc = await db[COLL].find_one({"_id": _id})
    return _to_out(doc) if doc else None


async def update_one(
    _id: PyObjectId,
    payload: PaymentStatusUpdate,
) -> Optional[PaymentStatusOut]:
    data = {k: v for k, v in payload.model_dump(mode="python").items() if v is not None}
    if not data:
        return None

    await db[COLL].update_one({"_id": _id}, {"$set": stamp_update(data)})
    doc = await db[COLL].find_one({"_id": _id})
    return _to_out(doc) if doc else None


async def delete_one(_id: PyObjectId) -> Optional[bool]:
    # Block delete if any payment references this status
    used = await db[PAYMENTS_COLL].find_one({"payment_status_id": _id})
    if used:
        return False

    r = await db[COLL].delete_one({"_id": _id})
    return r.deleted_count == 1