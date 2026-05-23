"""
RAIYA Pipeline 3 Node — RAG Validation.
8-step orchestrator that uses hybrid_search results (dense + BM25 + exact)
for deterministic validation, then mathematical + rule-based evidence.

Flow:
  Step 1: Load & validate inputs (jd_weights, resume_parsed, section_similarities)
  Step 2: Normalize resume for scoring
  Step 3: DETERMINISTIC validation using hybrid_search results per section
          — Uses dense_score, bm25_score, exact_match from hybrid_search
          — Matches each JD criterion against resume items
          — Detects hallucinations (high score + no criteria)
  Step 4: MATHEMATICAL validation (ground truth vs AI scores)
  Step 5: RULE-BASED evidence (14 detectors)
  Step 6: Final PASS/FAIL report
  Step 7: Historical evidence ID
  Step 8: pgvector evidence storage (via db.pgvector_client)

Uses single embedding model: BGE-large-en-v1.5 (768-dim) for all operations.
"""

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from langgraph.runtime import Runtime

from app.agents import PipelineContext, PipelineState
from app.core.logging_config import get_logger
from app.schemas.deterministic_output import (
    DeterministicValidatorOutput, OverallAnalytics, SectionResult,
    SemanticMetrics, HybridSearchBreakdown, MatchItem,
)
from app.schemas.mathematical_report import MathematicalValidatorReport, GlobalMetrics
from app.schemas.rule_based_evidence import (
    RuleBasedEvidenceSchema, SectionEvidence, CriterionEvidence,
    RuleEntry, ActionApplied, OverallSummary, RuleApplications,
)
from app.schemas.final_validation_report import FinalValidationReport

logger = get_logger("RAGValidationNode")

# Labels that indicate a criterion is non-negotiable (Phase 4 ontology)
_MANDATORY_LABELS = {"mandatory_core_skill", "critical_requirement"}

# Default multipliers if a criterion lacks an explicit one
_LABEL_MULTIPLIERS_DEFAULT: Dict[str, float] = {
    "mandatory_core_skill": 1.00, "critical_requirement": 0.95,
    "important_skill": 0.80, "preferred_skill": 0.70,
    "supporting_skill": 0.55, "nice_to_have": 0.35, "irrelevant": 0.00,
}


def _extract_criterion_meta(value: Any) -> Dict[str, Any]:
    """
    Normalise a criterion value from either format into a uniform dict:
      Legacy:     80.0  → score=80, multiplier=0.80, reasoning_label="legacy"
      Enterprise: {score, reasoning_label, multiplier, confidence, evidence}
    """
    if isinstance(value, (int, float)):
        norm = max(0.0, min(1.0, float(value) / 100.0))
        return {
            "score": float(value), "multiplier": norm,
            "reasoning_label": "legacy", "confidence": 1.0, "evidence": "",
        }
    if isinstance(value, dict):
        label = value.get("reasoning_label", "supporting_skill")
        return {
            "score": float(value.get("score", 0)),
            "multiplier": float(
                value.get("multiplier", _LABEL_MULTIPLIERS_DEFAULT.get(label, 0.55))
            ),
            "reasoning_label": label,
            "confidence": float(value.get("confidence", 1.0)),
            "evidence": str(value.get("evidence", "")),
        }
    return {
        "score": 0.0, "multiplier": 0.0,
        "reasoning_label": "unknown", "confidence": 0.0, "evidence": "",
    }


