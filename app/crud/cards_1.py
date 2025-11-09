# app/crud/cards_1.py
from __future__ import annotations
from typing import List, Optional

from app.core.database import db
from app.utils.mongo import stamp_create, stamp_update
from app.schemas.object_id import PyObjectId
from app.schemas.cards_1 import Cards1Create, Cards1Update, Cards1Out

COLL = "cards_1"


def _to_out(doc: dict) -> Cards1Out:
    return Cards1Out.model_validate(doc)


async def create(payload: Cards1Create) -> Cards1Out:
    # Keep native types (ObjectId, datetime, etc.)
    doc = stamp_create(payload.model_dump(mode="python"))
    res = await db[COLL].insert_one(doc)
    saved = await db[COLL].find_one({"_id": res.inserted_id})
    return _to_out(saved)


async def list_all(skip: int = 0, limit: int = 50, sort_by_idx: bool = True) -> List[Cards1Out]:
    base = db[COLL].find({}).skip(max(skip, 0)).limit(max(limit, 0))
    cur = base.sort([("idx", 1), ("createdAt", -1)]) if sort_by_idx else base.sort("createdAt", -1)
    docs = await cur.to_list(length=limit)
    return [_to_out(d) for d in docs]


async def get_one(_id: PyObjectId) -> Optional[Cards1Out]:
    # _id is already a real ObjectId thanks to PyObjectId
    doc = await db[COLL].find_one({"_id": _id})
    return _to_out(doc) if doc else None


async def update_one(_id: PyObjectId, payload: Cards1Update) -> Optional[Cards1Out]:
    data = {k: v for k, v in payload.model_dump(mode="python",exclude_none=True).items() if v is not None}
    if not data:
        return None
    await db[COLL].update_one({"_id": _id}, {"$set": stamp_update(data)})
    doc = await db[COLL].find_one({"_id": _id})
    return _to_out(doc) if doc else None


async def delete_one(_id: PyObjectId) -> Optional[bool]:
    r = await db[COLL].delete_one({"_id": _id})
    return r.deleted_count == 1