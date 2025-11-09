# app/crud/order_items.py
from __future__ import annotations
from typing import List, Optional, Dict, Any

from bson import ObjectId
from app.core.database import db
from app.schemas.object_id import PyObjectId
from app.schemas.order_items import OrderItemsOut

COLL = "order_items"


def _to_out(doc: dict) -> OrderItemsOut:
    return OrderItemsOut.model_validate(doc)


def _to_oid(v: Any) -> Optional[ObjectId]:
    try:
        return ObjectId(str(v))
    except Exception:
        return None


def _normalize_query(query: Dict[str, Any] | None) -> Dict[str, Any]:
    """Coerce known FK filters to ObjectId if they arrive as strings/PyObjectId."""
    if not query:
        return {}

    out: Dict[str, Any] = {}
    for k, v in query.items():
        if v is None:
            continue
        if k in ("order_id", "user_id", "product_id"):
            if isinstance(v, dict) and "$in" in v and isinstance(v["$in"], list):
                out[k] = {"$in": [x for x in ( _to_oid(x) for x in v["$in"] ) if x ]}
            else:
                oid = _to_oid(v)
                out[k] = oid if oid else v  # if not coercible, pass-through (won't match)
        else:
            out[k] = v
    return out


async def list_all(
    skip: int = 0,
    limit: int = 50,
    query: Dict[str, Any] | None = None,
) -> List[OrderItemsOut]:
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


async def get_one(_id: PyObjectId) -> Optional[OrderItemsOut]:
    oid = _to_oid(_id)
    if not oid:
        return None
    doc = await db[COLL].find_one({"_id": oid})
    return _to_out(doc) if doc else None