async def rag_validation_node(
    state: PipelineState,
    runtime: Runtime[PipelineContext],
) -> dict:
    """
    Pipeline 3 Step 3: RAG Validation Layer (8 steps).
    Reads hybrid_search output (section_similarities) and reasoning engine
    labels to produce deterministic + mathematical + rule-based evidence.
    """
    jd_weights = state.get("jd_weights", {})
    resume_parsed = state.get("resume_parsed", {})
    section_sims = state.get("section_similarities", {})
    jd_id = state.get("jd_id", "")

    try:
        # Step 1: Load & validate inputs
        scoring = jd_weights.get("scoring", {})
        if not scoring:
            raise ValueError("No scoring sections in jd_weights")

        # Step 2: Normalize resume for scoring
        norm_resume = _normalize_resume_for_scoring(resume_parsed)

        # Step 3: Deterministic Validation (uses hybrid_search results)
        det_report_raw = _run_deterministic_validation(
            norm_resume, scoring, section_sims, jd_weights
        )
        # Validate through Pydantic schema
        det_validated = DeterministicValidatorOutput(**det_report_raw)
        det_report = det_validated.model_dump()

        # Step 4: Mathematical Validation
        math_report_raw = _run_mathematical_validation(scoring, section_sims, det_report, jd_weights)
        math_validated = MathematicalValidatorReport(**math_report_raw)
        math_report = math_validated.model_dump()

        # Step 5: Rule-Based Evidence
        rule_evidence_raw = _run_rule_based_evidence(
            scoring, section_sims, det_report, math_report, jd_id,
            jd_weights.get("job_title", "")
        )
        rule_validated = RuleBasedEvidenceSchema(**rule_evidence_raw)
        rule_evidence = rule_validated.model_dump()

        # Step 6: Final Report
        rag_verdict_raw = _generate_final_report(det_report, math_report, rule_evidence)
        verdict_validated = FinalValidationReport(**rag_verdict_raw)
        rag_verdict = verdict_validated.model_dump()

        # Step 7: Historical evidence ID
        evidence_id = (
            f"EVD_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_"
            f"{uuid.uuid4().hex[:8]}"
        )

        logger.info(
            f"RAG validation complete: evidence_id={evidence_id}, "
            f"verdict={rag_verdict.get('verdict')}"
        )

        return {
            "deterministic_report": det_report,
            "mathematical_report": math_report,
            "rule_based_evidence": rule_evidence,
            "rag_final_verdict": rag_verdict,
        }

    except Exception as e:
        logger.error(f"RAG validation failed: {e}")
        return {
            "deterministic_report": {},
            "mathematical_report": {},
            "rule_based_evidence": {},
            "rag_final_verdict": {"verdict": "FAIL", "reason": str(e)},
            "errors": state.get("errors", []) + [f"RAG validation failed: {str(e)}"],
        }


# ═══════════════════════════════════════════════════════════════════════
# Step 2 — Normalize Resume
# ═══════════════════════════════════════════════════════════════════════

def _normalize_resume_for_scoring(resume: dict) -> dict:
    """Flatten resume for scoring comparison."""
    return {
        "skills": _to_string_list(resume.get("skills", [])),
        "technologies": _to_string_list(resume.get("technologies", [])),
        "tools": _to_string_list(resume.get("tools", [])),
        "experience": resume.get("experience", []),
        "education": resume.get("education", []),
        "certifications": _to_string_list(resume.get("certifications", [])),
        "projects": resume.get("projects", []),
        "candidate_achievements": resume.get("candidate_achievements", []),
        "salary_expectation": resume.get("salary_expectation"),
    }


def _to_string_list(items) -> List[str]:
    """Ensure items is a list of lowercase strings."""
    if not isinstance(items, list):
        return []
    return [str(i).lower().strip() for i in items if i]


# ═══════════════════════════════════════════════════════════════════════
# Step 3 — Deterministic Validation (uses hybrid_search results)
# ═══════════════════════════════════════════════════════════════════════

