from app.core.database import db
from app.utils.mongo import stamp_create

async def add_revocation(jti: str, expiresAt, reason: str):
    doc = {"jti": jti, "expiresAt": expiresAt, "reason": reason, **stamp_create({})}
    await db["token_revocations"].update_one({"jti": jti}, {"$set": doc}, upsert=True)

async def is_revoked(jti: str) -> bool:
    return bool(await db["token_revocations"].find_one({"jti": jti}))
