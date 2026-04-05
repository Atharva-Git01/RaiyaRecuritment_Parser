import unittest

from test_cases.evaluation_harness import (
    CORE_ARCHETYPE_ORDER,
    build_core_rankings,
    build_cross_jd_summary,
    build_gate_summary,
    evaluate_result_payload,
    extract_candidate_name,
    infer_root_causes,
    summarize_runs,
    validate_evidence_expectations,
    validate_operational_quality,
    validate_output_quality,
)
from test_cases.evaluation_schemas import BenchmarkCase, EvaluationRunResult


class TestValidationHarness(unittest.TestCase):
    def test_extract_candidate_name_supports_nested_personal_info(self):
        self.assertEqual(
            extract_candidate_name({"personal_info": {"name": "Nested Name"}}),
            "Nested Name",
        )

    def test_evidence_validator_flags_positive_scores_without_experience_text(self):
        case = BenchmarkCase.model_validate(
            {
                "case_id": "synthetic",
                "resume_path": "generated://synthetic",
                "jd_path": "uploads/jd/job_description.json",
                "case_type": "adversarial_synthetic",
                "expected_final_band": {"min": 0, "max": 100},
                "expected_component_bands": {},
                "expected_rank_bucket": "any",
                "must_match_evidence": [],
                "must_not_match_evidence": [
                    {
                        "score_key": "technologies_score",
                        "required_terms": [],
                        "forbidden_terms": ["Python", "AWS"],
                    }
                ],
                "expected_overrides": [],
                "review_owner": "engineering",
                "review_status": "draft",
                "notes": "",
            }
        )
        failures = validate_evidence_expectations(
            case,
            {"technologies_score": 70},
            {"experience": [{"description": "Worked on many things."}]},
        )
        self.assertTrue(failures)

    def test_output_quality_flags_trace_mismatch(self):
        failures = validate_output_quality(
            {
                "skills_score": 50,
                "notes": "Looks fine",
                "guardrails_applied": [],
                "scoring_trace": {"skills": {"score_awarded": 10}},
            }
        )
        self.assertTrue(any("trace mismatch" in failure for failure in failures))

    def test_operational_quality_requires_completed_state_for_success(self):
        failures = validate_operational_quality(
            {"success": True, "current_state": "SCORING", "result": {}}
        )
        self.assertTrue(failures)

    def test_evaluation_payload_contains_failures_and_root_causes(self):
        case = BenchmarkCase.model_validate(
            {
                "case_id": "synthetic",
                "resume_path": "generated://synthetic",
                "jd_path": "uploads/jd/job_description.json",
                "case_type": "adversarial_synthetic",
                "expected_final_band": {"min": 0, "max": 10},
                "expected_component_bands": {},
                "expected_rank_bucket": "bottom",
                "must_match_evidence": [],
                "must_not_match_evidence": [],
                "expected_overrides": [],
                "review_owner": "engineering",
                "review_status": "draft",
                "notes": "",
            }
        )
        evaluation = evaluate_result_payload(
            case=case,
            output={
                "success": True,
                "current_state": "COMPLETED",
                "inputs": {"resume": {"personal_info": {"name": "Test"}}},
                "result": {
                    "final_score": 55,
                    "notes": "Too high",
                    "guardrails_applied": [],
                    "scoring_trace": {},
                },
                "token_usage": {"total_tokens": 10},
            },
            latency_ms=42,
            deployment="test",
            prompt_version="v1",
            suite_mode="smoke",
            suite_batch_id="batch",
            repeat_index=1,
            scope="all",
        )
        self.assertEqual(evaluation.pass_fail, "fail")
        self.assertEqual(evaluation.request_status, "ok")
        self.assertTrue(evaluation.failure_reason)
        self.assertTrue(evaluation.root_causes)

    def test_request_errors_are_not_misclassified_as_benchmark_failures(self):
        case = BenchmarkCase.model_validate(
            {
                "case_id": "synthetic",
                "resume_path": "generated://synthetic",
                "jd_path": "uploads/jd/job_description.json",
                "case_type": "adversarial_synthetic",
                "expected_final_band": {"min": 0, "max": 10},
                "expected_component_bands": {},
                "expected_rank_bucket": "bottom",
                "must_match_evidence": [],
                "must_not_match_evidence": [],
                "expected_overrides": [],
                "review_owner": "engineering",
                "review_status": "draft",
                "notes": "",
            }
        )
        evaluation = evaluate_result_payload(
            case=case,
            output={"success": False, "error": "AI request failed after 3 attempts. Last error: timeout"},
            latency_ms=42,
            deployment="test",
            prompt_version="v1",
            suite_mode="smoke",
            suite_batch_id="batch",
            repeat_index=1,
            scope="all",
        )
        self.assertEqual(evaluation.pass_fail, "error")
        self.assertEqual(evaluation.request_status, "request_error")
        self.assertTrue(evaluation.request_error)
        self.assertEqual(evaluation.failure_reason, "")

    def test_root_cause_inference_covers_observability_and_overrides(self):
        root_causes = infer_root_causes(
            [
                "salary_score=90 outside expected band 0-40",
                "output is not JSON-serializable: boom",
            ]
        )
        self.assertIn("override_bug", root_causes)
        self.assertIn("observability_gap", root_causes)

    def test_build_core_rankings_detects_pairwise_inversion(self):
        runs = []
        for repeat_index, scores in [(1, [10, 20, 5, 4, 3])]:
            for case_id, score in zip(CORE_ARCHETYPE_ORDER, scores):
                runs.append(
                    EvaluationRunResult(
                        run_id=f"{case_id}-{repeat_index}",
                        timestamp="2026-04-05T00:00:00+00:00",
                        deployment="test",
                        prompt_version="v1",
                        case_id=case_id,
                        suite_mode="repro",
                        suite_batch_id="batch",
                        repeat_index=repeat_index,
                        scope="core",
                        request_status="ok",
                        request_error="",
                        scores={"final_score": score},
                        scoring_trace={},
                        guardrails_applied=[],
                        overrides_fired=[],
                        latency_ms=1,
                        token_usage={"total_tokens": 1},
                        pass_fail="pass",
                        failure_reason="",
                        raw_result_path="exists.json",
                        root_causes=[],
                    )
                )
        ranking = build_core_rankings(runs)
        self.assertGreater(ranking["inversion_count"], 0)

    def test_cross_jd_summary_requires_ds_to_beat_ce_per_repeat(self):
        runs = [
            EvaluationRunResult(
                run_id="ce",
                timestamp="2026-04-05T00:00:00+00:00",
                deployment="test",
                prompt_version="v1",
                case_id="3_phd_academic_ce",
                suite_mode="repro",
                suite_batch_id="batch",
                repeat_index=1,
                scope="all",
                request_status="ok",
                request_error="",
                scores={"final_score": 40},
                scoring_trace={},
                guardrails_applied=[],
                overrides_fired=[],
                latency_ms=1,
                token_usage={"total_tokens": 1},
                pass_fail="pass",
                failure_reason="",
                raw_result_path="ce.json",
                root_causes=[],
            ),
            EvaluationRunResult(
                run_id="ds",
                timestamp="2026-04-05T00:00:00+00:00",
                deployment="test",
                prompt_version="v1",
                case_id="3_phd_academic_ds",
                suite_mode="repro",
                suite_batch_id="batch",
                repeat_index=1,
                scope="all",
                request_status="ok",
                request_error="",
                scores={"final_score": 55},
                scoring_trace={},
                guardrails_applied=[],
                overrides_fired=[],
                latency_ms=1,
                token_usage={"total_tokens": 1},
                pass_fail="pass",
                failure_reason="",
                raw_result_path="ds.json",
                root_causes=[],
            ),
        ]
        summary = build_cross_jd_summary(runs)
        self.assertTrue(summary["all_passed"])

    def test_repro_gate_summary_uses_drift_and_request_gates(self):
        runs = []
        for repeat_index, base_score in [(1, 80), (2, 83), (3, 81), (4, 82), (5, 81)]:
            for case_id in CORE_ARCHETYPE_ORDER:
                runs.append(
                    EvaluationRunResult(
                        run_id=f"{case_id}-{repeat_index}",
                        timestamp="2026-04-05T00:00:00+00:00",
                        deployment="test",
                        prompt_version="v1",
                        case_id=case_id,
                        suite_mode="repro",
                        suite_batch_id="batch",
                        repeat_index=repeat_index,
                        scope="all",
                        request_status="ok",
                        request_error="",
                        scores={
                            "final_score": base_score - CORE_ARCHETYPE_ORDER.index(case_id) * 10,
                            "skills_score": 50,
                            "technologies_score": 50,
                            "relevant_experience_score": 50,
                            "position_score": 50,
                            "tools_score": 50,
                        },
                        scoring_trace={},
                        guardrails_applied=[],
                        overrides_fired=[],
                        latency_ms=1,
                        token_usage={"total_tokens": 1, "prompt_tokens": 1, "completion_tokens": 0},
                        pass_fail="pass",
                        failure_reason="",
                        raw_result_path=__file__,
                        root_causes=[],
                    )
                )
        runs.extend(
            [
                EvaluationRunResult(
                    run_id="ce",
                    timestamp="2026-04-05T00:00:00+00:00",
                    deployment="test",
                    prompt_version="v1",
                    case_id="3_phd_academic_ce",
                    suite_mode="repro",
                    suite_batch_id="batch",
                    repeat_index=1,
                    scope="all",
                    request_status="ok",
                    request_error="",
                    scores={"final_score": 40},
                    scoring_trace={},
                    guardrails_applied=[],
                    overrides_fired=[],
                    latency_ms=1,
                    token_usage={"total_tokens": 1, "prompt_tokens": 1, "completion_tokens": 0},
                    pass_fail="pass",
                    failure_reason="",
                    raw_result_path=__file__,
                    root_causes=[],
                ),
                EvaluationRunResult(
                    run_id="ds",
                    timestamp="2026-04-05T00:00:00+00:00",
                    deployment="test",
                    prompt_version="v1",
                    case_id="3_phd_academic_ds",
                    suite_mode="repro",
                    suite_batch_id="batch",
                    repeat_index=1,
                    scope="all",
                    request_status="ok",
                    request_error="",
                    scores={"final_score": 55},
                    scoring_trace={},
                    guardrails_applied=[],
                    overrides_fired=[],
                    latency_ms=1,
                    token_usage={"total_tokens": 1, "prompt_tokens": 1, "completion_tokens": 0},
                    pass_fail="pass",
                    failure_reason="",
                    raw_result_path=__file__,
                    root_causes=[],
                ),
            ]
        )
        gate_summary = build_gate_summary(runs, suite_mode="repro")
        self.assertTrue(gate_summary["core_final_score_drift_lte_5"]["passed"])
        self.assertTrue(gate_summary["request_error_rate_zero"]["passed"])
        self.assertTrue(gate_summary["cross_jd_differential_positive"]["passed"])

    def test_summarize_runs_marks_preflight_failures_as_not_ready(self):
        summary = summarize_runs(
            [],
            suite_mode="smoke",
            runner_config={"mode": "smoke"},
            preflight_result={"ok": False, "errors": ["missing creds"]},
        )
        self.assertFalse(summary["gate_summary"]["operational_ready_for_repro"]["passed"])


if __name__ == "__main__":
    unittest.main()
