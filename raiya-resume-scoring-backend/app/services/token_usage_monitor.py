"""
RAIYA Token Usage Monitor — Logs every LLM call to JSONL + PostgreSQL.
"""

import json
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.core.config import settings
from app.core.logging_config import get_logger

logger = get_logger("TokenUsageMonitor")

# JSONL log file
JSONL_LOG_PATH = Path("storage/token_usage.jsonl")


def log_token_usage_jsonl(
    model: str,
    prompt_tokens: int,
    completion_tokens: int,
    pipeline_stage: str,
    batch_id: Optional[str] = None,
    resume_file_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Log token usage to JSONL file and return the log entry."""
    total_tokens = prompt_tokens + completion_tokens
    est_cost = (
        (prompt_tokens / 1000) * settings.PROMPT_COST_PER_1K +
        (completion_tokens / 1000) * settings.COMPLETION_COST_PER_1K
    )

    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "model": model,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": total_tokens,
        "est_cost_usd": round(est_cost, 6),
        "pipeline_stage": pipeline_stage,
        "batch_id": batch_id,
        "resume_file_id": resume_file_id,
    }

    JSONL_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(JSONL_LOG_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, default=str) + "\n")

    logger.info(
        f"Token usage: {model} | {total_tokens} tokens | ${est_cost:.6f} | {pipeline_stage}",
        extra={"pipeline_stage": pipeline_stage}
    )
    return entry


async def log_token_usage_db(
    session: AsyncSession,
    model: str,
    prompt_tokens: int,
    completion_tokens: int,
    pipeline_stage: str,
    batch_id: Optional[str] = None,
    resume_file_id: Optional[str] = None,
) -> None:
    """Log token usage to PostgreSQL token_usage_log table."""
    total_tokens = prompt_tokens + completion_tokens
    est_cost = (
        (prompt_tokens / 1000) * settings.PROMPT_COST_PER_1K +
        (completion_tokens / 1000) * settings.COMPLETION_COST_PER_1K
    )

    await session.execute(
        text("""
            INSERT INTO token_usage_log 
            (batch_id, resume_file_id, model, prompt_tokens, completion_tokens, 
             total_tokens, est_cost_usd, pipeline_stage)
            VALUES (:bid, :rid, :model, :pt, :ct, :tt, :cost, :stage)
        """),
        {
            "bid": batch_id,
            "rid": resume_file_id,
            "model": model,
            "pt": prompt_tokens,
            "ct": completion_tokens,
            "tt": total_tokens,
            "cost": est_cost,
            "stage": pipeline_stage,
        }
    )
    await session.commit()

    # Also log to JSONL
    log_token_usage_jsonl(
        model, prompt_tokens, completion_tokens,
        pipeline_stage, batch_id, resume_file_id
    )
