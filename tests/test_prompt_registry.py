import sys
import os
import json
import unittest
from datetime import datetime

# Add app to path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from app.prompt_registry import PromptRegistryAuthority

# Clean up any existing test file
TEST_REGISTRY_FILE = os.path.join(os.path.dirname(__file__), "test_registry.json")
if os.path.exists(TEST_REGISTRY_FILE):
    os.remove(TEST_REGISTRY_FILE)

class TestPromptRegistry(unittest.TestCase):
    
    def setUp(self):
        self.registry = PromptRegistryAuthority(storage_path=TEST_REGISTRY_FILE)

    def tearDown(self):
        if os.path.exists(TEST_REGISTRY_FILE):
            os.remove(TEST_REGISTRY_FILE)

    def test_register_and_resolve_success(self):
        """Test happy path for registration and resolution"""
        prompt_text = "You are a resume parser."
        compatibility = {
            "score_schema_versions": ["1.0.0"],
            "evidence_schema_versions": ["1.0.0"],
            "guardrail_schema_versions": ["1.0.0"]
        }
        
        # Register
        record = self.registry.register_prompt(
            prompt_text=prompt_text,
            prompt_id="test_parser",
            prompt_version="1.0.0",
            prompt_type="resume_parsing",
            compatibility=compatibility
        )
        
        self.assertEqual(record["prompt_id"], "test_parser")
        self.assertEqual(record["status"], "active")
        
        # Resolve
        result = self.registry.resolve_prompt(
            prompt_id="test_parser",
            prompt_version="1.0.0",
            active_score_schema="1.0.0",
            active_evidence_schema="1.0.0",
            active_guardrail_schema="1.0.0"
        )
        
        self.assertEqual(result["prompt_text"], prompt_text)
        self.assertTrue("checksum" in result)

    def test_immutability(self):
        """Test rejection of duplicate version"""
        prompt_text = "You are a resume parser."
        compatibility = {
            "score_schema_versions": ["1.0.0"],
            "evidence_schema_versions": ["1.0.0"],
            "guardrail_schema_versions": ["1.0.0"]
        }
        
        # First Registration
        self.registry.register_prompt(
            prompt_text=prompt_text,
            prompt_id="test_parser",
            prompt_version="1.0.0",
            prompt_type="resume_parsing",
            compatibility=compatibility
        )
        
        # Second Registration (Same version)
        result = self.registry.register_prompt(
            prompt_text="New text",
            prompt_id="test_parser",
            prompt_version="1.0.0", # SAME VERSION
            prompt_type="resume_parsing",
            compatibility=compatibility
        )
        
        self.assertEqual(result.get("error_type"), "IMMUTABILITY_VIOLATION")

    def test_compatibility_enforcement(self):
        """Test resolution fails with incompatible schema"""
        prompt_text = "You are a resume parser."
        compatibility = {
            "score_schema_versions": ["1.0.0"],
            "evidence_schema_versions": ["1.0.0"],
            "guardrail_schema_versions": ["1.0.0"]
        }
        
        self.registry.register_prompt(
            prompt_text=prompt_text,
            prompt_id="test_parser",
            prompt_version="1.0.0",
            prompt_type="resume_parsing",
            compatibility=compatibility
        )
        
        # Resolve with WRONG score schema
        result = self.registry.resolve_prompt(
            prompt_id="test_parser",
            prompt_version="1.0.0",
            active_score_schema="2.0.0", # MISMATCH
            active_evidence_schema="1.0.0",
            active_guardrail_schema="1.0.0"
        )
        
        self.assertEqual(result.get("error_type"), "COMPATIBILITY_ERROR")

    def test_deprecation(self):
        """Test deprecation flow"""
        prompt_text_v1 = "V1"
        prompt_text_v2 = "V2"
        compatibility = {
            "score_schema_versions": ["1.0.0"],
            "evidence_schema_versions": ["1.0.0"],
            "guardrail_schema_versions": ["1.0.0"]
        }
        
        # Register V1 and V2
        self.registry.register_prompt(prompt_text_v1, "test_parser", "1.0.0", "resume_parsing", compatibility)
        self.registry.register_prompt(prompt_text_v2, "test_parser", "2.0.0", "resume_parsing", compatibility)
        
        # Deprecate V1 -> V2
        res = self.registry.deprecate_prompt("test_parser", "1.0.0", "2.0.0")
        self.assertEqual(res["status"], "deprecated")
        self.assertTrue(res["deprecation"]["deprecated"])
        
        # Try to resolve V1
        result = self.registry.resolve_prompt(
            "test_parser", "1.0.0", "1.0.0", "1.0.0", "1.0.0"
        )
        self.assertEqual(result.get("error_type"), "COMPATIBILITY_ERROR", "Should reject deprecated/inactive prompts (usually Status check fails first)")
        # Actually my code returns "Prompt is deprecated" via status check 
        self.assertIn("Prompt is deprecated", result.get("message"))

    def test_invalid_types(self):
        """Test rejection of invalid prompt type"""
        result = self.registry.register_prompt(
            prompt_text="foo",
            prompt_id="foo",
            prompt_version="1.0.0",
            prompt_type="invalid_type", # BAD
            compatibility={
                "score_schema_versions": ["1.0.0"],
                "evidence_schema_versions": ["1.0.0"],
                "guardrail_schema_versions": ["1.0.0"]
            }
        )
        self.assertEqual(result.get("error_type"), "VALIDATION_ERROR")

if __name__ == '__main__':
    unittest.main()
