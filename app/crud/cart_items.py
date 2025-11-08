from __future__ import annotations
from typing import List, Optional, Dict, Any

from bson import ObjectId
from app.core.database import db
from app.utils.mongo import stamp_create, stamp_update
from app.schemas.object_id import PyObjectId
from app.schemas.cart_items import CartItemsCreate, CartItemsUpdate, CartItemsOut

COLL = "cart_items"


def _to_out(doc: dict) -> CartItemsOut:
    return CartItemsOut.model_validate(doc)


def _maybe_oid(v):
    if isinstance(v, ObjectId):
        return v
    try:
        return ObjectId(str(v))
    except Exception:
        return v  # leave as-is if not coercible


# Unique key for a cart line — keep as ObjectIds (not strings)
def _uk(doc: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "cart_id": _maybe_oid(doc.get("cart_id")),
        "product_id": _maybe_oid(doc.get("product_id")),
        "size": doc.get("size"),
    }


async def create(payload: CartItemsCreate) -> CartItemsOut:
    """
    Create-or-merge:
      If (cart_id, product_id, size) exists -> $inc quantity by payload.quantity
      Else insert a new line with that quantity.
    """
    base = payload.model_dump(mode="python")  # preserve ObjectId/datetime
    f = _uk(base)

    # Upsert pattern: set on insert then inc quantity
    await db[COLL].update_one(
        f,
        {
            "$setOnInsert": stamp_create({**f, "quantity": 0}),
            "$inc": {"quantity": base.get("quantity", 1)},
            "$currentDate": {"updatedAt": True},
        },
        upsert=True,
    )

    doc = await db[COLL].find_one(f)
    # Should always exist after upsert
    return _to_out(doc) if doc else None  # type: ignore[return-value]


async def list_all(skip: int = 0, limit: int = 50, query: Dict[str, Any] | None = None) -> List[CartItemsOut]:
    q: Dict[str, Any] = {}
    if query:
        q = {
            k: (_maybe_oid(v) if k in {"cart_id", "product_id", "_id"} else v)
            for k, v in query.items()
        }

    cur = (
        db[COLL]
        .find(q)
        .skip(max(skip, 0))
        .limit(max(limit, 0))
        .sort("createdAt", -1)
    )
    docs = await cur.to_list(length=limit)
    return [_to_out(d) for d in docs]


async def get_one(_id: PyObjectId) -> Optional[CartItemsOut]:
    doc = await db[COLL].find_one({"_id": _id})
    return _to_out(doc) if doc else None


async def update_one(_id: PyObjectId, payload: CartItemsUpdate) -> Optional[CartItemsOut]:
    """
    Plain field update; if a change would cause a duplicate (same cart_id+product_id+size),
    let a unique index prevent conflicts (or merge in service layer if desired).
    """
    data = {k: v for k, v in payload.model_dump(mode="python").items() if v is not None}
    if not data:
        return None

    await db[COLL].update_one({"_id": _id}, {"$set": stamp_update(data)})
    doc = await db[COLL].find_one({"_id": _id})
    return _to_out(doc) if doc else None


async def delete_one(_id: PyObjectId) -> Optional[bool]:
    r = await db[COLL].delete_one({"_id": _id})
    return r.deleted_count == 1