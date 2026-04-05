import json
import os
import unittest

from app.runtime_paths import get_jd_dir, get_resume_dir, list_resume_files, resolve_jd_path, resolve_resume_path
from test_cases.evaluation_harness import validate_operational_quality


class TestOperationalQualitySuite(unittest.TestCase):
    def test_runtime_path_helpers_match_current_repo_layout(self):
        self.assertTrue(os.path.isdir(get_resume_dir()))
        self.assertTrue(os.path.isdir(get_jd_dir()))
        self.assertTrue(resolve_resume_path("5_perfect_lead.json").endswith("5_perfect_lead.json"))
        self.assertTrue(resolve_jd_path("job_description.json").endswith("job_description.json"))
        self.assertTrue(any(path.endswith(".json") for path in list_resume_files()))

    def test_existing_result_payload_is_json_and_terminal(self):
        result_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "results",
            "score_5_perfect_lead_20260304_154606.json",
        )
        with open(result_path, "r", encoding="utf-8") as handle:
            payload = json.load(handle)
        failures = validate_operational_quality(payload)
        self.assertFalse(failures)


if __name__ == "__main__":
    unittest.main()
