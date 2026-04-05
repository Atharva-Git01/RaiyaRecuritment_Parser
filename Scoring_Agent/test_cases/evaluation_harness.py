import json
import os
import time
import uuid
from collections import Counter, defaultdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Tuple

from test_cases.evaluation_schemas import (
    BenchmarkCase,
    EvaluationRunResult,
    ManualReviewRubric,
    ROOT_CAUSE_TAXONOMY,
    load_json_file,
)

try:
    from token_usage_monitor import COMPLETION_COST_PER_1K, PROMPT_COST_PER_1K
except ImportError:
    PROMPT_COST_PER_1K = 0.00030
    COMPLETION_COST_PER_1K = 0.00060

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEST_CASES_DIR = os.path.join(BASE_DIR, "test_cases")
DEFAULT_MANIFEST_PATH = os.path.join(TEST_CASES_DIR, "benchmark_manifest.json")
DEFAULT_RUBRIC_PATH = os.path.join(TEST_CASES_DIR, "manual_review_rubrics.json")
DEFAULT_BASELINE_PATH = os.path.join(TEST_CASES_DIR, "baseline_snapshot.json")
DEFAULT_RESULTS_DIR = os.path.join(TEST_CASES_DIR, "evaluation_results")

CORE_ARCHETYPE_ORDER = [
    "5_perfect_lead_ce",
    "1_senior_java_mismatch_ce",
    "2_junior_prodigy_ce",
    "3_phd_academic_ce",
    "4_career_switcher_ce",
]

AI_COMPONENTS = [
    "skills_score",
    "technologies_score",
    "relevant_experience_score",
    "position_score",
    "tools_score",
]

SCORE_KEYS = [
    "final_score",
    "skills_score",
    "experience_score",
    "relevant_experience_score",
    "projects_score",
    "certificates_score",
    "tools_score",
    "technologies_score",
    "qualification_score",
    "responsibilities_score",
    "salary_score",
    "position_score",
]


def load_benchmark_manifest(path: str = DEFAULT_MANIFEST_PATH) -> List[BenchmarkCase]:
    return [BenchmarkCase.model_validate(item) for item in load_json_file(path)]


def load_manual_review_rubrics(path: str = DEFAULT_RUBRIC_PATH) -> List[ManualReviewRubric]:
    return [ManualReviewRubric.model_validate(item) for item in load_json_file(path)]


def load_baseline_snapshot(path: str = DEFAULT_BASELINE_PATH) -> Dict[str, Any]:
    return load_json_file(path)


def extract_candidate_name(resume: Dict[str, Any]) -> str:
    if not isinstance(resume, dict):
        return "unknown"
    return (
        resume.get("name")
        or (resume.get("personal_info") or {}).get("name")
        or resume.get("candidate_name")
        or "unknown"
    )


def collect_resume_evidence(resume: Dict[str, Any]) -> str:
    experiences = resume.get("experience") or []
    projects = resume.get("projects") or []
    text_parts: List[str] = []

    for item in experiences:
        if isinstance(item, dict):
            text_parts.append(str(item.get("description", "")))

    for item in projects:
        if isinstance(item, dict):
            text_parts.append(str(item.get("description", "")))

    return " ".join(part.lower() for part in text_parts if part).strip()


def validate_evidence_expectations(case: BenchmarkCase, result: Dict[str, Any], resume: Dict[str, Any]) -> List[str]:
    failures: List[str] = []
    evidence_text = collect_resume_evidence(resume)

    for expectation in case.must_match_evidence:
        score = int(result.get(expectation.score_key, 0) or 0)
        if score <= 0:
            failures.append(
                f"{expectation.score_key} expected evidence-backed score but received {score}"
            )
            continue
        missing_terms = [term for term in expectation.required_terms if term.lower() not in evidence_text]
        if missing_terms:
            failures.append(
                f"{expectation.score_key} missing evidence terms: {', '.join(missing_terms)}"
            )

    for expectation in case.must_not_match_evidence:
        score = int(result.get(expectation.score_key, 0) or 0)
        forbidden_terms = [term for term in expectation.forbidden_terms if term.lower() in evidence_text]
        if score > 0 and not forbidden_terms:
            failures.append(
                f"{expectation.score_key} is {score} without explicit supporting evidence in experience/projects"
            )

    return failures


