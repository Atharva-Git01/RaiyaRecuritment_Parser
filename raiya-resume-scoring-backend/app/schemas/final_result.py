"""
RAIYA Final Result Scoring Agent Schema — Maps final_result_scoring_agent_schema.json.
This is the CANONICAL output of score_adjustment_node.
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any, Literal


class ScoringTraceEntry(BaseModel):
    score_awarded: float
    weight: float
    label_weighted_coverage: float = 0.0   # section label_weighted_coverage (0–100)
    notes: str                              # label range, hybrid, verdict, correction, R005 penalty


class AgentResult(BaseModel):
    final_score: float
    skills_score: float
    experience_score: float
    relevant_experience_score: float
    projects_score: float
    certificates_score: float
    tools_score: float
    technologies_score: float
    qualification_score: float
    responsibilities_score: float
    salary_score: float
    position_score: float
    notes: str
    jd_weights_math_valid: bool = True      # propagated from rag_final_verdict (Phase 13)
    scoring_trace: Dict[str, ScoringTraceEntry] = Field(default_factory=dict)
    guardrails_applied: List[str] = Field(default_factory=list)


class StateHistory(BaseModel):
    from_state: str
    to_state: str
    timestamp: str
    reason: Optional[str] = None


class FinalResultScoringAgent(BaseModel):
    """Canonical final result scoring agent output schema."""
    current_state: Literal[
        "INIT", "VALIDATING_INPUT", "FETCHING_CONTEXT",
        "SCORING", "VERIFYING_OUTPUT", "COMPLETED", "FAILED"
    ]
    inputs: Dict[str, Any]                  # resume + jd + weights
    history: List[StateHistory]
    result: AgentResult
    error: Optional[Any] = None
    success: bool
    token_usage: Optional[Dict[str, Any]] = None
