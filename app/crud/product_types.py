from __future__ import annotations
from typing import List, Optional
from bson import ObjectId

from app.core.database import db
from app.utils.mongo import stamp_create, stamp_update
from app.schemas.object_id import PyObjectId
from app.schemas.product_types import ProductTypesCreate, ProductTypesUpdate, ProductTypesOut

COLL = "product_types"


def _to_out(doc: dict) -> ProductTypesOut:
    return ProductTypesOut.model_validate(doc)


async def create(payload: ProductTypesCreate) -> ProductTypesOut:
    doc = stamp_create(payload.model_dump(mode="python"))
    res = await db[COLL].insert_one(doc)
    saved = await db[COLL].find_one({"_id": res.inserted_id})
    return _to_out(saved)


async def list_all(skip: int = 0, limit: int = 50) -> List[ProductTypesOut]:
    cur = (
        db[COLL]
        .find({})
        .skip(max(skip, 0))
        .limit(max(limit, 0))
        .sort("createdAt", -1)
    )
    return [_to_out(d) for d in await cur.to_list(length=limit)]


async def get_one(_id: PyObjectId) -> Optional[ProductTypesOut]:
    try:
        oid = ObjectId(str(_id))
    except Exception:
        return None
    doc = await db[COLL].find_one({"_id": oid})
    return _to_out(doc) if doc else None


async def update_one(_id: PyObjectId, payload: ProductTypesUpdate) -> Optional[ProductTypesOut]:
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

    # Block deletion if referenced by any product
    used = await db["products"].find_one({"product_type_id": oid})
    if used:
        return False

    r = await db[COLL].delete_one({"_id": oid})
    return r.deleted_count == 1