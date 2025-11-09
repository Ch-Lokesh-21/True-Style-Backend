from __future__ import annotations
from typing import List, Optional, Dict, Any

from app.core.database import db
from app.utils.mongo import stamp_create, stamp_update
from app.schemas.object_id import PyObjectId
from app.schemas.exchange_status import (
    ExchangeStatusCreate,
    ExchangeStatusUpdate,
    ExchangeStatusOut,
)

COLL = "exchange_status"
EXCHANGES_COLL = "exchanges"   # Collection where statuses are referenced


def _to_out(doc: dict) -> ExchangeStatusOut:
    return ExchangeStatusOut.model_validate(doc)


async def create(payload: ExchangeStatusCreate) -> ExchangeStatusOut:
    # Preserve native types (ObjectId/datetime)
    doc = stamp_create(payload.model_dump(mode="python"))
    res = await db[COLL].insert_one(doc)
    saved = await db[COLL].find_one({"_id": res.inserted_id})
    return _to_out(saved)


async def list_all(
    skip: int = 0,
    limit: int = 50,
    query: Dict[str, Any] | None = None,
) -> List[ExchangeStatusOut]:
    cur = (
        db[COLL]
        .find(query or {})
        .skip(max(skip, 0))
        .limit(max(limit, 0))
        .sort([("idx", 1), ("createdAt", -1)])
    )
    docs = await cur.to_list(length=limit)
    return [_to_out(d) for d in docs]


async def get_one(_id: PyObjectId) -> Optional[ExchangeStatusOut]:
    doc = await db[COLL].find_one({"_id": _id})
    return _to_out(doc) if doc else None


async def update_one(_id: PyObjectId, payload: ExchangeStatusUpdate) -> Optional[ExchangeStatusOut]:
    data = {k: v for k, v in payload.model_dump(mode="python",exclude_none=True).items() if v is not None}
    if not data:
        return None

    await db[COLL].update_one({"_id": _id}, {"$set": stamp_update(data)})
    doc = await db[COLL].find_one({"_id": _id})
    return _to_out(doc) if doc else None


async def delete_one(_id: PyObjectId) -> Optional[bool]:
    """
    Returns:
      True  -> deleted
      False -> in use by one or more exchanges
      None  -> not found (or invalid, though PyObjectId should guarantee validity)
    """
    # Is this status referenced by any exchange?
    used = await db[EXCHANGES_COLL].find_one({"exchange_status_id": _id})
    if used:
        return False

    r = await db[COLL].delete_one({"_id": _id})
    if r.deleted_count == 1:
        return True
    return None