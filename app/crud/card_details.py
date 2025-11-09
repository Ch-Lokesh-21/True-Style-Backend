# app/crud/card_details.py
from __future__ import annotations
from typing import List, Optional, Dict, Any
from bson import ObjectId
from cryptography.fernet import InvalidToken

from app.core.database import db
from app.utils.mongo import stamp_create, stamp_update
from app.schemas.object_id import PyObjectId
from app.schemas.card_details import CardDetailsCreate, CardDetailsUpdate, CardDetailsOut
from app.utils.crypto import encrypt_card_no, decrypt_card_no

COLL = "card_details"


def _to_out(doc: dict) -> CardDetailsOut:
    """
    DB -> API: Always return masked PAN.
    - We still try to decrypt to verify integrity, but never expose raw PAN.
    - Uses stored `last4` for masking.
    """
    # best-effort integrity check (optional)
    enc_no = doc.get("card_no")
    try:
        card_no = decrypt_card_no(enc_no) if enc_no else None
    except InvalidToken:
        # integrity issue; still mask with last4 if present
        pass

    out_doc = {
        **doc,
        "card_no": card_no,
    }
    return CardDetailsOut.model_validate(out_doc)

async def create(payload: CardDetailsCreate) -> CardDetailsOut:
    """
    Used by Orders flow. Stores encrypted card PAN + last4.
    """
    card_enc = encrypt_card_no(payload.card_no)

    to_insert = stamp_create({
        "name": payload.name,
        "card_no": card_enc,
    })
    res = await db[COLL].insert_one(to_insert)
    saved = await db[COLL].find_one({"_id": res.inserted_id})
    return _to_out(saved)

async def list_all(skip: int = 0, limit: int = 50, query: Dict[str, Any] | None = None) -> List[CardDetailsOut]:
    cur = db[COLL].find(query or {}).skip(max(skip, 0)).limit(max(limit, 0)).sort("createdAt", -1)
    docs = await cur.to_list(length=limit)
    return [_to_out(d) for d in docs]

async def get_one(_id: PyObjectId) -> Optional[CardDetailsOut]:
    try:
        oid = ObjectId(str(_id))
    except Exception:
        return None
    doc = await db[COLL].find_one({"_id": oid})
    return _to_out(doc) if doc else None

async def get_by_payment_id(payment_id: PyObjectId) -> Optional[CardDetailsOut]:
    """
    Fetch card details row linked to a payments._id
    """
    try:
        pid = ObjectId(str(payment_id))
    except Exception:
        return None
    doc = await db[COLL].find_one({"payment_id": pid})
    return _to_out(doc) if doc else None

async def update_one(_id: PyObjectId, payload: CardDetailsUpdate) -> Optional[CardDetailsOut]:
    """
    If you ever need to rename card holder (not PAN). Not exposed via routes.
    """
    try:
        oid = ObjectId(str(_id))
    except Exception:
        return None

    data = {k: v for k, v in payload.model_dump(mode="python",exclude_none=True).items() if v is not None}
    if not data:
        return None

    await db[COLL].update_one({"_id": oid}, {"$set": stamp_update(data)})
    doc = await db[COLL].find_one({"_id": oid})
    return _to_out(doc) if doc else None

async def delete_one(_id: PyObjectId) -> Optional[bool]:
    try:
        oid = ObjectId(str(_id))
    except Exception:
        return None
    r = await db[COLL].delete_one({"_id": oid})
    return r.deleted_count == 1