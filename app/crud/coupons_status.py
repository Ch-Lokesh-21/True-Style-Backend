# app/crud/coupons_status.py
from __future__ import annotations
from typing import List, Optional, Dict, Any
from bson import ObjectId

from app.core.database import db
from app.utils.mongo import stamp_create, stamp_update
from app.schemas.object_id import PyObjectId
from app.schemas.coupons_status import (
    CouponsStatusCreate,
    CouponsStatusUpdate,
    CouponsStatusOut,
)

COLL = "coupons_status"
COUPONS_COLL = "coupons"


def _to_out(doc: dict) -> CouponsStatusOut:
    return CouponsStatusOut.model_validate(doc)


async def create(payload: CouponsStatusCreate) -> CouponsStatusOut:
    # keep native types (ObjectId/datetime)
    doc = stamp_create(payload.model_dump(mode="python"))
    res = await db[COLL].insert_one(doc)
    saved = await db[COLL].find_one({"_id": res.inserted_id})
    return _to_out(saved)


async def list_all(
    skip: int = 0,
    limit: int = 50,
    query: Dict[str, Any] | None = None,
) -> List[CouponsStatusOut]:
    cur = (
        db[COLL]
        .find(query or {})
        .skip(max(0, int(skip)))
        .limit(max(0, int(limit)))
        .sort([("idx", 1), ("createdAt", -1)])
    )
    docs = await cur.to_list(length=limit)
    return [_to_out(d) for d in docs]


async def get_one(_id: PyObjectId) -> Optional[CouponsStatusOut]:
    # _id is already an ObjectId
    doc = await db[COLL].find_one({"_id": _id})
    return _to_out(doc) if doc else None


async def update_one(_id: PyObjectId, payload: CouponsStatusUpdate) -> Optional[CouponsStatusOut]:
    data = {k: v for k, v in payload.model_dump(mode="python").items() if v is not None}
    if not data:
        return None

    await db[COLL].update_one({"_id": _id}, {"$set": stamp_update(data)})
    doc = await db[COLL].find_one({"_id": _id})
    return _to_out(doc) if doc else None


async def delete_one(_id: PyObjectId) -> Optional[bool]:
    """
    Returns:
      - True  -> deleted
      - False -> cannot delete (in use by one or more coupons)
      - None  -> invalid id (not coercible to ObjectId)
    """
    # Validate ObjectId (PyObjectId should already be OK, but keep guard for callers)
    try:
        oid = _id if isinstance(_id, ObjectId) else ObjectId(str(_id))
    except Exception:
        return None

    # Check if any coupon uses this status
    used = await db[COUPONS_COLL].find_one({"coupons_status_id": oid})
    if used:
        return False

    # Proceed to delete
    r = await db[COLL].delete_one({"_id": oid})
    return r.deleted_count == 1