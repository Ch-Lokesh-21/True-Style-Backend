from __future__ import annotations
from typing import List, Optional, Dict, Any

from app.core.database import db
from app.utils.mongo import stamp_create, stamp_update
from app.schemas.object_id import PyObjectId
from app.schemas.wishlist_items import (
    WishlistItemsCreate,
    WishlistItemsUpdate,
    WishlistItemsOut,
)

COLL = "wishlist_items"


def _to_out(doc: dict) -> WishlistItemsOut:
    return WishlistItemsOut.model_validate(doc)


async def create(payload: WishlistItemsCreate) -> WishlistItemsOut:
    """
    Insert wishlist item.
    PyObjectId ensures FKs are real ObjectIds; model_dump(mode="python") keeps them as such.
    """
    doc = stamp_create(payload.model_dump(mode="python"))
    res = await db[COLL].insert_one(doc)
    saved = await db[COLL].find_one({"_id": res.inserted_id})
    return _to_out(saved)


async def list_all(
    skip: int = 0,
    limit: int = 50,
    query: Dict[str, Any] | None = None,
) -> List[WishlistItemsOut]:
    cur = (
        db[COLL]
        .find(query or {})
        .skip(max(0, int(skip)))
        .limit(max(0, int(limit)))
        .sort("createdAt", -1)
    )
    docs = await cur.to_list(length=limit)
    return [_to_out(d) for d in docs]


async def get_one(_id: PyObjectId) -> Optional[WishlistItemsOut]:
    doc = await db[COLL].find_one({"_id": _id})
    return _to_out(doc) if doc else None


async def update_one(_id: PyObjectId, payload: WishlistItemsUpdate) -> Optional[WishlistItemsOut]:
    """
    Partial update. Any FK fields in payload are already real ObjectIds via PyObjectId.
    """
    data = payload.model_dump(mode="python", exclude_none=True)
    if not data:
        return None

    await db[COLL].update_one({"_id": _id}, {"$set": stamp_update(data)})
    doc = await db[COLL].find_one({"_id": _id})
    return _to_out(doc) if doc else None


async def delete_one(_id: PyObjectId) -> Optional[bool]:
    r = await db[COLL].delete_one({"_id": _id})
    return r.deleted_count == 1