def validate_expected_bands(case: BenchmarkCase, result: Dict[str, Any]) -> List[str]:
    failures: List[str] = []
    final_score = int(result.get("final_score", 0) or 0)
    if not (case.expected_final_band.min <= final_score <= case.expected_final_band.max):
        failures.append(
            f"final_score={final_score} outside expected band {case.expected_final_band.min}-{case.expected_final_band.max}"
        )

    for score_key, band in case.expected_component_bands.items():
        value = int(result.get(score_key, 0) or 0)
        if not (band.min <= value <= band.max):
            failures.append(
                f"{score_key}={value} outside expected band {band.min}-{band.max}"
            )

    return failures


def validate_output_quality(result: Dict[str, Any]) -> List[str]:
    failures: List[str] = []
    trace = result.get("scoring_trace", {})

    if not isinstance(trace, dict):
        failures.append("scoring_trace is not a dictionary")
        return failures

    trace_mapping = {
        "experience": "experience_score",
        "relevant_experience": "relevant_experience_score",
        "skills": "skills_score",
        "technologies": "technologies_score",
        "qualification": "qualification_score",
        "salary": "salary_score",
        "tools": "tools_score",
        "position": "position_score",
    }

    for trace_key, result_key in trace_mapping.items():
        if trace_key not in trace:
            continue
        trace_item = trace[trace_key]
        if not isinstance(trace_item, dict):
            failures.append(f"scoring_trace.{trace_key} is not an object")
            continue
        if trace_item.get("score_awarded") != result.get(result_key):
            failures.append(
                f"trace mismatch for {result_key}: trace={trace_item.get('score_awarded')}, result={result.get(result_key)}"
            )

    if not isinstance(result.get("notes", ""), str):
        failures.append("notes is not a string")

    guardrails_applied = result.get("guardrails_applied", [])
    if not isinstance(guardrails_applied, list):
        failures.append("guardrails_applied is not a list")
    elif any(not isinstance(item, str) for item in guardrails_applied):
        failures.append("guardrails_applied contains non-string values")

    return failures


def validate_operational_quality(output: Dict[str, Any]) -> List[str]:
    failures: List[str] = []
    if output.get("success"):
        if output.get("current_state") != "COMPLETED":
            failures.append("successful output did not end in COMPLETED")
        if not isinstance(output.get("result"), dict):
            failures.append("successful output is missing result payload")

    try:
        json.dumps(output)
    except TypeError as exc:
        failures.append(f"output is not JSON-serializable: {exc}")

    token_usage = output.get("token_usage", {})
    if token_usage and not isinstance(token_usage, dict):
        failures.append("token_usage is not a dictionary")

    return failures


def infer_root_causes(failures: List[str]) -> List[str]:
    text = " ".join(failures).lower()
    inferred: List[str] = []
    mapping = {
        "prompt_issue": ["outside expected band", "missing evidence terms"],
        "override_bug": ["salary", "qualification", "experience_score", "relevant_experience_score"],
        "jd_normalization_issue": ["jd", "weight"],
        "evidence_extraction_gap": ["without explicit supporting evidence", "missing evidence"],
        "guardrail_gap": ["guardrails_applied", "trace mismatch"],
        "observability_gap": ["token_usage", "json-serializable"],
        "entrypoint_bug": ["completed", "result payload"],
        "test_expectation_wrong": ["expected band"],
    }

    for root_cause, indicators in mapping.items():
        if any(indicator.lower() in text for indicator in indicators):
            inferred.append(root_cause)

    if not inferred and failures:
        inferred.append("prompt_issue")

    return [root_cause for root_cause in inferred if root_cause in ROOT_CAUSE_TAXONOMY]


def classify_request_status(output: Dict[str, Any]) -> Tuple[str, str]:
    if not isinstance(output, dict):
        return "request_error", "Output payload is not a dictionary."

    if output.get("success"):
        return "ok", ""

    error_text = str(output.get("error", "") or "")
    lowered = error_text.lower()

    if "missing azure_openai credentials" in lowered:
        return "credential_error", error_text

    malformed_indicators = [
        "could not parse json from ai output",
        "empty model response content",
        "pydantic validation failed",
        "ai output validation failed",
        "authority rejected the ai score",
    ]
    if any(indicator in lowered for indicator in malformed_indicators):
        return "malformed_output", error_text

    return "request_error", error_text or "Unknown request error."


