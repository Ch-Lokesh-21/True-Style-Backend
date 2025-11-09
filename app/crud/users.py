from __future__ import annotations
from typing import List, Optional, Dict, Any
from bson import ObjectId
from pymongo.errors import DuplicateKeyError
from app.core.database import db
from app.utils.mongo import stamp_create, stamp_update
from app.core.security import hash_password
from app.schemas.object_id import PyObjectId
from app.schemas.users import UserCreate, UserUpdate, UserOut
from app.crud import carts as carts_crud
from app.crud import wishlists as wishlists_crud
from app.schemas.carts import CartsCreate
from app.schemas.wishlists import WishlistsCreate
COLL = "users"

def _to_out(doc: dict) -> UserOut:
    return UserOut.model_validate(doc)

async def create(payload: UserCreate) -> UserOut:
    data = stamp_create(payload.model_dump(mode="python"))
    # hash password if provided
    pwd = data.get("password")
    if pwd:
        data["password"] = hash_password(pwd)

    try:
        res = await db[COLL].insert_one(data)
    except Exception as e:
        raise e

    saved = await db[COLL].find_one({"_id": res.inserted_id})
    cart = CartsCreate(
        user_id=res.inserted_id
    )
    wishlist = WishlistsCreate(
        user_id=res.inserted_id
    )
    try:
        await carts_crud.create(cart)
        await wishlists_crud.create(wishlist)
    except Exception as e:
        raise e
    return _to_out(saved)

async def list_all(skip: int = 0, limit: int = 50, query: Dict[str, Any] | None = None) -> List[UserOut]:
    cur = (
        db[COLL]
        .find(query or {})
        .skip(max(skip, 0))
        .limit(max(limit, 0))
        .sort("createdAt", -1)
    )
    docs = await cur.to_list(length=limit)
    return [_to_out(d) for d in docs]

async def get_one(_id: PyObjectId) -> Optional[UserOut]:
    try:
        oid = ObjectId(str(_id))
    except Exception:
        return None
    doc = await db[COLL].find_one({"_id": oid})
    return _to_out(doc) if doc else None

async def get_by_email(email: str) -> Optional[UserOut]:
    doc = await db[COLL].find_one({"email": email})
    return _to_out(doc) if doc else None

async def update_one(_id: PyObjectId, payload: UserUpdate | Dict[str, Any]) -> Optional[UserOut]:
    try:
        oid = ObjectId(str(_id))
    except Exception:
        return None

    data = payload.model_dump(mode="python",exclude_none=True) if isinstance(payload, UserUpdate) else dict(payload)
    data = {k: v for k, v in data.items() if v is not None}
    if not data:
        return None

    try:
        await db[COLL].update_one({"_id": oid}, {"$set": stamp_update(data)})
    except DuplicateKeyError as e:
        raise e

    doc = await db[COLL].find_one({"_id": oid})
    return _to_out(doc) if doc else None

async def delete_one(_id: PyObjectId) -> Optional[bool]:
    try:
        uid = ObjectId(_id)
    except Exception:
        raise 

    client = db.client  # AsyncIOMotorClient
    async with await client.start_session() as s:
        async with s.start_transaction():
            # 1) PREFETCH parent IDs (before we delete those parents)
            wish_ids = [d["_id"] async for d in db["wishlists"].find(
                {"user_id": uid}, {"_id": 1}, session=s
            )]
            cart_ids = [d["_id"] async for d in db["carts"].find(
                {"user_id": uid}, {"_id": 1}, session=s
            )]

            # 2) DELETE leaf children that depend on those IDs
            if wish_ids:
                await db["wishlist_items"].delete_many(
                    {"wishlist_id": {"$in": wish_ids}}, session=s
                )
            if cart_ids:
                await db["cart_items"].delete_many(
                    {"cart_id": {"$in": cart_ids}}, session=s
                )

            # 3) DELETE direct children that reference user_id
            for coll in (
                "user_address",
                "user_reviews",
                "carts",
                "wishlists",
            ):
                await db[coll].delete_many({"user_id": uid}, session=s)
            res = await db["users"].delete_one({"_id": uid}, session=s)
            return res.deleted_count == 1
    
    return False