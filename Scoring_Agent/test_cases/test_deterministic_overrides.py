"""
Phase 3: Deterministic Override Unit Tests
==========================================
Tests each deterministic function in ai_scorer.py in isolation.
NO API calls — pure Python logic testing.
"""

import unittest
import sys
import os
import datetime
import types
from unittest.mock import patch, MagicMock

# Fix Windows console encoding
os.environ["PYTHONIOENCODING"] = "utf-8"

# Ensure import path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Mock Monitor_Agent before importing ai_scorer (it may not exist in test env)
mock_monitor = types.ModuleType("Monitor_Agent")
mock_metrics = types.ModuleType("Monitor_Agent.metrics_collector")
mock_metrics.log_token_usage = MagicMock()
mock_metrics.log_latency = MagicMock()
mock_metrics.MetricsCollector = MagicMock()
mock_metrics.MetricType = MagicMock()
mock_monitor.metrics_collector = mock_metrics
sys.modules["Monitor_Agent"] = mock_monitor
sys.modules["Monitor_Agent.metrics_collector"] = mock_metrics

from ai_scorer import (
    _clamp_and_int,
    _compute_weighted_final,
    _extract_json_from_text,
    _calculate_total_years,
    _scale_criteria_dict,
)
from app.scoring_contracts import ScoringWeights


class TestClampAndInt(unittest.TestCase):
    """Test _clamp_and_int — coerce any value to int 0-100."""

    def test_normal_int(self):
        self.assertEqual(_clamp_and_int(50), 50)

    def test_float_rounds(self):
        self.assertEqual(_clamp_and_int(55.7), 56)
        self.assertEqual(_clamp_and_int(55.4), 55)

    def test_clamp_above_100(self):
        self.assertEqual(_clamp_and_int(150), 100)
        self.assertEqual(_clamp_and_int(999), 100)

    def test_clamp_below_0(self):
        self.assertEqual(_clamp_and_int(-10), 0)
        self.assertEqual(_clamp_and_int(-0.5), 0)

    def test_string_garbage(self):
        self.assertEqual(_clamp_and_int("garbage"), 0)

    def test_none(self):
        self.assertEqual(_clamp_and_int(None), 0)

    def test_string_number(self):
        self.assertEqual(_clamp_and_int("75"), 75)

    def test_zero(self):
        self.assertEqual(_clamp_and_int(0), 0)

    def test_hundred(self):
        self.assertEqual(_clamp_and_int(100), 100)