def evaluate_result_payload(
    case: BenchmarkCase,
    output: Dict[str, Any],
    latency_ms: int,
    deployment: str,
    prompt_version: str,
    suite_mode: str,
    suite_batch_id: str,
    repeat_index: int,
    scope: str,
    raw_result_path: str = "",
) -> EvaluationRunResult:
    result = output.get("result", {}) if isinstance(output, dict) else {}
    resume = ((output.get("inputs") or {}).get("resume")) if isinstance(output, dict) else {}
    request_status, request_error = classify_request_status(output)
    failures: List[str] = []

    if request_status == "ok":
        failures.extend(validate_expected_bands(case, result))
        failures.extend(validate_evidence_expectations(case, result, resume or {}))
        failures.extend(validate_output_quality(result))
        failures.extend(validate_operational_quality(output))

    if request_status == "ok":
        pass_fail = "pass" if not failures else "fail"
        root_causes = infer_root_causes(failures)
    else:
        pass_fail = "error"
        root_causes = []

    return EvaluationRunResult(
        run_id=str(uuid.uuid4()),
        timestamp=datetime.now(timezone.utc).isoformat(),
        deployment=deployment,
        prompt_version=prompt_version,
        case_id=case.case_id,
        suite_mode=suite_mode,
        suite_batch_id=suite_batch_id,
        repeat_index=repeat_index,
        scope=scope,
        request_status=request_status,
        request_error=request_error,
        scores={key: int(result.get(key, 0) or 0) for key in SCORE_KEYS if key in result},
        scoring_trace=result.get("scoring_trace", {}),
        guardrails_applied=result.get("guardrails_applied", []),
        overrides_fired=list(result.get("overrides_fired", []) or []),
        latency_ms=max(int(latency_ms), 0),
        token_usage=output.get("token_usage", {}) or {},
        pass_fail=pass_fail,
        failure_reason="; ".join(failures),
        raw_result_path=raw_result_path,
        root_causes=root_causes,
    )


def estimate_cost_from_usage(token_usage: Dict[str, int]) -> float:
    prompt_tokens = int(token_usage.get("prompt_tokens", 0) or 0)
    completion_tokens = int(token_usage.get("completion_tokens", 0) or 0)
    return round(
        (prompt_tokens / 1000.0) * PROMPT_COST_PER_1K
        + (completion_tokens / 1000.0) * COMPLETION_COST_PER_1K,
        6,
    )


def canonical_successful_runs(runs: List[EvaluationRunResult]) -> List[EvaluationRunResult]:
    canonical: List[EvaluationRunResult] = []
    seen_repeat_indexes = set()

    for run in runs:
        if run.request_status != "ok":
            continue
        if run.repeat_index in seen_repeat_indexes:
            continue
        seen_repeat_indexes.add(run.repeat_index)
        canonical.append(run)

    return canonical


def summarize_case_runs(runs: List[EvaluationRunResult]) -> Dict[str, Any]:
    successful_runs = canonical_successful_runs(runs)
    final_scores = [run.scores.get("final_score", 0) for run in successful_runs]
    component_drifts: Dict[str, Dict[str, Any]] = {}

    for score_key in SCORE_KEYS:
        values = [run.scores.get(score_key, 0) for run in successful_runs if score_key in run.scores]
        if not values:
            continue
        component_drifts[score_key] = {
            "values": values,
            "max_drift": max(values) - min(values),
        }

    ai_component_drifts: Dict[str, Dict[str, Any]] = {}
    for score_key in AI_COMPONENTS:
        values = [run.scores.get(score_key, 0) for run in successful_runs if score_key in run.scores]
        if values:
            ai_component_drifts[score_key] = {
                "values": values,
                "max_drift": max(values) - min(values),
            }

    request_status_counts = Counter(run.request_status for run in runs)
    return {
        "run_count": len(runs),
        "successful_run_count": len(successful_runs),
        "pass_count": len([run for run in runs if run.pass_fail == "pass"]),
        "fail_count": len([run for run in runs if run.pass_fail == "fail"]),
        "error_count": len([run for run in runs if run.pass_fail == "error"]),
        "request_status_counts": dict(request_status_counts),
        "final_scores": final_scores,
        "final_score_drift": max(final_scores) - min(final_scores) if final_scores else None,
        "component_drifts": component_drifts,
        "ai_component_drifts": ai_component_drifts,
        "avg_latency_ms": round(sum(run.latency_ms for run in runs) / max(len(runs), 1), 2),
        "avg_total_tokens": round(
            sum(run.token_usage.get("total_tokens", 0) for run in successful_runs) / max(len(successful_runs), 1),
            2,
        ) if successful_runs else 0,
        "raw_result_paths": [run.raw_result_path for run in runs if run.raw_result_path],
    }


