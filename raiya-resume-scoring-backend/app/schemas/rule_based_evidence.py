"""
RAIYA Rule-Based Evidence Schema — Maps rule_based_evidence_schema.json.
Updated: R005_MANDATORY_UNMATCHED added; coverage_pct = label_weighted_coverage.
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Literal


RuleId = Literal[
    "R001_LOW_COVERAGE",
    "R002_OVERESTIMATION",
    "R003_DENSE_BM25_DIVERGENCE",
    "R004_NO_EXACT_HIGH_HYBRID",
    "R005_MANDATORY_UNMATCHED",
]


class CriterionEvidence(BaseModel):
    criterion: str
    # Enterprise: criteria score (0–100). Legacy: original numeric value.
    criterion_weight: Optional[float] = None
    matched: bool
    evidence: Optional[str] = None


class ActionApplied(BaseModel):
    explanation: str
    score_after: float


class RuleEntry(BaseModel):
    rule_id: RuleId
    description: str
    fired: bool
    # Human-readable condition e.g. 'coverage=15.3% < 23%' or 'mandatory_unmatched=[Python, Docker]'
    condition_evaluation: str
    action_applied: ActionApplied


class SectionEvidence(BaseModel):
    section_name: str
    section_weight: float
    rule_type: Literal["hybrid_search_validated"] = "hybrid_search_validated"
    criteria_evaluated: List[CriterionEvidence] = Field(default_factory=list)
    total_criteria: Optional[int] = None
    matched_count: Optional[int] = None
    # label_weighted_coverage: Σ(matched multipliers) / Σ(all multipliers) × 100
    coverage_pct: float = 0.0
    ai_score: float
    ground_truth_score: float
    score_delta: float                       # ai_score − ground_truth_score
    verdict: Literal["ACCURATE", "OVERESTIMATED", "UNDERESTIMATED"]
    applied_rules: List[RuleEntry] = Field(default_factory=list)


class OverallSummary(BaseModel):
    total_sections: int = 0
    sections_with_overestimation: int = 0
    sections_with_underestimation: int = 0
    sections_accurate: int = 0
    ai_final_score: float = 0.0
    rule_based_final_score: float = 0.0
    delta: float = 0.0


class RuleApplications(BaseModel):
    total_rules_generated: int = 0
    rule_log: List[RuleEntry] = Field(default_factory=list)


class RuleBasedEvidenceSchema(BaseModel):
    """Canonical rule-based evidence output schema (R001–R005)."""
    evidence_id: str
    timestamp: str
    job_id: str
    job_title: str
    section_evidences: List[SectionEvidence] = Field(default_factory=list)
    overall_summary: OverallSummary = Field(default_factory=OverallSummary)
    rule_applications: RuleApplications = Field(default_factory=RuleApplications)