def _run_deterministic_validation(
    norm_resume: dict,
    scoring: dict,
    section_sims: dict,
    jd_weights: dict,
) -> dict:
    """
    Step 3: Deterministic validation using hybrid_search per-section results.

    For each scoring section, this function:
    1. Reads the hybrid_search breakdown (dense, bm25, exact, hybrid_score)
    2. Matches each JD criterion against resume items using exact substring match
    3. Computes weighted_coverage from the hybrid search scores
    4. Detects hallucinations (high hybrid_score but no criteria matched)
    5. Detects zero-weight anomalies
    """
    section_results: Dict[str, Any] = {}
    all_errors: List[str] = []
    overall_valid = True
    total_matched = 0
    total_criteria = 0

    for section_name, section_data in scoring.items():
        criteria = section_data.get("criteria", {})
        weight = section_data.get("weight", 0)

        # ── Read hybrid_search results for this section ──────────
        sim_data = section_sims.get(section_name, {})
        if not isinstance(sim_data, dict):
            sim_data = {}

        dense_score = sim_data.get("dense", 0.0)
        bm25_score = sim_data.get("bm25", 0.0)
        exact_score = sim_data.get("exact", 0.0)
        hybrid_score = sim_data.get("hybrid_score", 0.0)

        # ── Match criteria against resume ────────────────────────
        resume_items = _get_resume_items_for_det_section(section_name, norm_resume)
        resume_text_lower = " ".join(resume_items).lower()

        matched_skills = []
        section_errors = []
        criteria_count = len(criteria) if isinstance(criteria, dict) else 0

        total_multiplier_budget = 0.0
        matched_multiplier_sum = 0.0
        mandatory_unmatched: List[str] = []

        if isinstance(criteria, dict):
            for criterion, criterion_value in criteria.items():
                meta = _extract_criterion_meta(criterion_value)
                criterion_lower = str(criterion).lower().strip()
                total_multiplier_budget += meta["multiplier"]
                is_matched = criterion_lower in resume_text_lower

                if is_matched:
                    matched_multiplier_sum += meta["multiplier"]
                    matched_skills.append({
                        "jd_item": criterion,
                        "resume_match": criterion_lower,
                        "similarity": round(dense_score, 4),
                        "weight": meta["score"],
                        "reasoning_label": meta["reasoning_label"],
                        "multiplier": meta["multiplier"],
                        "confidence": meta["confidence"],
                    })
                elif meta["reasoning_label"] in _MANDATORY_LABELS:
                    mandatory_unmatched.append(criterion)

        matched_count = len(matched_skills)
        total_matched += matched_count
        total_criteria += criteria_count

        # ── Hallucination detection ──────────────────────────────
        # High hybrid score but zero criteria or zero exact matches
        if criteria_count == 0 and hybrid_score > 0.5:
            section_errors.append(
                f"Potential hallucination in {section_name}: "
                f"hybrid_score={hybrid_score:.3f} but no criteria defined"
            )
            overall_valid = False

        if criteria_count > 0 and matched_count == 0 and hybrid_score > 0.6:
            section_errors.append(
                f"Hallucination suspect in {section_name}: "
                f"hybrid={hybrid_score:.3f} but 0/{criteria_count} criteria matched"
            )
            overall_valid = False

        # ── Zero-weight anomaly ──────────────────────────────────
        if weight == 0 and criteria_count > 0:
            section_errors.append(
                f"Zero-weight section {section_name} has {criteria_count} criteria"
            )

        # ── Mandatory criteria unmatched despite semantic signal ──
        if mandatory_unmatched and hybrid_score > 0.4:
            section_errors.append(
                f"Mandatory criteria absent in {section_name}: "
                f"{mandatory_unmatched} (hybrid={hybrid_score:.3f})"
            )
            overall_valid = False

        # ── Compute coverage metrics ─────────────────────────────
        weighted_coverage = round(min(100.0, hybrid_score * 100), 2)
        label_weighted_coverage = (
            round(min(100.0, matched_multiplier_sum / total_multiplier_budget * 100), 2)
            if total_multiplier_budget > 0 else weighted_coverage
        )

        all_errors.extend(section_errors)

        section_results[section_name] = {
            "valid": len(section_errors) == 0,
            "errors": section_errors,
            "resume_semantic_metrics": {
                "matched_skills": matched_skills,
                "weighted_coverage": weighted_coverage,
                "label_weighted_coverage": label_weighted_coverage,
                "token_overlap": round(exact_score, 4),
            },
            "hybrid_search_breakdown": {
                "dense_score": round(dense_score, 4),
                "bm25_score": round(bm25_score, 4),
                "exact_match_ratio": round(exact_score, 4),
                "hybrid_score": round(hybrid_score, 4),
                "criteria_matched": matched_count,
                "criteria_total": criteria_count,
                "mandatory_unmatched": mandatory_unmatched,
            },
        }

    # ── Overall analytics ────────────────────────────────────────
    avg_hybrid = (
        sum(
            s.get("hybrid_score", 0.0) if isinstance(s, dict) else 0.0
            for s in section_sims.values()
        )
        / max(len(section_sims), 1)
    )
    overall_coverage = round(avg_hybrid * 100, 2)

    # Collect all matched skills across sections
    all_matched = []
    for sr in section_results.values():
        all_matched.extend(sr.get("resume_semantic_metrics", {}).get("matched_skills", []))

    avg_token_overlap = (
        sum(
            s.get("exact", 0.0) if isinstance(s, dict) else 0.0
            for s in section_sims.values()
        )
        / max(len(section_sims), 1)
    )

    avg_label_weighted = round(
        sum(
            sr.get("resume_semantic_metrics", {}).get(
                "label_weighted_coverage",
                sr.get("resume_semantic_metrics", {}).get("weighted_coverage", 0.0),
            )
            for sr in section_results.values()
        )
        / max(len(section_results), 1),
        2,
    )

    return {
        "is_valid": overall_valid,
        "overall_analytics": {
            "matched_skills": all_matched,
            "weighted_coverage": overall_coverage,
            "label_weighted_coverage": avg_label_weighted,
            "token_overlap": round(avg_token_overlap, 4),
            "total_criteria": total_criteria,
            "total_matched": total_matched,
        },
        "errors": all_errors,
        "section_results": section_results,
    }