def build_core_rankings(run_results: List[EvaluationRunResult]) -> Dict[str, Any]:
    runs_by_repeat: Dict[int, Dict[str, EvaluationRunResult]] = defaultdict(dict)
    inversions: List[Dict[str, Any]] = []
    rankings: List[Dict[str, Any]] = []

    for run in run_results:
        if run.case_id in CORE_ARCHETYPE_ORDER and run.request_status == "ok":
            runs_by_repeat[run.repeat_index].setdefault(run.case_id, run)

    for repeat_index in sorted(runs_by_repeat):
        repeat_runs = runs_by_repeat[repeat_index]
        missing_cases = [case_id for case_id in CORE_ARCHETYPE_ORDER if case_id not in repeat_runs]
        ordered_scores = [
            {
                "case_id": case_id,
                "final_score": repeat_runs[case_id].scores.get("final_score", 0),
            }
            for case_id in CORE_ARCHETYPE_ORDER
            if case_id in repeat_runs
        ]
        actual_ranking = sorted(
            ordered_scores,
            key=lambda item: (-item["final_score"], CORE_ARCHETYPE_ORDER.index(item["case_id"])),
        )

        repeat_inversions = []
        for higher_index, higher_case in enumerate(CORE_ARCHETYPE_ORDER):
            if higher_case not in repeat_runs:
                continue
            higher_score = repeat_runs[higher_case].scores.get("final_score", 0)
            for lower_case in CORE_ARCHETYPE_ORDER[higher_index + 1 :]:
                if lower_case not in repeat_runs:
                    continue
                lower_score = repeat_runs[lower_case].scores.get("final_score", 0)
                if lower_score > higher_score:
                    inversion = {
                        "repeat_index": repeat_index,
                        "higher_expected_case": higher_case,
                        "higher_expected_score": higher_score,
                        "lower_expected_case": lower_case,
                        "lower_expected_score": lower_score,
                    }
                    inversions.append(inversion)
                    repeat_inversions.append(inversion)

        rankings.append(
            {
                "repeat_index": repeat_index,
                "ranking": actual_ranking,
                "missing_cases": missing_cases,
                "inversions": repeat_inversions,
            }
        )

    return {
        "expected_order": CORE_ARCHETYPE_ORDER,
        "rankings_by_repeat": rankings,
        "inversions": inversions,
        "inversion_count": len(inversions),
    }


def build_cross_jd_summary(run_results: List[EvaluationRunResult]) -> Dict[str, Any]:
    by_repeat: Dict[int, Dict[str, int]] = defaultdict(dict)
    for run in run_results:
        if run.request_status != "ok":
            continue
        if run.case_id in {"3_phd_academic_ce", "3_phd_academic_ds"}:
            by_repeat[run.repeat_index].setdefault(run.case_id, run.scores.get("final_score", 0))

    comparisons = []
    missing_repeats = []
    all_passed = True
    for repeat_index in sorted(by_repeat):
        ce_score = by_repeat[repeat_index].get("3_phd_academic_ce")
        ds_score = by_repeat[repeat_index].get("3_phd_academic_ds")
        if ce_score is None or ds_score is None:
            missing_repeats.append(
                {
                    "repeat_index": repeat_index,
                    "computer_engineer_score": ce_score,
                    "data_scientist_score": ds_score,
                }
            )
            continue

        passed = ds_score > ce_score
        all_passed = all_passed and passed
        comparisons.append(
            {
                "repeat_index": repeat_index,
                "computer_engineer_score": ce_score,
                "data_scientist_score": ds_score,
                "passed": passed,
            }
        )

    return {
        "comparisons": comparisons,
        "missing_repeats": missing_repeats,
        "all_passed": bool(comparisons) and all_passed,
    }


def build_cost_summary(run_results: List[EvaluationRunResult]) -> Dict[str, Any]:
    successful_runs = [run for run in run_results if run.request_status == "ok"]
    total_prompt_tokens = sum(run.token_usage.get("prompt_tokens", 0) for run in successful_runs)
    total_completion_tokens = sum(run.token_usage.get("completion_tokens", 0) for run in successful_runs)
    total_tokens = sum(run.token_usage.get("total_tokens", 0) for run in successful_runs)
    total_estimated_cost = round(sum(estimate_cost_from_usage(run.token_usage) for run in successful_runs), 6)

    return {
        "successful_calls": len(successful_runs),
        "total_prompt_tokens": total_prompt_tokens,
        "total_completion_tokens": total_completion_tokens,
        "total_tokens": total_tokens,
        "estimated_cost_usd": total_estimated_cost,
        "avg_tokens_per_call": round(total_tokens / max(len(successful_runs), 1), 2) if successful_runs else 0,
    }


