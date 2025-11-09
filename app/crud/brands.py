from __future__ import annotations

from typing import List, Optional, Dict, Any
import re

from app.core.database import db
from app.utils.mongo import stamp_create, stamp_update
from app.schemas.object_id import PyObjectId
from app.schemas.brands import BrandsCreate, BrandsUpdate, BrandsOut

COLL = "brands"

# Collections that reference products by product_id (now as REAL ObjectId)
RELATED_COLLECTIONS_BY_PRODUCT_ID: Dict[str, str] = {
    "product_images": "product_id",
    "wishlist_items": "product_id",
    "cart_items": "product_id",
    "user_ratings": "product_id",
    "user_reviews": "product_id",
}


def _to_out(doc: dict) -> BrandsOut:
    return BrandsOut.model_validate(doc)


async def create(payload: BrandsCreate) -> Optional[BrandsOut]:
    # Keep native types for Mongo (ObjectId, datetime, etc.)
    doc = stamp_create(payload.model_dump(mode="python"))
    res = await db[COLL].insert_one(doc)
    saved = await db[COLL].find_one({"_id": res.inserted_id})
    return _to_out(saved) if saved else None


async def list_all(
    skip: int = 0,
    limit: int = 50,
    name: Optional[str] = None,
    q: Optional[str] = None,
) -> List[BrandsOut]:
    """
    List brands with optional exact `name` match or fuzzy `q` search (regex on name).
    """
    query: Dict[str, Any] = {}
    if name:
        query["name"] = name
    if q:
        safe = re.escape(q)
        query["name"] = {"$regex": safe, "$options": "i"}

    cursor = (
        db[COLL]
        .find(query)
        .skip(max(0, int(skip)))
        .limit(max(0, int(limit)))
        .sort("createdAt", -1)
    )
    docs = await cursor.to_list(length=limit)
    return [_to_out(d) for d in docs]


async def get_one(_id: PyObjectId) -> Optional[BrandsOut]:
    # _id is already ObjectId thanks to PyObjectId
    doc = await db[COLL].find_one({"_id": _id})
    return _to_out(doc) if doc else None


async def update_one(_id: PyObjectId, payload: BrandsUpdate) -> Optional[BrandsOut]:
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
    Transactionally delete a brand and all its products and product-related documents.

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
      - Assumes products.brand_id is stored as ObjectId.
      - Assumes product_images.product_id (and other related product_id fields) are ObjectId.
    """
    image_urls: list[str] = []
    related_deleted_counts: Dict[str, int] = {}
    products_deleted = 0
    product_images_deleted = 0

    try:
        async with await db.client.start_session() as session:  # type: ignore[attr-defined]
            async with session.start_transaction():
                # Ensure brand exists
                brand_doc = await db[COLL].find_one({"_id": _id}, session=session)
                if not brand_doc:
                    return {"status": "not_found", "image_urls": [], "stats": {}}

                # Find all products for this brand (brand_id stored as ObjectId)
                product_cursor = db["products"].find({"brand_id": _id}, session=session)
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

                # Finally delete the brand
                r_brand = await db[COLL].delete_one({"_id": _id}, session=session)
                if r_brand.deleted_count != 1:
                    raise RuntimeError("Primary brand delete failed")

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