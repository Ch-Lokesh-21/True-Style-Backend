# app/crud/payments.py
from __future__ import annotations
from typing import List, Optional, Dict, Any

from bson import ObjectId
from app.core.database import db
from app.utils.mongo import stamp_update
from app.schemas.object_id import PyObjectId
from app.schemas.payments import PaymentsUpdate, PaymentsOut

COLL = "payments"


def _to_out(doc: dict) -> PaymentsOut:
    return PaymentsOut.model_validate(doc)


def _to_oid(v: Any) -> Optional[ObjectId]:
    try:
        return ObjectId(str(v))
    except Exception:
        return None


def _normalize_query(query: Dict[str, Any] | None) -> Dict[str, Any]:
    """
    Convert known FK filters to ObjectId (single value or $in), passthrough otherwise.
    """
    if not query:
        return {}

    out: Dict[str, Any] = {}
    fk_fields = {"user_id", "order_id", "payment_types_id", "payment_status_id"}
    for k, v in query.items():
        if v is None:
            continue

        if k in fk_fields:
            if isinstance(v, dict) and "$in" in v and isinstance(v["$in"], list):
                out[k] = {"$in": [oid for oid in (_to_oid(x) for x in v["$in"]) if oid]}
            else:
                oid = _to_oid(v)
                out[k] = oid if oid else v
        else:
            out[k] = v
    return out


async def list_all(
    skip: int = 0,
    limit: int = 50,
    query: Dict[str, Any] | None = None,
) -> List[PaymentsOut]:
    q = _normalize_query(query)
    cur = (
        db[COLL]
        .find(q)
        .skip(max(0, int(skip)))
        .limit(max(0, int(limit)))
        .sort("createdAt", -1)
    )
    docs = await cur.to_list(length=limit)
    return [_to_out(d) for d in docs]


async def get_one(_id: PyObjectId) -> Optional[PaymentsOut]:
    oid = _to_oid(_id)
    if not oid:
        return None
    doc = await db[COLL].find_one({"_id": oid})
    return _to_out(doc) if doc else None


async def update_one(_id: PyObjectId, payload: PaymentsUpdate) -> Optional[PaymentsOut]:
    """
    Admin use: update allowed fields (today we expect payment_status_id).
    """
    oid = _to_oid(_id)
    if not oid:
        return None

    data = payload.model_dump(mode="python", exclude_none=True)
    if "payment_status_id" in data:
        ps = _to_oid(data["payment_status_id"])
        if not ps:
            return None
        data["payment_status_id"] = ps

    if not data:
        return None

    await db[COLL].update_one({"_id": oid}, {"$set": stamp_update(data)})
    doc = await db[COLL].find_one({"_id": oid})
    return _to_out(doc) if doc else None