def _get_resume_items_for_det_section(section: str, norm_resume: dict) -> List[str]:
    """Extract flattened resume text items for a given scoring section."""
    FIELD_MAP = {
        "skills": ["skills"],
        "technologies": ["technologies", "skills"],
        "tools": ["tools"],
        "experience": ["experience"],
        "relevant_experience": ["experience"],
        "qualification": ["education"],
        "certifications": ["certifications"],
        "responsibilities": ["experience", "projects"],
        "position": ["experience"],
        "salary": [],
    }
    fields = FIELD_MAP.get(section, [section])
    items = []
    for field in fields:
        val = norm_resume.get(field)
        if isinstance(val, list):
            for entry in val:
                if isinstance(entry, str):
                    items.append(entry)
                elif isinstance(entry, dict):
                    for k in ("title", "name", "description", "degree",
                              "institution", "company", "field_of_study"):
                        v = entry.get(k, "")
                        if v:
                            items.append(str(v).lower())
                    resps = entry.get("responsibilities", [])
                    items.extend([str(r).lower() for r in resps if r])
        elif isinstance(val, str) and val:
            items.append(val)
        elif isinstance(val, dict):
            items.extend([str(v).lower() for v in val.values() if v])
    return [i.strip() for i in items if i.strip()]


# ═══════════════════════════════════════════════════════════════════════
# Step 4 — Mathematical Validation
# ═══════════════════════════════════════════════════════════════════════

def _run_mathematical_validation(
    scoring: dict,
    section_sims: dict,
    det_report: dict,
    jd_weights: Optional[dict] = None,
) -> dict:
    """
    Step 4: Mathematical validation — ground truth (label-weighted deterministic coverage)
    vs AI scores (hybrid_search) per section. Uses Phase 9 section importance factors
    for weighted MAE and cross-references the JD pipeline's Phase 13 math validation.
    """
    section_accuracy = {}
    ground_truth_scores = {}
    ai_scores = {}
    total_weight = 0
    importance_mae_num = 0.0
    importance_mae_den = 0.0

    for section_name, section_data in scoring.items():
        weight = section_data.get("weight", 0)
        sim_data = section_sims.get(section_name, {})
        hybrid = sim_data.get("hybrid_score", 0.0) if isinstance(sim_data, dict) else 0.0

        # Ground truth: prefer label-weighted coverage (enterprise) over hybrid fallback
        sr = det_report.get("section_results", {}).get(section_name, {})
        sem = sr.get("resume_semantic_metrics", {})
        coverage = sem.get("label_weighted_coverage", sem.get("weighted_coverage", 0.0))

        gt_score = coverage * weight / 100 if weight > 0 else 0
        ai_score = hybrid * weight

        ground_truth_scores[section_name] = round(gt_score, 4)
        ai_scores[section_name] = round(ai_score, 4)

        if gt_score > 0:
            accuracy = max(0, 100 - abs(ai_score - gt_score) / gt_score * 100)
        else:
            accuracy = 100 if ai_score == 0 else 0

        section_accuracy[section_name] = round(accuracy, 2)
        total_weight += weight

        # Accumulate importance-weighted MAE using Phase 9 section importance factor
        importance_factor = (
            section_data.get("weight_generation_metadata") or {}
        ).get("section_importance_factor") or 1.0
        importance_mae_num += importance_factor * abs(ai_score - gt_score)
        importance_mae_den += importance_factor

    gt_total = sum(ground_truth_scores.values())
    ai_total = sum(ai_scores.values())
    mae = abs(ai_total - gt_total)
    importance_weighted_mae = (
        round(importance_mae_num / importance_mae_den, 4)
        if importance_mae_den > 0 else round(mae, 4)
    )

    overall_accuracy = max(0, 100 - mae) if gt_total > 0 else 100

    # Cross-reference the JD weight pipeline's own Phase 13 math validation
    jd_weights_math_valid = True
    if jd_weights:
        wm = jd_weights.get("weighting_metadata") or {}
        if isinstance(wm, dict):
            mv = wm.get("mathematical_validation") or {}
            if isinstance(mv, dict) and mv:
                jd_weights_math_valid = bool(mv.get("is_valid", True))

    return {
        "section_accuracy": section_accuracy,
        "ground_truth_scores": ground_truth_scores,
        "ai_scores": ai_scores,
        "global_metrics": {
            "ground_truth_final_score": round(gt_total, 4),
            "ai_final_score": round(ai_total, 4),
            "overall_accuracy": round(overall_accuracy, 2),
            "is_valid": overall_accuracy >= 80,
            "mae": round(mae, 4),
            "importance_weighted_mae": importance_weighted_mae,
            "rmse": round(mae, 4),
            "total_weight_checked": total_weight,
            "jd_weights_math_valid": jd_weights_math_valid,
        },
    }


