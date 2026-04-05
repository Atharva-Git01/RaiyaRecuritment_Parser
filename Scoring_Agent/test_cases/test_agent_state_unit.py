import unittest
import sys
import os
import json
from dataclasses import asdict

# Ensure path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from agent_state import AgentState, AgentMemory

class TestAgentStateUnit(unittest.TestCase):
    """
    Unit tests for AgentMemory and StateSnapshotting.
    """

    def setUp(self):
        self.resume = {"name": "Memory Test"}
        self.jd = {"title": "Role"}
        self.memory = AgentMemory(resume_data=self.resume, jd_data=self.jd)

    def test_initialization(self):
        """Verify initial state of memory."""
        self.assertEqual(self.memory.current_state, AgentState.INIT)
        self.assertEqual(len(self.memory.history), 0)
        self.assertIsNone(self.memory.result)
        self.assertEqual(self.memory.resume_data, self.resume)

    def test_transition_snapshotting(self):
        """Test that transitions record a properly formatted snapshot."""
        # Perform transition
        self.memory.transition(AgentState.VALIDATING_INPUT, reason="Start Validation")
        
        self.assertEqual(self.memory.current_state, AgentState.VALIDATING_INPUT)
        self.assertEqual(len(self.memory.history), 1)
        
        snapshot = self.memory.history[0]
        self.assertEqual(snapshot.from_state, AgentState.INIT.value)
        self.assertEqual(snapshot.to_state, AgentState.VALIDATING_INPUT.value)
        self.assertEqual(snapshot.reason, "Start Validation")
        self.assertIsNotNone(snapshot.timestamp)

    def test_audit_dump_structure(self):
        """Verify the to_dict method produces the expected audit artifact."""
        self.memory.transition(AgentState.VALIDATING_INPUT)
        self.memory.result = {"score": 100}
        self.memory.error = "None"
        
        dump = self.memory.to_dict()
        
        # Check keys
        self.assertIn("current_state", dump)
        self.assertIn("inputs", dump)
        self.assertIn("history", dump)
        self.assertIn("result", dump)
        self.assertIn("error", dump)
        
        # Check values
        self.assertEqual(dump["current_state"], AgentState.VALIDATING_INPUT.value)
        self.assertEqual(dump["inputs"]["resume"], self.resume)
        self.assertEqual(len(dump["history"]), 1)
        self.assertEqual(dump["result"], {"score": 100})

    def test_history_integrity(self):
        """Ensure history is appended chronologically."""
        self.memory.transition(AgentState.VALIDATING_INPUT)
        self.memory.transition(AgentState.FETCHING_CONTEXT)
        
        self.assertEqual(len(self.memory.history), 2)
        self.assertEqual(self.memory.history[0].to_state, AgentState.VALIDATING_INPUT.value)
        self.assertEqual(self.memory.history[1].to_state, AgentState.FETCHING_CONTEXT.value)
        self.assertEqual(self.memory.history[1].from_state, AgentState.VALIDATING_INPUT.value)

if __name__ == '__main__':
    unittest.main()