class TestComputeWeightedFinal(unittest.TestCase):
    """Test _compute_weighted_final — weighted sum of component scores."""

    def test_all_100_with_full_weights(self):
        """With all scores at 100 and weights summing to 1.0, final should be 100."""
        scores = {
            "skills_score": 100,
            "experience_score": 100,
            "relevant_experience_score": 100,
            "projects_score": 100,
            "certificates_score": 100,
            "tools_score": 100,
            "technologies_score": 100,
            "qualification_score": 100,
            "responsibilities_score": 100,
            "salary_score": 100,
            "position_score": 100,
        }
        # Weights that sum to 1.0 (matching JD)
        weights = ScoringWeights(
            skills_score=0.1,
            experience_score=0.1,
            relevant_experience_score=0.3,
            projects_score=0.0,
            certificates_score=0.0,
            tools_score=0.02,
            technologies_score=0.2,
            qualification_score=0.1,
            responsibilities_score=0.0,
            salary_score=0.15,
            position_score=0.03,
        )
        result = _compute_weighted_final(scores, weights)
        self.assertEqual(result, 100)

    def test_all_zero(self):
        scores = {k: 0 for k in [
            "skills_score", "experience_score", "relevant_experience_score",
            "projects_score", "certificates_score", "tools_score",
            "technologies_score", "qualification_score", "responsibilities_score",
            "salary_score", "position_score"
        ]}
        weights = ScoringWeights(
            skills_score=0.1, experience_score=0.1, relevant_experience_score=0.3,
            projects_score=0.0, certificates_score=0.0, tools_score=0.02,
            technologies_score=0.2, qualification_score=0.1, responsibilities_score=0.0,
            salary_score=0.15, position_score=0.03,
        )
        result = _compute_weighted_final(scores, weights)
        self.assertEqual(result, 0)

    def test_single_component(self):
        """Only skills=100 with weight 0.1 → final should be 10."""
        scores = {
            "skills_score": 100,
            "experience_score": 0,
            "relevant_experience_score": 0,
            "projects_score": 0,
            "certificates_score": 0,
            "tools_score": 0,
            "technologies_score": 0,
            "qualification_score": 0,
            "responsibilities_score": 0,
            "salary_score": 0,
            "position_score": 0,
        }
        weights = ScoringWeights(
            skills_score=0.1, experience_score=0.1, relevant_experience_score=0.3,
            projects_score=0.0, certificates_score=0.0, tools_score=0.02,
            technologies_score=0.2, qualification_score=0.1, responsibilities_score=0.0,
            salary_score=0.15, position_score=0.03,
        )
        result = _compute_weighted_final(scores, weights)
        self.assertEqual(result, 10)

    def test_ignores_final_score_key(self):
        """Ensure final_score in dict is NOT included in weighted sum."""
        scores = {
            "final_score": 999,  # should be ignored
            "skills_score": 50,
            "experience_score": 0,
            "relevant_experience_score": 0,
            "projects_score": 0,
            "certificates_score": 0,
            "tools_score": 0,
            "technologies_score": 0,
            "qualification_score": 0,
            "responsibilities_score": 0,
            "salary_score": 0,
            "position_score": 0,
        }
        weights = ScoringWeights(
            skills_score=0.1, experience_score=0.1, relevant_experience_score=0.3,
            projects_score=0.0, certificates_score=0.0, tools_score=0.02,
            technologies_score=0.2, qualification_score=0.1, responsibilities_score=0.0,
            salary_score=0.15, position_score=0.03,
        )
        result = _compute_weighted_final(scores, weights)
        self.assertEqual(result, 5)  # 50 * 0.1 = 5


class TestExtractJsonFromText(unittest.TestCase):
    """Test _extract_json_from_text — finds JSON in mixed text."""

    def test_pure_json(self):
        ok, data = _extract_json_from_text('{"score": 50}')
        self.assertTrue(ok)
        self.assertEqual(data["score"], 50)

    def test_json_in_text(self):
        ok, data = _extract_json_from_text('Here is the result: {"score": 50} done')
        self.assertTrue(ok)
        self.assertEqual(data["score"], 50)

    def test_no_json(self):
        ok, data = _extract_json_from_text("no json here")
        self.assertFalse(ok)
        self.assertIsNone(data)

    def test_empty_string(self):
        ok, data = _extract_json_from_text("")
        self.assertFalse(ok)
        self.assertIsNone(data)

    def test_none_input(self):
        ok, data = _extract_json_from_text(None)
        self.assertFalse(ok)
        self.assertIsNone(data)

    def test_markdown_wrapped(self):
        text = '```json\n{"skills_score": 80}\n```'
        ok, data = _extract_json_from_text(text)
        self.assertTrue(ok)
        self.assertEqual(data["skills_score"], 80)


