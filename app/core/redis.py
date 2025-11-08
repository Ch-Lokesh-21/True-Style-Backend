import asyncio
import json
from typing import Any, Optional, Dict
from redis import asyncio as redis_async  # built-in async client
from app.core.config import settings
REDIS_URL = settings.REDIS_HOST
PERM_CACHE_TTL_SECONDS = settings.PERM_CACHE_TTL_SECONDS
_redis_client: Optional[redis_async.Redis] = None
_redis_lock = asyncio.Lock()

async def get_redis() -> redis_async.Redis:
    """
    Create or reuse a global Redis connection.
    We avoid checking internal .closed flags; instead we ping and recreate if needed.
    """
    global _redis_client
    async with _redis_lock:
        if _redis_client is None:
            _redis_client = redis_async.from_url(
                REDIS_URL,
                encoding="utf-8",
                decode_responses=True,
            )
        else:
            try:
                await _redis_client.ping()
            except Exception:
                # Recreate the client if the pool/connection is bad
                _redis_client = redis_async.from_url(
                    REDIS_URL,
                    encoding="utf-8",
                    decode_responses=True,
                )
    return _redis_client


async def close_redis():
    """Gracefully close Redis connection."""
    global _redis_client
    if _redis_client is not None:
        await _redis_client.close()
        _redis_client = None


# ---------------------------------------------------
# Utility functions for cache invalidation / clearing
# ---------------------------------------------------

def _redis_key(role_id: Any, resource: str) -> str:
    return f"perm:{str(role_id)}:{resource.strip().lower()}"


async def get_cached_policy(role_id: Any, resource: str) -> Optional[Dict[str, bool]]:
    redis = await get_redis()
    val = await redis.get(_redis_key(role_id, resource))
    if not val:
        return None
    try:
        return json.loads(val)
    except json.JSONDecodeError:
        return None


async def set_cached_policy(role_id: Any, resource: str, policy: Dict[str, bool]) -> None:
    redis = await get_redis()
    await redis.setex(_redis_key(role_id, resource), PERM_CACHE_TTL_SECONDS, json.dumps(policy))


async def invalidate_permission_cache(
    role_id: Optional[Any] = None, resource: Optional[str] = None
) -> int:
    """
    Safely delete permission cache keys from Redis.
    - If both role_id and resource given → delete single key
    - If only one given → delete matching keys
    - If none → delete all 'perm:*' keys
    Returns count of deleted keys.
    """
    redis = await get_redis()

    # Exact key case
    if role_id and resource:
        await redis.delete(_redis_key(role_id, resource))
        return 1

    # Pattern cases
    if role_id:
        pattern = f"perm:{role_id}:*"
    elif resource:
        pattern = f"perm:*:{resource.strip().lower()}"
    else:
        pattern = "perm:*"

    cursor = 0
    total_deleted = 0
    while True:
        cursor, keys = await redis.scan(cursor=cursor, match=pattern, count=500)
        if keys:
            try:
                # Native UNLINK (non-blocking)
                await redis.unlink(*keys)
            except Exception:
                await redis.delete(*keys)
            total_deleted += len(keys)
        if cursor == 0:
            break

    return total_deleted


async def clear_permissions_cache() -> int:
    """Shortcut to delete all permission cache keys."""
    return await invalidate_permission_cache()


async def flush_entire_redis() -> None:
    """Dangerous: wipe the whole Redis DB (use only if DB is cache-only)."""
    redis = await get_redis()
    try:
        # Non-blocking flush if supported
        await redis.flushdb(asynchronous=True)
    except TypeError:
        # Fallback for older redis-py versions
        await redis.flushdb()