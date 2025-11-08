from __future__ import annotations
from typing import List, Optional, Dict, Any
from bson import ObjectId
import re

from app.core.database import db
from app.utils.mongo import stamp_create, stamp_update
from app.schemas.object_id import PyObjectId
from app.schemas.products import ProductsCreate, ProductsUpdate, ProductsOut

COLL = "products"

# All related collections store product_id as **ObjectId** now.
RELATED_COLLECTIONS: Dict[str, str] = {
   "product_images": "product_id",   
    "wishlist_items": "product_id",   
    "cart_items": "product_id",       
    "user_ratings": "product_id",     
    "user_reviews": "product_id",
}

def _to_out(doc: dict) -> ProductsOut:
    return ProductsOut.model_validate(doc)


async def create(payload: ProductsCreate) -> Optional[ProductsOut]:
    try:
        doc = stamp_create(payload.model_dump(mode="python"))
        # Ensure all FK fields are stored as ObjectId (PyObjectId already produces ObjectId)
        for fk in ("brand_id", "occasion_id", "category_id", "product_type_id"):
            if fk in doc and isinstance(doc[fk], str) and ObjectId.is_valid(doc[fk]):
                doc[fk] = ObjectId(doc[fk])
        res = await db[COLL].insert_one(doc)
        saved = await db[COLL].find_one({"_id": res.inserted_id})
        return _to_out(saved) if saved else None
    except Exception:
        return None


async def list_all(
    skip: int = 0,
    limit: int = 50,
    q: Optional[str] = None,
    brand_id: Optional[PyObjectId] = None,
    category_id: Optional[PyObjectId] = None,
    occasion_id: Optional[PyObjectId] = None,
    product_type_id: Optional[PyObjectId] = None,
    color: Optional[str] = None,
    out_of_stock: Optional[bool] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
) -> List[ProductsOut]:
    try:
        query: Dict[str, Any] = {}

        if brand_id is not None:
            query["brand_id"] = ObjectId(str(brand_id))
        if category_id is not None:
            query["category_id"] = ObjectId(str(category_id))
        if occasion_id is not None:
            query["occasion_id"] = ObjectId(str(occasion_id))
        if product_type_id is not None:
            query["product_type_id"] = ObjectId(str(product_type_id))
        if color is not None:
            query["color"] = color
        if out_of_stock is not None:
            query["out_of_stock"] = out_of_stock
        if min_price is not None or max_price is not None:
            pr: Dict[str, Any] = {}
            if min_price is not None:
                pr["$gte"] = min_price
            if max_price is not None:
                pr["$lte"] = max_price
            if pr:
                query["price"] = pr
        if q:
            safe = re.escape(q)
            query["$or"] = [
                {"name": {"$regex": safe, "$options": "i"}},
                {"description": {"$regex": safe, "$options": "i"}},
            ]

        cursor = (
            db[COLL]
            .find(query)
            .skip(max(0, int(skip)))
            .limit(max(0, int(limit)))
            .sort("createdAt", -1)
        )
        docs = await cursor.to_list(length=limit)
        return [_to_out(d) for d in docs]
    except Exception:
        return []


async def get_one(_id: PyObjectId) -> Optional[ProductsOut]:
    try:
        oid = ObjectId(str(_id))
    except Exception:
        return None
    try:
        doc = await db[COLL].find_one({"_id": oid})
        return _to_out(doc) if doc else None
    except Exception:
        return None


async def update_one(_id: PyObjectId, payload: ProductsUpdate) -> Optional[ProductsOut]:
    try:
        oid = ObjectId(str(_id))
    except Exception:
        return None

    try:
        data = {k: v for k, v in payload.model_dump(mode="python").items() if v is not None}

        # Ensure FKs remain ObjectId in updates
        for fk in ("brand_id", "occasion_id", "category_id", "product_type_id"):
            if fk in data and data[fk] is not None:
                data[fk] = ObjectId(str(data[fk]))

        if not data:
            return None

        await db[COLL].update_one({"_id": oid}, {"$set": stamp_update(data)})
        doc = await db[COLL].find_one({"_id": oid})
        return _to_out(doc) if doc else None
    except Exception:
        return None


async def delete_one_cascade(_id: PyObjectId) -> Optional[Dict[str, Any]]:
    """
    Transactionally delete product + all related docs.
    Assumes related collections store product_id as ObjectId.
    """
    try:
        oid = ObjectId(str(_id))
    except Exception:
        return None

    session = await db.client.start_session()
    image_urls: list[str] = []

    try:
        async with session.start_transaction():
            prod = await db[COLL].find_one({"_id": oid}, session=session)
            if not prod:
                await session.end_session()
                return {"status": "not_found", "image_urls": []}

            if thumb := prod.get("thumbnail_url"):
                image_urls.append(thumb)

            # Delete product_images (collect URLs first)
            if "product_images" in RELATED_COLLECTIONS:
                rel_field = RELATED_COLLECTIONS["product_images"]  # "product_id"
                rel_cursor = db["product_images"].find({rel_field: oid}, session=session)
                rel_docs = await rel_cursor.to_list(length=None)
                image_urls.extend([d.get("image_url") for d in rel_docs if d.get("image_url")])
                await db["product_images"].delete_many({rel_field: oid}, session=session)

            # Delete other referencing docs using ObjectId
            for coll, field in RELATED_COLLECTIONS.items():
                if coll == "product_images":
                    continue
                await db[coll].delete_many({field: oid}, session=session)

            # Finally delete the product
            r = await db[COLL].delete_one({"_id": oid}, session=session)
            if r.deleted_count != 1:
                raise RuntimeError("Primary product delete failed")

        await session.end_session()
        return {"status": "deleted", "image_urls": [u for u in image_urls if u]}
    except Exception:
        try:
            await session.abort_transaction()
        except Exception:
            pass
        try:
            await session.end_session()
        except Exception:
            pass
        return {"status": "error", "image_urls": []}