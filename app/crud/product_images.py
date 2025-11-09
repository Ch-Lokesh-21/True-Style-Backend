from __future__ import annotations
from typing import List, Optional
from bson import ObjectId

from app.core.database import db
from app.utils.mongo import stamp_create, stamp_update
from app.schemas.object_id import PyObjectId
from app.schemas.product_images import (
    ProductImagesCreate,
    ProductImagesUpdate,
    ProductImagesOut,
)

COLL = "product_images"


def _to_out(doc: dict) -> ProductImagesOut:
    return ProductImagesOut.model_validate(doc)


async def create(payload: ProductImagesCreate) -> Optional[ProductImagesOut]:
    """
    Insert a new product image document.
    Because PyObjectId is used and we dump with mode='python',
    product_id is a real BSON ObjectId in MongoDB.
    """
    try:
        doc = stamp_create(payload.model_dump(mode="python"))
        res = await db[COLL].insert_one(doc)
        saved = await db[COLL].find_one({"_id": res.inserted_id})
        return _to_out(saved) if saved else None
    except Exception:
        return None


async def list_all(
    skip: int = 0,
    limit: int = 50,
    product_id: Optional[PyObjectId] = None,
) -> List[ProductImagesOut]:
    try:
        query: dict = {}
        if product_id is not None:
            # product_id is already an ObjectId (PyObjectId)
            query["product_id"] = product_id

        cursor = (
            db[COLL]
            .find(query)
            .skip(max(skip, 0))
            .limit(max(limit, 0))
            .sort("createdAt", -1)
        )
        docs = await cursor.to_list(length=limit)
        return [_to_out(d) for d in docs]
    except Exception:
        return []


async def get_one(_id: PyObjectId) -> Optional[ProductImagesOut]:
    try:
        oid = ObjectId(str(_id))
    except Exception:
        return None
    try:
        doc = await db[COLL].find_one({"_id": oid})
        return _to_out(doc) if doc else None
    except Exception:
        return None


async def update_one(
    _id: PyObjectId,
    payload: ProductImagesUpdate,
) -> Optional[ProductImagesOut]:
    try:
        oid = ObjectId(str(_id))
    except Exception:
        return None

    try:
        # Keep ObjectIds intact by dumping in python mode
        data = {k: v for k, v in payload.model_dump(mode="python",exclude_none=True).items() if v is not None}
        if not data:
            return None

        await db[COLL].update_one({"_id": oid}, {"$set": stamp_update(data)})
        doc = await db[COLL].find_one({"_id": oid})
        return _to_out(doc) if doc else None
    except Exception:
        return None


async def delete_one(_id: PyObjectId) -> Optional[bool]:
    try:
        oid = ObjectId(str(_id))
    except Exception:
        return None
    try:
        r = await db[COLL].delete_one({"_id": oid})
        return r.deleted_count == 1
    except Exception:
        return None