class TestCalculateTotalYears(unittest.TestCase):
    """Test _calculate_total_years — experience duration calculator."""

    def test_single_role_5_years(self):
        exp = [{"start_date": "2019-01", "end_date": "2024-01"}]
        years = _calculate_total_years(exp)
        self.assertAlmostEqual(years, 5.0, delta=0.2)

    def test_multiple_non_overlapping(self):
        exp = [
            {"start_date": "2015-01", "end_date": "2018-01"},  # 3 years
            {"start_date": "2019-01", "end_date": "2021-01"},  # 2 years
        ]
        years = _calculate_total_years(exp)
        self.assertAlmostEqual(years, 5.0, delta=0.2)

    def test_overlapping_intervals(self):
        """Two overlapping roles should not double-count."""
        exp = [
            {"start_date": "2018-01", "end_date": "2022-01"},  # 4 years
            {"start_date": "2020-01", "end_date": "2023-01"},  # 3 years, overlaps 2yr
        ]
        years = _calculate_total_years(exp)
        # Merged: 2018-01 to 2023-01 = 5 years
        self.assertAlmostEqual(years, 5.0, delta=0.2)

    def test_present_end_date(self):
        """'Present' should use current date."""
        exp = [{"start_date": "2023-01", "end_date": "Present"}]
        years = _calculate_total_years(exp)
        # Should be > 2 years from 2023-01 to now (April 2026)
        self.assertGreater(years, 2.0)
        self.assertLess(years, 5.0)

    def test_missing_start_date(self):
        exp = [{"start_date": None, "end_date": "2024-01"}]
        years = _calculate_total_years(exp)
        self.assertEqual(years, 0.0)

    def test_reversed_dates(self):
        """Start > end should be skipped."""
        exp = [{"start_date": "2024-01", "end_date": "2020-01"}]
        years = _calculate_total_years(exp)
        self.assertEqual(years, 0.0)

    def test_empty_list(self):
        self.assertEqual(_calculate_total_years([]), 0.0)

    def test_none_list(self):
        self.assertEqual(_calculate_total_years(None), 0.0)

    def test_alternative_key_names(self):
        """Test 'start'/'end' keys (alternative to 'start_date'/'end_date')."""
        exp = [{"start": "2019-01", "end": "2022-01"}]
        years = _calculate_total_years(exp)
        self.assertAlmostEqual(years, 3.0, delta=0.2)

    def test_current_as_end(self):
        """'current' should behave like 'Present'."""
        exp = [{"start_date": "2023-06", "end_date": "current"}]
        years = _calculate_total_years(exp)
        self.assertGreater(years, 1.5)


class TestScaleCriteriaDict(unittest.TestCase):
    """Test _scale_criteria_dict — normalize criteria values to 0-100."""

    def test_already_0_100(self):
        criteria = {"A": 100, "B": 80, "C": 50}
        result = _scale_criteria_dict(criteria)
        self.assertEqual(result["A"], 100)
        self.assertEqual(result["B"], 80)
        self.assertEqual(result["C"], 50)

    def test_scale_from_small(self):
        """Criteria like weight values (3, 4, 2) should be scaled up."""
        criteria = {"A": 4, "B": 3, "C": 2}
        result = _scale_criteria_dict(criteria)
        self.assertEqual(result["A"], 100)  # 4/4 * 100
        self.assertEqual(result["B"], 75)  # 3/4 * 100
        self.assertEqual(result["C"], 50)  # 2/4 * 100

    def test_empty_dict(self):
        self.assertEqual(_scale_criteria_dict({}), {})

    def test_none_input(self):
        self.assertEqual(_scale_criteria_dict(None), {})

    def test_all_zeros(self):
        criteria = {"A": 0, "B": 0}
        result = _scale_criteria_dict(criteria)
        self.assertEqual(result["A"], 0)
        self.assertEqual(result["B"], 0)


