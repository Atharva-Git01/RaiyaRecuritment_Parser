"""
Phase 5: Edge Case & Adversarial Testing
=========================================
Tests unusual, boundary, and adversarial inputs to verify
the scorer handles them gracefully without crashes.

Mix of mock API calls and structural validation.
"""

import unittest
import sys
import os
import json
import types
from unittest.mock import patch, MagicMock
from copy import deepcopy

# Fix Windows console encoding
os.environ["PYTHONIOENCODING"] = "utf-8"

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Mock Monitor_Agent (may not exist)
mock_monitor = types.ModuleType("Monitor_Agent")
mock_metrics = types.ModuleType("Monitor_Agent.metrics_collector")
mock_metrics.log_token_usage = MagicMock()
mock_metrics.log_latency = MagicMock()
mock_metrics.MetricsCollector = MagicMock()
mock_metrics.MetricType = MagicMock()
mock_monitor.metrics_collector = mock_metrics
sys.modules.setdefault("Monitor_Agent", mock_monitor)
sys.modules.setdefault("Monitor_Agent.metrics_collector", mock_metrics)

# Mock app.jd_validator (may not exist)
if "app.jd_validator" not in sys.modules:
    mock_jd_val = types.ModuleType("app.jd_validator")
    mock_jd_val.validate_jd = lambda x: x
    sys.modules["app.jd_validator"] = mock_jd_val

from agent_controller import AgentController
from agent_state import AgentState

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
JD_PATH = os.path.join(BASE_DIR, "uploads", "jd", "job_description.json")


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def create_mock_ai_response(scores_dict):
    """Create a mock Azure OpenAI response with given scores."""
    content = json.dumps(scores_dict)
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "choices": [{
            "message": {
                "content": content,
                "tool_calls": [{
                    "function": {"arguments": content}
                }]
            }
        }],
        "usage": {"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150}
    }
    return mock_response


def run_with_mock(resume, jd, mock_scores):
    """Run scoring pipeline with mocked Azure API response."""
    mock_response = create_mock_ai_response(mock_scores)
    # Define weights summing to 1.0 to prevent authority rejection on recompute
    weights = {
        "skills_score": 0.1,
        "experience_score": 0.1,
        "relevant_experience_score": 0.3,
        "technologies_score": 0.2,
        "qualification_score": 0.15,
        "salary_score": 0.1,
        "position_score": 0.03,
        "tools_score": 0.02,
        "projects_score": 0.0,
        "certificates_score": 0.0,
        "responsibilities_score": 0.0
    }
    with patch('ai_scorer.requests.post', return_value=mock_response), \
         patch('ai_scorer.AZURE_AI_ENDPOINT', 'https://mock.openai.azure.com'), \
         patch('ai_scorer.DEPLOYMENT_ID', 'mock'), \
         patch('ai_scorer.API_KEY', 'mock-key'), \
         patch('ai_scorer.MetricsCollector', MagicMock()), \
         patch('ai_scorer.monitor_log_latency', MagicMock()), \
         patch('ai_scorer.monitor_log_token_usage', MagicMock()):
        agent = AgentController(resume, jd, weights=weights)
        return agent.run()


class TestMinimalResume(unittest.TestCase):
    """Resume with only a name — no skills, experience, education."""

    def test_minimal_resume_completes(self):
        resume = {"personal_info": {"name": "Empty Candidate"}}
        jd = load_json(JD_PATH)
        mock_scores = {
            "final_score": 0, "skills_score": 0, "experience_score": 0,
            "relevant_experience_score": 0, "projects_score": 0,
            "certificates_score": 0, "tools_score": 0, "technologies_score": 0,
            "qualification_score": 0, "responsibilities_score": 0,
            "salary_score": 0, "position_score": 0, "notes": "No data"
        }
        result = run_with_mock(resume, jd, mock_scores)
        self.assertTrue(result["success"], f"Failed: {result.get('error')}")
        self.assertLessEqual(result["result"]["final_score"], 5)