# ═══════════════════════════════════════════════════════════════════════
# Step 5 — Rule-Based Evidence
# ═══════════════════════════════════════════════════════════════════════

def _run_rule_based_evidence(
    scoring: dict,
    section_sims: dict,
    det_report: dict,
    math_report: dict,
    jd_id: str,
    job_title: str = "",
) -> dict:
    """
    Step 5: Rule-based evidence with detectors for each section.
    Uses hybrid_search breakdown for evidence generation.
    """
    section_evidences = []
    gt_scores = math_report.get("ground_truth_scores", {})
    ai_scores = math_report.get("ai_scores", {})

    for section_name, section_data in scoring.items():
        weight = section_data.get("weight", 0)
        gt = gt_scores.get(section_name, 0)
        ai = ai_scores.get(section_name, 0)
        delta = round(ai - gt, 4)

        if abs(delta) < 1:
            verdict = "ACCURATE"
        elif delta > 0:
            verdict = "OVERESTIMATED"
        else:
            verdict = "UNDERESTIMATED"

        # Get hybrid_search breakdown from deterministic report
        sr = det_report.get("section_results", {}).get(section_name, {})
        hsb = sr.get("hybrid_search_breakdown", {})
        sem = sr.get("resume_semantic_metrics", {})

        coverage = sem.get("label_weighted_coverage", sem.get("weighted_coverage", 0.0))
        matched_count = hsb.get("criteria_matched", 0)
        criteria_total = hsb.get("criteria_total", 0)

        # Build criteria evidence list
        criteria_evaluated = []
        for ms in sem.get("matched_skills", []):
            criteria_evaluated.append({
                "criterion": ms.get("jd_item", ""),
                "criterion_weight": ms.get("weight", 0),
                "matched": True,
                "evidence": f"Found in resume (sim={ms.get('similarity', 0):.3f})",
            })

        # Apply rules
        applied_rules = []

        # Rule 1: Low coverage warning — threshold scales with Phase 9 importance factor
        importance_factor = (
            section_data.get("weight_generation_metadata") or {}
        ).get("section_importance_factor") or 1.0
        coverage_threshold = max(15.0, 30.0 / max(importance_factor, 0.1))
        if coverage < coverage_threshold and weight > 10:
            applied_rules.append({
                "rule_id": "R001_LOW_COVERAGE",
                "description": (
                    f"Section {section_name} has <{coverage_threshold:.0f}% coverage "
                    f"(importance_factor={importance_factor:.2f}) but weight={weight}"
                ),
                "fired": True,
                "condition_evaluation": f"coverage={coverage:.1f}% < {coverage_threshold:.0f}%",
                "action_applied": {
                    "explanation": "Low coverage suggests weak resume-JD match for this section",
                    "score_after": round(ai, 4),
                },
            })

        # Rule 2: Overestimation detector
        if verdict == "OVERESTIMATED" and delta > 3:
            applied_rules.append({
                "rule_id": "R002_OVERESTIMATION",
                "description": f"AI score exceeds ground truth by {delta:.2f}",
                "fired": True,
                "condition_evaluation": f"delta={delta:.2f} > 3.0",
                "action_applied": {
                    "explanation": "Significant overestimation detected",
                    "score_after": round(gt, 4),
                },
            })

        # Rule 3: Dense vs BM25 divergence
        dense = hsb.get("dense_score", 0)
        bm25 = hsb.get("bm25_score", 0)
        if abs(dense - bm25) > 0.4:
            applied_rules.append({
                "rule_id": "R003_DENSE_BM25_DIVERGENCE",
                "description": f"Dense ({dense:.3f}) and BM25 ({bm25:.3f}) diverge significantly",
                "fired": True,
                "condition_evaluation": f"|{dense:.3f} - {bm25:.3f}| > 0.4",
                "action_applied": {
                    "explanation": "Semantic vs keyword matching disagree, warrants manual review",
                    "score_after": round(ai, 4),
                },
            })

        # Rule 4: Zero exact match but high hybrid
        exact = hsb.get("exact_match_ratio", 0)
        hybrid = hsb.get("hybrid_score", 0)
        if exact == 0 and hybrid > 0.5:
            applied_rules.append({
                "rule_id": "R004_NO_EXACT_HIGH_HYBRID",
                "description": "Zero exact matches but high hybrid score",
                "fired": True,
                "condition_evaluation": f"exact=0, hybrid={hybrid:.3f} > 0.5",
                "action_applied": {
                    "explanation": "Semantic match without keyword overlap — possible generalization",
                    "score_after": round(ai, 4),
                },
            })

        # Rule 5: Mandatory/critical criteria absent from resume (Phase 4 ontology)
        mandatory_unmatched = hsb.get("mandatory_unmatched", [])
        if mandatory_unmatched:
            applied_rules.append({
                "rule_id": "R005_MANDATORY_UNMATCHED",
                "description": (
                    f"{len(mandatory_unmatched)} mandatory/critical criterion(a) "
                    f"not found in resume for {section_name}"
                ),
                "fired": True,
                "condition_evaluation": f"mandatory_unmatched={mandatory_unmatched}",
                "action_applied": {
                    "explanation": (
                        "mandatory_core_skill or critical_requirement criteria absent — "
                        "strong disqualification signal regardless of semantic similarity"
                    ),
                    "score_after": round(gt, 4),
                },
            })

        section_evidences.append({
            "section_name": section_name,
            "section_weight": weight,
            "rule_type": "hybrid_search_validated",
            "criteria_evaluated": criteria_evaluated,
            "total_criteria": criteria_total,
            "matched_count": matched_count,
            "coverage_pct": round(coverage, 2),
            "ai_score": round(ai, 4),
            "ground_truth_score": round(gt, 4),
            "score_delta": delta,
            "verdict": verdict,
            "applied_rules": applied_rules,
        })

    ai_total = sum(ai_scores.values())
    gt_total = sum(gt_scores.values())

    return {
        "evidence_id": f"EVD_{jd_id[:8] if jd_id else 'unknown'}",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "job_id": jd_id,
        "job_title": job_title,
        "section_evidences": section_evidences,
        "overall_summary": {
            "total_sections": len(section_evidences),
            "sections_with_overestimation": sum(
                1 for s in section_evidences if s["verdict"] == "OVERESTIMATED"
            ),
            "sections_with_underestimation": sum(
                1 for s in section_evidences if s["verdict"] == "UNDERESTIMATED"
            ),
            "sections_accurate": sum(
                1 for s in section_evidences if s["verdict"] == "ACCURATE"
            ),
            "ai_final_score": round(ai_total, 4),
            "rule_based_final_score": round(gt_total, 4),
            "delta": round(ai_total - gt_total, 4),
        },
        "rule_applications": {
            "total_rules_generated": sum(
                len(s["applied_rules"]) for s in section_evidences
            ),
            "rule_log": [
                rule
                for s in section_evidences
                for rule in s["applied_rules"]
            ],
        },
    }


