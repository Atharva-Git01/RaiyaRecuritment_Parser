"""
RAIYA LLM Tool — Azure Phi-4 integration with prompt caching and token monitoring.
"""

import json
from typing import Dict, Any, Optional

from app.core.config import settings
from app.core.hashing import hash_content
from app.db.redis_client import cache_get, cache_set, CacheKeys
from app.services.token_usage_monitor import log_token_usage_jsonl
from app.core.logging_config import get_logger

logger = get_logger("LLMTool")

# Lazy-loaded client
_client = None


def _get_client():
    """Lazy-load the Azure OpenAI client."""
    global _client
    if _client is None:
        try:
            from azure.ai.inference import ChatCompletionsClient
            from azure.core.credentials import AzureKeyCredential

            _client = ChatCompletionsClient(
                endpoint=settings.AZURE_OPENAI_ENDPOINT,
                credential=AzureKeyCredential(settings.AZURE_OPENAI_API_KEY),
            )
            logger.info("Azure Phi-4 client initialized")
        except ImportError:
            logger.warning("azure-ai-inference not installed, LLM calls will fail")
            _client = None
    return _client


async def call_llm(
    system_prompt: str,
    user_prompt: str,
    temperature: float = 0.0,
    max_tokens: int = 4096,
    pipeline_stage: str = "unknown",
    batch_id: Optional[str] = None,
    resume_file_id: Optional[str] = None,
    use_cache: bool = True,
) -> Dict[str, Any]:
    """
    Call Azure Phi-4 LLM with caching and token monitoring.
    
    Returns:
        Dict with 'content', 'prompt_tokens', 'completion_tokens', 'total_tokens', 'cached'
    """
    # ── Check prompt cache ───────────────────────────────────────
    prompt_hash = hash_content(f"{system_prompt}|{user_prompt}|{temperature}")

    if use_cache:
        cache_key = CacheKeys.phi4(prompt_hash)
        cached = await cache_get(cache_key)
        if cached:
            logger.info(f"LLM cache HIT: {pipeline_stage}")
            result = json.loads(cached)
            result["cached"] = True
            return result

    # ── Call Azure Phi-4 ─────────────────────────────────────────
    client = _get_client()
    if client is None:
        return {
            "content": "{}",
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
            "cached": False,
            "error": "LLM client not available",
        }

    try:
        from azure.ai.inference.models import SystemMessage, UserMessage

        response = client.complete(
            messages=[
                SystemMessage(content=system_prompt),
                UserMessage(content=user_prompt),
            ],
            temperature=temperature,
            max_tokens=max_tokens,
            model=settings.AZURE_OPENAI_MODEL_NAME,
        )

        content = response.choices[0].message.content
        usage = response.usage
        prompt_tokens = usage.prompt_tokens if usage else 0
        completion_tokens = usage.completion_tokens if usage else 0
        total_tokens = prompt_tokens + completion_tokens

        result = {
            "content": content,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": total_tokens,
            "cached": False,
        }

        # ── Log token usage ──────────────────────────────────
        log_token_usage_jsonl(
            model=settings.AZURE_OPENAI_MODEL_NAME,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            pipeline_stage=pipeline_stage,
            batch_id=batch_id,
            resume_file_id=resume_file_id,
        )

        # ── Cache result ─────────────────────────────────────
        if use_cache:
            await cache_set(CacheKeys.phi4(prompt_hash), result, ttl_key="phi4")

        logger.info(
            f"LLM call complete: {pipeline_stage} | "
            f"{total_tokens} tokens | temp={temperature}"
        )
        return result

    except Exception as e:
        logger.error(f"LLM call failed: {e}")
        return {
            "content": "{}",
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
            "cached": False,
            "error": str(e),
        }


def parse_llm_json(content: str) -> Dict[str, Any]:
    """Parse JSON from LLM response, handling markdown code blocks."""
    content = content.strip()
    # Remove markdown code blocks
    if content.startswith("```json"):
        content = content[7:]
    elif content.startswith("```"):
        content = content[3:]
    if content.endswith("```"):
        content = content[:-3]
    content = content.strip()

    try:
        return json.loads(content)
    except json.JSONDecodeError:
        logger.warning("Failed to parse LLM JSON response")
        return {}
