# seed.py
import asyncio
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional

from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId
from pymongo.errors import OperationFailure
from pymongo.read_concern import ReadConcern
from pymongo.write_concern import WriteConcern
from pymongo.read_preferences import ReadPreference

from app.core.config import settings
from app.core.security import hash_password

# -----------------------
# Safe index creation (DDL; cannot be inside transactions)
# -----------------------
async def safe_create_index(coll, keys, **opts):
    try:
        return await coll.create_index(keys, **opts)
    except OperationFailure as e:
        # IndexOptionsConflict (exists with different name/options)
        if e.code == 85:
            return None
        raise

# -----------------------
# Collections
# -----------------------
ALL_COLLECTIONS: List[str] = [
    "user_roles", "permissions", "role_permissions",
    "user_status", "order_status", "return_status", "exchange_status",
    "brands", "product_types", "occasions", "categories", "review_status",
    "payment_types", "payment_status", "coupons_status",
    "hero_images", "cards_1", "cards_2", "how_it_works", "testimonials",
    "about", "policies", "faq", "terms_and_conditions", "store_details",
    "users", "products", "product_images",
    "wishlists", "wishlist_items",
    "carts", "cart_items",
    "user_address",
    "orders", "order_items",
    "user_reviews", "user_ratings",
    "returns", "exchanges",
    "payments", "card_details", "upi_details",
    "coupons", "subscriptions",
    "backup_logs", "restore_logs",
]

NON_COLLECTION_RESOURCES: List[str] = [
    "dashboard", "contact_us", "login_logs", "register_logs", "logout_logs"
]
RESOURCES_FOR_PERMS: List[str] = ALL_COLLECTIONS + NON_COLLECTION_RESOURCES

LOOKUP_COLLECTIONS = {
    "user_status", "order_status", "return_status", "exchange_status",
    "brands", "product_types", "occasions", "categories", "review_status",
    "payment_types", "payment_status", "coupons_status",
}
 
CMS_COLLECTIONS = {
    "hero_images", "cards_1", "cards_2", "how_it_works", "testimonials",
    "about", "policies", "faq", "terms_and_conditions", "store_details",
}

SYSTEM_LOG_COLLECTIONS = {"backup_logs", "restore_logs"}

USER_READ_BLOCKED = {
    "backup_logs", "restore_logs", "dashboard", "contact_us", "login_logs", "register_logs", "logout_logs"
}

USER_WRITABLE_COLLECTIONS = {
    "users", "user_address", "wishlists", "wishlist_items",
    "carts", "cart_items", "orders", "order_items",
    "user_reviews", "user_ratings", "returns", "exchanges", "subscriptions",
    "payments", "card_details", "upi_details"
}

USER_DELETE_COLLECTIONS = {
    "user_address", "wishlist_items", "cart_items", "user_reviews", "user_ratings"
}

# -----------------------
# Index configs
# -----------------------
UNIQUE_FIELDS: Dict[str, List[str]] = {
    "user_roles": ["role"],
    "permissions": ["resource_name"],
    "user_status": ["status"],
    "order_status": ["status"],
    "return_status": ["status"],
    "exchange_status": ["status"],
    "brands": ["name"],
    "product_types": ["type", "size_chart_url", "thumbnail_url"],
    "occasions": ["occasion"],
    "categories": ["category"],
    "review_status": ["status"],
    "payment_types": ["type"],
    "payment_status": ["status"],
    "coupons_status": ["status"],
    "hero_images": ["idx", "image_url"],
    "cards_1": ["idx", "image_url", "title"],
    "cards_2": ["idx", "image_url", "title"],
    "how_it_works": ["idx", "image_url", "title"],
    "testimonials": ["idx", "image_url", "description"],
    "about": ["idx", "image_url", "description"],
    "policies": ["idx", "image_url", "description", "title"],
    "faq": ["idx"],
    "terms_and_conditions": ["idx"],
    "store_details": ["name", "pan_no", "gst_no"],
    "users": ["email", "phone_no"],
    "products": ["thumbnail_url"],
    "payments": ["invoice_no"],
    "coupons": ["code"],
}

