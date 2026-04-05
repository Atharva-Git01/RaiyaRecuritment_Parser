# Product/RAG - Evidence/tests/test_deterministic_validator.py
import pytest
from unittest.mock import MagicMock
import sys

from deterministic_validator import DeterministicValidator

@pytest.fixture
def sample_jd():
    return {"job_description": "We need 5 years of Python and React. AWS is a plus."}

@pytest.fixture
def sample_parsed():
    return {
        "skills": ["Python", "Machine Learning"],
        "experience": [{"title": "Dev", "company": "Tech", "description": "Used React"}]
    }

def test_hallucination_detection(sample_jd, sample_parsed):
    validator = DeterministicValidator(sample_jd)
    ai_score = {
        "skills_assessed": ["Python", "Docker"]
    }
    payload = {"raw_text": "Experienced Python developer with React.", "parsed_json": sample_parsed, "ai_score": ai_score}
    report = validator.validate(payload)
    
    # "Docker" is not in parsed JSON or raw_text
    assert report["is_valid"] is False
    assert len(report["hallucinations"]) == 1
    assert "Docker" in report["hallucinations"][0]

def test_rule_adherence_fallback(sample_jd, sample_parsed):
    validator = DeterministicValidator(sample_jd)
    payload = {"raw_text": "Python and React", "parsed_json": sample_parsed, "ai_score": {}}
    report = validator.validate(payload)
    
    # Fallback keyword matcher should find Python and React from JD
    assert report["rule_adherence"]["required_tools_found"] == ["python", "react"]
    assert "is_valid" in report
