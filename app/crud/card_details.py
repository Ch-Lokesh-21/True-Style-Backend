from __future__ import annotations
from typing import List, Optional, Dict, Any
from bson import ObjectId
from cryptography.fernet import InvalidToken

from app.core.database import db
from app.utils.mongo import stamp_create, stamp_update
from app.schemas.object_id import PyObjectId
from app.schemas.card_details import CardDetailsCreate, CardDetailsUpdate, CardDetailsOut
from app.utils.crypto import encrypt_card_no , decrypt_card_no

COLL = "card_details"

def _to_out(doc: dict) -> CardDetailsOut:
    """
    Convert DB doc -> Pydantic Out by decrypting the stored encrypted card number.
    Falls back to masked/placeholder if decryption fails (shouldn't normally happen).
    """
    enc = doc.get("card_enc")
    try:
        card_no = decrypt_card_no(enc) if enc else None
    except InvalidToken:
        # Fallback: if key rotated/invalid, avoid crashing the API
        card_no = "**** decryption_failed ****"

    out_doc = {
        **doc,
        "card_no": card_no or "****",
    }
    # Pydantic model is configured with extra="ignore", so internal fields (card_enc/last4) are dropped
    return CardDetailsOut.model_validate(out_doc)

async def create(payload: CardDetailsCreate) -> CardDetailsOut:
    """
    Store only name + encrypted card number (card_enc). Optionally store last4 for convenience.
    """
    try:
        card_enc = encrypt_card_no(payload.card_no)
        digits = "".join(ch for ch in payload.card_no if ch.isdigit())
        last4 = digits[-4:] if len(digits) >= 4 else digits

        to_insert = stamp_create({
            "name": payload.name,
            "card_enc": card_enc,
            "last4": last4,  # optional helper, not exposed by schema
        })
        res = await db[COLL].insert_one(to_insert)
        saved = await db[COLL].find_one({"_id": res.inserted_id})
        return _to_out(saved)
    except Exception as e:
        # Let router turn into HTTPException
        raise e

async def list_all(skip: int = 0, limit: int = 50, query: Dict[str, Any] | None = None) -> List[CardDetailsOut]:
    try:
        cur = db[COLL].find(query or {}).skip(max(skip, 0)).limit(max(limit, 0)).sort("createdAt", -1)
        docs = await cur.to_list(length=limit)
        return [_to_out(d) for d in docs]
    except Exception as e:
        raise e

async def get_one(_id: PyObjectId) -> Optional[CardDetailsOut]:
    try:
        oid = ObjectId(str(_id))
    except Exception:
        return None
    try:
        doc = await db[COLL].find_one({"_id": oid})
        return _to_out(doc) if doc else None
    except Exception as e:
        raise e

async def update_one(_id: PyObjectId, payload: CardDetailsUpdate) -> Optional[CardDetailsOut]:
    """
    Only allows updating non-sensitive fields (name). PAN updates should go through a dedicated rotate endpoint if needed.
    """
    try:
        oid = ObjectId(str(_id))
    except Exception:
        return None

    data = {k: v for k, v in payload.model_dump().items() if v is not None}
    if not data:
        return None

    try:
        await db[COLL].update_one({"_id": oid}, {"$set": stamp_update(data)})
        doc = await db[COLL].find_one({"_id": oid})
        return _to_out(doc) if doc else None
    except Exception as e:
        raise e

async def delete_one(_id: PyObjectId) -> Optional[bool]:
    try:
        oid = ObjectId(str(_id))
    except Exception:
        return None
    try:
        r = await db[COLL].delete_one({"_id": oid})
        return r.deleted_count == 1
    except Exception as e:
        raise e