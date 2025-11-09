from __future__ import annotations
from typing import List, Optional, Dict, Any
import re

from app.core.database import db
from app.utils.mongo import stamp_create, stamp_update
from app.schemas.object_id import PyObjectId
from app.schemas.occasions import OccasionsCreate, OccasionsUpdate, OccasionsOut

COLL = "occasions"

# Collections that reference products by product_id (stringified ObjectId)
RELATED_COLLECTIONS_BY_PRODUCT_ID: Dict[str, str] = {
    "product_images": "product_id",
    "wishlist_items": "product_id",
    "cart_items": "product_id",
    "user_ratings": "product_id",
    "user_reviews": "product_id",
}


def _to_out(doc: dict) -> OccasionsOut:
    return OccasionsOut.model_validate(doc)


async def create(payload: OccasionsCreate) -> Optional[OccasionsOut]:
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
    occasion: Optional[str] = None,
    q: Optional[str] = None,
) -> List[OccasionsOut]:
    """
    List occasions with optional exact filters (idx, occasion) and fuzzy `q` search on `occasion`.
    """
    try:
        query: Dict[str, Any] = {}
        if occasion:
            query["occasion"] = occasion
        if q:
            safe = re.escape(q)
            query["occasion"] = {"$regex": safe, "$options": "i"}

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


async def get_one(_id: PyObjectId) -> Optional[OccasionsOut]:
    try:
        doc = await db[COLL].find_one({"_id": _id})
        return _to_out(doc) if doc else None
    except Exception:
        return None


async def update_one(_id: PyObjectId, payload: OccasionsUpdate) -> Optional[OccasionsOut]:
    data = {k: v for k, v in payload.model_dump(mode="python",exclude_none=True).items() if v is not None}
    if not data:
        return None
    try:
        await db[COLL].update_one({"_id": _id}, {"$set": stamp_update(data)})
        doc = await db[COLL].find_one({"_id": _id})
        return _to_out(doc) if doc else None
    except Exception:
        return None


async def delete_one(_id: PyObjectId) -> Optional[bool]:
    """Legacy single-collection delete (kept for parity). Prefer delete_one_cascade."""
    try:
        r = await db[COLL].delete_one({"_id": _id})
        return r.deleted_count == 1
    except Exception:
        return None


async def delete_one_cascade(_id: PyObjectId) -> Optional[Dict[str, Any]]:
    """
    Transactionally delete an occasion and all its products and product-related documents.

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

    Assumptions:
      - products.occasion_id is stored as **ObjectId** (per your products schema).
      - product_images.product_id (and other related product_id fields) are **str(ObjectId)**.
      - Requires MongoDB replica set for transactions.
    """
    session = await db.client.start_session()
    image_urls: list[str] = []
    related_deleted_counts: Dict[str, int] = {}
    products_deleted = 0
    product_images_deleted = 0

    try:
        async with session.start_transaction():
            # Ensure occasion exists
            occ_doc = await db[COLL].find_one({"_id": _id}, session=session)
            if not occ_doc:
                await session.end_session()
                return {"status": "not_found", "image_urls": [], "stats": {}}

            # Find all products for this occasion (occasion_id stored as ObjectId)
            product_cursor = db["products"].find({"occasion_id": _id}, session=session)
            products = await product_cursor.to_list(length=None)

            if products:
                product_ids = [p["_id"] for p in products]              # real ObjectIds
                product_ids_str = [str(pid) for pid in product_ids]     # str(ObjectId)

                # Collect product thumbnails
                for p in products:
                    thumb = p.get("thumbnail_url")
                    if thumb:
                        image_urls.append(thumb)

                # Collect product_images URLs
                rel_cursor = db["product_images"].find(
                    {"product_id": {"$in": product_ids_str}}, session=session
                )
                rel_docs = await rel_cursor.to_list(length=None)
                image_urls.extend([d.get("image_url") for d in rel_docs if d.get("image_url")])

                # Delete product_images for these products
                r_pi = await db["product_images"].delete_many(
                    {"product_id": {"$in": product_ids_str}}, session=session
                )
                product_images_deleted = getattr(r_pi, "deleted_count", 0) or 0

                # Delete other related documents referencing these products
                for coll, field in RELATED_COLLECTIONS_BY_PRODUCT_ID.items():
                    if coll == "product_images":
                        continue
                    r_rel = await db[coll].delete_many({field: {"$in": product_ids_str}}, session=session)
                    related_deleted_counts[coll] = getattr(r_rel, "deleted_count", 0) or 0

                # Delete the products themselves
                r_prod = await db["products"].delete_many({"_id": {"$in": product_ids}}, session=session)
                products_deleted = getattr(r_prod, "deleted_count", 0) or 0

            # Finally delete the occasion
            r_occ = await db[COLL].delete_one({"_id": _id}, session=session)
            if r_occ.deleted_count != 1:
                raise RuntimeError("Primary occasion delete failed")

        await session.end_session()
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
        try:
            await session.abort_transaction()
        except Exception:
            pass
        try:
            await session.end_session()
        except Exception:
            pass
        return {"status": "error", "image_urls": [], "stats": {}}