class TestExperienceBand(unittest.TestCase):
    """Test the hardcoded _exp_band logic used in ai_score_resume."""

    # The _exp_band function is defined inline (local function) inside ai_score_resume.
    # We replicate its logic here to test it.

    @staticmethod
    def _exp_band(years):
        if years >= 8:
            return 100
        if years >= 5:
            return 80
        if years >= 3:
            return 60
        return 30

    def test_10_years(self):
        self.assertEqual(self._exp_band(10.0), 100)

    def test_8_years_boundary(self):
        self.assertEqual(self._exp_band(8.0), 100)

    def test_7_9_years(self):
        self.assertEqual(self._exp_band(7.9), 80)

    def test_5_years_boundary(self):
        self.assertEqual(self._exp_band(5.0), 80)

    def test_4_9_years(self):
        self.assertEqual(self._exp_band(4.9), 60)

    def test_3_years_boundary(self):
        self.assertEqual(self._exp_band(3.0), 60)

    def test_2_9_years(self):
        self.assertEqual(self._exp_band(2.9), 30)

    def test_fresher(self):
        self.assertEqual(self._exp_band(0.5), 30)

    def test_zero(self):
        self.assertEqual(self._exp_band(0.0), 30)


class TestSalaryOverrideLogic(unittest.TestCase):
    """Test salary LPA/INR conversion and range matching logic."""

    @staticmethod
    def compute_salary_score(amount_inr, currency, jd_criteria):
        """Replicates the salary override logic from ai_scorer.py."""
        resume_lpa = None
        val = amount_inr
        curr = currency.upper() if currency else "INR"

        if val and curr == "INR":
            if val > 100000:
                resume_lpa = val / 100000.0
            elif val < 100:
                resume_lpa = val
            else:
                resume_lpa = None

        if not resume_lpa or not jd_criteria:
            return None  # No override

        best_score = 0
        for range_str, score in jd_criteria.items():
            try:
                r = range_str.replace("LPA", "").strip()
                match = False
                if r.startswith("<"):
                    limit = float(r[1:])
                    if resume_lpa < limit:
                        match = True
                elif r.startswith(">"):
                    limit = float(r[1:])
                    if resume_lpa > limit:
                        match = True
                elif "-" in r:
                    parts = r.split("-")
                    low, high = float(parts[0]), float(parts[1])
                    if low <= resume_lpa <= high:
                        match = True
                if match:
                    best_score = max(best_score, int(score))
            except Exception:
                continue

        return best_score if best_score > 0 else None

    def setUp(self):
        self.jd_criteria = {"<3": 100, "3-6": 80, "6-10": 53, ">10": 33}

    def test_low_salary_under_3(self):
        score = self.compute_salary_score(200000, "INR", self.jd_criteria)
        self.assertEqual(score, 100)  # 2 LPA < 3

    def test_mid_salary_3_to_6(self):
        score = self.compute_salary_score(500000, "INR", self.jd_criteria)
        self.assertEqual(score, 80)  # 5 LPA in 3-6

    def test_high_salary_6_to_10(self):
        score = self.compute_salary_score(800000, "INR", self.jd_criteria)
        self.assertEqual(score, 53)  # 8 LPA in 6-10

    def test_very_high_salary_above_10(self):
        score = self.compute_salary_score(1500000, "INR", self.jd_criteria)
        self.assertEqual(score, 33)  # 15 LPA > 10

    def test_null_salary(self):
        score = self.compute_salary_score(None, "INR", self.jd_criteria)
        self.assertIsNone(score)  # No override

    def test_zero_salary(self):
        score = self.compute_salary_score(0, "INR", self.jd_criteria)
        self.assertIsNone(score)  # No override

    def test_boundary_3_lpa(self):
        score = self.compute_salary_score(300000, "INR", self.jd_criteria)
        # 3 LPA — matches both "<3" (no, 3 is not < 3) and "3-6" (yes, 3 >= 3 and 3 <= 6)
        self.assertEqual(score, 80)

    def test_boundary_10_lpa(self):
        score = self.compute_salary_score(1000000, "INR", self.jd_criteria)
        # 10 LPA — matches "6-10" (yes, 10 <= 10) but not ">10" (no, 10 is not > 10)
        self.assertEqual(score, 53)


