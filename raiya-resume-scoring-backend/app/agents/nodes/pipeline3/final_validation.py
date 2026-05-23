"""
RAIYA Pipeline 3 Node — Final Validation.

PASS/FAIL gate that aggregates the three independent validation signals
produced earlier in Pipeline 3 and the JD Phase 13 mathematical validation:

    final_pass = det_valid AND math_valid AND jd_weights_math_valid

Writes `verification_report` (PASS/FAIL summary) and propagates the
`importance_weighted_mae` figure for the explanation node + report PDF.
"""

from typing import Any

from langgraph.runtime import Runtime

from app.agents import PipelineState, PipelineContext
from app.core.logging_config import get_logger

logger = get_logger("FinalValidationNode")


async def final_validation_node(
    state: PipelineState,
    runtime: Runtime[PipelineContext],
) -> dict:
    """
    Aggregate validation flags into a single PASS/FAIL verdict.

    Reads:
      - state["rag_final_verdict"]            (from rag_validation)
      - state["match_output"]                 (from score_adjustment)
      - state["jd_weights"]["weighting_metadata"]["mathematical_validation"]
                                              (from JD Phase 13, set by assign_weights)

    Writes:
      - state["verification_report"]: {
            "final_pass": bool,
            "det_valid": bool,
            "math_valid": bool,
            "jd_weights_math_valid": bool,
            "importance_weighted_mae": float | None,
            "notes": list[str],
        }
    """
    rag_verdict = state.get("rag_final_verdict") or {}
    match_output = state.get("match_output") or {}
    jd_weights = state.get("jd_weights") or {}

    det_valid: bool = bool(rag_verdict.get("deterministic_valid", False))
    math_valid: bool = bool(rag_verdict.get("mathematical_valid", False))

    jd_math = (
        jd_weights.get("weighting_metadata", {})
        .get("mathematical_validation", {})
    )
    jd_weights_math_valid: bool = bool(jd_math.get("is_valid", True))

    importance_weighted_mae = rag_verdict.get("importance_weighted_mae")
    if importance_weighted_mae is None:
        # Fall back to flat MAE for legacy runs.
        importance_weighted_mae = rag_verdict.get("mae")

    final_pass = det_valid and math_valid and jd_weights_math_valid

    notes: list[str] = []
    if not det_valid:
        notes.append("Deterministic validator failed — coverage or hallucination flags raised.")
    if not math_valid:
        notes.append("Mathematical validator failed — ground-truth deviation above tolerance.")
    if not jd_weights_math_valid:
        notes.append("JD Phase 13 math validation failed — weights may sum incorrectly.")
    if not match_output.get("success", True):
        notes.append("score_adjustment reported success=False.")

    verification_report: dict[str, Any] = {
        "final_pass": final_pass,
        "det_valid": det_valid,
        "math_valid": math_valid,
        "jd_weights_math_valid": jd_weights_math_valid,
        "importance_weighted_mae": importance_weighted_mae,
        "notes": notes,
    }

    logger.info(
        "Final validation: pass=%s det=%s math=%s jd_math=%s mae=%s",
        final_pass,
        det_valid,
        math_valid,
        jd_weights_math_valid,
        importance_weighted_mae,
    )

    return {
        "verification_report": verification_report,
        "agent_state": "VERIFYING_OUTPUT" if final_pass else "FAILED",
    }
