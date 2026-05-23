"""
RAIYA Reasoning Schemas — Data structures for the 5-phase reasoning engine.
All label dimensions and their allowed ranges.
"""

from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any, Literal


# ── Label Dimensions ────────────────────────────────────────────────
LABEL_DIMENSIONS = {
    "technical_fit": {
        "strong": (0.80, 1.00),
        "moderate": (0.55, 0.79),
        "weak": (0.30, 0.54),
        "none": (0.00, 0.29),
    },
    "experience_fit": {
        "exceeds": (0.90, 1.00),
        "meets": (0.70, 0.89),
        "below": (0.40, 0.69),
        "significantly_below": (0.00, 0.39),
    },
    "seniority_fit": {
        "overqualified": (0.50, 0.70),
        "match": (0.80, 1.00),
        "junior": (0.30, 0.59),
        "intern": (0.00, 0.29),
    },
    "education_fit": {
        "exceeds": (0.85, 1.00),
        "meets": (0.60, 0.84),
        "below": (0.00, 0.59),
    },
    "domain_fit": {
        "deep": (0.80, 1.00),
        "moderate": (0.55, 0.79),
        "surface": (0.25, 0.54),
        "none": (0.00, 0.24),
    },
    "certification_fit": {
        "all_present": (0.90, 1.00),
        "some_present": (0.40, 0.89),
        "none": (0.00, 0.39),
    },
    "tool_fit": {
        "full": (0.85, 1.00),
        "partial": (0.40, 0.84),
        "none": (0.00, 0.39),
    },
    "soft_skill_fit": {
        "strong": (0.75, 1.00),
        "moderate": (0.45, 0.74),
        "weak": (0.00, 0.44),
    },
}

# Section-to-dimension mapping
SECTION_TO_LABEL_DIMENSION = {
    "technologies": "technical_fit",
    "skills": "technical_fit",
    "tools": "tool_fit",
    "relevant_experience": "experience_fit",
    "experience": "experience_fit",
    "qualification": "education_fit",
    "certifications": "certification_fit",
    "position": "seniority_fit",
    "responsibilities": "domain_fit",
    "salary": "soft_skill_fit",
}


# ── Phase Output Schemas ────────────────────────────────────────────

class StructuralFact(BaseModel):
    """A single structural fact from Phase 1."""
    field: str
    present: bool
    count: Optional[int] = None
    summary: Optional[str] = None


class StructuralFactsOutput(BaseModel):
    """Phase 1 output: structural facts about the resume."""
    facts: List[StructuralFact]
    total_fields_checked: int = 0
    resume_completeness: float = 0.0


class EvidenceEntry(BaseModel):
    """A single evidence classification entry from Phase 2."""
    section: str
    classification: Literal["EXPLICIT", "PARTIAL", "ABSENT"]
    matched_items: List[str] = []
    missing_items: List[str] = []
    confidence: float = 0.0


class EvidenceMapOutput(BaseModel):
    """Phase 2 output: evidence map."""
    entries: Dict[str, EvidenceEntry]
    total_explicit: int = 0
    total_partial: int = 0
    total_absent: int = 0


class LabelSet(BaseModel):
    """Phase 3 output: categorical labels per dimension."""
    technical_fit: str = "moderate"
    experience_fit: str = "meets"
    seniority_fit: str = "match"
    education_fit: str = "meets"
    domain_fit: str = "moderate"
    certification_fit: str = "some_present"
    tool_fit: str = "partial"
    soft_skill_fit: str = "moderate"


class VerificationEntry(BaseModel):
    """A single verification result from Phase 4."""
    dimension: str
    original_label: str
    verified_label: str
    similarity_score: float
    expected_range: tuple = (0.0, 1.0)
    corrected: bool = False
    reason: str = ""


class VerificationReport(BaseModel):
    """Phase 4 output: verified labels + corrections."""
    entries: List[VerificationEntry]
    total_corrections: int = 0
    labels: LabelSet


class ReasoningContext(BaseModel):
    """Phase 5 output: narrative reasoning context for RAG."""
    narrative: str
    section_summaries: Dict[str, str] = {}
    confidence_level: str = "medium"


class ReasoningOutput(BaseModel):
    """Complete reasoning engine output across all 5 phases."""
    structural_facts: Dict[str, Any]
    evidence_map: Dict[str, Any]
    reasoning_labels: Dict[str, str]
    verification_report: Dict[str, Any]
    reasoning_context: str
    phases_completed: int = 5
    corrections_applied: int = 0
    reasoning_hash: str = ""
