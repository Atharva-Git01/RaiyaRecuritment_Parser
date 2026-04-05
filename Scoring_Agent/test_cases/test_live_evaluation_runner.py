import json
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from test_cases.evaluation_schemas import BenchmarkCase
from test_cases.evaluation_runner import (
    build_filename_prefix,
    filter_manifest_cases,
    parse_runner_args,
    preflight_live_run,
    run_manifest,
)


class TestLiveEvaluationRunner(unittest.TestCase):
    def test_parse_runner_args_uses_mode_specific_defaults(self):
        smoke_args = parse_runner_args(["--mode", "smoke"])
        repro_args = parse_runner_args(["--mode", "repro"])

        self.assertEqual(smoke_args.repeats, 1)
        self.assertEqual(repro_args.repeats, 5)
        self.assertEqual(smoke_args.scope, "all")
        self.assertEqual(smoke_args.sleep_seconds, 1.0)

    def test_filter_manifest_cases_supports_scope_and_case_filter(self):
        cases = [
            BenchmarkCase.model_validate(
                {
                    "case_id": "5_perfect_lead_ce",
                    "resume_path": "uploads/parsed resumes/5_perfect_lead.json",
                    "jd_path": "uploads/jd/job_description.json",
                    "case_type": "archetype",
                    "expected_final_band": {"min": 0, "max": 100},
                    "expected_component_bands": {},
                    "expected_rank_bucket": "top",
                    "must_match_evidence": [],
                    "must_not_match_evidence": [],
                    "expected_overrides": [],
                    "review_owner": "",
                    "review_status": "",
                    "notes": "",
                }
            ),
            BenchmarkCase.model_validate(
                {
                    "case_id": "skills_only_inflation",
                    "resume_path": "generated://skills_only_candidate",
                    "jd_path": "uploads/jd/job_description.json",
                    "case_type": "adversarial",
                    "expected_final_band": {"min": 0, "max": 100},
                    "expected_component_bands": {},
                    "expected_rank_bucket": "low",
                    "must_match_evidence": [],
                    "must_not_match_evidence": [],
                    "expected_overrides": [],
                    "review_owner": "",
                    "review_status": "",
                    "notes": "",
                }
            ),
        ]

        self.assertEqual(len(filter_manifest_cases(cases, scope="all")), 2)
        self.assertEqual(len(filter_manifest_cases(cases, scope="real")), 1)
        self.assertEqual(len(filter_manifest_cases(cases, scope="core")), 1)
        self.assertEqual(
            filter_manifest_cases(cases, scope="all", case_filter="skills")[0].case_id,
            "skills_only_inflation",
        )

    def test_preflight_detects_missing_credentials(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch("test_cases.evaluation_runner.AZURE_AI_ENDPOINT", ""), patch(
                "test_cases.evaluation_runner.API_KEY", ""
            ), patch("test_cases.evaluation_runner.DEPLOYMENT_ID", ""):
                result = preflight_live_run(temp_dir)
        self.assertFalse(result["ok"])
        self.assertTrue(result["missing_credentials"])

    def test_preflight_warns_but_does_not_fail_on_env_parse_issues_if_creds_exist(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch("test_cases.evaluation_runner.inspect_env_file", return_value=["bad line"]), patch(
                "test_cases.evaluation_runner.AZURE_AI_ENDPOINT", "https://example"
            ), patch("test_cases.evaluation_runner.API_KEY", "key"), patch(
                "test_cases.evaluation_runner.DEPLOYMENT_ID", "deployment"
            ):
                result = preflight_live_run(temp_dir)
        self.assertTrue(result["ok"])
        self.assertTrue(result["warnings"])

    def test_build_filename_prefix_supports_optional_tag(self):
        self.assertEqual(build_filename_prefix("smoke"), "azure_smoke")
        self.assertEqual(build_filename_prefix("repro", "nightly"), "azure_repro_nightly")

    def test_smoke_mode_writes_reports_and_marks_request_failures_as_not_ready(self):
        cases = [
            BenchmarkCase.model_validate(
                {
                    "case_id": "5_perfect_lead_ce",
                    "resume_path": "generated://minimal_resume",
                    "jd_path": "uploads/jd/job_description.json",
                    "case_type": "archetype",
                    "expected_final_band": {"min": 0, "max": 100},
                    "expected_component_bands": {},
                    "expected_rank_bucket": "top",
                    "must_match_evidence": [],
                    "must_not_match_evidence": [],
                    "expected_overrides": [],
                    "review_owner": "",
                    "review_status": "",
                    "notes": "",
                }
            ),
            BenchmarkCase.model_validate(
                {
                    "case_id": "1_senior_java_mismatch_ce",
                    "resume_path": "generated://minimal_resume",
                    "jd_path": "uploads/jd/job_description.json",
                    "case_type": "archetype",
                    "expected_final_band": {"min": 0, "max": 100},
                    "expected_component_bands": {},
                    "expected_rank_bucket": "middle",
                    "must_match_evidence": [],
                    "must_not_match_evidence": [],
                    "expected_overrides": [],
                    "review_owner": "",
                    "review_status": "",
                    "notes": "",
                }
            ),
        ]
        outputs = [
            (
                {
                    "success": True,
                    "current_state": "COMPLETED",
                    "inputs": {"resume": {"personal_info": {"name": "Case 1"}}},
                    "result": {"final_score": 10, "notes": "", "guardrails_applied": [], "scoring_trace": {}},
                    "token_usage": {"total_tokens": 10, "prompt_tokens": 5, "completion_tokens": 5},
                },
                100,
            ),
            (
                {
                    "success": False,
                    "error": "AI request failed after 3 attempts. Last error: timeout",
                },
                120,
            ),
        ]

        def fake_time_call(*args, **kwargs):
            return outputs.pop(0)

        with tempfile.TemporaryDirectory() as temp_dir, patch(
            "test_cases.evaluation_runner.load_benchmark_manifest",
            return_value=cases,
        ), patch(
            "test_cases.evaluation_runner.preflight_live_run",
            return_value={"ok": True, "warnings": [], "errors": [], "deployment": "dep", "prompt_version": "v1"},
        ), patch(
            "test_cases.evaluation_runner.resolve_case_input",
            return_value={"personal_info": {"name": "Fixture"}},
        ), patch(
            "test_cases.evaluation_runner.AgentController",
            return_value=SimpleNamespace(run=lambda: None),
        ), patch(
            "test_cases.evaluation_runner.time_call",
            side_effect=fake_time_call,
        ):
            result = run_manifest(mode="smoke", repeats=1, output_dir=temp_dir, sleep_seconds=0)
            with open(result["summary_path"], "r", encoding="utf-8") as handle:
                summary = json.load(handle)

        self.assertFalse(summary["gate_summary"]["operational_ready_for_repro"]["passed"])
        self.assertEqual(summary["runner_config"]["mode"], "smoke")
        self.assertEqual(summary["runner_config"]["selected_cases_count"], 2)
        self.assertTrue(result["run_results"])

    def test_repro_mode_writes_grouped_repeat_outputs(self):
        cases = [
            BenchmarkCase.model_validate(
                {
                    "case_id": "5_perfect_lead_ce",
                    "resume_path": "generated://minimal_resume",
                    "jd_path": "uploads/jd/job_description.json",
                    "case_type": "archetype",
                    "expected_final_band": {"min": 0, "max": 100},
                    "expected_component_bands": {},
                    "expected_rank_bucket": "top",
                    "must_match_evidence": [],
                    "must_not_match_evidence": [],
                    "expected_overrides": [],
                    "review_owner": "",
                    "review_status": "",
                    "notes": "",
                }
            )
        ]
        outputs = [
            (
                {
                    "success": True,
                    "current_state": "COMPLETED",
                    "inputs": {"resume": {"personal_info": {"name": "Case 1"}}},
                    "result": {
                        "final_score": 80,
                        "skills_score": 50,
                        "technologies_score": 50,
                        "relevant_experience_score": 50,
                        "position_score": 50,
                        "tools_score": 50,
                        "notes": "",
                        "guardrails_applied": [],
                        "scoring_trace": {},
                    },
                    "token_usage": {"total_tokens": 10, "prompt_tokens": 5, "completion_tokens": 5},
                },
                100,
            )
            for _ in range(5)
        ]

        def fake_time_call(*args, **kwargs):
            return outputs.pop(0)

        with tempfile.TemporaryDirectory() as temp_dir, patch(
            "test_cases.evaluation_runner.load_benchmark_manifest",
            return_value=cases,
        ), patch(
            "test_cases.evaluation_runner.preflight_live_run",
            return_value={"ok": True, "warnings": [], "errors": [], "deployment": "dep", "prompt_version": "v1"},
        ), patch(
            "test_cases.evaluation_runner.resolve_case_input",
            return_value={"personal_info": {"name": "Fixture"}},
        ), patch(
            "test_cases.evaluation_runner.AgentController",
            return_value=SimpleNamespace(run=lambda: None),
        ), patch(
            "test_cases.evaluation_runner.time_call",
            side_effect=fake_time_call,
        ):
            result = run_manifest(mode="repro", repeats=5, output_dir=temp_dir, sleep_seconds=0, scope="core")
            with open(result["summary_path"], "r", encoding="utf-8") as handle:
                summary = json.load(handle)

        self.assertEqual(len(result["run_results"]), 5)
        self.assertEqual(summary["runner_config"]["mode"], "repro")
        self.assertEqual(summary["cases"]["5_perfect_lead_ce"]["run_count"], 5)


if __name__ == "__main__":
    unittest.main()