FK_INDEXES: Dict[str, List[str]] = {
    "role_permissions": ["role_id", "permission_id"],
    "users": ["user_status_id", "role_id"],
    "products": ["brand_id", "occasion_id", "category_id", "product_type_id"],
    "product_images": ["product_id"],
    "wishlists": ["user_id"],
    "wishlist_items": ["wishlist_id", "product_id"],
    "carts": ["user_id"],
    "cart_items": ["cart_id", "product_id"],
    "user_address": ["user_id"],
    "orders": ["user_id", "address_id", "status_id"],
    "order_items": ["order_id", "product_id"],
    "user_reviews": ["product_id", "user_id", "review_status_id"],
    "user_ratings": ["product_id", "user_id"],
    "returns": ["order_id", "product_id", "return_status_id", "user_id"],
    "exchanges": ["order_id", "product_id", "exchange_status_id", "user_id"],
    "payments": ["user_id", "order_id", "payment_types_id", "payment_status_id"],
    "card_details": ["payment_id"],
    "upi_details": ["payment_id"],
    "coupons": ["coupons_status_id"],
    "subscriptions": ["user_id"],
}

COMPOUND_UNIQUES = {
    "role_permissions": [("role_id", 1), ("permission_id", 1)],
    "wishlists": [("user_id", 1)],
    "carts": [("user_id", 1)],
    "wishlist_items": [("wishlist_id", 1), ("product_id", 1)],
    "cart_items": [("cart_id", 1), ("product_id", 1), ("size", 1)],
    "product_images": [("product_id", 1), ("image_url", 1)],
    "order_items": [("order_id", 1), ("product_id", 1), ("size", 1)],
    "user_reviews": [("product_id", 1), ("user_id", 1)],
    "user_ratings": [("product_id", 1), ("user_id", 1)],
    "card_details": [("payment_id", 1)],
    "upi_details": [("payment_id", 1)],
}

# -----------------------
# RBAC helpers
# -----------------------
def perm_id_for(collection: str) -> str:
    return f"perm:{collection}"

def policy_for_user(collection: str) -> Dict[str, bool]:
    if collection == "users":
        return {"Create": False, "Read": True, "Update": True, "Delete": False}
    if collection in USER_READ_BLOCKED:
        return {"Create": False, "Read": False, "Update": False, "Delete": False}
    can_write = (collection in USER_WRITABLE_COLLECTIONS)
    can_delete = (collection in USER_DELETE_COLLECTIONS)
    return {"Create": bool(can_write), "Read": True, "Update": bool(can_write), "Delete": bool(can_delete)}

ADMIN_POLICY = {"Create": True, "Read": True, "Update": True, "Delete": True}

# -----------------------
# Index creation (preflight; non-transactional)
# -----------------------
async def ensure_indexes(db):
    for coll, uniques in UNIQUE_FIELDS.items():
        for field in uniques:
            await safe_create_index(db[coll], [(field, 1)], name=f"uniq_{field}", unique=True)

    for coll, fk_fields in FK_INDEXES.items():
        for field in fk_fields:
            await safe_create_index(db[coll], [(field, 1)], name=f"idx_{field}")

    for coll, spec in COMPOUND_UNIQUES.items():
        await safe_create_index(db[coll], spec, name="uniq_compound_" + "_".join([k for k, _ in spec]), unique=True)

# -----------------------
# RBAC seeding (transactional)
# -----------------------
async def upsert_role(db, role_name: str, *, session) -> ObjectId:
    existing = await db["user_roles"].find_one({"role": role_name}, session=session)
    if existing:
        return existing["_id"]
    res = await db["user_roles"].insert_one({"role": role_name}, session=session)
    return res.inserted_id

