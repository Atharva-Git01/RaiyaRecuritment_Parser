"""
RAIYA Reasoning Schemas — ReasoningOutput, LabelSet, VerificationReport.
"""

from pydantic import BaseModel
from typing import Optional, Dict, List, Literal


class LabelSet(BaseModel):
    """Categorical labels assigned by the reasoning engine Phase 3."""
    technical_fit: Literal["strong", "moderate", "weak", "none"] = "moderate"
    experience_fit: Literal["exceeds", "meets", "below", "significantly_below"] = "meets"
    seniority_fit: Literal["overqualified", "match", "junior", "intern"] = "match"
    education_fit: Literal["exceeds", "meets", "below"] = "meets"
    domain_fit: Literal["deep", "moderate", "surface", "none"] = "moderate"
    certification_fit: Literal["all_present", "some_present", "none"] = "some_present"
    tool_fit: Literal["full", "partial", "none"] = "partial"
    soft_skill_fit: Literal["strong", "moderate", "weak"] = "moderate"


class VerificationEntry(BaseModel):
    label: str
    hybrid_score: float
    expected_range: List[float]     # [lo, hi]
    within_range: bool
    corrected_label: Optional[str] = None


class VerificationReport(BaseModel):
    """Cross-verification report from Phase 4."""
    entries: Dict[str, VerificationEntry]
    total_corrections: int = 0


class ReasoningOutput(BaseModel):
    """Complete output from the 5-phase reasoning engine."""
    structural_facts: Dict[str, any]           # Phase 1 output
    evidence_map: Dict[str, str]               # Phase 2: dimension → EXPLICIT|PARTIAL|ABSENT
    reasoning_labels: LabelSet                  # Phase 3 output
    verification_report: VerificationReport     # Phase 4 output
    reasoning_context: str                      # Phase 5 narrative
    phases_completed: int = 5
    corrections_applied: int = 0
