# Product/RAG - Evidence/tests/test_mathematical_validator.py
import pytest
from mathematical_validator import MathematicalValidator

def test_calculate_ground_truth_perfect():
    deterministic_report = {
        "rule_adherence": {
            "hard_rules_met": 2, "total_hard_rules": 2,
            "soft_rules_met": 1, "total_soft_rules": 1,
            "required_tools_found": ["python", "react", "aws", "docker"]
        },
        "hallucinations": []
    }
    ai_payload = {"ai_score": {"overall_score": 95}}
    
    validator = MathematicalValidator({}, ai_payload, deterministic_report)
    res = validator.calculate_ground_truth()
    
    # 4 tools = 20 weight. 60 from hard rules, 20 from soft. Total 100.
    assert res["calculated_ground_truth"] == 100.0
    assert res["global_metrics"]["mae"] == 5.0
    assert res["global_metrics"]["accuracy"] == 95.0
    assert res["verdict"]["is_confident"] is True
    assert res["verdict"]["hallucinations_present"] is False

def test_calculate_ground_truth_bad_ai():
    deterministic_report = {
        "rule_adherence": {
            "hard_rules_met": 0, "total_hard_rules": 1,
            "soft_rules_met": 0, "total_soft_rules": 1,
            "required_tools_found": []
        },
        "hallucinations": ["Claimed Java but not found."]
    }
    ai_payload = {"ai_score": 90} # AI hallucinated a high score
    
    validator = MathematicalValidator({}, ai_payload, deterministic_report)
    res = validator.calculate_ground_truth()
    
    assert res["calculated_ground_truth"] == 0.0
    assert res["global_metrics"]["mae"] == 90.0
    assert res["global_metrics"]["accuracy"] == 10.0
    assert res["verdict"]["is_confident"] is False
    assert res["verdict"]["hallucinations_present"] is True
