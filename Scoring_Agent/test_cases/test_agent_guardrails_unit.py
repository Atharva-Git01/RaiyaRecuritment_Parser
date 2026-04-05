import unittest
import sys
import os

# Ensure path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from agent_guardrails import AgentGuardrails, ValidationFailure

class TestAgentGuardrailsUnit(unittest.TestCase):
    """
    Unit tests for AgentGuardrails validation logic.
    """

    def test_validate_resume_schema_valid(self):
        """Test with valid resume data."""
        valid_resume = {"name": "John Doe", "skills": ["Python"]}
        self.assertTrue(AgentGuardrails.validate_resume_schema(valid_resume))

    def test_validate_resume_schema_valid_nested(self):
        """Test with valid resume data (nested personal_info)."""
        valid_resume = {
            "personal_info": {"name": "Jane Doe"}, 
            "skills": ["Java"]
        }
        self.assertTrue(AgentGuardrails.validate_resume_schema(valid_resume))

    def test_validate_resume_schema_invalid(self):
        """Test with invalid resume data."""
        # Missing critical field
        with self.assertRaises(ValidationFailure):
            AgentGuardrails.validate_resume_schema({"skills": ["Python"]}) # No name
            
        # Incorrect type
        with self.assertRaises(ValidationFailure):
            AgentGuardrails.validate_resume_schema({"name": "Joe", "skills": "NotAList"})
            
        # Empty
        with self.assertRaises(ValidationFailure):
            AgentGuardrails.validate_resume_schema({})
            
        with self.assertRaises(ValidationFailure):
            AgentGuardrails.validate_resume_schema(None)

    def test_validate_jd_schema_valid(self):
        """Test with valid JD data."""
        self.assertTrue(AgentGuardrails.validate_jd_schema({"title": "Dev"}))
        self.assertTrue(AgentGuardrails.validate_jd_schema({"description": "Code"}))
        self.assertTrue(AgentGuardrails.validate_jd_schema({"requirements": ["Code"]}))
        self.assertTrue(AgentGuardrails.validate_jd_schema({"job_title": "Manager"}))
        self.assertTrue(AgentGuardrails.validate_jd_schema({"job_description": "Managing"}))

    def test_validate_jd_schema_invalid(self):
        """Test with invalid JD data."""
        # Empty dict
        with self.assertRaises(ValidationFailure):
            AgentGuardrails.validate_jd_schema({})
            
        # Missing relevant fields
        with self.assertRaises(ValidationFailure):
            AgentGuardrails.validate_jd_schema({"irrelevant": "data"})
            
        # None
        with self.assertRaises(ValidationFailure):
            AgentGuardrails.validate_jd_schema(None)

    def test_validate_weights_valid(self):
        """Test with valid weights."""
        self.assertTrue(AgentGuardrails.validate_weights({"score": 1}))
        self.assertTrue(AgentGuardrails.validate_weights({"score": 0.5}))
        self.assertTrue(AgentGuardrails.validate_weights(None)) # Optional

    def test_validate_weights_invalid(self):
        """Test with invalid weights."""
        with self.assertRaises(ValidationFailure):
            AgentGuardrails.validate_weights("NotADict")
            
        with self.assertRaises(ValidationFailure):
            AgentGuardrails.validate_weights({"score": "NotNumeric"})

    def test_pre_scoring_check(self):
        """Test final boundary check."""
        with self.assertRaises(ValidationFailure):
            AgentGuardrails.pre_scoring_check({}, {"title": "JD"}) # Empty resume validation technically handled earlier but check enforces logic
            
        with self.assertRaises(ValidationFailure):
            AgentGuardrails.pre_scoring_check({"name": "R"}, {})

if __name__ == '__main__':
    unittest.main()
