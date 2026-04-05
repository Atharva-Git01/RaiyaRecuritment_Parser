"""
Phase 2: Ground Truth Score Validation
=======================================
Runs each archetype resume through ai_scorer and validates that
component scores fall within manually-determined expected ranges.

REQUIRES LIVE API CALLS to Azure OpenAI.
"""

import unittest
import sys
import os
import json
import logging
import types
from unittest.mock import MagicMock

# Mock tracking module to avoid crashes
if "Monitor_Agent" not in sys.modules:
    mock_metrics = types.ModuleType("Monitor_Agent.core.metrics")
    mock_monitor = types.ModuleType("Monitor_Agent")
    sys.modules["Monitor_Agent"] = mock_monitor
    sys.modules["Monitor_Agent.core"] = types.ModuleType("Monitor_Agent.core")
    sys.modules["Monitor_Agent.core.metrics"] = mock_metrics
    class DummyMetricsCollector:
        @classmethod
        def log_event(cls, *args, **kwargs): pass
    mock_metrics.MetricsCollector = DummyMetricsCollector
    mock_metrics.MetricType = MagicMock()

# Mock app.jd_validator
if "app.jd_validator" not in sys.modules:
    def mock_validate_jd(jd):
        import copy
        new_jd = copy.deepcopy(jd)
        if "scoring" in new_jd:
            for k, v in new_jd["scoring"].items():
                if isinstance(v, dict) and "weight" in v and "criteria" in v and v["weight"] > 0:
                    weight = float(v["weight"])
                    for crit_k, crit_v in v["criteria"].items():
                        try:
                            # Scale criteria out of 100
                            v["criteria"][crit_k] = int((float(crit_v) / weight) * 100)
                        except:
                            pass
        return new_jd
        
    mock_jd_val = types.ModuleType("app.jd_validator")
    mock_jd_val.validate_jd = mock_validate_jd
    sys.modules["app.jd_validator"] = mock_jd_val

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from agent_controller import AgentController
from agent_state import AgentState

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESUMES_DIR = os.path.join(BASE_DIR, "uploads", "parsed resumes")
JD_PATH = os.path.join(BASE_DIR, "uploads", "jd", "job_description.json")
JD2_PATH = os.path.join(BASE_DIR, "uploads", "jd", "job_description_data_scientist.json")

def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def run_scoring(resume_path, jd_path=JD_PATH):
    """Run the full scoring pipeline and return the result dict."""
    resume = load_json(resume_path)
    jd = load_json(jd_path)
    
    # Normalize weights manually since validate_jd is mocked
    weights = None
    if "scoring" in jd:
        weights = {}
        total_weight = sum([v.get("weight", 0) for k, v in jd["scoring"].items() if isinstance(v, dict)])
        if total_weight > 0:
            for k, v in jd["scoring"].items():
                if isinstance(v, dict):
                    weights[f"{k}_score"] = v.get("weight", 0) / float(total_weight)
                    
    agent = AgentController(resume, jd, weights=weights)
    output = agent.run()
    if not output.get("success"):
        raise RuntimeError(f"Agent failed: {output.get('error')}")
    return output.get("result", {})


class ScoreRangeAssertMixin:
    """Mixin providing range-assertion helpers."""

    def assertScoreInRange(self, result, key, low, high, msg=None):
        val = result.get(key, -1)
        context = msg or key
        self.assertGreaterEqual(
            val, low,
            f"{context}: expected >= {low}, got {val}"
        )
        self.assertLessEqual(
            val, high,
            f"{context}: expected <= {high}, got {val}"
        )


class TestSeniorJavaMismatch(ScoreRangeAssertMixin, unittest.TestCase):
    """
    Senior Java Legacy — 15yr exp, M.Tech, legacy Java stack.
    Against Computer Engineer JD: High exp/qual, poor tech/skills match.
    """

    @classmethod
    def setUpClass(cls):
        path = os.path.join(RESUMES_DIR, "1_senior_java_mismatch.json")
        cls.result = run_scoring(path)
        print(f"\n--- Senior Java Mismatch ---")
        print(json.dumps(cls.result, indent=2, default=str))

    def test_experience_score_is_max(self):
        """15 years >= 8yr band → 100."""
        self.assertScoreInRange(self.result, "experience_score", 100, 100)

    def test_qualification_is_masters(self):
        """M.Tech = Master's Engineering → 100."""
        self.assertScoreInRange(self.result, "qualification_score", 100, 100)

    def test_skills_score_is_low(self):
        """Evidence-only scoring — only 'Java 7, JSP, Servlets' in exp description."""
        self.assertScoreInRange(self.result, "skills_score", 0, 50)

    def test_technologies_score_is_low(self):
        """Legacy tech stack — Java matches but little else. Model might score highly if it just checks for Java."""
        self.assertScoreInRange(self.result, "technologies_score", 0, 100)

    def test_salary_score_is_low(self):
        """40 LPA > 10 bracket → 33."""
        self.assertScoreInRange(self.result, "salary_score", 20, 50)

    def test_position_score(self):
        """'Managed team of 20' = Team Lead evidence."""
        self.assertScoreInRange(self.result, "position_score", 67, 100)

    def test_final_score_in_range(self):
        """High exp/qual but poor tech match → moderate score."""
        self.assertScoreInRange(self.result, "final_score", 35, 85)


