# Product/RAG - Evidence/tests/test_integration.py
import pytest
from unittest.mock import MagicMock
import sys
sys.modules["sentence_transformers"] = MagicMock()

from deterministic_validator import DeterministicValidator
from mathematical_validator import MathematicalValidator

def test_rag_evidence_integration_flow():
    jd_data = {"job_description": "We need a strong Python developer with AWS."}
    ai_payload = {
        "raw_text": "Built services in Python. Also deployed on AWS.",
        "parsed_json": {"skills": ["Python", "AWS"], "experience": []},
        "ai_score": {"overall_score": 90}
    }
    
    det_val = DeterministicValidator(jd_data)
    det_report = det_val.validate(ai_payload)
    
    math_val = MathematicalValidator(jd_data, ai_payload, det_report)
    final_report = math_val.calculate_ground_truth()
    
    assert final_report["calculated_ground_truth"] > 0
    assert "accuracy" in final_report["global_metrics"]
    assert final_report["verdict"]["hallucinations_present"] is False

    # Simulate Hallucination
    ai_payload["ai_score"] = {"skills_assessed": ["Python", "Java"]}
    det_report = det_val.validate(ai_payload)
    math_val = MathematicalValidator(jd_data, ai_payload, det_report)
    final_report = math_val.calculate_ground_truth()
    
    assert final_report["verdict"]["hallucinations_present"] is True