async def upsert_permission(db, resource_name: str, policy: Dict[str, bool], *, session) -> str:
    _id = perm_id_for(resource_name)
    now = datetime.now(timezone.utc)
    await db["permissions"].update_one(
        {"_id": _id},
        {
            "$set": {"resource_name": resource_name, **policy, "updatedAt": now},
            "$setOnInsert": {"createdAt": now},
        },
        upsert=True,
        session=session,
    )
    return _id

async def upsert_role_permission(db, role_id: ObjectId, permission_id: str, *, session):
    now = datetime.now(timezone.utc)
    await db["role_permissions"].update_one(
        {"role_id": role_id, "permission_id": permission_id},
        {
            "$set": {"updatedAt": now},
            "$setOnInsert": {"createdAt": now},
        },
        upsert=True,
        session=session,
    )

async def seed_rbac(db, *, session):
    admin_role_id = await upsert_role(db, "admin", session=session)
    user_role_id  = await upsert_role(db, "user",  session=session)

    for coll in RESOURCES_FOR_PERMS:
        admin_perm_id = await upsert_permission(db, coll, ADMIN_POLICY, session=session)
        await upsert_role_permission(db, admin_role_id, admin_perm_id, session=session)

        user_policy = policy_for_user(coll)
        user_perm_id = await upsert_permission(db, f"user:{coll}", user_policy, session=session)
        await upsert_role_permission(db, user_role_id, user_perm_id, session=session)

# -----------------------
# Lookup seeding (transactional)
# -----------------------
LOOKUP_SEED: Dict[str, List[Dict[str, Any]]] = {
    "user_status": [{"status": "active"}, {"status": "blocked"}],
    "order_status": [
        {"status": "placed"}, {"status": "confirmed"}, {"status": "packed"},
        {"status": "shipped"}, {"status": "out for delivery"}, {"status": "delivered"},
        {"status": "cancelled"},
    ],
    "return_status": [
        {"status": "requested"}, {"status": "approved"}, {"status": "rejected"},
        {"status": "received"}, {"status": "refunded"},
    ],
    "exchange_status": [
        {"status": "requested"}, {"status": "approved"}, {"status": "rejected"},
        {"status": "shipped"}, {"status": "completed"},
    ],
    "review_status": [{"status": "visible"}, {"status": "hidden"}],
    "payment_types": [{"type": "cod"}, {"type": "card"}, {"type": "upi"}],
    "payment_status": [{"status": "pending"}, {"status": "success"}, {"status": "failed"}],
    "coupons_status": [{"status": "active"}, {"status": "inactive"}],
    "occasions": [{"occasion": "casual"}, {"occasion": "formal"}, {"occasion": "ethnic"}],
    "categories": [{"category": "jeans"}, {"category": "shirts"}, {"category": "T-shirts"}, {"category": "Sweatshirts"}],
    "brands": [{"name": "DMNX"}, {"name": "H&M"}],
}

LOOKUP_MATCH_KEYS: Dict[str, List[str]] = {
    "user_status": ["status"],
    "order_status": ["status"],
    "return_status": ["status"],
    "exchange_status": ["status"],
    "review_status": ["status"],
    "payment_types": ["type"],
    "payment_status": ["status"],
    "coupons_status": ["status"],
    "occasions": ["occasion"],
    "categories": ["category"],
    "brands": ["name"],
    "product_types": ["type"],
}

def _build_match(doc: Dict[str, Any], keys: List[str]) -> Dict[str, Any]:
    return {k: doc[k] for k in keys if k in doc}

async def seed_lookup_collections(db, *, session):
    now = datetime.now(timezone.utc)
    for coll, items in LOOKUP_SEED.items():
        if not items:
            continue
        keys = LOOKUP_MATCH_KEYS.get(coll)
        if not keys:
            continue
        for item in items:
            match = _build_match(item, keys)
            if not match:
                continue
            await db[coll].update_one(
                match,
                {"$set": {**item, "updatedAt": now}, "$setOnInsert": {"createdAt": now}},
                upsert=True,
                session=session,
            )

