"""
RAIYA Pipeline 3 Node — Score Adjustment.
Reads reasoning_labels + RAG evidence → applies Guardrails AI →
produces final_result_scoring_agent_schema output.
"""

from langgraph.runtime import Runtime

from app.agents import PipelineContext, PipelineState
from app.core.hashing import hash_json
from app.core.logging_config import get_logger
from app.guardrails_config.score_guards import apply_batch_score_guards
from app.reasoning.reasoning_schemas import LABEL_DIMENSIONS, SECTION_TO_LABEL_DIMENSION
from app.schemas.final_result import FinalResultScoringAgent, AgentResult, ScoringTraceEntry

logger = get_logger("ScoreAdjustmentNode")


async def score_adjustment_node(
    state: PipelineState,
    runtime: Runtime[PipelineContext],
) -> dict:
    """
    Pipeline 3 Step 4: Score adjustment with guardrails.
    Output: match_output (final_result_scoring_agent_schema), final_score.
    """
    section_sims = state.get("section_similarities", {})
    labels = state.get("reasoning_labels", {})
    det_report = state.get("deterministic_report", {})
    math_report = state.get("mathematical_report", {})
    rule_evidence = state.get("rule_based_evidence", {})
    jd_weights = state.get("jd_weights", {}).get("scoring", {})
    jd_id = state.get("jd_id", "")

    section_scores = {}
    scoring_trace = {}

    for section, sec_data in jd_weights.items():
        jd_weight = sec_data.get("weight", 0)
        if jd_weight == 0:
            section_scores[section] = 0.0
            scoring_trace[section] = {"score_awarded": 0.0, "weight": 0.0, "notes": "Weight=0; skipped"}
            continue

        sim_data = section_sims.get(section, {})
        hybrid = sim_data.get("hybrid_score", 0.0) if isinstance(sim_data, dict) else 0.0

        # Step 1: Constrain to reasoning label range
        dim = SECTION_TO_LABEL_DIMENSION.get(section, "technical_fit")
        label = labels.get(dim, "moderate")
        ranges = LABEL_DIMENSIONS.get(dim, {})
        lo, hi = ranges.get(label, (0.0, 1.0))
        constrained = max(lo, min(hi, hybrid))

        # Step 2: Apply mathematical report correction
        gt_score = math_report.get("ground_truth_scores", {}).get(section)
        section_ev = _find_section_evidence(rule_evidence, section)
        verdict = section_ev.get("verdict", "ACCURATE") if section_ev else "ACCURATE"

        correction_note = ""
        if verdict == "OVERESTIMATED" and gt_score is not None:
            old = constrained
            constrained = min(constrained, gt_score / 100.0) if gt_score > 0 else constrained
            correction_note = f"OVER: {old:.3f}→{constrained:.3f}"
        elif verdict == "UNDERESTIMATED" and gt_score is not None:
            old = constrained
            constrained = max(constrained, (gt_score / 100.0) * 0.9) if gt_score > 0 else constrained
            correction_note = f"UNDER: {old:.3f}→{constrained:.3f}"

        # Step 3: Deterministic penalties — label-weighted coverage + mandatory gap signal
        overall_label_coverage = det_report.get("overall_analytics", {}).get(
            "label_weighted_coverage",
            det_report.get("overall_analytics", {}).get("weighted_coverage", 100),
        )
        if overall_label_coverage < 20:
            constrained *= 0.85

        # R005 per-section knockdown: mandatory/critical criteria absent from resume
        if section_ev:
            for rule in section_ev.get("applied_rules", []):
                if rule.get("rule_id") == "R005_MANDATORY_UNMATCHED" and rule.get("fired"):
                    constrained *= 0.70
                    correction_note += " +R005_MANDATORY_PENALTY"
                    break

        constrained = max(lo, min(hi, constrained))
        raw_section_score = constrained * jd_weight

        section_scores[section] = raw_section_score
        trace_note = f"label={label}({lo:.2f},{hi:.2f}), hybrid={hybrid:.3f}, verdict={verdict}"
        if correction_note:
            trace_note += f", {correction_note}"
        sec_sr = det_report.get("section_results", {}).get(section, {})
        sec_sem = sec_sr.get("resume_semantic_metrics", {}) if isinstance(sec_sr, dict) else {}
        sec_label_cov = sec_sem.get("label_weighted_coverage", sec_sem.get("weighted_coverage", 0.0))
        scoring_trace[section] = {
            "score_awarded": round(raw_section_score, 4),
            "weight": jd_weight,
            "label_weighted_coverage": round(sec_label_cov, 2),
            "notes": trace_note,
        }

    # Step 4: Guardrails AI
    try:
        validated_scores, guardrails_fired = await apply_batch_score_guards(section_scores, jd_id)
    except Exception:
        validated_scores = section_scores
        guardrails_fired = []

    final_score = round(sum(validated_scores.values()), 2)
    jd_weights_math_valid = state.get("rag_final_verdict", {}).get("jd_weights_math_valid", True)

    # Step 5: Build output via Pydantic schema validation
    # Build scoring_trace with Pydantic models
    validated_trace = {}
    for sec, trace_data in scoring_trace.items():
        validated_trace[sec] = ScoringTraceEntry(**trace_data).model_dump()

    agent_result = AgentResult(
        final_score=final_score,
        skills_score=round(validated_scores.get("skills", 0), 4),
        experience_score=round(validated_scores.get("experience", 0), 4),
        relevant_experience_score=round(validated_scores.get("relevant_experience", 0), 4),
        projects_score=0.0,
        certificates_score=round(validated_scores.get("certifications", 0), 4),
        tools_score=round(validated_scores.get("tools", 0), 4),
        technologies_score=round(validated_scores.get("technologies", 0), 4),
        qualification_score=round(validated_scores.get("qualification", 0), 4),
        responsibilities_score=round(validated_scores.get("responsibilities", 0), 4),
        salary_score=round(validated_scores.get("salary", 0), 4),
        position_score=round(validated_scores.get("position", 0), 4),
        notes=(
            "Score adjustment complete."
            if jd_weights_math_valid
            else "Score adjustment complete. Warning: JD weight math validation failed."
        ),
        jd_weights_math_valid=jd_weights_math_valid,
        scoring_trace=validated_trace,
        guardrails_applied=guardrails_fired,
    )

    final_result = FinalResultScoringAgent(
        current_state="VERIFYING_OUTPUT",
        inputs={
            "resume": state.get("resume_parsed", {}),
            "jd": state.get("jd_normalized", {}),
            "weights": state.get("jd_weights", {}),
        },
        history=[],
        result=agent_result,
        success=True,
        token_usage=state.get("token_usage_summary", {}),
    )

    match_output = final_result.model_dump()
    output_hash = hash_json(match_output)

    logger.info(f"Score adjustment complete: final_score={final_score}")

    return {
        "match_output": match_output,
        "final_score": final_score,
        "output_hash": output_hash,
        "agent_state": "VERIFYING_OUTPUT",
    }


def _find_section_evidence(rule_evidence: dict, section: str) -> dict:
    """Find section evidence by name."""
    for ev in rule_evidence.get("section_evidences", []):
        if ev.get("section_name") == section:
            return ev
    return {}