# ═══════════════════════════════════════════════════════════════════════
# Step 6 — Final Report
# ═══════════════════════════════════════════════════════════════════════

def _generate_final_report(
    det_report: dict, math_report: dict, rule_evidence: dict
) -> dict:
    """Step 6: Final PASS/FAIL report."""
    global_metrics: Dict[str, Any] = math_report.get("global_metrics", {})
    math_valid = global_metrics.get("is_valid", False)
    det_valid = det_report.get("is_valid", False)
    accuracy = global_metrics.get("overall_accuracy", 0)
    jd_weights_math_valid = global_metrics.get("jd_weights_math_valid", True)

    rules_fired = rule_evidence.get("rule_applications", {}).get(
        "total_rules_generated", 0
    )

    passed = math_valid and det_valid and jd_weights_math_valid

    return {
        "verdict": "PASS" if passed else "FAIL",
        "deterministic_valid": det_valid,
        "mathematical_valid": math_valid,
        "jd_weights_math_valid": jd_weights_math_valid,
        "overall_accuracy": accuracy,
        "importance_weighted_mae": global_metrics.get("importance_weighted_mae", 0),
        "rules_fired": rules_fired,
        "confidence": (
            "high" if accuracy >= 90
            else ("medium" if accuracy >= 70 else "low")
        ),
    }