# -----------------------
# Initial credentials (transactional)
# -----------------------
async def seed_initial_users(db, *, session):
    now = datetime.now(timezone.utc)

    admin_role = await db["user_roles"].find_one({"role": "admin"}, session=session)
    user_role  = await db["user_roles"].find_one({"role": "user"},  session=session)
    active_status = await db["user_status"].find_one({"status": "active"}, session=session)

    if not admin_role or not user_role or not active_status:
        raise RuntimeError("Missing roles/status. Run lookup + RBAC seeding first (inside the same transaction).")

    admin_role_id = admin_role["_id"]
    user_role_id  = user_role["_id"]
    active_status_id = active_status["_id"]

    # --- admin credential ---
    admin_email = "truestyle419@gmail.com"
    existing_admin = await db["users"].find_one({"email": admin_email}, session=session)
    if not existing_admin:
        res = await db["users"].insert_one({
            "first_name": "True",
            "last_name": "Style",
            "email": admin_email,
            "country_code": "+91",
            "phone_no": "1234567890",
            "password": hash_password("Truestyle*1234"),
            "role_id": admin_role_id,
            "user_status_id": active_status_id,
            "createdAt": now,
            "updatedAt": now,
        }, session=session)
        await db["carts"].insert_one({"user_id": res.inserted_id}, session=session)
        await db["wishlists"].insert_one({"user_id": res.inserted_id}, session=session)

    # --- normal user credential ---
    user_email = "lokeshchirumamilla59@gmail.com"
    existing_user = await db["users"].find_one({"email": user_email}, session=session)
    if not existing_user:
        res = await db["users"].insert_one({
            "first_name": "Lokesh",
            "last_name": "Chirumamilla",
            "email": user_email,
            "country_code": "+91",
            "phone_no": "8978739281",
            "password": hash_password("Truestyle*1234"),
            "role_id": user_role_id,
            "user_status_id": active_status_id,
            "createdAt": now,
            "updatedAt": now,
        }, session=session)
        await db["carts"].insert_one({"user_id": res.inserted_id}, session=session)
        await db["wishlists"].insert_one({"user_id": res.inserted_id}, session=session)

# -----------------------
# Main
# -----------------------
async def main():
    client = AsyncIOMotorClient(settings.MONGO_URI)
    try:
        db = client[settings.MONGO_DB]

        # 0) Pre-create collections to avoid implicit creation inside a txn (optional but safer)
        for name in ALL_COLLECTIONS:
            # touching collection causes implicit creation in many cases, but we can also create explicitly:
            await db.create_collection(name) if name not in await db.list_collection_names() else None
        # (Ignore if collection exists; OperationFailure handled by Motor)

        # 1) Indexes (non-transactional)
        await ensure_indexes(db)

        # 2) DATA SEEDING in ONE TRANSACTION (all-or-nothing)
        #    Use majority write concern and primary read preference.
        async with await client.start_session() as session:
            try:
                async with session.start_transaction(
                    read_concern=ReadConcern("local"),
                    write_concern=WriteConcern("majority"),
                    read_preference=ReadPreference.PRIMARY,
                ):
                    await seed_lookup_collections(db, session=session)
                    await seed_rbac(db, session=session)
                    await seed_initial_users(db, session=session)
                # If we exit the context without exception, the transaction is committed.
                print("Seed complete: indexes done; data seeding committed atomically.")
            except Exception as txn_err:
                # Transaction is automatically aborted on exception.
                raise RuntimeError(f"Transaction aborted. No data changes were committed. Reason: {txn_err}") from txn_err

    except Exception as e:
        print(f"Error during seeding: {e}")
    finally:
        client.close()

if __name__ == "__main__":
    asyncio.run(main())