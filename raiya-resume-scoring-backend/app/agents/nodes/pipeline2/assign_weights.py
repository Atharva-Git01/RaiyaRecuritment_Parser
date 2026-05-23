"""
RAIYA Pipeline 2 Node — Assign Weights.
Runs the 14-phase enterprise weight assignment sub-graph.

Flow:
    jd_normalized → WeightAssignmentGraph (Phases 4–14) → jd_weights

Phases inside the sub-graph:
    Phase  4 — LLM Reasoning Label Assignment  (semantic only)
    Phase  5 — Reasoning Validation            (deterministic)
    Phase  6 — Multiplier Assignment            (deterministic)
    Phase  7 — Criteria Score Generation        (deterministic)
    Phase  8 — Raw Section Weights              (deterministic)
    Phase  9 — Section Importance Factors       (deterministic)
    Phase 10 — Adjusted Raw Weights             (deterministic)
    Phase 11 — Total Raw Weight                 (deterministic)
    Phase 12 — Global Normalization             (deterministic)
    Phase 13 — Mathematical Validation          (deterministic)
    Phase 14 — Final Output Assembly            (deterministic)
"""

from langgraph.runtime import Runtime

from app.agents import PipelineContext, PipelineState
from app.agents.nodes.pipeline2.weight_assignment_graph import run_weight_assignment
from app.core.hashing import hash_json
from app.core.logging_config import get_logger
from app.guardrails_config.weight_guards import validate_jd_weights

logger = get_logger("AssignWeightsNode")

_WEIGHT_STRATEGY = "ontology_label_criteria_average_normalized"


async def assign_weights_node(
    state: PipelineState,
    runtime: Runtime[PipelineContext],
) -> dict:
    """
    Pipeline 2: Assign scoring weights using the 14-phase enterprise sub-graph.

    LLM (Phase 4) assigns ontology reasoning labels per criterion.
    Deterministic Python (Phases 5–13) owns all mathematical operations.
    Output criteria format: {score, reasoning_label, multiplier, confidence, evidence}
    """
    jd_normalized   = state.get("jd_normalized", {})
    jd_content_hash = state.get("jd_content_hash", "")

    try:
        result = await run_weight_assignment(
            jd_normalized=jd_normalized,
            jd_content_hash=jd_content_hash,
            batch_id=state.get("batch_id"),
        )

        weights           = result.get("final_weights_schema", {})
        validation_passed = result.get("validation_passed", False)
        validation_errors = result.get("validation_errors", [])

        if "jd_content_hash" not in weights:
            weights["jd_content_hash"] = jd_content_hash

        # Post-graph guardrails check (weight ranges + sum)
        valid, guard_errors = validate_jd_weights(weights)
        if not valid:
            logger.warning("Post-graph guardrail issues: %s", guard_errors)
            if not validation_passed:
                logger.error("Weight assignment failed both validations — applying defaults")
                weights = _apply_default_weights(jd_normalized, jd_content_hash)

        weights_hash = hash_json(weights)

        logger.info(
            "Weight assignment complete: validation=%s guardrails=%s hash=%s",
            "PASS" if validation_passed else "FAIL",
            "PASS" if valid else "FAIL",
            weights_hash[:16],
        )

        return {
            "jd_weights":  weights,
            "weights_hash": weights_hash,
            "agent_state": "SCORING",
        }

    except Exception as e:
        logger.error("Weight assignment failed: %s", e)
        weights = _apply_default_weights(jd_normalized, jd_content_hash)
        return {
            "jd_weights":  weights,
            "weights_hash": hash_json(weights),
            "errors": state.get("errors", []) + [f"Weight assignment failed: {e}"],
        }


def _apply_default_weights(jd: dict, content_hash: str) -> dict:
    """
    Fallback weights used when the sub-graph fails.
    Criteria use the legacy plain-number format (valid for both validator and scorer).
    """
    def _meta(raw: float, count: int, factor: float = 1.0) -> dict:
        return {
            "raw_weight":               raw,
            "criteria_count":           count,
            "section_importance_factor": factor,
            "normalization_method":     "default_fallback",
            "normalization_factor":     100.0,
        }

    technologies = jd.get("technologies", [])
    skills       = jd.get("skills", [])
    tools        = jd.get("tools", [])
    certs        = jd.get("certifications", [])
    resps        = jd.get("responsibilities", [])

    tech_crit  = {t: 50 for t in technologies if isinstance(t, str)}
    skill_crit = {s: 50 for s in skills       if isinstance(s, str)}
    tool_crit  = {t: 50 for t in tools        if isinstance(t, str)}
    cert_crit  = {c: 50 for c in certs        if isinstance(c, str)}
    resp_crit  = {r[:80]: 50 for r in resps   if isinstance(r, str)}

    return {
        "jd_content_hash": content_hash,
        "weighting_metadata": {
            "weight_generation_strategy": "default_fallback",
            "normalization_applied": True,
            "total_raw_weight": 100.0,
            "normalized_total_weight": 100.0,
            "hitl_review": {
                "reviewed_by_human": False,
                "review_stage": "pipeline_hitl_pause",
                "labels_modified": 0,
                "audit_log": [],
            },
        },
        "job_title":       jd.get("job_title", ""),
        "experience":      "",
        "qualification":   "",
        "technologies":    technologies,
        "skills":          skills,
        "tools":           tools,
        "certifications":  certs,
        "location":        jd.get("location", ""),
        "position":        jd.get("position", "") if isinstance(jd.get("position"), str) else "",
        "job_description": jd.get("job_description", ""),
        "responsibilities": resps,
        "employment_type": jd.get("employment_type", ""),
        "work_mode":       {"remote_option": False, "work_from_office": False, "hybrid": False},
        "scoring": {
            "relevant_experience": {
                "weight": 15, "weight_generation_metadata": _meta(15, 4),
                "criteria": {
                    ">=5 years_relevant": 30, "3-4 years_relevant": 50,
                    "1-2 years_relevant": 40, "<1 year_relevant": 20,
                },
            },
            "experience": {
                "weight": 10, "weight_generation_metadata": _meta(10, 4),
                "criteria": {
                    ">=8 years": 20, "5-7 years": 40, "3-4 years": 60, "<3 years": 40,
                },
            },
            "qualification": {
                "weight": 8, "weight_generation_metadata": _meta(8, 6),
                "criteria": {
                    "PhD": 20, "Masters": 60, "Bachelors": 80,
                    "Associate": 20, "Diploma": 10, "Certification": 30,
                },
            },
            "technologies": {
                "weight": 20,
                "weight_generation_metadata": _meta(20, len(tech_crit)),
                "criteria": tech_crit,
            },
            "skills": {
                "weight": 15,
                "weight_generation_metadata": _meta(15, len(skill_crit)),
                "criteria": skill_crit,
            },
            "position": {
                "weight": 5, "weight_generation_metadata": _meta(5, 3),
                "criteria": {"senior_level": 30, "mid_level": 50, "entry_level": 30},
            },
            "tools": {
                "weight": 10,
                "weight_generation_metadata": _meta(10, len(tool_crit)),
                "criteria": tool_crit,
            },
            "certifications": {
                "weight": 5,
                "weight_generation_metadata": _meta(5, len(cert_crit)),
                "criteria": cert_crit,
            },
            "responsibilities": {
                "weight": 7,
                "weight_generation_metadata": _meta(7, len(resp_crit)),
                "criteria": resp_crit,
            },
            "salary": {
                "weight": 5, "fallback_score": 50,
                "criteria_based_on_salary_expectation": {"3-6": 0, "6-10": 0, ">10": 0},
            },
        },
    }
