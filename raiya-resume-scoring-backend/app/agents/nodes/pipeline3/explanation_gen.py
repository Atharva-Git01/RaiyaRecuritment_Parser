"""
RAIYA Pipeline 3 Node — Explanation Generator.
Reads reasoning_context + RAG reports → 6-section audit-safe explanation.
"""

from langgraph.runtime import Runtime

from app.agents import PipelineContext, PipelineState
from app.agents.tools.llm_tool import call_llm
from app.core.hashing import hash_content
from app.core.logging_config import get_logger
from app.guardrails_config.explanation_guards import validate_explanation_guardrails
from app.schemas.final_validation_report import FinalValidationReport

logger = get_logger("ExplanationGenNode")


async def explanation_gen_node(
    state: PipelineState,
    runtime: Runtime[PipelineContext],
) -> dict:
    """Generate audit-safe explanation from reasoning context and RAG evidence."""
    reasoning_context = state.get("reasoning_context", "")
    match_output = state.get("match_output", {})
    result = match_output.get("result", {})
    final_score = result.get("final_score", 0)
    scoring_trace = result.get("scoring_trace", {})

    sections = [
        f"## Overall Assessment\nFinal Score: {final_score}/100\n",
        f"## Reasoning Analysis\n{reasoning_context[:500]}\n",
        "## Section Breakdown\n" + "\n".join(
            f"- **{s}**: {t.get('score_awarded', 0):.1f} "
            f"(weight={t.get('weight', 0)}, label_cov={t.get('label_weighted_coverage', 'N/A')}%) "
            f"— {t.get('notes', '')}"
            for s, t in scoring_trace.items()
        ),
        "## Guardrails Applied\n" + (", ".join(result.get("guardrails_applied", [])) or "None"),
        "## Validation Status\n" + _build_validation_status(state),
        "## Recommendation\n" + _generate_recommendation(final_score),
    ]
    explanation = "\n\n".join(sections)

    # Apply explanation guardrails
    cleaned, fired = validate_explanation_guardrails(explanation)
    explanation_hash = hash_content(cleaned)

    logger.info(f"Explanation generated: {len(cleaned)} chars")
    return {
        "llm_explanation": cleaned,
        "explanation_hash": explanation_hash,
    }


def _build_validation_status(state: dict) -> str:
    """Build a concise validation status string surfacing RAG + JD weight signals."""
    rag_verdict = state.get("rag_final_verdict", {})
    lines = [
        f"RAG Verdict: {rag_verdict.get('verdict', 'N/A')} | "
        f"Accuracy: {rag_verdict.get('overall_accuracy', 'N/A')}% | "
        f"Confidence: {rag_verdict.get('confidence', 'N/A')}"
    ]
    if not rag_verdict.get("jd_weights_math_valid", True):
        lines.append(
            "Warning: JD weight pipeline math validation failed — "
            "section weights may be unreliable."
        )
    rule_evidence = state.get("rule_based_evidence", {})
    r005_sections = [
        ev.get("section_name", "")
        for ev in rule_evidence.get("section_evidences", [])
        for rule in ev.get("applied_rules", [])
        if rule.get("rule_id") == "R005_MANDATORY_UNMATCHED"
    ]
    if r005_sections:
        lines.append(
            f"Warning: Mandatory/critical criteria absent in: {', '.join(r005_sections)}"
        )
    return "\n".join(lines)


def _generate_recommendation(score: float) -> str:
    if score >= 85:
        return "Strong candidate. Recommend for immediate interview."
    elif score >= 70:
        return "Good candidate. Recommend for further evaluation."
    elif score >= 55:
        return "Average candidate. May need additional screening."
    elif score >= 40:
        return "Below average. Consider only if pool is limited."
    return "Does not meet minimum requirements."
