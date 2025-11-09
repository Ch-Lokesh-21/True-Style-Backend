from __future__ import annotations
from typing import List, Optional, Dict, Any
from bson import ObjectId

from app.core.database import db
from app.utils.mongo import stamp_create, stamp_update
from app.schemas.object_id import PyObjectId
from app.schemas.review_status import (
    ReviewStatusCreate,
    ReviewStatusUpdate,
    ReviewStatusOut,
)

COLL = "review_status"
REVIEWS_COLL = "user_reviews"  # collection where this status may be referenced


def _to_out(doc: dict) -> ReviewStatusOut:
    return ReviewStatusOut.model_validate(doc)


async def create(payload: ReviewStatusCreate) -> ReviewStatusOut:
    doc = stamp_create(payload.model_dump(mode="python"))
    res = await db[COLL].insert_one(doc)
    saved = await db[COLL].find_one({"_id": res.inserted_id})
    return _to_out(saved)


async def list_all(
    skip: int = 0,
    limit: int = 50,
    query: Dict[str, Any] | None = None,
) -> List[ReviewStatusOut]:
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


async def get_one(_id: PyObjectId) -> Optional[ReviewStatusOut]:
    try:
        oid = ObjectId(str(_id))
    except Exception:
        return None
    doc = await db[COLL].find_one({"_id": oid})
    return _to_out(doc) if doc else None


async def update_one(_id: PyObjectId, payload: ReviewStatusUpdate) -> Optional[ReviewStatusOut]:
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
    """
    Returns:
      - True  -> deleted
      - False -> in use (cannot delete)
      - None  -> invalid id or not found
    """
    try:
        oid = ObjectId(str(_id))
    except Exception:
        return None

    # Block delete if referenced by any review
    used = await db[REVIEWS_COLL].find_one({"review_status_id": oid})
    if used:
        return False

    r = await db[COLL].delete_one({"_id": oid})
    return r.deleted_count == 1