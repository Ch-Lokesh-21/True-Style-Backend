from __future__ import annotations
from typing import List, Optional, Dict, Any
from bson import ObjectId

from app.core.database import db
from app.utils.mongo import stamp_create, stamp_update
from app.schemas.object_id import PyObjectId
from app.schemas.upi_details import UpiDetailsCreate, UpiDetailsUpdate, UpiDetailsOut

COLL = "upi_details"

def _to_out(doc: dict) -> UpiDetailsOut:
    return UpiDetailsOut.model_validate(doc)

async def create(payload: UpiDetailsCreate) -> UpiDetailsOut:
    try:
        doc = stamp_create(payload.model_dump())
        res = await db[COLL].insert_one(doc)
        saved = await db[COLL].find_one({"_id": res.inserted_id})
        return _to_out(saved)
    except Exception as e:
        raise e

async def list_all(skip: int = 0, limit: int = 50, query: Dict[str, Any] | None = None) -> List[UpiDetailsOut]:
    try:
        cur = (
            db[COLL]
            .find(query or {})
            .skip(max(skip, 0))
            .limit(max(limit, 0))
            .sort("createdAt", -1)
        )
        docs = await cur.to_list(length=limit)
        return [_to_out(d) for d in docs]
    except Exception as e:
        raise e

async def get_one(_id: PyObjectId) -> Optional[UpiDetailsOut]:
    try:
        oid = ObjectId(str(_id))
    except Exception:
        return None
    try:
        doc = await db[COLL].find_one({"_id": oid})
        return _to_out(doc) if doc else None
    except Exception as e:
        raise e

async def update_one(_id: PyObjectId, payload: UpiDetailsUpdate) -> Optional[UpiDetailsOut]:
    try:
        oid = ObjectId(str(_id))
    except Exception:
        return None

    data = {k: v for k, v in payload.model_dump().items() if v is not None}
    if not data:
        return None

    try:
        await db[COLL].update_one({"_id": oid}, {"$set": stamp_update(data)})
        doc = await db[COLL].find_one({"_id": oid})
        return _to_out(doc) if doc else None
    except Exception as e:
        raise e

async def delete_one(_id: PyObjectId) -> Optional[bool]:
    try:
        oid = ObjectId(str(_id))
    except Exception:
        return None
    try:
        r = await db[COLL].delete_one({"_id": oid})
        return r.deleted_count == 1
    except Exception as e:
        raise e