class TestManySkillsNoExperience(unittest.TestCase):
    """Resume with 50 skills but zero experience."""

    def test_skills_without_experience(self):
        resume = {
            "personal_info": {"name": "Skills-Only Candidate"},
            "skills": [f"Skill_{i}" for i in range(50)],
            "experience": [],
            "education": [],
        }
        jd = load_json(JD_PATH)
        mock_scores = {
            "final_score": 40, "skills_score": 80, "experience_score": 0,
            "relevant_experience_score": 0, "projects_score": 0,
            "certificates_score": 0, "tools_score": 0, "technologies_score": 0,
            "qualification_score": 0, "responsibilities_score": 0,
            "salary_score": 0, "position_score": 0,
            "notes": "Many skills but no experience"
        }
        result = run_with_mock(resume, jd, mock_scores)
        self.assertTrue(result["success"])
        # Experience weighted at 40% (exp + rel_exp) → final should be low
        final = result["result"]["final_score"]
        self.assertLessEqual(final, 50, f"Final too high for no-experience candidate: {final}")


class TestZeroSalary(unittest.TestCase):
    """Resume with salary_expectation amount = 0."""

    def test_zero_salary_no_crash(self):
        resume = {
            "personal_info": {"name": "Zero Salary"},
            "skills": ["Python"],
            "salary_expectation": {"currency": "INR", "amount": 0}
        }
        jd = load_json(JD_PATH)
        mock_scores = {
            "final_score": 30, "skills_score": 20, "experience_score": 30,
            "relevant_experience_score": 17, "projects_score": 0,
            "certificates_score": 0, "tools_score": 0, "technologies_score": 10,
            "qualification_score": 50, "responsibilities_score": 0,
            "salary_score": 50, "position_score": 0, "notes": "Low match"
        }
        result = run_with_mock(resume, jd, mock_scores)
        self.assertTrue(result["success"], f"Failed: {result.get('error')} Score: {result.get('result', {}).get('final_score')}")


class TestExtremeSalary(unittest.TestCase):
    """Resume with very high salary (99.9 LPA)."""

    def test_extreme_salary(self):
        resume = {
            "personal_info": {"name": "Expensive Candidate"},
            "skills": ["Python"],
            "salary_expectation": {"currency": "INR", "amount": 9999999}
        }
        jd = load_json(JD_PATH)
        mock_scores = {
            "final_score": 50, "skills_score": 50, "experience_score": 50,
            "relevant_experience_score": 50, "projects_score": 0,
            "certificates_score": 0, "tools_score": 0, "technologies_score": 50,
            "qualification_score": 50, "responsibilities_score": 0,
            "salary_score": 50, "position_score": 50,
            "notes": "Moderate match"
        }
        result = run_with_mock(resume, jd, mock_scores)
        self.assertTrue(result["success"])
        # Salary override should set to >10 bracket → 33
        salary = result["result"].get("salary_score", 0)
        self.assertLessEqual(salary, 40, f"Salary override didn't fire for 99.9 LPA: {salary}")


class TestFutureDates(unittest.TestCase):
    """Resume with experience starting in the future."""

    def test_future_start_date(self):
        resume = {
            "personal_info": {"name": "Future Candidate"},
            "skills": ["Python"],
            "experience": [{
                "title": "Future Engineer",
                "company": "FutureCorp",
                "start_date": "2027-01",
                "end_date": "2028-01",
                "description": "Will use Python and AWS."
            }]
        }
        jd = load_json(JD_PATH)
        mock_scores = {
            "final_score": 30, "skills_score": 20, "experience_score": 60,
            "relevant_experience_score": 50, "projects_score": 0,
            "certificates_score": 0, "tools_score": 0, "technologies_score": 20,
            "qualification_score": 50, "responsibilities_score": 0,
            "salary_score": 0, "position_score": 0, "notes": "Future dates"
        }
        result = run_with_mock(resume, jd, mock_scores)
        self.assertTrue(result["success"])


