from __future__ import annotations
from typing import List, Optional, Dict, Any
from bson import ObjectId
from app.core.database import db  
from app.utils.mongo import stamp_create, stamp_update
from app.schemas.object_id import PyObjectId
from app.schemas.user_ratings import (
    UserRatingsCreate,
    UserRatingsUpdate,
    UserRatingsOut,
)

COLL = "user_ratings"
PRODUCTS = "products"


def _to_out(doc: dict) -> UserRatingsOut:
    return UserRatingsOut.model_validate(doc)


def _to_oid(value: Any) -> Optional[ObjectId]:
    try:
        return ObjectId(str(value))
    except Exception:
        return None


# in app/crud/user_ratings.py

async def _recompute_product_rating(session, product_oid: ObjectId) -> None:
    """
    Recompute products.rating (0–5) from user_ratings for this product.
    Must be called inside a running transaction.
    """
    pipeline = [
        {"$match": {"product_id": product_oid}},
        {"$group": {"_id": "$product_id", "count": {"$sum": 1}, "avg": {"$avg": "$rating"}}},
    ]
    cursor = db[COLL].aggregate(pipeline, session=session)
    group = None
    async for g in cursor:
        group = g
        break

    # If there are no ratings left, set rating to 0.0 (or None if you prefer)
    new_rating = float(group.get("avg", 0.0)) if group else 0.0

    updates = {"rating": new_rating}
    updates = stamp_update(updates)
    await db[PRODUCTS].update_one({"_id": product_oid}, {"$set": updates}, session=session)


# -------------------
# Basic CRUD (list/get)
# -------------------
async def list_all(
    skip: int = 0,
    limit: int = 50,
    query: Dict[str, Any] | None = None,
) -> List[UserRatingsOut]:
    q: Dict[str, Any] = {}
    if query:
        # normalize optional filter string ids to ObjectId if possible
        if "product_id" in query and query["product_id"] is not None:
            poid = _to_oid(query["product_id"])
            q["product_id"] = poid if poid else query["product_id"]
        if "user_id" in query and query["user_id"] is not None:
            uoid = _to_oid(query["user_id"])
            q["user_id"] = uoid if uoid else query["user_id"]

    cur = (
        db[COLL]
        .find(q)
        .skip(max(skip, 0))
        .limit(max(limit, 0))
        .sort("createdAt", -1)
    )
    docs = await cur.to_list(length=limit)
    return [_to_out(d) for d in docs]


async def get_one(_id: PyObjectId) -> Optional[UserRatingsOut]:
    oid = _to_oid(_id)
    if not oid:
        return None
    doc = await db[COLL].find_one({"_id": oid})
    return _to_out(doc) if doc else None


async def get_by_user_and_product(*, user_id: str, product_id: str) -> Optional[UserRatingsOut]:
    uoid = _to_oid(user_id)
    poid = _to_oid(product_id)
    if not (uoid and poid):
        return None
    doc = await db[COLL].find_one({"user_id": uoid, "product_id": poid})
    return _to_out(doc) if doc else None


# -------------------------
# Transactional mutations
# -------------------------
async def create_with_recalc(payload: UserRatingsCreate) -> UserRatingsOut:
    # Expect payload.user_id and payload.product_id to be (coercible to) ObjectId.
    product_oid = _to_oid(payload.product_id)
    if not product_oid:
        raise ValueError("Invalid product_id")

    async with await db.client.start_session() as s:  # type: ignore[attr-defined]
        async with s.start_transaction():
            doc = stamp_create(payload.model_dump())
            res = await db[COLL].insert_one(doc, session=s)
            saved = await db[COLL].find_one({"_id": res.inserted_id}, session=s)
            # recompute product rating inside the same txn
            await _recompute_product_rating(s, product_oid)
            return _to_out(saved)


async def update_with_recalc(_id: PyObjectId, payload: UserRatingsUpdate) -> Optional[UserRatingsOut]:
    oid = _to_oid(_id)
    if not oid:
        return None

    # Need product_id to recompute; read existing doc first
    existing = await db[COLL].find_one({"_id": oid})
    if not existing:
        return None
    product_oid = existing.get("product_id")
    if not isinstance(product_oid, ObjectId):
        product_oid = _to_oid(product_oid)
    if not product_oid:
        return None

    data = {k: v for k, v in payload.model_dump().items() if v is not None}
    if not data:
        return None

    async with await db.client.start_session() as s:  # type: ignore[attr-defined]
        async with s.start_transaction():
            await db[COLL].update_one({"_id": oid}, {"$set": stamp_update(data)}, session=s)
            doc = await db[COLL].find_one({"_id": oid}, session=s)
            await _recompute_product_rating(s, product_oid)
            return _to_out(doc) if doc else None


async def delete_with_recalc(_id: PyObjectId) -> Optional[bool]:
    oid = _to_oid(_id)
    if not oid:
        return None

    # Need product_id before delete
    existing = await db[COLL].find_one({"_id": oid})
    if not existing:
        return None
    product_oid = existing.get("product_id")
    if not isinstance(product_oid, ObjectId):
        product_oid = _to_oid(product_oid)
    if not product_oid:
        return None

    async with await db.client.start_session() as s:  # type: ignore[attr-defined]
        async with s.start_transaction():
            r = await db[COLL].delete_one({"_id": oid}, session=s)
            # recompute after delete within txn
            await _recompute_product_rating(s, product_oid)
            return r.deleted_count == 1