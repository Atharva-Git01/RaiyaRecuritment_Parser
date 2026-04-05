import unittest
import sys
import os
import json
from unittest.mock import MagicMock, patch

# Ensure path to import modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# --- MOCK SETUP FOR APP.CONTRACTS ---
import app.scoring_contracts
sys.modules["app.scoring_contracts"] = app.scoring_contracts
sys.modules["app.jd_validator"].validate_jd = lambda x: x
sys.modules["app.ai_guardrails"] = MagicMock()
sys.modules["app.ai_guardrails"].apply_guardrails = lambda x, y: x
sys.modules["app.validator"] = MagicMock()
sys.modules["app.validator"].calculate_duration = MagicMock(return_value=1)

from agent_controller import AgentController
from agent_state import AgentState
import ai_scorer

class TestFullStackIntegration(unittest.TestCase):
    """
    Tests AgentController -> AgentAuthority -> ai_scorer (Logic) -> Network Mock.
    """

    def setUp(self):
        self.resume = {"name": "Integrated Test User", "skills": ["Python", "Testing"]}
        self.jd = {"title": "QA Engineer", "requirements": ["Testing"], "weights": {"skills_score": 1}}
        self.weights = {"skills_score": 1}
        self.agent = AgentController(self.resume, self.jd, self.weights)
        
        # Patch credentials globally for this test instance
        self.patcher1 = patch('ai_scorer.AZURE_AI_ENDPOINT', 'https://mock.openai.azure.com')
        self.patcher2 = patch('ai_scorer.DEPLOYMENT_ID', 'mock-deployment')
        self.patcher3 = patch('ai_scorer.API_KEY', 'mock-key')
        self.patcher4 = patch('ai_scorer.MetricsCollector')
        self.patcher5 = patch('ai_scorer.monitor_log_latency')
        self.patcher6 = patch('ai_scorer.monitor_log_token_usage')
        self.patcher1.start()
        self.patcher2.start()
        self.patcher3.start()
        self.patcher4.start()
        self.patcher5.start()
        self.patcher6.start()

    def tearDown(self):
        self.patcher1.stop()
        self.patcher2.stop()
        self.patcher3.stop()
        self.patcher4.stop()
        self.patcher5.stop()
        self.patcher6.stop()

    @patch('ai_scorer.requests.post')
    def test_complete_flow_success(self, mock_post):
        """
        Verify the full flow:
        """
        # Mock LLM Response matching schema
        llm_response_content = json.dumps({
            "final_score": 88, # Ignored, recomputed
            "skills_score": 90,
            "notes": "Great fit."
        })
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        # Updated Metadata: Now logic uses tool calls
        mock_response.json.return_value = {
            "choices": [{
                "message": {
                    "tool_calls": [{
                        "function": {
                            "arguments": llm_response_content
                        }
                    }]
                }
            }],
            "usage": {"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30}
        }
        mock_post.return_value = mock_response

        # Execute
        result = self.agent.run()

        # Debug print if failed
        if not result["success"]:
            print("\nDEBUG: Agent Failed. Result:", json.dumps(result, indent=2, default=str))

        # Checks
        self.assertTrue(result["success"], f"Agent failed with error: {result.get('error')}")
        self.assertEqual(result["current_state"], AgentState.COMPLETED.value)
        # 1. Weights: skills_score=1. skills_score=90. Final = 90.
        self.assertEqual(result["result"]["final_score"], 90)

        # Verify Mock Call
        mock_post.assert_called_once()
        # Verify Authority was checked via History
        # Note: History format is now StateSnapshot (from_state, to_state)
        transitions = [item["to_state"] for item in result["history"]]
        expected_path = ["VALIDATING_INPUT", "FETCHING_CONTEXT", "SCORING", "VERIFYING_OUTPUT", "COMPLETED"]
        self.assertEqual(transitions, expected_path)

    @patch('ai_scorer.requests.post')
    def test_full_flow_sanitization(self, mock_post):
        """
        Test that bad LLM scores are sanitized by ai_scorer, ensuring Authority receives valid data.
        """
        # Mock LLM returns Out of Bounds score
        llm_response_content = json.dumps({
            "final_score": 999, # Ignored
            "skills_score": 200, # Should be clamped to 100
            "notes": "Hallucinated score."
        }, default=str)
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{
                "message": {
                    "tool_calls": [{
                        "function": {
                            "arguments": llm_response_content
                        }
                    }]
                }
            }]
        }
        mock_post.return_value = mock_response

        # Execute
        result = self.agent.run()

        # Should SUCCESS because ai_scorer sanitizes inputs
        self.assertTrue(result["success"])
        self.assertEqual(result["current_state"], AgentState.COMPLETED.value)
        
        # 200 clamped to 100. Weights=1. Final = 100.
        self.assertEqual(result["result"]["final_score"], 100)

if __name__ == '__main__':
    unittest.main()
