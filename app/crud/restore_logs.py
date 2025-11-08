from typing import List
from bson import ObjectId
from app.core.database import db
from app.utils.mongo import stamp_create, stamp_update

COLL = "restore_logs"

async def create(data: dict) -> dict:
    doc = stamp_create(data)
    res = await db[COLL].insert_one(doc)
    return await db[COLL].find_one({"_id": res.inserted_id})

async def list_all(skip=0, limit=50, query=None) -> List[dict]:
    cur = db[COLL].find(query or {}).skip(skip).limit(limit).sort("createdAt", -1)
    return await cur.to_list(length=limit)

async def get_one(_id: str) -> dict | None:
    return await db[COLL].find_one({"_id": ObjectId(_id)})

async def update_one(_id: str, data: dict) -> dict | None:
    await db[COLL].update_one({"_id": ObjectId(_id)}, {"$set": stamp_update(data)})
    return await get_one(_id)

async def delete_one(_id: str) -> bool:
    r = await db[COLL].delete_one({"_id": ObjectId(_id)})
    return r.deleted_count == 1