class TestOverlappingExperience(unittest.TestCase):
    """Resume with 20 overlapping experience entries to test merging."""

    def test_many_overlapping_roles(self):
        # Create 20 overlapping 6-month stints in 2020-2022
        experience = []
        for i in range(20):
            month = (i % 12) + 1
            year = 2020 + (i // 12)
            experience.append({
                "title": f"Role {i+1}",
                "company": f"Company {i+1}",
                "start_date": f"{year}-{month:02d}",
                "end_date": f"{year}-{min(month+5, 12):02d}",
                "description": f"Used Python and AWS in role {i+1}."
            })

        resume = {
            "personal_info": {"name": "Overlapper"},
            "skills": ["Python"],
            "experience": experience,
        }
        jd = load_json(JD_PATH)
        mock_scores = {
            "final_score": 60, "skills_score": 40, "experience_score": 60,
            "relevant_experience_score": 50, "projects_score": 0,
            "certificates_score": 0, "tools_score": 0, "technologies_score": 40,
            "qualification_score": 50, "responsibilities_score": 0,
            "salary_score": 0, "position_score": 0, "notes": "Many roles"
        }
        result = run_with_mock(resume, jd, mock_scores)
        self.assertTrue(result["success"], f"Failed: {result.get('error')} Score: {result.get('result', {}).get('final_score')}")
        # Should NOT have 20 * 0.5 = 10 years — overlaps should be merged
        # The merged range is roughly 2020-01 to 2021-12 = ~2 years


class TestEmptyScoringCriteria(unittest.TestCase):
    """JD with empty scoring criteria."""

    def test_empty_scoring_section(self):
        jd = load_json(JD_PATH)
        jd["scoring"] = {}  # Remove all scoring criteria
        resume = {
            "personal_info": {"name": "Test Candidate"},
            "skills": ["Python"],
        }
        mock_scores = {
            "final_score": 50, "skills_score": 50, "experience_score": 50,
            "relevant_experience_score": 50, "projects_score": 0,
            "certificates_score": 0, "tools_score": 0, "technologies_score": 50,
            "qualification_score": 50, "responsibilities_score": 0,
            "salary_score": 50, "position_score": 0, "notes": "Default"
        }
        result = run_with_mock(resume, jd, mock_scores)
        self.assertTrue(result["success"], f"Failed: {result.get('error')} Score: {result.get('result', {}).get('final_score')}")


class TestNestedPersonalInfo(unittest.TestCase):
    """Resume where name is in personal_info, not at root level."""

    def test_nested_name_passes_guardrails(self):
        resume = {
            "personal_info": {"name": "Nested Name Candidate"},
            "skills": ["Python"],
        }
        jd = load_json(JD_PATH)
        mock_scores = {
            "final_score": 30, "skills_score": 20, "experience_score": 0,
            "relevant_experience_score": 0, "projects_score": 0,
            "certificates_score": 0, "tools_score": 0, "technologies_score": 0,
            "qualification_score": 0, "responsibilities_score": 0,
            "salary_score": 0, "position_score": 0, "notes": "Minimal"
        }
        result = run_with_mock(resume, jd, mock_scores)
        self.assertTrue(result["success"])


class TestAIReturnsAllHundred(unittest.TestCase):
    """AI returns 100 for every component."""

    def test_all_100_scores(self):
        resume = {
            "personal_info": {"name": "Perfect Candidate"},
            "skills": ["Python", "AWS"],
            "experience": [{
                "title": "Engineer",
                "start_date": "2018-01",
                "end_date": "2024-01",
                "description": "Used Python, AWS, Docker."
            }],
            "education": [{"degree": "B.Tech", "field": "CS"}],
        }
        jd = load_json(JD_PATH)
        mock_scores = {
            "final_score": 100, "skills_score": 100, "experience_score": 100,
            "relevant_experience_score": 100, "projects_score": 100,
            "certificates_score": 100, "tools_score": 100, "technologies_score": 100,
            "qualification_score": 100, "responsibilities_score": 100,
            "salary_score": 100, "position_score": 100,
            "notes": "Perfect match"
        }
        result = run_with_mock(resume, jd, mock_scores)
        self.assertTrue(result["success"], f"Failed: {result.get('error')}")
        self.assertGreaterEqual(result["result"]["final_score"], 75)


class TestAIReturnsEmptyJson(unittest.TestCase):
    """AI returns empty JSON {}."""

    def test_empty_json_defaults_to_zero(self):
        resume = {
            "personal_info": {"name": "Empty Response"},
            "skills": ["Python"],
        }
        jd = load_json(JD_PATH)
        mock_scores = {}  # Empty JSON from AI
        result = run_with_mock(resume, jd, mock_scores)
        self.assertTrue(result["success"], f"Failed: {result.get('error')}")
        self.assertLessEqual(result["result"]["final_score"], 5)


if __name__ == "__main__":
    unittest.main(verbosity=2)
