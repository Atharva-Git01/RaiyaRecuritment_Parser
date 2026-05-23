"""
RAIYA Redis Client — Connection and cache key patterns.
"""

import json
from typing import Optional, Any

import redis.asyncio as aioredis

from app.core.config import settings
from app.core.logging_config import get_logger

logger = get_logger("redis_client")


# ── Redis Connection Pool ────────────────────────────────────────

redis_client: Optional[aioredis.Redis] = None


async def init_redis() -> aioredis.Redis:
    """Initialize Redis connection pool."""
    global redis_client
    redis_client = aioredis.from_url(
        settings.REDIS_URL,
        encoding="utf-8",
        decode_responses=True,
        max_connections=50,
    )
    # Test connection
    await redis_client.ping()
    logger.info("Redis connection established")
    return redis_client


async def close_redis():
    """Close Redis connection pool."""
    global redis_client
    if redis_client:
        await redis_client.close()
        logger.info("Redis connection closed")


async def get_redis() -> aioredis.Redis:
    """Get the Redis client instance."""
    global redis_client
    if redis_client is None:
        await init_redis()
    return redis_client


# ── Cache Key Builders ───────────────────────────────────────────

class CacheKeys:
    """Cache key patterns matching Section 10 of the master plan."""

    @staticmethod
    def ocr(file_hash: str) -> str:
        return f"ocr:{file_hash}"

    @staticmethod
    def parsed(content_hash: str) -> str:
        return f"parsed:{content_hash}"

    @staticmethod
    def embedding(chunk_hash: str) -> str:
        return f"emb:{chunk_hash}"

    @staticmethod
    def weights(content_hash: str) -> str:
        return f"weights:{content_hash}"

    @staticmethod
    def search(r_hash: str, j_hash: str, w_hash: str, section: str) -> str:
        return f"search:{r_hash}:{j_hash}:{w_hash}:{section}"

    @staticmethod
    def phi4(prompt_hash: str) -> str:
        return f"phi4:{prompt_hash}"

    @staticmethod
    def rag(r_hash: str, j_hash: str) -> str:
        return f"rag:{r_hash}:{j_hash}"

    @staticmethod
    def reason(r_hash: str, j_hash: str, w_hash: str) -> str:
        return f"reason:{r_hash}:{j_hash}:{w_hash}"

    @staticmethod
    def reason_context(output_hash: str) -> str:
        return f"reason_ctx:{output_hash}"

    @staticmethod
    def explanation(output_hash: str) -> str:
        return f"explain:{output_hash}"

    @staticmethod
    def score_history(jd_id: str, section: str) -> str:
        return f"score_history:{jd_id}:{section}"

    @staticmethod
    def batch(batch_id: str) -> str:
        return f"batch:{batch_id}:status"


# ── Cache TTLs ───────────────────────────────────────────────────

CACHE_TTLS = {
    "ocr": settings.CACHE_TTL_OCR,
    "parsed": 604800,
    "embedding": settings.CACHE_TTL_EMBEDDING,
    "weights": settings.CACHE_TTL_WEIGHTS,
    "search": settings.CACHE_TTL_SEARCH,
    "phi4": settings.CACHE_TTL_PHI4,
    "rag": settings.CACHE_TTL_RAG,
    "reason": settings.CACHE_TTL_REASON,
    "reason_context": settings.CACHE_TTL_REASON,
    "explanation": settings.CACHE_TTL_EXPLANATION,
    "score_history": settings.CACHE_TTL_SCORE_HISTORY,
    "batch": 3600,
}


# ── Cache Helpers ────────────────────────────────────────────────

async def cache_get(key: str) -> Optional[str]:
    """Get a cached value by key."""
    r = await get_redis()
    return await r.get(key)


async def cache_set(key: str, value: Any, ttl_key: str = "parsed") -> None:
    """Set a cached value with TTL from CACHE_TTLS."""
    r = await get_redis()
    ttl = CACHE_TTLS.get(ttl_key, 3600)
    if isinstance(value, (dict, list)):
        value = json.dumps(value, default=str)
    await r.setex(key, ttl, value)


async def cache_get_json(key: str) -> Optional[dict]:
    """Get and parse a JSON-cached value."""
    raw = await cache_get(key)
    if raw:
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return None
    return None
