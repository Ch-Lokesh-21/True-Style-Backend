from __future__ import annotations
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone

from bson import ObjectId
from fastapi import HTTPException

from app.core.database import db
from app.schemas.object_id import PyObjectId
from app.schemas.wishlist_items import WishlistItemsCreate, WishlistItemsOut
from app.crud import wishlist_items as crud


def _coerce_oid(v: Any, field: str) -> ObjectId:
    try:
        return ObjectId(str(v))
    except Exception:
        raise HTTPException(status_code=400, detail=f"Invalid or missing {field}")


async def create_wishlist_item(product_id: PyObjectId, current_user: Dict) -> WishlistItemsOut:
    # validate/coerce wishlist_id from the current user
    wishlist_id = None
    try:
        wishlist_id = PyObjectId(current_user["wishlist_id"])
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid or missing wishlist_id for current user")

    payload = WishlistItemsCreate(product_id=product_id, wishlist_id=wishlist_id)
    try:
        return await crud.create(payload)
    except HTTPException:
        raise
    except Exception as e:
        if "E11000" in str(e):
            raise HTTPException(status_code=409, detail="Duplicate wishlist item")
        raise HTTPException(status_code=500, detail=f"Failed to create wishlist item: {e}")


async def list_wishlist_items(
    skip: int,
    limit: int,
    product_id: Optional[PyObjectId],
    current_user: Dict,
) -> List[WishlistItemsOut]:
    try:
        wishlist_id = PyObjectId(current_user["wishlist_id"])
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid or missing wishlist_id for current user")

    q: Dict[str, Any] = {"wishlist_id": wishlist_id}
    if product_id is not None:
        q["product_id"] = product_id

    try:
        return await crud.list_all(skip=skip, limit=limit, query=q)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list wishlist items: {e}")


async def get_wishlist_item(item_id: PyObjectId, current_user: Dict) -> WishlistItemsOut:
    try:
        item = await crud.get_one(item_id)
        if not item:
            raise HTTPException(status_code=404, detail="Wishlist item not found")

        if str(item.wishlist_id) != str(current_user.get("wishlist_id")):
            raise HTTPException(status_code=403, detail="Forbidden")

        return item
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get wishlist item: {e}")


async def move_wishlist_item_to_cart(
    item_id: PyObjectId,
    size: Optional[str],
    current_user: Dict,
) -> WishlistItemsOut:
    normalized_size = (size or "M").strip()
    if not normalized_size:
        raise HTTPException(status_code=400, detail="Size must be provided")

    # Validate/coerce ids from current user
    try:
        cart_id = PyObjectId(current_user["cart_id"])
        wishlist_id = PyObjectId(current_user["wishlist_id"])
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid or missing cart_id/wishlist_id for current user")

    # Load snapshot for return value after commit
    snapshot = await db["wishlist_items"].find_one({"_id": item_id})
    if not snapshot:
        raise HTTPException(status_code=404, detail="Wishlist item not found")

    if str(snapshot.get("wishlist_id")) != str(wishlist_id):
        raise HTTPException(status_code=403, detail="Forbidden")

    product_id = _coerce_oid(snapshot["product_id"], "product_id")

    async with await db.client.start_session() as session:
        async with session.start_transaction():
            # Upsert/merge cart line atomically
            filter_doc = {
                "cart_id": cart_id,
                "product_id": product_id,
                "size": normalized_size,
            }

            await db["cart_items"].update_one(
                filter_doc,
                {
                    "$setOnInsert": {
                        "cart_id": cart_id,
                        "product_id": product_id,
                        "size": normalized_size,
                        "quantity": 0,  # becomes 1 via $inc
                        "createdAt": datetime.now(timezone.utc),
                    },
                    "$inc": {"quantity": 1},
                    "$currentDate": {"updatedAt": True},
                },
                upsert=True,
                session=session,
            )

            del_res = await db["wishlist_items"].delete_one({"_id": item_id}, session=session)
            if del_res.deleted_count != 1:
                raise HTTPException(status_code=400, detail="Unable to move")

    # return the pre-delete snapshot as the API originally did
    return WishlistItemsOut.model_validate(snapshot)


async def delete_wishlist_item(item_id: PyObjectId, current_user: Dict) -> bool:
    try:
        item = await crud.get_one(item_id)
        if not item:
            raise HTTPException(status_code=404, detail="Wishlist item not found")

        if str(item.wishlist_id) != str(current_user.get("wishlist_id")):
            raise HTTPException(status_code=403, detail="Forbidden")

        ok = await crud.delete_one(item_id)
        if not ok:
            raise HTTPException(status_code=404, detail="Wishlist item not found")

        return True
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete wishlist item: {e}")