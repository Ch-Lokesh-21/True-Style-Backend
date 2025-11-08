from __future__ import annotations
from typing import List, Optional, Dict, Any

from app.core.database import db
from app.utils.mongo import stamp_create, stamp_update
from app.schemas.object_id import PyObjectId
from app.schemas.payment_types import (
    PaymentTypesCreate,
    PaymentTypesUpdate,
    PaymentTypesOut,
)

COLL = "payment_types"


def _to_out(doc: dict) -> PaymentTypesOut:
    return PaymentTypesOut.model_validate(doc)


async def create(payload: PaymentTypesCreate) -> PaymentTypesOut:
    doc = stamp_create(payload.model_dump(mode="python"))
    res = await db[COLL].insert_one(doc)
    saved = await db[COLL].find_one({"_id": res.inserted_id})
    return _to_out(saved)


async def list_all(
    skip: int = 0,
    limit: int = 50,
    query: Dict[str, Any] | None = None,
) -> List[PaymentTypesOut]:
    skip = max(0, int(skip))
    limit = max(0, int(limit))
    cur = (
        db[COLL]
        .find(query or {})
        .skip(skip)
        .limit(limit)
        .sort([("idx", 1), ("createdAt", -1)])  # nicer lookup ordering
    )
    docs = await cur.to_list(length=limit)
    return [_to_out(d) for d in docs]


async def get_one(_id: PyObjectId) -> Optional[PaymentTypesOut]:
    doc = await db[COLL].find_one({"_id": _id})
    return _to_out(doc) if doc else None


async def update_one(_id: PyObjectId, payload: PaymentTypesUpdate) -> Optional[PaymentTypesOut]:
    data = {k: v for k, v in payload.model_dump(mode="python").items() if v is not None}
    if not data:
        return None

    await db[COLL].update_one({"_id": _id}, {"$set": stamp_update(data)})
    doc = await db[COLL].find_one({"_id": _id})
    return _to_out(doc) if doc else None


async def delete_one(_id: PyObjectId) -> Optional[bool]:
    # Block deletion if any payment references this type
    used = await db["payments"].find_one({"payment_types_id": _id})
    if used:
        return False

    r = await db[COLL].delete_one({"_id": _id})
    return r.deleted_count == 1