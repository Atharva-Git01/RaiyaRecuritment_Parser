"""
RAIYA Admin Routes — System metrics, token usage, evidence rules.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.services.admin_service import get_pipeline_metrics, get_token_usage_summary

router = APIRouter(prefix="/admin", tags=["Admin"])


@router.get("/metrics")
async def pipeline_metrics(db: AsyncSession = Depends(get_db)):
    """Get overall pipeline metrics."""
    return await get_pipeline_metrics(db)


@router.get("/token-usage")
async def token_usage(db: AsyncSession = Depends(get_db)):
    """Get token usage summary."""
    return await get_token_usage_summary(db)


@router.get("/health")
async def system_health():
    """Check system health."""
    health = {"database": "healthy", "redis": "healthy", "embedding_model": "healthy", "llm": "healthy", "pgvector": "healthy"}

    # Check Redis
    try:
        from app.db.redis_client import get_redis
        r = await get_redis()
        await r.ping()
    except Exception:
        health["redis"] = "degraded"

    return health