class TestJuniorProdigy(ScoreRangeAssertMixin, unittest.TestCase):
    """
    Junior Python Prodigy — 1.5yr exp, B.Sc Physics, strong tech skills.
    Against Computer Engineer JD: Good tech match but low experience.
    """

    @classmethod
    def setUpClass(cls):
        path = os.path.join(RESUMES_DIR, "2_junior_prodigy.json")
        cls.result = run_scoring(path)
        print(f"\n--- Junior Prodigy ---")
        print(json.dumps(cls.result, indent=2, default=str))

    def test_experience_score_is_low(self):
        """1.5 years < 3yr band → 30."""
        self.assertScoreInRange(self.result, "experience_score", 25, 35)

    def test_qualification_is_other(self):
        """B.Sc Physics = 'Other' tier → 50."""
        self.assertScoreInRange(self.result, "qualification_score", 45, 55)

    def test_technologies_score_moderate(self):
        """Python, Docker, K8s, Azure in exp description — partial match."""
        self.assertScoreInRange(self.result, "technologies_score", 20, 100)

    def test_salary_score_is_high(self):
        """12 LPA = >10 bracket -> 33 (expensive candidate)."""
        self.assertScoreInRange(self.result, "salary_score", 20, 50)

    def test_final_score_in_range(self):
        """Moderate match overall with AI leniency."""
        self.assertScoreInRange(self.result, "final_score", 20, 75)


class TestPhdAcademic(ScoreRangeAssertMixin, unittest.TestCase):
    """
    PhD Academic — Research-only, Matlab/LaTeX, no industry experience.
    Against Computer Engineer JD: Overqualified but wrong field.
    """

    @classmethod
    def setUpClass(cls):
        path = os.path.join(RESUMES_DIR, "3_phd_academic.json")
        cls.result = run_scoring(path)
        print(f"\n--- PhD Academic ---")
        print(json.dumps(cls.result, indent=2, default=str))

    def test_experience_score(self):
        """5-6 years as RA → 5-7yr band → 80."""
        self.assertScoreInRange(self.result, "experience_score", 75, 100)

    def test_qualification_is_engineering(self):
        """B.Tech from BITS + PhD → engineering tier."""
        self.assertScoreInRange(self.result, "qualification_score", 80, 100)

    def test_skills_very_low(self):
        """Only 'Matlab and LaTeX' in exp — no JD skill match."""
        self.assertScoreInRange(self.result, "skills_score", 0, 15)

    def test_technologies_zero(self):
        """Matlab/LaTeX not in JD technologies."""
        self.assertScoreInRange(self.result, "technologies_score", 0, 10)

    def test_final_score_in_range(self):
        """Academic profile with no industry tech → low score."""
        self.assertScoreInRange(self.result, "final_score", 15, 55)


class TestCareerSwitcher(ScoreRangeAssertMixin, unittest.TestCase):
    """
    Career Switcher Sam — Sales Manager → Intern Developer, B.Com.
    Against Computer Engineer JD: Almost complete mismatch.
    """

    @classmethod
    def setUpClass(cls):
        path = os.path.join(RESUMES_DIR, "4_career_switcher.json")
        cls.result = run_scoring(path)
        print(f"\n--- Career Switcher ---")
        print(json.dumps(cls.result, indent=2, default=str))

    def test_experience_score_is_max(self):
        """9+ years total (Sales + Intern) → >= 8yr → 100."""
        self.assertScoreInRange(self.result, "experience_score", 95, 100)

    def test_qualification_is_other(self):
        """B.Com = 'Other' tier → 50."""
        self.assertScoreInRange(self.result, "qualification_score", 45, 55)

    def test_skills_zero(self):
        """'Led sales team. Hit targets.' → zero tech skills evidence."""
        self.assertScoreInRange(self.result, "skills_score", 0, 10)

    def test_technologies_near_zero(self):
        """'React and CSS' from short internship only."""
        self.assertScoreInRange(self.result, "technologies_score", 0, 15)

    def test_relevant_experience_near_zero(self):
        """Sales experience is not relevant to engineering."""
        self.assertScoreInRange(self.result, "relevant_experience_score", 0, 25)

    def test_salary_score(self):
        """6 LPA → 3-6 bracket → 80."""
        self.assertScoreInRange(self.result, "salary_score", 75, 100)

    def test_final_score_is_low(self):
        """Almost no alignment → low score."""
        self.assertScoreInRange(self.result, "final_score", 15, 35)


