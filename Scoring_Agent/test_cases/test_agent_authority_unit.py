import unittest
import sys
import os

# Ensure path to import agent_authority
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from agent_authority import AuthorityGovernance
from agent_state import AgentState

class TestAgentAuthorityUnit(unittest.TestCase):
    """
    Unit tests for AuthorityGovernance.
    Verifies whitelist logic and score validation isolation.
    """

    def setUp(self):
        self.auth = AuthorityGovernance()

    def test_whitelist_structure(self):
        """Verify defined transitions exist."""
        self.assertIn(AgentState.INIT.value, self.auth._allowed_transitions)
        self.assertIn(AgentState.VALIDATING_INPUT.value, self.auth._allowed_transitions[AgentState.INIT.value])

    def test_authorize_transition_allowed(self):
        """Test a valid transition."""
        self.assertTrue(self.auth.authorize_transition(AgentState.INIT.value, AgentState.VALIDATING_INPUT.value))
        self.assertTrue(self.auth.authorize_transition(AgentState.SCORING.value, AgentState.VERIFYING_OUTPUT.value))

    def test_authorize_transition_denied(self):
        """Test an invalid transition."""
        # Jumping steps
        self.assertFalse(self.auth.authorize_transition(AgentState.INIT.value, AgentState.SCORING.value))
        # Going backwards (unless allowed, but usually not in this monotonic flow)
        self.assertFalse(self.auth.authorize_transition(AgentState.COMPLETED.value, AgentState.INIT.value))

    def test_authorize_transition_idempotent_loop(self):
        """Test that staying in the same state is always allowed (idempotency support)."""
        self.assertTrue(self.auth.authorize_transition(AgentState.SCORING.value, AgentState.SCORING.value))

    def test_score_validation(self):
        """Test score structure rules."""
        # Valid
        self.assertTrue(self.auth.authorize_score({"final_score": 50}))
        self.assertTrue(self.auth.authorize_score({"final_score": 0}))
        self.assertTrue(self.auth.authorize_score({"final_score": 100}))
        
        # Invalid
        self.assertFalse(self.auth.authorize_score({})) # Empty
        self.assertFalse(self.auth.authorize_score({"score": 50})) # Wrong key
        self.assertFalse(self.auth.authorize_score({"final_score": "50"})) # Wrong type
        self.assertFalse(self.auth.authorize_score({"final_score": 101})) # Out of bounds
        self.assertFalse(self.auth.authorize_score({"final_score": -1})) # Out of bounds

if __name__ == '__main__':
    unittest.main()
