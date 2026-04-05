# Product/RAG - Evidence/tests/test_rule_extractor.py
import pytest
from rule_extractor import RuleExtractor

def test_extract_hard_rules():
    jd = "You MUST have 5 years of Python.\nNice to have AWS.\nCandidate is REQUIRED to know Git."
    ext = RuleExtractor(jd)
    hard = ext.extract_hard_rules()
    assert len(hard) == 2
    assert "MUST have 5 years" in hard[0]
    assert "REQUIRED to know" in hard[1]

def test_extract_soft_rules():
    jd = "Must know Python.\nAWS is a PLUS.\nNice to have Docker."
    ext = RuleExtractor(jd)
    soft = ext.extract_soft_rules()
    assert len(soft) == 2
    assert "PLUS" in soft[0]
    assert "Nice to have Docker" in soft[1]

def test_extract_required_tools():
    jd = "We need Python, React, and AWS."
    ext = RuleExtractor(jd)
    tools = ext.extract_required_tools()
    assert "python" in tools
    assert "react" in tools
    assert "aws" in tools
    assert "docker" not in tools
