"""
RAIYA JD Weights Schema — Maps the enterprise 14-phase weight assignment output.

Criteria format (enterprise):
    {"score": float, "reasoning_label": str, "multiplier": float,
     "confidence": float, "evidence": str}

Legacy flat format (plain number) is also accepted for fallback/default weights.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple, Union

from pydantic import BaseModel, Field


# ── Criteria formats ─────────────────────────────────────────────────

class CriteriaDetail(BaseModel):
    """Enterprise rich criteria entry produced by Phase 7."""
    score:           float = 0.0
    reasoning_label: str   = "manually_assigned"
    multiplier:      float = 0.0
    confidence:      float = 1.0
    evidence:        str   = "manual"


# ── Weight generation metadata ───────────────────────────────────────

class WeightGenerationMetadata(BaseModel):
    raw_weight:               float = 0.0
    criteria_count:           int   = 0
    section_importance_factor: Optional[float] = None
    normalization_factor:     float = 0.0
    # Legacy field — kept for backwards compat with default_fallback outputs
    normalization_method:     Optional[str] = None


# ── HITL review block ────────────────────────────────────────────────

class HITLReview(BaseModel):
    reviewed_by_human: bool             = False
    review_stage:      str              = "pipeline_hitl_pause"
    reviewed_at:       Optional[str]    = None
    labels_modified:   int              = 0
    audit_log:         List[Dict[str, Any]] = Field(default_factory=list)


# ── Math validation block ────────────────────────────────────────────

class MathValidation(BaseModel):
    is_valid:              bool        = True
    normalized_total_weight: float     = 100.0
    variance_score:        float       = 0.0
    section_balance_valid: bool        = True
    errors:                List[str]   = Field(default_factory=list)
    warnings:              List[str]   = Field(default_factory=list)


# ── Top-level weighting metadata ────────────────────────────────────

class WeightingMetadata(BaseModel):
    weight_generation_strategy: str   = "ontology_label_criteria_average_normalized"
    normalization_applied:      bool  = True
    total_raw_weight:           float = 0.0
    normalized_total_weight:    float = 100.0
    hitl_review:                Optional[HITLReview]    = None
    mathematical_validation:    Optional[MathValidation] = None


# ── Work mode ────────────────────────────────────────────────────────

class WorkMode(BaseModel):
    remote_option:    bool = False
    work_from_office: bool = False
    hybrid:           bool = False


# ── Scoring section ──────────────────────────────────────────────────

class ScoringSection(BaseModel):
    weight:                    float = 0.0
    weight_generation_metadata: Optional[WeightGenerationMetadata] = None
    # Accepts both legacy plain numbers and enterprise CriteriaDetail dicts
    criteria: Dict[str, Union[float, CriteriaDetail]] = Field(default_factory=dict)


class SalarySection(BaseModel):
    weight:                             float = 0.0
    weight_generation_metadata:         Optional[WeightGenerationMetadata] = None
    fallback_score:                     float = 50.0
    criteria_based_on_salary_expectation: Dict[str, float] = Field(
        default_factory=lambda: {"3-6": 0.0, "6-10": 0.0, ">10": 0.0}
    )


# ── Full scoring block ───────────────────────────────────────────────

class JDScoringBlock(BaseModel):
    relevant_experience: ScoringSection = Field(default_factory=ScoringSection)
    experience:          ScoringSection = Field(default_factory=ScoringSection)
    qualification:       ScoringSection = Field(default_factory=ScoringSection)
    technologies:        ScoringSection = Field(default_factory=ScoringSection)
    skills:              ScoringSection = Field(default_factory=ScoringSection)
    position:            ScoringSection = Field(default_factory=ScoringSection)
    tools:               ScoringSection = Field(default_factory=ScoringSection)
    certifications:      ScoringSection = Field(default_factory=ScoringSection)
    responsibilities:    ScoringSection = Field(default_factory=ScoringSection)
    salary:              SalarySection  = Field(default_factory=SalarySection)


# ── Top-level schema ─────────────────────────────────────────────────

class JDWeightsSchema(BaseModel):
    """Canonical enterprise JD weights output schema (14-phase pipeline)."""
    jd_content_hash:    str                      = ""
    weighting_metadata: Optional[WeightingMetadata] = None
    job_title:          str                      = ""
    experience:         str                      = ""
    qualification:      str                      = ""
    technologies:       List[str]                = Field(default_factory=list)
    relevant_experience: List[str]               = Field(default_factory=list)
    skills:             List[str]                = Field(default_factory=list)
    tools:              List[str]                = Field(default_factory=list)
    certifications:     List[str]                = Field(default_factory=list)
    location:           str                      = ""
    position:           str                      = ""
    job_description:    str                      = ""
    responsibilities:   List[str]                = Field(default_factory=list)
    employment_type:    str                      = ""
    work_mode:          Optional[WorkMode]       = None
    scoring:            JDScoringBlock           = Field(default_factory=JDScoringBlock)

    def validate_weight_sum(self) -> Tuple[bool, float]:
        """Check that all section weights sum to 100 (±0.5)."""
        total = sum([
            self.scoring.relevant_experience.weight,
            self.scoring.experience.weight,
            self.scoring.qualification.weight,
            self.scoring.technologies.weight,
            self.scoring.skills.weight,
            self.scoring.position.weight,
            self.scoring.tools.weight,
            self.scoring.certifications.weight,
            self.scoring.responsibilities.weight,
            self.scoring.salary.weight,
        ])
        return abs(total - 100.0) <= 0.5, round(total, 4)

    class Config:
        from_attributes = True
