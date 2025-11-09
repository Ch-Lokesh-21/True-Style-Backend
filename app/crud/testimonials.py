from __future__ import annotations
from typing import List, Optional
from bson import ObjectId

from app.core.database import db
from app.utils.mongo import stamp_create, stamp_update
from app.schemas.object_id import PyObjectId
from app.schemas.testimonials import TestimonialsCreate, TestimonialsUpdate, TestimonialsOut

COLL = "testimonials"


def _to_out(doc: dict) -> TestimonialsOut:
    return TestimonialsOut.model_validate(doc)


async def create(payload: TestimonialsCreate) -> TestimonialsOut:
    # keep ObjectIds as ObjectIds
    doc = stamp_create(payload.model_dump(mode="python"))
    res = await db[COLL].insert_one(doc)
    saved = await db[COLL].find_one({"_id": res.inserted_id})
    return _to_out(saved)


async def list_all(skip: int = 0, limit: int = 50, sort_by_idx: bool = True) -> List[TestimonialsOut]:
    cur = (
        db[COLL]
        .find({})
        .skip(max(skip, 0))
        .limit(max(limit, 0))
        .sort([("idx", 1), ("createdAt", -1)]) if sort_by_idx
        else db[COLL].find({}).skip(max(skip, 0)).limit(max(limit, 0)).sort("createdAt", -1)
    )
    return [_to_out(d) for d in await cur.to_list(length=limit)]


async def get_one(_id: PyObjectId) -> Optional[TestimonialsOut]:
    try:
        oid = ObjectId(str(_id))
    except Exception:
        return None
    doc = await db[COLL].find_one({"_id": oid})
    return _to_out(doc) if doc else None


async def update_one(_id: PyObjectId, payload: TestimonialsUpdate) -> Optional[TestimonialsOut]:
    try:
        oid = ObjectId(str(_id))
    except Exception:
        return None

    data = {k: v for k, v in payload.model_dump(mode="python",exclude_none=True).items() if v is not None}
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