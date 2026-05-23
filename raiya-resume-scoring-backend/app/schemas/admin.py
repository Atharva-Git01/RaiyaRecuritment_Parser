"""
RAIYA Admin Schemas — Request/Response models for admin operations.
"""

from pydantic import BaseModel
from typing import Optional, List, Dict, Any


class TokenUsageSummary(BaseModel):
    total_prompt_tokens: int
    total_completion_tokens: int
    total_tokens: int
    total_cost_usd: float
    by_stage: Dict[str, Dict[str, Any]]


class PipelineMetricsResponse(BaseModel):
    total_batches: int
    total_resumes_processed: int
    total_jds: int
    average_score: float
    accuracy_rate: float
    hallucination_rate: float


class EvidenceRulesUpdateRequest(BaseModel):
    rules: Dict[str, Any]


class SystemHealthResponse(BaseModel):
    database: str  # healthy|degraded|down
    redis: str
    embedding_model: str
    llm: str
    pgvector: str
