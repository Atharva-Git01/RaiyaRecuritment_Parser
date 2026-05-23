"""
RAIYA Admin Service — System metrics and admin operations.
"""

from typing import Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.models.batch import Batch, MatchResult
from app.models.document import Resume, JobDescription
from app.models.audit import TokenUsageLog
from app.core.logging_config import get_logger

logger = get_logger("AdminService")


async def get_pipeline_metrics(session: AsyncSession) -> Dict[str, Any]:
    """Get overall pipeline metrics."""
    total_batches = (await session.execute(select(func.count(Batch.id)))).scalar() or 0
    total_resumes = (await session.execute(select(func.count(Resume.file_id)))).scalar() or 0
    total_jds = (await session.execute(select(func.count(JobDescription.id)))).scalar() or 0

    avg_score_result = await session.execute(
        select(func.avg(MatchResult.final_score)).where(MatchResult.final_score.isnot(None))
    )
    avg_score = avg_score_result.scalar() or 0.0

    accuracy_result = await session.execute(
        select(func.avg(MatchResult.math_accuracy)).where(MatchResult.math_accuracy.isnot(None))
    )
    accuracy = accuracy_result.scalar() or 0.0

    hallucination_count = (await session.execute(
        select(func.count(MatchResult.id)).where(MatchResult.hallucinations_detected == True)
    )).scalar() or 0
    total_results = (await session.execute(select(func.count(MatchResult.id)))).scalar() or 1

    return {
        "total_batches": total_batches,
        "total_resumes_processed": total_resumes,
        "total_jds": total_jds,
        "average_score": round(float(avg_score), 2),
        "accuracy_rate": round(float(accuracy), 2),
        "hallucination_rate": round(hallucination_count / total_results * 100, 2),
    }


async def get_token_usage_summary(session: AsyncSession) -> Dict[str, Any]:
    """Get token usage summary."""
    result = await session.execute(
        select(
            func.sum(TokenUsageLog.prompt_tokens),
            func.sum(TokenUsageLog.completion_tokens),
            func.sum(TokenUsageLog.total_tokens),
            func.sum(TokenUsageLog.est_cost_usd),
        )
    )
    row = result.one_or_none()
    if not row:
        return {"total_prompt_tokens": 0, "total_completion_tokens": 0, "total_tokens": 0, "total_cost_usd": 0.0, "by_stage": {}}

    return {
        "total_prompt_tokens": int(row[0] or 0),
        "total_completion_tokens": int(row[1] or 0),
        "total_tokens": int(row[2] or 0),
        "total_cost_usd": float(row[3] or 0.0),
        "by_stage": {},  # TODO: group by pipeline_stage
    }
