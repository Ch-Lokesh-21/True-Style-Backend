from __future__ import annotations
from typing import List, Optional, Dict, Any
import re

from app.core.database import db
from app.utils.mongo import stamp_create, stamp_update
from app.schemas.object_id import PyObjectId
from app.schemas.categories import CategoriesCreate, CategoriesUpdate, CategoriesOut

COLL = "categories"

# Collections that reference products by product_id (now as REAL ObjectId)
RELATED_COLLECTIONS_BY_PRODUCT_ID: Dict[str, str] = {
    "product_images": "product_id",
    "wishlist_items": "product_id",
    "cart_items": "product_id",
    "user_ratings": "product_id",
    "user_reviews": "product_id",
}

def _to_out(doc: dict) -> CategoriesOut:
    return CategoriesOut.model_validate(doc)


async def create(payload: CategoriesCreate) -> Optional[CategoriesOut]:
    doc = stamp_create(payload.model_dump(mode="python"))  # keep ObjectId/datetime
    res = await db[COLL].insert_one(doc)
    saved = await db[COLL].find_one({"_id": res.inserted_id})
    return _to_out(saved) if saved else None


async def list_all(
    skip: int = 0,
    limit: int = 50,
    category: Optional[str] = None,
    q: Optional[str] = None,
) -> List[CategoriesOut]:
    """List categories with optional exact `category` match or fuzzy `q` search (regex on category)."""
    query: Dict[str, Any] = {}
    if category:
        query["category"] = category
    if q:
        safe = re.escape(q)
        query["category"] = {"$regex": safe, "$options": "i"}

    cursor = (
        db[COLL]
        .find(query)
        .skip(max(0, int(skip)))
        .limit(max(0, int(limit)))
        .sort("createdAt", -1)
    )
    docs = await cursor.to_list(length=limit)
    return [_to_out(d) for d in docs]


async def get_one(_id: PyObjectId) -> Optional[CategoriesOut]:
    doc = await db[COLL].find_one({"_id": _id})
    return _to_out(doc) if doc else None


async def update_one(_id: PyObjectId, payload: CategoriesUpdate) -> Optional[CategoriesOut]:
    data = {k: v for k, v in payload.model_dump(mode="python",exclude_none=True).items() if v is not None}
    if not data:
        return None

    await db[COLL].update_one({"_id": _id}, {"$set": stamp_update(data)})
    doc = await db[COLL].find_one({"_id": _id})
    return _to_out(doc) if doc else None


async def delete_one(_id: PyObjectId) -> Optional[bool]:
    r = await db[COLL].delete_one({"_id": _id})
    return r.deleted_count == 1


async def delete_one_cascade(_id: PyObjectId) -> Optional[Dict[str, Any]]:
    """
    Transactionally delete a category and all its products and product-related documents.

    Returns:
      {
        "status": "deleted" | "not_found" | "error",
        "image_urls": [str, ...],   # all image URLs (product thumbnails + product_images)
        "stats": {
            "products_deleted": int,
            "product_images_deleted": int,
            "related_deleted": {coll: int, ...}
        }
      }

    Notes:
      - Requires MongoDB replica set for transactions.
      - Assumes products.category_id is ObjectId.
      - Assumes related collections store product_id as ObjectId.
    """
    image_urls: list[str] = []
    related_deleted_counts: Dict[str, int] = {}
    products_deleted = 0
    product_images_deleted = 0

    try:
        async with await db.client.start_session() as session:  # type: ignore[attr-defined]
            async with session.start_transaction():
                # Ensure category exists
                cat_doc = await db[COLL].find_one({"_id": _id}, session=session)
                if not cat_doc:
                    return {"status": "not_found", "image_urls": [], "stats": {}}

                # Find all products for this category (category_id is ObjectId)
                product_cursor = db["products"].find({"category_id": _id}, session=session)
                products = await product_cursor.to_list(length=None)

                if products:
                    product_ids = [p["_id"] for p in products]  # ObjectIds

                    # Collect product thumbnails
                    for p in products:
                        thumb = p.get("thumbnail_url")
                        if thumb:
                            image_urls.append(thumb)

                    # Collect product_images URLs (product_id is ObjectId)
                    rel_cursor = db["product_images"].find(
                        {"product_id": {"$in": product_ids}},
                        session=session,
                    )
                    rel_docs = await rel_cursor.to_list(length=None)
                    image_urls.extend([d.get("image_url") for d in rel_docs if d.get("image_url")])

                    # Delete product_images for these products
                    r_pi = await db["product_images"].delete_many(
                        {"product_id": {"$in": product_ids}},
                        session=session,
                    )
                    product_images_deleted = getattr(r_pi, "deleted_count", 0) or 0

                    # Delete other related documents referencing these products
                    for coll, field in RELATED_COLLECTIONS_BY_PRODUCT_ID.items():
                        if coll == "product_images":
                            continue
                        r_rel = await db[coll].delete_many(
                            {field: {"$in": product_ids}},
                            session=session,
                        )
                        related_deleted_counts[coll] = getattr(r_rel, "deleted_count", 0) or 0

                    # Delete products
                    r_prod = await db["products"].delete_many(
                        {"_id": {"$in": product_ids}},
                        session=session,
                    )
                    products_deleted = getattr(r_prod, "deleted_count", 0) or 0

                # Finally delete the category itself
                r_cat = await db[COLL].delete_one({"_id": _id}, session=session)
                if r_cat.deleted_count != 1:
                    raise RuntimeError("Primary category delete failed")

        return {
            "status": "deleted",
            "image_urls": [u for u in image_urls if u],
            "stats": {
                "products_deleted": products_deleted,
                "product_images_deleted": product_images_deleted,
                "related_deleted": related_deleted_counts,
            },
        }
    except Exception:
        return {"status": "error", "image_urls": [], "stats": {}}