def build_gate_summary(run_results: List[EvaluationRunResult], suite_mode: str) -> Dict[str, Any]:
    total_runs = len(run_results)
    request_status_counts = Counter(run.request_status for run in run_results)
    successful_runs = [run for run in run_results if run.request_status == "ok"]
    missing_artifacts = [run.case_id for run in run_results if not run.raw_result_path or not os.path.exists(run.raw_result_path)]
    missing_token_usage = [
        run.case_id
        for run in successful_runs
        if int(run.token_usage.get("total_tokens", 0) or 0) <= 0
    ]

    case_summaries = {
        case_id: summarize_case_runs(runs)
        for case_id, runs in defaultdict(list, {
            case_id: [run for run in run_results if run.case_id == case_id]
            for case_id in sorted({run.case_id for run in run_results})
        }).items()
    }

    core_ranking = build_core_rankings(run_results)
    cross_jd = build_cross_jd_summary(run_results)

    max_core_drift = max(
        [
            case_summaries[case_id]["final_score_drift"] or 0
            for case_id in CORE_ARCHETYPE_ORDER
            if case_id in case_summaries
        ],
        default=0,
    )
    non_core_case_ids = [case_id for case_id in case_summaries if case_id not in CORE_ARCHETYPE_ORDER]
    max_non_core_drift = max(
        [
            case_summaries[case_id]["final_score_drift"] or 0
            for case_id in non_core_case_ids
        ],
        default=0,
    )

    max_ai_component_drift = 0
    ai_drift_details: Dict[str, Dict[str, int]] = {}
    for case_id, summary in case_summaries.items():
        ai_drift_details[case_id] = {}
        for score_key, detail in summary["ai_component_drifts"].items():
            drift = detail["max_drift"]
            ai_drift_details[case_id][score_key] = drift
            max_ai_component_drift = max(max_ai_component_drift, drift)

    gate_summary = {
        "suite_mode": suite_mode,
        "operational_ready_for_repro": {
            "passed": (
                total_runs > 0
                and
                request_status_counts.get("credential_error", 0) == 0
                and request_status_counts.get("malformed_output", 0) == 0
                and request_status_counts.get("request_error", 0) == 0
                and not missing_artifacts
                and not missing_token_usage
            ),
            "reasons": [],
        },
        "no_credential_errors": {
            "passed": request_status_counts.get("credential_error", 0) == 0,
            "actual": request_status_counts.get("credential_error", 0),
        },
        "no_malformed_output_failures": {
            "passed": request_status_counts.get("malformed_output", 0) == 0,
            "actual": request_status_counts.get("malformed_output", 0),
        },
        "no_request_level_failures": {
            "passed": request_status_counts.get("request_error", 0) == 0,
            "actual": request_status_counts.get("request_error", 0),
        },
        "all_artifacts_present": {
            "passed": not missing_artifacts,
            "missing_cases": missing_artifacts,
        },
        "all_successful_calls_have_token_usage": {
            "passed": not missing_token_usage,
            "missing_cases": missing_token_usage,
        },
    }

    if total_runs == 0:
        gate_summary["operational_ready_for_repro"]["reasons"].append("no runs were executed")
    if not gate_summary["no_credential_errors"]["passed"]:
        gate_summary["operational_ready_for_repro"]["reasons"].append("credential errors detected")
    if not gate_summary["no_malformed_output_failures"]["passed"]:
        gate_summary["operational_ready_for_repro"]["reasons"].append("malformed output failures detected")
    if not gate_summary["no_request_level_failures"]["passed"]:
        gate_summary["operational_ready_for_repro"]["reasons"].append("request-level failures detected")
    if missing_artifacts:
        gate_summary["operational_ready_for_repro"]["reasons"].append("missing raw result artifacts")
    if missing_token_usage:
        gate_summary["operational_ready_for_repro"]["reasons"].append("missing token usage on successful calls")

    if suite_mode == "repro":
        gate_summary.update(
            {
                "core_final_score_drift_lte_5": {
                    "passed": max_core_drift <= 5,
                    "actual": max_core_drift,
                    "threshold": 5,
                },
                "non_core_final_score_drift_lte_8": {
                    "passed": max_non_core_drift <= 8,
                    "actual": max_non_core_drift,
                    "threshold": 8,
                },
                "ai_component_drift_lte_10": {
                    "passed": max_ai_component_drift <= 10,
                    "actual": max_ai_component_drift,
                    "threshold": 10,
                    "details": ai_drift_details,
                },
                "malformed_output_rate_zero": {
                    "passed": request_status_counts.get("malformed_output", 0) == 0,
                    "actual_rate": request_status_counts.get("malformed_output", 0) / max(total_runs, 1),
                },
                "request_error_rate_zero": {
                    "passed": request_status_counts.get("request_error", 0) == 0,
                    "actual_rate": request_status_counts.get("request_error", 0) / max(total_runs, 1),
                },
                "core_ranking_inversions_zero": {
                    "passed": core_ranking["inversion_count"] == 0
                    and not any(entry["missing_cases"] for entry in core_ranking["rankings_by_repeat"]),
                    "actual": core_ranking["inversion_count"],
                    "missing_cases": [
                        entry["missing_cases"] for entry in core_ranking["rankings_by_repeat"] if entry["missing_cases"]
                    ],
                },
                "cross_jd_differential_positive": {
                    "passed": cross_jd["all_passed"],
                    "comparisons": cross_jd["comparisons"],
                },
            }
        )

    return gate_summary


