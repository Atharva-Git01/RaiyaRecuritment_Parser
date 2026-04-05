import json
from datetime import datetime
from typing import Any, Dict, List, Literal

from pydantic import BaseModel, Field, field_validator


ROOT_CAUSE_TAXONOMY = [
    "prompt_issue",
    "override_bug",
    "jd_normalization_issue",
    "evidence_extraction_gap",
    "guardrail_gap",
    "observability_gap",
    "entrypoint_bug",
    "test_expectation_wrong",
]

SUITE_MODES = ["smoke", "repro"]
SUITE_SCOPES = ["all", "real", "core"]
REQUEST_STATUSES = ["ok", "request_error", "malformed_output", "credential_error"]


class ScoreBand(BaseModel):
    min: int = Field(ge=0, le=100)
    max: int = Field(ge=0, le=100)

    @field_validator("max")
    @classmethod
    def validate_bounds(cls, value: int, info):
        min_value = info.data.get("min", 0)
        if value < min_value:
            raise ValueError("max must be greater than or equal to min")
        return value


class EvidenceExpectation(BaseModel):
    score_key: Literal["skills_score", "technologies_score"]
    required_terms: List[str] = Field(default_factory=list)
    forbidden_terms: List[str] = Field(default_factory=list)
    notes: str = ""


class BenchmarkCase(BaseModel):
    case_id: str
    resume_path: str
    jd_path: str
    case_type: str
    expected_final_band: ScoreBand
    expected_component_bands: Dict[str, ScoreBand] = Field(default_factory=dict)
    expected_rank_bucket: str
    must_match_evidence: List[EvidenceExpectation] = Field(default_factory=list)
    must_not_match_evidence: List[EvidenceExpectation] = Field(default_factory=list)
    expected_overrides: List[str] = Field(default_factory=list)
    review_owner: str = ""
    review_status: str = "pending_review"
    notes: str = ""


class ManualReviewRubric(BaseModel):
    case_id: str
    expected_hiring_judgment: Literal[
        "strong_yes", "yes", "lean_yes", "mixed", "lean_no", "no", "strong_no"
    ]
    component_expectations: Dict[str, str] = Field(default_factory=dict)
    required_evidence: Dict[str, List[str]] = Field(default_factory=dict)
    disallowed_evidence: Dict[str, List[str]] = Field(default_factory=dict)
    explanation_quality_notes: str = ""
    recruiter_reviewer: str = ""
    engineering_reviewer: str = ""
    review_status: str = "pending_review"


class EvaluationRunResult(BaseModel):
    run_id: str
    timestamp: str
    deployment: str
    prompt_version: str
    case_id: str
    suite_mode: Literal["smoke", "repro"]
    suite_batch_id: str
    repeat_index: int = Field(ge=1)
    scope: Literal["all", "real", "core"]
    request_status: Literal["ok", "request_error", "malformed_output", "credential_error"]
    request_error: str = ""
    scores: Dict[str, int] = Field(default_factory=dict)
    scoring_trace: Dict[str, Any] = Field(default_factory=dict)
    guardrails_applied: List[str] = Field(default_factory=list)
    overrides_fired: List[str] = Field(default_factory=list)
    latency_ms: int = Field(ge=0)
    token_usage: Dict[str, int] = Field(default_factory=dict)
    pass_fail: Literal["pass", "fail", "baseline_fail", "error"]
    failure_reason: str = ""
    raw_result_path: str = ""
    root_causes: List[str] = Field(default_factory=list)

    @field_validator("timestamp")
    @classmethod
    def validate_timestamp(cls, value: str) -> str:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
        return value

    @field_validator("root_causes")
    @classmethod
    def validate_root_causes(cls, values: List[str]) -> List[str]:
        invalid = [value for value in values if value not in ROOT_CAUSE_TAXONOMY]
        if invalid:
            raise ValueError(f"Unknown root causes: {invalid}")
        return values


def load_json_file(path: str) -> Any:
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)
