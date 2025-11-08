from __future__ import annotations
from typing import Dict, Literal, Optional, Any
from fastapi import Depends, HTTPException, Request, status
from bson import ObjectId
from app.core.security import decode_access_token
from app.core.database import db
from app.crud.token_revocations import is_revoked
from app.core.redis import get_cached_policy, set_cached_policy
from app.core.security import oauth2_scheme
UNAUTH = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Unauthorized",
    headers={"WWW-Authenticate": "Bearer"},
)
UNAUTH = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")
FORBID = HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden: insufficient permissions")

Action = Literal["Create", "Read", "Update", "Delete"]


def _maybe_object_id(value) -> Any:
    if isinstance(value, ObjectId):
        return value
    try:
        return ObjectId(str(value))
    except Exception:
        return value


# -----------------------------
# Auth
# -----------------------------


async def get_current_user(token: str = Depends(oauth2_scheme)) -> Dict:
    payload = decode_access_token(token)

    if not payload or payload.get("type") != "access":
        raise UNAUTH

    if await is_revoked(payload.get("jti", "")):
        raise UNAUTH

    required = ["user_id", "user_role_id","wishlist_id","cart_id"]
    if not all(k in payload for k in required):
        raise UNAUTH

    return {k: payload[k] for k in required}


# -----------------------------
# DB Fetch
# -----------------------------
async def _fetch_policy_from_db(role_id: Any, resource: str) -> Optional[Dict[str, bool]]:
    cursor = db["permissions"].find(
        {"resource_name": {"$in": [resource, f"user:{resource}"]}},
        projection={"_id": 1, "resource_name": 1, "Create": 1, "Read": 1, "Update": 1, "Delete": 1},
    )
    perms = await cursor.to_list(length=3)
    if not perms:
        return None

    perm_ids = [p["_id"] for p in perms]
    link = await db["role_permissions"].find_one(
        {"role_id": _maybe_object_id(role_id), "permission_id": {"$in": perm_ids}},
        projection={"permission_id": 1},
    )
    if not link:
        return None

    matched = next((p for p in perms if p["_id"] == link["permission_id"]), None)
    if not matched:
        return None

    return {
        "Create": bool(matched.get("Create", False)),
        "Read": bool(matched.get("Read", False)),
        "Update": bool(matched.get("Update", False)),
        "Delete": bool(matched.get("Delete", False)),
    }


# -----------------------------
# AuthZ dependency
# -----------------------------
def require_permission(resource: str, action: Action, role: Optional[str] = None):
    if role is not None and role != "" and role == "admin":
        async def _admin_dep(current: Dict = Depends(get_current_user)) -> Dict:
            role_id = current["user_role_id"]
            get_role = await db["user_roles"].find_one({"_id": _maybe_object_id(role_id)})
            if not get_role or get_role.get("role") != "admin":
                raise FORBID
            return current
        return _admin_dep
        
    async def _dep(current: Dict = Depends(get_current_user)) -> Dict:
        role_id = current["user_role_id"]

        # 1. Try Redis cache
        policy = await get_cached_policy(role_id, resource)

        # 2. Cache miss → Fetch from DB & store
        if policy is None:
            policy = await _fetch_policy_from_db(role_id, resource)
            if policy is None:
                raise FORBID
            await set_cached_policy(role_id, resource, policy)
        # 3. Check action
        if not policy.get(action, False):
            raise FORBID
        return current
    return _dep

def user_required():
    pass

def admin_required():
    pass