class TestQualificationOverrideLogic(unittest.TestCase):
    """Test qualification degree classification logic."""

    ENGINEERING_KEYWORDS = [
        "b.tech", "btech", "b.e", "be ", "m.tech", "mtech", "m.e", "me ",
        "bachelor of technology", "bachelor of engineering",
        "master of technology", "master of engineering",
    ]
    MASTERS_ENGINEERING = [
        "m.tech", "mtech", "m.e", "master of technology", "master of engineering"
    ]
    OTHER_KEYWORDS = [
        "bca", "mca", "b.sc", "bsc", "b.a", "ba ", "b.com",
        "bachelor of computer application", "master of computer application",
        "bachelor of science", "master of science",
    ]

    def classify(self, degree_str):
        """Replicates qualification override logic from ai_scorer.py."""
        all_degrees = degree_str.lower()
        is_engineering = any(kw in all_degrees for kw in self.ENGINEERING_KEYWORDS)
        is_masters_eng = any(kw in all_degrees for kw in self.MASTERS_ENGINEERING)
        is_other = any(kw in all_degrees for kw in self.OTHER_KEYWORDS)

        if is_other and not is_engineering:
            return 50  # Other tier
        elif is_engineering and is_masters_eng:
            return 100  # Master's Engineering
        elif is_engineering:
            return 80  # Bachelor's Engineering
        return None  # No override (unknown degree)

    def test_btech_cs(self):
        self.assertEqual(self.classify("B.Tech Computer Science"), 80)

    def test_mtech_cs(self):
        self.assertEqual(self.classify("M.Tech Computer Science"), 100)

    def test_bca(self):
        self.assertEqual(self.classify("BCA Information Technology"), 50)

    def test_bsc_physics(self):
        self.assertEqual(self.classify("B.Sc Physics"), 50)

    def test_bcom(self):
        self.assertEqual(self.classify("B.Com Commerce"), 50)

    def test_be_electronics(self):
        self.assertEqual(self.classify("B.E. Electronics"), 80)

    def test_mca(self):
        self.assertEqual(self.classify("MCA Computer Applications"), 50)

    def test_phd(self):
        """PhD alone shouldn't match engineering keywords."""
        result = self.classify("Ph.D. Computer Science")
        self.assertIsNone(result)  # No engineering or other keyword match


class TestFresherGuardrailLogic(unittest.TestCase):
    """Test the <1 year experience guardrail."""

    def apply_fresher_guardrail(self, total_years, exp_score, rel_exp_score):
        """Replicates fresher guardrail from ai_scorer.py."""
        if total_years < 1.0:
            exp_score = min(exp_score, 25)
            rel_exp_score = min(rel_exp_score, 25)
            return exp_score, rel_exp_score, True
        return exp_score, rel_exp_score, False

    def test_half_year_caps(self):
        exp, rel, fired = self.apply_fresher_guardrail(0.5, 80, 73)
        self.assertEqual(exp, 25)
        self.assertEqual(rel, 25)
        self.assertTrue(fired)

    def test_0_9_years_caps(self):
        exp, rel, fired = self.apply_fresher_guardrail(0.9, 60, 50)
        self.assertEqual(exp, 25)
        self.assertEqual(rel, 25)
        self.assertTrue(fired)

    def test_1_year_no_cap(self):
        exp, rel, fired = self.apply_fresher_guardrail(1.0, 60, 50)
        self.assertEqual(exp, 60)
        self.assertEqual(rel, 50)
        self.assertFalse(fired)

    def test_3_years_no_cap(self):
        exp, rel, fired = self.apply_fresher_guardrail(3.0, 80, 73)
        self.assertEqual(exp, 80)
        self.assertEqual(rel, 73)
        self.assertFalse(fired)

    def test_already_below_25(self):
        """If scores already below 25, should keep them as-is."""
        exp, rel, fired = self.apply_fresher_guardrail(0.5, 10, 5)
        self.assertEqual(exp, 10)
        self.assertEqual(rel, 5)
        self.assertTrue(fired)


if __name__ == "__main__":
    unittest.main(verbosity=2)
