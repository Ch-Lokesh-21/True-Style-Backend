from __future__ import annotations
from typing import List, Optional, Dict, Any, Any  # ensure Any is available
from bson import ObjectId

from app.core.database import db
from app.utils.mongo import stamp_create, stamp_update
from app.schemas.object_id import PyObjectId
from app.schemas.user_reviews import UserReviewsCreate, UserReviewsUpdate, UserReviewsOut

COLL = "user_reviews"

def _to_out(doc: dict) -> UserReviewsOut:
    return UserReviewsOut.model_validate(doc)

def _to_oid(value: Any) -> Optional[ObjectId]:
    try:
        return ObjectId(str(value))
    except Exception:
        return None

async def create(payload: UserReviewsCreate) -> UserReviewsOut:
    """
    Insert a new review. PyObjectId fields become real ObjectId via mode="python".
    """
    doc = stamp_create(payload.model_dump(mode="python", exclude_none=True))
    res = await db[COLL].insert_one(doc)
    saved = await db[COLL].find_one({"_id": res.inserted_id})
    return _to_out(saved)

async def list_all(
    skip: int = 0,
    limit: int = 50,
    query: Dict[str, Any] | None = None,
) -> List[UserReviewsOut]:
    q: Dict[str, Any] = {}
    if query:
        if "product_id" in query and query["product_id"] is not None:
            poid = _to_oid(query["product_id"])
            if poid:
                q["product_id"] = poid
        if "user_id" in query and query["user_id"] is not None:
            uoid = _to_oid(query["user_id"])
            if uoid:
                q["user_id"] = uoid
        if "review_status_id" in query and query["review_status_id"] is not None:
            rsoid = _to_oid(query["review_status_id"])
            if rsoid:
                q["review_status_id"] = rsoid

    cur = (
        db[COLL]
        .find(q)
        .skip(max(skip, 0))
        .limit(max(limit, 0))
        .sort("createdAt", -1)
    )
    docs = await cur.to_list(length=limit)
    return [_to_out(d) for d in docs]

async def get_one(_id: PyObjectId) -> Optional[UserReviewsOut]:
    oid = _to_oid(_id)
    if not oid:
        return None
    doc = await db[COLL].find_one({"_id": oid})
    return _to_out(doc) if doc else None

async def get_by_user_and_product(*, user_id: PyObjectId | str, product_id: PyObjectId | str) -> Optional[UserReviewsOut]:
    uoid = _to_oid(user_id)
    poid = _to_oid(product_id)
    if not (uoid and poid):
        return None
    doc = await db[COLL].find_one({"user_id": uoid, "product_id": poid})
    return _to_out(doc) if doc else None

async def update_one(_id: PyObjectId, payload: UserReviewsUpdate) -> Optional[UserReviewsOut]:
    oid = _to_oid(_id)
    if not oid:
        return None
    data = payload.model_dump(mode="python", exclude_none=True)
    if not data:
        return None
    await db[COLL].update_one({"_id": oid}, {"$set": stamp_update(data)})
    doc = await db[COLL].find_one({"_id": oid})
    return _to_out(doc) if doc else None

async def admin_set_status(*, item_id: PyObjectId, review_status_id: PyObjectId) -> Optional[UserReviewsOut]:
    oid = _to_oid(item_id)
    rsoid = _to_oid(review_status_id)
    if not (oid and rsoid):
        return None
    update = stamp_update({"review_status_id": rsoid})
    r = await db[COLL].update_one({"_id": oid}, {"$set": update})
    if r.matched_count != 1:
        return None
    doc = await db[COLL].find_one({"_id": oid})
    return _to_out(doc) if doc else None

async def delete_one(_id: PyObjectId) -> Optional[bool]:
    oid = _to_oid(_id)
    if not oid:
        return None
    r = await db[COLL].delete_one({"_id": oid})
    return r.deleted_count == 1