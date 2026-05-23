"""
RAIYA Deterministic Validator Output Schema — Maps deterministic_validator_output_schema.json.
Updated for enterprise pipeline: label_weighted_coverage, reasoning_label, multiplier,
confidence, mandatory_unmatched.
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Literal


# ── Ontology label enum ──────────────────────────────────────────────
ReasoningLabel = Literal[
    "mandatory_core_skill",
    "critical_requirement",
    "important_skill",
    "preferred_skill",
    "supporting_skill",
    "nice_to_have",
    "irrelevant",
    "legacy",
    "unknown",
]


class MatchItem(BaseModel):
    """A single criterion matched in the resume. Carries Phase 4 ontology metadata."""
    jd_item: str
    resume_match: str
    similarity: float = Field(..., ge=0.0, le=1.0)
    weight: float                                    # enterprise: criteria score (0–100); legacy: original numeric
    reasoning_label: ReasoningLabel = "legacy"       # Phase 4 ontology label
    multiplier: float = Field(default=0.55, ge=0.0, le=1.0)  # deterministic multiplier (Phase 6)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)   # LLM confidence in label


class SemanticMetrics(BaseModel):
    matched_skills: List[MatchItem] = Field(default_factory=list)
    weighted_coverage: float = 0.0           # hybrid_score × 100 (legacy fallback)
    label_weighted_coverage: float = 0.0     # Σ(matched_multiplier) / Σ(total_budget) × 100
    token_overlap: float = 0.0               # exact_match_ratio


class HybridSearchBreakdown(BaseModel):
    dense_score: float = Field(default=0.0, ge=0.0, le=1.0)
    bm25_score: float = Field(default=0.0, ge=0.0, le=1.0)
    exact_match_ratio: float = Field(default=0.0, ge=0.0, le=1.0)
    hybrid_score: float = Field(default=0.0, ge=0.0, le=1.0)
    criteria_matched: int = 0
    criteria_total: int = 0
    # Criteria with mandatory_core_skill / critical_requirement labels absent from resume
    mandatory_unmatched: List[str] = Field(default_factory=list)


class SectionResult(BaseModel):
    valid: bool
    errors: List[str] = Field(default_factory=list)
    resume_semantic_metrics: Optional[SemanticMetrics] = None
    hybrid_search_breakdown: Optional[HybridSearchBreakdown] = None


class OverallAnalytics(BaseModel):
    matched_skills: List[MatchItem] = Field(default_factory=list)
    weighted_coverage: float = 0.0           # legacy: avg hybrid_score × 100
    label_weighted_coverage: float = 0.0     # enterprise: avg Σ(matched_mult)/Σ(budget) × 100
    token_overlap: float = 0.0
    total_criteria: int = 0
    total_matched: int = 0


class DeterministicValidatorOutput(BaseModel):
    """Canonical deterministic validator output schema (enterprise-aware)."""
    is_valid: bool
    overall_analytics: OverallAnalytics
    errors: List[str] = Field(default_factory=list)
    section_results: Dict[str, SectionResult] = Field(default_factory=dict)
