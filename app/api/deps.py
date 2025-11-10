"""
Authorization & Authentication Dependencies

Provides:
- Access token validation
- Current user extraction
- Role & permission checking with Redis caching
- DB fallback for role-permission mapping
"""

from __future__ import annotations
from typing import Dict, Literal, Optional, Any
from fastapi import Depends, HTTPException, Request, status
from bson import ObjectId

from app.core.security import decode_access_token, oauth2_scheme
from app.core.database import db
from app.crud.token_revocations import is_revoked
from app.core.redis import get_cached_policy, set_cached_policy

UNAUTH = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Unauthorized",
    headers={"WWW-Authenticate": "Bearer"},
)
FORBID = HTTPException(
    status_code=status.HTTP_403_FORBIDDEN,
    detail="Forbidden: insufficient permissions",
)

Action = Literal["Create", "Read", "Update", "Delete"]


def _maybe_object_id(value) -> Any:
    """
    Internal helper:
    Convert a value to ObjectId if possible, otherwise return original value.
    Used to normalize role_id and other reference keys.
    """
    if isinstance(value, ObjectId):
        return value
    try:
        return ObjectId(str(value))
    except Exception:
        return value


# ---------------------------------------------------------------------------
# Authentication
# ---------------------------------------------------------------------------

async def get_current_user(token: str = Depends(oauth2_scheme)) -> Dict:
    """
    Dependency: Extract and validate the currently authenticated user
    from a Bearer access token.

    Validates:
        - Token must be decodable
        - Must be an "access" type token
        - Must not be revoked
        - Must include user_id, user_role_id, wishlist_id, cart_id

    Returns:
        Dict containing {user_id, user_role_id, wishlist_id, cart_id}

    Raises:
        HTTPException(401) if token invalid or revoked
    """
    payload = decode_access_token(token)

    if not payload or payload.get("type") != "access":
        raise UNAUTH

    # Check revocation (logout / forced logout / security)
    if await is_revoked(payload.get("jti", "")):
        raise UNAUTH

    required = ["user_id", "user_role_id", "wishlist_id", "cart_id"]
    if not all(k in payload for k in required):
        raise UNAUTH

    return {k: payload[k] for k in required}


# ---------------------------------------------------------------------------
# Permission Lookup (DB fallback when Redis lacks policy)
# ---------------------------------------------------------------------------

async def _fetch_policy_from_db(role_id: Any, resource: str) -> Optional[Dict[str, bool]]:
    """
    Query MongoDB for a role's permission policy for a given resource.

    Steps:
        1. Look up permission documents for:
           - resource_name = resource
           - resource_name = "user:{resource}" (user-scoped override)
        2. Find the role_permission link
        3. Extract CRUD flags

    Returns:
        Dict of {"Create": bool, "Read": bool, "Update": bool, "Delete": bool}
        OR None if no permission found.
    """
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


# ---------------------------------------------------------------------------
# Authorization Dependency
# ---------------------------------------------------------------------------

def require_permission(resource: str, action: Action, role: Optional[str] = None):
    """
    Dependency factory for route-level authorization.

    Args:
        resource (str): Resource name defined in permissions collection
                        (e.g., "users", "products", "coupons")
        action (Literal): One of ["Create", "Read", "Update", "Delete"]
        role (Optional[str]): If "admin", enforce admin-only access without DB lookup.

    Usage:
        @router.get("/items", dependencies=[Depends(require_permission("products","Read"))])
        @router.post("/admin", dependencies=[Depends(require_permission("users","Create","admin"))])

    Returns:
        A dependency function which:
          - Validates current user via get_current_user
          - If admin-only, checks role="admin"
          - Otherwise loads permission policy from Redis cache, falling back to MongoDB
          - Raises 403 if action is not permitted
    """

    # Admin-only override
    if role is not None and role != "" and role == "admin":
        async def _admin_dep(current: Dict = Depends(get_current_user)) -> Dict:
            role_id = current["user_role_id"]
            get_role = await db["user_roles"].find_one({"_id": _maybe_object_id(role_id)})
            if not get_role or get_role.get("role") != "admin":
                raise FORBID
            return current
        return _admin_dep

    # Standard permission dependency
    async def _dep(current: Dict = Depends(get_current_user)) -> Dict:
        role_id = current["user_role_id"]

        # 1. Try Redis lookup
        policy = await get_cached_policy(role_id, resource)

        # 2. Cache miss → DB lookup + set cache
        if policy is None:
            policy = await _fetch_policy_from_db(role_id, resource)
            if policy is None:
                raise FORBID
            await set_cached_policy(role_id, resource, policy)

        # 3. Check if the requested action is allowed
        if not policy.get(action, False):
            raise FORBID

        return current

    return _dep