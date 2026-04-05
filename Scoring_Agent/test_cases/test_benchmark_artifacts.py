import os
import unittest

from test_cases.evaluation_harness import (
    BASE_DIR,
    load_baseline_snapshot,
    load_benchmark_manifest,
    load_manual_review_rubrics,
)
from test_cases.evaluation_schemas import ROOT_CAUSE_TAXONOMY


class TestBenchmarkArtifacts(unittest.TestCase):
    def test_manifest_is_present_and_covers_required_case_shapes(self):
        cases = load_benchmark_manifest()
        self.assertGreaterEqual(len(cases), 16)

        adversarial_cases = [case for case in cases if case.case_type.startswith("adversarial_")]
        self.assertGreaterEqual(len(adversarial_cases), 10)

        case_types = {case.case_type for case in cases}
        self.assertIn("cross_jd_differentiation", case_types)
        self.assertIn("archetype_strong_match", case_types)

    def test_manifest_file_paths_are_resolvable(self):
        cases = load_benchmark_manifest()
        for case in cases:
            if case.resume_path.startswith("generated://"):
                continue
            resume_path = os.path.join(BASE_DIR, case.resume_path)
            jd_path = os.path.join(BASE_DIR, case.jd_path)
            self.assertTrue(os.path.exists(resume_path), resume_path)
            self.assertTrue(os.path.exists(jd_path), jd_path)

    def test_manual_review_rubrics_cover_every_case(self):
        cases = load_benchmark_manifest()
        rubrics = load_manual_review_rubrics()
        rubric_case_ids = {rubric.case_id for rubric in rubrics}
        self.assertEqual({case.case_id for case in cases}, rubric_case_ids)

    def test_baseline_snapshot_preserves_current_failures(self):
        baseline = load_baseline_snapshot()
        known = baseline["known_regressions"]
        self.assertGreaterEqual(known["ranking_inversions"], 1)
        self.assertGreaterEqual(known["max_final_score_drift"], 5)
        self.assertGreaterEqual(known["ground_truth_failures"], 1)

    def test_root_cause_taxonomy_contains_expected_labels(self):
        expected = {
            "prompt_issue",
            "override_bug",
            "jd_normalization_issue",
            "evidence_extraction_gap",
            "guardrail_gap",
            "observability_gap",
            "entrypoint_bug",
            "test_expectation_wrong",
        }
        self.assertEqual(expected, set(ROOT_CAUSE_TAXONOMY))


if __name__ == "__main__":
    unittest.main()