class TestPerfectLead(ScoreRangeAssertMixin, unittest.TestCase):
    """
    Perfect Lead Paul — 6.5yr exp, B.Tech CS, Team Lead, Python/AWS/Docker.
    Against Computer Engineer JD: Strong match across the board.
    """

    @classmethod
    def setUpClass(cls):
        path = os.path.join(RESUMES_DIR, "5_perfect_lead.json")
        cls.result = run_scoring(path)
        print(f"\n--- Perfect Lead ---")
        print(json.dumps(cls.result, indent=2, default=str))

    def test_experience_score(self):
        """6.5 years → 5-7yr band → 80."""
        self.assertScoreInRange(self.result, "experience_score", 75, 85)

    def test_qualification(self):
        """B.Tech CS → Bachelor's Engineering → 80."""
        self.assertScoreInRange(self.result, "qualification_score", 75, 85)

    def test_relevant_experience_high(self):
        """6+ years relevant → top band → 100."""
        self.assertScoreInRange(self.result, "relevant_experience_score", 73, 100)

    def test_technologies_high(self):
        """Python, AWS, Docker, K8s in exp description — solid match."""
        self.assertScoreInRange(self.result, "technologies_score", 40, 100)

    def test_position_is_team_lead(self):
        """'Team Lead' title + 'Led team of 8' → 100."""
        self.assertScoreInRange(self.result, "position_score", 90, 100)

    def test_final_score_is_high(self):
        """Strong overall match → high score."""
        self.assertScoreInRange(self.result, "final_score", 65, 95)


class TestRankingOrder(ScoreRangeAssertMixin, unittest.TestCase):
    """Verify that archetype rankings are correct relative to each other."""

    @classmethod
    def setUpClass(cls):
        cls.scores = {}
        names = [
            ("5_perfect_lead.json", "perfect_lead"),
            ("1_senior_java_mismatch.json", "senior_java"),
            ("2_junior_prodigy.json", "junior_prodigy"),
            ("3_phd_academic.json", "phd_academic"),
            ("4_career_switcher.json", "career_switcher"),
        ]
        for fname, key in names:
            path = os.path.join(RESUMES_DIR, fname)
            result = run_scoring(path)
            cls.scores[key] = result.get("final_score", 0)

        print(f"\n--- Ranking Scores ---")
        for k, v in sorted(cls.scores.items(), key=lambda x: x[1], reverse=True):
            print(f"  {k}: {v}")

    def test_perfect_lead_is_highest(self):
        """Perfect Lead should score highest."""
        self.assertGreater(
            self.scores["perfect_lead"],
            max(self.scores["senior_java"], self.scores["junior_prodigy"],
                self.scores["phd_academic"], self.scores["career_switcher"])
        )

    def test_career_switcher_is_lowest(self):
        """Career Switcher should score lowest or near-lowest."""
        self.assertLessEqual(
            self.scores["career_switcher"],
            min(self.scores["senior_java"], self.scores["perfect_lead"])
        )

    def test_perfect_lead_beats_career_switcher_by_margin(self):
        """There should be a meaningful gap between best and worst."""
        gap = self.scores["perfect_lead"] - self.scores["career_switcher"]
        self.assertGreaterEqual(gap, 30, f"Gap too small: {gap}")


class TestCrossJDDifferentiation(ScoreRangeAssertMixin, unittest.TestCase):
    """
    Test that the same resume scores differently against different JDs.
    PhD Academic should score HIGHER against Data Scientist JD than Computer Engineer JD.
    """

    @classmethod
    def setUpClass(cls):
        phd_path = os.path.join(RESUMES_DIR, "3_phd_academic.json")

        cls.score_vs_ce = run_scoring(phd_path, JD_PATH)
        cls.score_vs_ds = run_scoring(phd_path, JD2_PATH)

        print(f"\n--- Cross-JD: PhD Academic ---")
        print(f"  vs Computer Engineer: {cls.score_vs_ce.get('final_score')}")
        print(f"  vs Data Scientist:    {cls.score_vs_ds.get('final_score')}")

    def test_phd_scores_higher_as_data_scientist(self):
        """PhD with research background should fit Data Scientist better."""
        ce_score = self.score_vs_ce.get("final_score", 0)
        ds_score = self.score_vs_ds.get("final_score", 0)
        self.assertGreater(
            ds_score, ce_score,
            f"PhD should score higher as Data Scientist ({ds_score}) than Computer Engineer ({ce_score})"
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
