import unittest
import sys
import os
from unittest.mock import MagicMock

# Ensure path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Mock app dependencies again purely for safe import
import app.scoring_contracts
sys.modules["app.scoring_contracts"] = app.scoring_contracts
sys.modules["app.jd_validator"] = MagicMock()
sys.modules["app.ai_guardrails"] = MagicMock()

from agent_controller import AgentController
from agent_state import AgentState
from agent_authority import AuthorityGovernance

class TestAgentAuthorityIntegration(unittest.TestCase):

    def setUp(self):
        self.resume = {"name": "Test"}
        self.jd = {"title": "Test"}
        self.agent = AgentController(self.resume, self.jd)

    def test_allowed_transition(self):
        """Test that a whitelisted transition proceeds."""
        # INIT -> VALIDATING_INPUT is allowed
        self.agent.memory.current_state = AgentState.INIT
        self.agent.transition_to(AgentState.VALIDATING_INPUT)
        self.assertEqual(self.agent.state, AgentState.VALIDATING_INPUT)
        self.assertIsNone(self.agent.error)

    def test_blocked_transition(self):
        """Test that a non-whitelisted transition is blocked and sets error."""
        # INIT -> SCORING is NOT allowed directly (skipping validation/fetching)
        self.agent.memory.current_state = AgentState.INIT
        
        self.agent.transition_to(AgentState.SCORING)
        
        # Should NOT be SCORING. Should be FAILED (due to security violation forcing failure)
        self.assertEqual(self.agent.state, AgentState.FAILED)
        self.assertIn("Unauthorized state transition", self.agent.error)

    def test_score_validation_rejection(self):
        """Test that authority rejects invalid scores."""
        # Manually inject invalid result and try to verify
        self.agent.memory.current_state = AgentState.VERIFYING_OUTPUT
        self.agent.memory.result = {"something_else": 100} # Missing final_score
        
        self.agent._do_verify_output()
        
        self.assertEqual(self.agent.state, AgentState.FAILED)
        self.assertIn("Authority rejected", self.agent.error)

    def test_score_validation_acceptance(self):
        """Test that authority accepts valid scores."""
        self.agent.memory.current_state = AgentState.VERIFYING_OUTPUT
        self.agent.memory.result = {"final_score": 95}
        
        self.agent._do_verify_output()
        
        self.assertEqual(self.agent.state, AgentState.COMPLETED)

if __name__ == '__main__':
    unittest.main()
