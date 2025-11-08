from datetime import datetime , timezone
from typing import Optional
from app.core.database import db
from app.utils.mongo import stamp_create

async def create_session(doc: dict) -> dict:
    d = stamp_create(doc)
    res = await db["sessions"].insert_one(d)
    return await db["sessions"].find_one({"_id": res.inserted_id})

async def get_by_refresh_hash(refresh_hash: str) -> Optional[dict]:
    return await db["sessions"].find_one({"refresh_hash": refresh_hash, "revokedAt": None})

async def revoke_session_by_jti(jti: str, reason: str):
    await db["sessions"].update_one({"jti": jti}, {"$set": {"revokedAt": datetime.now(timezone.utc), "revocationReason": reason}})

async def revoke_all_user_sessions(user_id: str):
    await db["sessions"].update_many({"user_id": user_id, "revokedAt": None}, {"$set": {"revokedAt": datetime.now(timezone.utc)}})
