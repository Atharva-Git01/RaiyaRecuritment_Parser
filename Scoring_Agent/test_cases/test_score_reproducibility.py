"""
Phase 4: Reproducibility Testing
=================================
Runs each archetype resume 3x and verifies:
  1. final_score variance <= 5 points
  2. Component score variance <= 10 points
  3. Deterministic overrides produce identical results
  4. Ranking order is preserved across runs

REQUIRES LIVE API CALLS to Azure OpenAI.
"""

import unittest
import sys
import os
import json
import statistics
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

NUM_RUNS = 3
FINAL_SCORE_TOLERANCE = 5
COMPONENT_TOLERANCE = 10

# Components that are deterministically overridden (should be exactly equal across runs)
DETERMINISTIC_COMPONENTS = [
    "experience_score",
    "qualification_score",
    "salary_score",
]

# Components where AI variance is expected
AI_COMPONENTS = [
    "skills_score",
    "technologies_score",
    "relevant_experience_score",
    "position_score",
    "tools_score",
]

ARCHETYPES = [
    ("5_perfect_lead.json", "Perfect Lead"),
    ("1_senior_java_mismatch.json", "Senior Java"),
    ("2_junior_prodigy.json", "Junior Prodigy"),
    ("3_phd_academic.json", "PhD Academic"),
    ("4_career_switcher.json", "Career Switcher"),
]

def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def run_scoring(resume_path):
    resume = load_json(resume_path)
    jd = load_json(JD_PATH)

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


class TestReproducibility(unittest.TestCase):
    """Run each archetype NUM_RUNS times and check variance."""

    @classmethod
    def setUpClass(cls):
        cls.all_runs = {}

        for fname, label in ARCHETYPES:
            path = os.path.join(RESUMES_DIR, fname)
            runs = []
            print(f"\n🔁 Running {label} x{NUM_RUNS}...")

            for i in range(NUM_RUNS):
                result = run_scoring(path)
                runs.append(result)
                print(f"  Run {i+1}: final_score = {result.get('final_score')}")

            cls.all_runs[label] = runs

    def _get_scores(self, label, key):
        return [r.get(key, 0) for r in self.all_runs[label]]

    def test_final_score_variance(self):
        """Final score variance should be <= FINAL_SCORE_TOLERANCE for each archetype."""
        for label in [l for _, l in ARCHETYPES]:
            scores = self._get_scores(label, "final_score")
            drift = max(scores) - min(scores)
            self.assertLessEqual(
                drift, FINAL_SCORE_TOLERANCE,
                f"{label}: final_score drift = {drift} (max: {FINAL_SCORE_TOLERANCE}), scores: {scores}"
            )

    def test_component_score_variance(self):
        """Each AI component should have variance <= COMPONENT_TOLERANCE."""
        for label in [l for _, l in ARCHETYPES]:
            for key in AI_COMPONENTS:
                scores = self._get_scores(label, key)
                drift = max(scores) - min(scores)
                self.assertLessEqual(
                    drift, COMPONENT_TOLERANCE,
                    f"{label}.{key}: drift = {drift} (max: {COMPONENT_TOLERANCE}), scores: {scores}"
                )

    def test_deterministic_overrides_identical(self):
        """Deterministic components should be EXACTLY the same across runs."""
        for label in [l for _, l in ARCHETYPES]:
            for key in DETERMINISTIC_COMPONENTS:
                scores = self._get_scores(label, key)
                self.assertEqual(
                    len(set(scores)), 1,
                    f"{label}.{key}: expected identical across runs, got: {scores}"
                )

    def test_ranking_order_preserved(self):
        """Perfect Lead > Career Switcher in every single run."""
        for i in range(NUM_RUNS):
            lead_score = self.all_runs["Perfect Lead"][i].get("final_score", 0)
            switcher_score = self.all_runs["Career Switcher"][i].get("final_score", 0)
            self.assertGreater(
                lead_score, switcher_score,
                f"Run {i+1}: Perfect Lead ({lead_score}) should beat Career Switcher ({switcher_score})"
            )

    def test_print_summary(self):
        """Print a reproducibility summary table (always passes)."""
        print("\n" + "=" * 80)
        print("REPRODUCIBILITY SUMMARY")
        print("=" * 80)
        print(f"{'Archetype':<25} | {'Run 1':>6} | {'Run 2':>6} | {'Run 3':>6} | {'Drift':>6} | {'StDev':>6}")
        print("-" * 80)

        for _, label in ARCHETYPES:
            scores = self._get_scores(label, "final_score")
            drift = max(scores) - min(scores)
            stdev = statistics.stdev(scores) if len(scores) > 1 else 0
            scores_str = " | ".join(f"{s:>6}" for s in scores)
            print(f"{label:<25} | {scores_str} | {drift:>6} | {stdev:>6.1f}")

        print("=" * 80)


if __name__ == "__main__":
    unittest.main(verbosity=2)
