"""
RAIYA Reasoning Cache — Redis caching for reasoning engine outputs.
Cache key: reason:{r_hash}:{j_hash}:{w_hash} TTL=2h
"""

import json
from typing import Optional, Dict, Any

from app.db.redis_client import cache_get, cache_set, CacheKeys
from app.core.logging_config import get_logger

logger = get_logger("ReasoningCache")


async def get_cached_reasoning(
    r_hash: str, j_hash: str, w_hash: str
) -> Optional[Dict[str, Any]]:
    """Check if reasoning output exists in cache."""
    key = CacheKeys.reason(r_hash, j_hash, w_hash)
    raw = await cache_get(key)
    if raw:
        try:
            logger.info(f"Reasoning cache HIT: {key}")
            return json.loads(raw)
        except json.JSONDecodeError:
            return None
    return None


async def set_cached_reasoning(
    r_hash: str, j_hash: str, w_hash: str, data: Dict[str, Any]
) -> None:
    """Cache reasoning output."""
    key = CacheKeys.reason(r_hash, j_hash, w_hash)
    await cache_set(key, data, ttl_key="reason")
    logger.info(f"Reasoning cached: {key}")


async def get_cached_context(output_hash: str) -> Optional[str]:
    """Get cached reasoning context narrative."""
    key = CacheKeys.reason_context(output_hash)
    return await cache_get(key)


async def set_cached_context(output_hash: str, context: str) -> None:
    """Cache reasoning context narrative."""
    key = CacheKeys.reason_context(output_hash)
    await cache_set(key, context, ttl_key="reason")
