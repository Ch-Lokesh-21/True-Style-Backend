# app/crud/cart_items.py
from __future__ import annotations
from typing import List, Optional, Dict, Any

from datetime import datetime, timezone
from bson import ObjectId
from pymongo import ReturnDocument

from app.core.database import db
from app.utils.mongo import stamp_update
from app.schemas.object_id import PyObjectId
from app.schemas.cart_items import CartItemsCreate, CartItemsUpdate, CartItemsOut

COLL = "cart_items"


def _to_out(doc: dict) -> CartItemsOut:
    return CartItemsOut.model_validate(doc)


def _as_oid(v: Any, field: str) -> ObjectId:
    if isinstance(v, ObjectId):
        return v
    try:
        return ObjectId(str(v))
    except Exception:
        raise ValueError(f"Invalid {field}")


def _uk(doc: Dict[str, Any]) -> Dict[str, Any]:
    # Enforce real ObjectIds for the identity fields
    return {
        "cart_id": _as_oid(doc.get("cart_id"), "cart_id"),
        "product_id": _as_oid(doc.get("product_id"), "product_id"),
        "size": doc.get("size"),
    }


async def create(payload: CartItemsCreate) -> CartItemsOut:
    """
    Create-or-merge a cart line.
      - If (cart_id, product_id, size) exists -> $inc quantity by payload.quantity (default 1)
      - Else insert with quantity initialized to 0 and then $inc
    Returns the upserted/updated document atomically.
    """
    base = payload.model_dump(mode="python")  # keep ObjectIds as-is
    f = _uk(base)

    # Normalize quantity
    qty = int(base.get("quantity", 1))
    if qty == 0:
        # no-op; you can choose to raise instead
        doc = await db[COLL].find_one(f)
        if not doc:
            # If no existing line and qty=0, treat as error
            raise ValueError("quantity must be non-zero")
        return _to_out(doc)
    if qty < 0:
        # If you want to support decrements, handle delete-on-zero elsewhere
        raise ValueError("quantity must be positive")

    now = datetime.now(timezone.utc)

    # Atomic upsert + return AFTER to avoid race
    doc = await db[COLL].find_one_and_update(
    f,                       # e.g. {"cart_id": oid_cart, "product_id": oid_prod, "size": size}
    {
        # Only fields that should exist on first insert:
        "$setOnInsert": {
            **f,             # identity fields only; no quantity here
            "createdAt": now
        },
        # Let $inc create quantity on first insert and add thereafter:
        "$inc": {"quantity": qty},    # qty > 0 validated earlier
        # Keep updatedAt consistent:
        "$currentDate": {"updatedAt": True},
    },
    upsert=True,
    return_document=ReturnDocument.AFTER,
)

    # Defensive: doc should always exist here
    if not doc:
        raise RuntimeError("Upsert failed unexpectedly")
    return _to_out(doc)


async def list_all(skip: int = 0, limit: int = 50, query: Dict[str, Any] | None = None) -> List[CartItemsOut]:
    q: Dict[str, Any] = {}
    if query:
        q = {
            k: (_as_oid(v, k) if k in {"cart_id", "product_id", "_id"} else v)
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
    Plain field update; avoid touching quantity here if you rely on merge semantics elsewhere.
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