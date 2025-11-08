from __future__ import annotations
from typing import List, Optional, Dict, Any
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import JSONResponse
from bson import ObjectId

from app.api.deps import require_permission, get_current_user
from app.core.database import db
from app.schemas.object_id import PyObjectId
from app.schemas.wishlist_items import WishlistItemsCreate, WishlistItemsOut
from app.crud import wishlist_items as crud

router = APIRouter()


@router.post(
    "/",
    response_model=WishlistItemsOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("wishlist_items", "Create"))],
)
async def create_item(
    product_id: PyObjectId,
    current_user: Dict = Depends(get_current_user),
):
    """
    Create wishlist item for the current user.
    All FKs are real ObjectIds via PyObjectId.
    """
    try:
        # current_user isn't validated by Pydantic; coerce once via PyObjectId
        wishlist_id = PyObjectId(current_user["wishlist_id"])
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid or missing wishlist_id for current user")

    payload = WishlistItemsCreate(
        product_id=product_id,
        wishlist_id=wishlist_id,
    )
    try:
        return await crud.create(payload)
    except HTTPException:
        raise
    except Exception as e:
        if "E11000" in str(e):
            raise HTTPException(status_code=409, detail="Duplicate wishlist item")
        raise HTTPException(status_code=500, detail=f"Failed to create wishlist item: {e}")


@router.get(
    "/",
    response_model=List[WishlistItemsOut],
    dependencies=[Depends(require_permission("wishlist_items", "Read"))],
)
async def list_items(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    product_id: Optional[PyObjectId] = Query(None, description="Filter by product_id"),
    current_user: Dict = Depends(get_current_user),
):
    """
    List current user's wishlist items. Optional filter by product_id.
    """
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


@router.get(
    "/{item_id}",
    response_model=WishlistItemsOut,
    dependencies=[Depends(require_permission("wishlist_items", "Read"))],
)
async def get_item(
    item_id: PyObjectId,
    current_user: Dict = Depends(get_current_user),
):
    """
    Get a wishlist item if it belongs to the current user.
    """
    try:
        item = await crud.get_one(item_id)
        if not item:
            raise HTTPException(status_code=404, detail="Wishlist item not found")

        # Compare by stringified ObjectIds to avoid type noise
        if str(item.wishlist_id) != str(current_user["wishlist_id"]):
            raise HTTPException(status_code=403, detail="Forbidden")

        return item
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get wishlist item: {e}")


@router.post(
    "/move-to-cart/{item_id}",
    response_model=WishlistItemsOut,
    dependencies=[Depends(require_permission("wishlist_items", "Delete"))],
)
async def move_item(
    item_id: PyObjectId,
    size: Optional[str] = None,
    current_user: Dict = Depends(get_current_user),
):
    """
    Atomically:
      1) Upsert/merge cart line {cart_id, product_id, size} (+1 quantity)
      2) Delete wishlist item
    """
    normalized_size = (size or "M").strip()
    if not normalized_size:
        raise HTTPException(status_code=400, detail="Size must be provided")

    # Validate/current-user IDs once
    try:
        cart_id = PyObjectId(current_user["cart_id"])
        wishlist_id = PyObjectId(current_user["wishlist_id"])
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid or missing cart_id/wishlist_id for current user")

    # Load snapshot (to return after commit)
    snapshot = await db["wishlist_items"].find_one({"_id": item_id})
    if not snapshot:
        raise HTTPException(status_code=404, detail="Wishlist item not found")

    if str(snapshot.get("wishlist_id")) != str(wishlist_id):
        raise HTTPException(status_code=403, detail="Forbidden")

    product_id = PyObjectId(snapshot["product_id"])

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
                        "createdAt": datetime.utcnow(),
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

    return WishlistItemsOut.model_validate(snapshot)


@router.delete(
    "/{item_id}",
    dependencies=[Depends(require_permission("wishlist_items", "Delete"))],
)
async def delete_item(
    item_id: PyObjectId,
    current_user: Dict = Depends(get_current_user),
):
    """
    Delete a wishlist item if it belongs to the current user.
    """
    try:
        item = await crud.get_one(item_id)
        if not item:
            raise HTTPException(status_code=404, detail="Wishlist item not found")

        if str(item.wishlist_id) != str(current_user["wishlist_id"]):
            raise HTTPException(status_code=403, detail="Forbidden")

        ok = await crud.delete_one(item_id)
        if not ok:
            raise HTTPException(status_code=404, detail="Wishlist item not found")

        return JSONResponse(status_code=200, content={"deleted": True})
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete wishlist item: {e}")