"""
RAIYA Score Guards — SimilarToPreviousValues + ValidRange.
Uses Guardrails AI to detect score drift across batch processing.
"""

import json
from typing import Tuple, List, Dict

from app.core.logging_config import get_logger
from app.core.config import settings

logger = get_logger("ScoreGuards")


async def validate_section_score(
    section: str, score: float, jd_id: str
) -> Tuple[float, bool]:
    """
    Validate a section score using rolling mean/std deviation check.
    Mimics SimilarToPreviousValues behavior without requiring guardrails hub install.
    Returns (validated_score, was_corrected).
    """
    from app.db.redis_client import get_redis
    
    redis = await get_redis()
    redis_key = f"score_history:{jd_id}:{section}"
    raw = await redis.get(redis_key)
    previous_scores: List[float] = json.loads(raw) if raw else []

    if len(previous_scores) < 3:
        # Not enough history — just range check
        validated = max(0.0, min(100.0, score))
        previous_scores.append(score)
        await redis.setex(redis_key, settings.CACHE_TTL_SCORE_HISTORY, json.dumps(previous_scores[-20:]))
        return validated, False

    # Compute rolling statistics
    mean = sum(previous_scores) / len(previous_scores)
    variance = sum((x - mean) ** 2 for x in previous_scores) / len(previous_scores)
    std_dev = variance ** 0.5
    threshold = settings.GUARDRAILS_SCORE_STD_DEVS

    # Check if score deviates by > threshold std devs
    if std_dev > 0 and abs(score - mean) > threshold * std_dev:
        # Clamp to closest boundary
        if score > mean:
            validated_score = mean + threshold * std_dev
        else:
            validated_score = mean - threshold * std_dev
        validated_score = max(0.0, min(100.0, round(validated_score, 2)))
        logger.warning(
            f"[ScoreGuard] {section} score corrected: {score:.2f} → {validated_score:.2f} "
            f"(prev_mean={mean:.2f}, std={std_dev:.2f})"
        )
        previous_scores.append(validated_score)
        await redis.setex(redis_key, settings.CACHE_TTL_SCORE_HISTORY, json.dumps(previous_scores[-20:]))
        return validated_score, True

    # Score is within range
    validated = max(0.0, min(100.0, score))
    previous_scores.append(validated)
    await redis.setex(redis_key, settings.CACHE_TTL_SCORE_HISTORY, json.dumps(previous_scores[-20:]))
    return validated, False


async def apply_batch_score_guards(
    section_scores: Dict[str, float],
    jd_id: str
) -> Tuple[Dict[str, float], List[str]]:
    """
    Apply SimilarToPreviousValues to all section scores.
    Returns (validated_scores, list of guardrail names that fired).
    """
    validated = {}
    fired = []
    for section, score in section_scores.items():
        v_score, corrected = await validate_section_score(section, score, jd_id)
        validated[section] = v_score
        if corrected:
            fired.append(f"SimilarToPreviousValues:{section}")
    return validated, fired
