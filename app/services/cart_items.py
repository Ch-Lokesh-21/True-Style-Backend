from __future__ import annotations
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone

from fastapi import HTTPException
from fastapi.responses import JSONResponse
from bson import ObjectId

from app.core.database import db
from app.schemas.object_id import PyObjectId
from app.schemas.cart_items import CartItemsCreate, CartItemsUpdate, CartItemsOut
from app.crud import cart_items as crud


async def create_item_service(
    product_id: PyObjectId,
    size: str,
    quantity: Optional[int],
    current_user: Dict[str, Any],
) -> CartItemsOut:
    payload = CartItemsCreate(
        cart_id=current_user["cart_id"],  # PyObjectId schema will coerce if this is a str
        product_id=product_id,
        size=size,
        quantity=quantity,
    )
    try:
        return await crud.create(payload)
    except HTTPException:
        raise
    except Exception as e:
        msg = str(e)
        if "E11000" in msg:
            raise HTTPException(status_code=409, detail="Duplicate cart item")
        raise HTTPException(status_code=500, detail=f"Failed to create cart item: {e}")


async def list_items_service(
    skip: int,
    limit: int,
    product_id: Optional[PyObjectId],
    current_user: Dict[str, Any],
) -> List[CartItemsOut]:
    try:
        q: Dict[str, Any] = {"cart_id": PyObjectId(current_user["cart_id"])}
        if product_id:
            q["product_id"] = product_id  # crud will normalize to ObjectId if valid
        return await crud.list_all(skip=skip, limit=limit, query=q)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list cart items: {e}")


async def get_item_service(item_id: PyObjectId, current_user: Dict[str, Any]) -> CartItemsOut:
    try:
        item = await crud.get_one(item_id)
        if not item:
            raise HTTPException(status_code=404, detail="Cart item not found")

        user_cart_id = str(current_user.get("cart_id", ""))
        if not user_cart_id:
            raise HTTPException(status_code=400, detail="Missing cart_id in current user")

        if str(item.cart_id) != user_cart_id:
            raise HTTPException(status_code=403, detail="Forbidden")
        return item
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get cart item: {e}")


async def update_item_service(
    item_id: PyObjectId,
    payload: CartItemsUpdate,
    current_user: Dict[str, Any],
) -> CartItemsOut:
    try:
        item = await crud.get_one(item_id)
        if not item:
            raise HTTPException(status_code=404, detail="Cart item not found")

        user_cart_id = str(current_user.get("cart_id", ""))
        if not user_cart_id:
            raise HTTPException(status_code=400, detail="Missing cart_id in current user")
        if str(item.cart_id) != user_cart_id:
            raise HTTPException(status_code=403, detail="Forbidden")

        if not any(v is not None for v in payload.model_dump().values()):
            raise HTTPException(status_code=400, detail="No fields provided for update")

        updated = await crud.update_one(item_id, payload)
        if not updated:
            raise HTTPException(status_code=404, detail="Cart item not found or not updated")
        return updated
    except HTTPException:
        raise
    except Exception as e:
        msg = str(e)
        if "E11000" in msg:
            raise HTTPException(status_code=409, detail="Duplicate cart item")
        raise HTTPException(status_code=500, detail=f"Failed to update cart item: {e}")


async def delete_item_service(item_id: PyObjectId, current_user: Dict[str, Any]):
    try:
        item = await crud.get_one(item_id)
        if not item:
            raise HTTPException(status_code=404, detail="Cart item not found")

        user_cart_id = str(current_user.get("cart_id", ""))
        if not user_cart_id:
            raise HTTPException(status_code=400, detail="Missing cart_id in current user")
        if str(item.cart_id) != user_cart_id:
            raise HTTPException(status_code=403, detail="Forbidden")

        ok = await crud.delete_one(item_id)
        if not ok:
            raise HTTPException(status_code=404, detail="Cart item not found")
        return JSONResponse(status_code=200, content={"deleted": True})
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete cart item: {e}")


# ----------------------------
# Transactional: Move to Wishlist
# ----------------------------
async def move_to_wishlist_service(item_id: PyObjectId, current_user: Dict[str, Any]) -> CartItemsOut:
    """
    Moves a cart line into wishlist_items atomically:
      - Upsert wishlist_items by (wishlist_id, product_id)
      - Delete the cart line
    Assumptions:
      - current_user contains "wishlist_id"
      - wishlist_items schema stores wishlist_id & product_id as ObjectId
    """
    # Ensure user owns the cart item
    cart_doc = await db["cart_items"].find_one({"_id": item_id})
    if not cart_doc:
        raise HTTPException(status_code=404, detail="Cart item not found")

    user_cart_id = current_user.get("cart_id", "")
    if not user_cart_id:
        raise HTTPException(status_code=400, detail="Missing cart_id in current user")
    if str(cart_doc["cart_id"]) != str(user_cart_id):
        raise HTTPException(status_code=403, detail="Forbidden")

    # Prepare ObjectIds for wishlist upsert
    product_oid = (
        cart_doc["product_id"]
        if isinstance(cart_doc.get("product_id"), ObjectId)
        else ObjectId(str(cart_doc["product_id"]))
    )
    wishlist_id_val = current_user.get("wishlist_id")
    try:
        wishlist_oid = wishlist_id_val if isinstance(wishlist_id_val, ObjectId) else ObjectId(str(wishlist_id_val))
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid wishlist_id in current user")

    try:
        async with await db.client.start_session() as session:
            async with session.start_transaction():
                # Upsert wishlist item (ObjectId FKs)
                f = {"wishlist_id": wishlist_oid, "product_id": product_oid}
                await db["wishlist_items"].update_one(
                    f,
                    {
                        "$setOnInsert": {
                            "wishlist_id": wishlist_oid,
                            "product_id": product_oid,
                            "createdAt": datetime.now(timezone.utc),
                        },
                        "$currentDate": {"updatedAt": True},
                    },
                    upsert=True,
                    session=session,
                )

                # Delete the cart line
                del_res = await db["cart_items"].delete_one({"_id": item_id}, session=session)
                if del_res.deleted_count != 1:
                    raise HTTPException(status_code=400, detail="Unable to move to wishlist")

        # committed — return the deleted cart snapshot
        return CartItemsOut.model_validate(cart_doc)

    except HTTPException:
        raise
    except Exception as e:
        msg = str(e)
        if "E11000" in msg:
            # unique index on (wishlist_id, product_id) may surface this from other writers
            raise HTTPException(status_code=409, detail="Duplicate wishlist item")
        raise HTTPException(status_code=500, detail=f"Failed to move to wishlist: {e}")