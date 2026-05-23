"""
RAIYA Batch Schemas — Request/Response models for batch operations.
"""

from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class BatchCreateRequest(BaseModel):
    jd_id: str
    name: Optional[str] = None


class BatchStatusResponse(BaseModel):
    id: str
    name: Optional[str]
    jd_id: str
    total_resumes: int
    completed: int
    failed: int
    status: str
    created_at: str
    completed_at: Optional[str] = None

    class Config:
        from_attributes = True


class MatchResultResponse(BaseModel):
    id: str
    resume_file_id: str
    candidate_name: str
    candidate_email: str
    final_score: Optional[float]
    recommendation: Optional[str]
    is_valid: bool
    hallucinations_detected: bool
    math_accuracy: Optional[float]
    rank: Optional[int]
    guardrails_applied: Optional[List[str]] = None
    section_scores: Optional[dict] = None
    scoring_trace: Optional[dict] = None
    created_at: str

    class Config:
        from_attributes = True


class BatchResultsResponse(BaseModel):
    batch: BatchStatusResponse
    results: List[MatchResultResponse]
    total_count: int