def summarize_runs(
    run_results: List[EvaluationRunResult],
    suite_mode: str,
    runner_config: Dict[str, Any] | None = None,
    preflight_result: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    by_case: Dict[str, List[EvaluationRunResult]] = defaultdict(list)
    for run in run_results:
        by_case[run.case_id].append(run)

    case_summaries = {
        case_id: summarize_case_runs(runs)
        for case_id, runs in sorted(by_case.items(), key=lambda item: item[0])
    }

    failure_reason_counts = Counter()
    root_cause_counts = Counter()
    request_error_counts = Counter()
    for run in run_results:
        if run.failure_reason:
            failure_reason_counts[run.failure_reason] += 1
        if run.request_error:
            request_error_counts[run.request_error] += 1
        for root_cause in run.root_causes:
            root_cause_counts[root_cause] += 1

    gate_summary = build_gate_summary(run_results, suite_mode=suite_mode)
    if preflight_result and not preflight_result.get("ok", True):
        gate_summary["operational_ready_for_repro"]["passed"] = False
        gate_summary["operational_ready_for_repro"]["reasons"].append("preflight checks failed")

    summary: Dict[str, Any] = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "runner_config": runner_config or {},
        "preflight_result": preflight_result or {},
        "cases": case_summaries,
        "core_ranking_table": build_core_rankings(run_results),
        "cross_jd_comparison": build_cross_jd_summary(run_results),
        "cost_summary": build_cost_summary(run_results),
        "gate_summary": gate_summary,
        "top_failure_reasons": failure_reason_counts.most_common(10),
        "top_request_errors": request_error_counts.most_common(10),
        "top_root_causes": root_cause_counts.most_common(10),
    }
    return summary


def write_evaluation_report(
    run_results: List[EvaluationRunResult],
    output_dir: str = DEFAULT_RESULTS_DIR,
    filename_prefix: str = "evaluation_report",
    runner_config: Dict[str, Any] | None = None,
    preflight_result: Dict[str, Any] | None = None,
) -> Tuple[str, str]:
    os.makedirs(output_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    suite_mode = runner_config.get("mode", "smoke") if runner_config else "smoke"
    detailed_path = os.path.join(output_dir, f"{filename_prefix}_{timestamp}.json")
    summary_path = os.path.join(output_dir, f"{filename_prefix}_{timestamp}_summary.json")
    summary = summarize_runs(
        run_results,
        suite_mode=suite_mode,
        runner_config=runner_config,
        preflight_result=preflight_result,
    )

    detailed_payload = {
        "generated_at": summary["generated_at"],
        "runner_config": runner_config or {},
        "preflight_result": preflight_result or {},
        "run_results": [run.model_dump() for run in run_results],
    }

    with open(detailed_path, "w", encoding="utf-8") as handle:
        json.dump(detailed_payload, handle, indent=2)

    with open(summary_path, "w", encoding="utf-8") as handle:
        json.dump(summary, handle, indent=2)

    return detailed_path, summary_path


def time_call(func, *args, **kwargs):
    start = time.perf_counter()
    result = func(*args, **kwargs)
    latency_ms = int((time.perf_counter() - start) * 1000)
    return result, latency_ms
