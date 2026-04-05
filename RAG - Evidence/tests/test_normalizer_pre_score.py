# Product/RAG - Evidence/tests/test_normalizer_pre_score.py
import pytest
from normalizer_pre_score import normalize_pre_score

def test_normalize_pre_score():
    parsed_payload = {
        "skills": ["Python", "Machine Learning, Deep Learning", None, "SQL"],
        "experience": [
            {"title": "SE", "company": "Tech", "duration": "2y", "description": "built stuff"},
            "Freelance Dev",
            None
        ],
        "education": [
            {"degree": "BTech CS", "institution": "MIT", "year": "2024"},
            "High School"
        ]
    }
    
    norm = normalize_pre_score(parsed_payload)
    
    assert "Python" in norm["skills"]
    assert "Machine Learning" in norm["skills"] or "Machine Learning, Deep Learning" in norm["skills"]
    assert len(norm["skills"]) == 3
    
    assert "Title: SE | Company: Tech | Duration: 2y | Description: built stuff" in norm["experience"]
    assert "Freelance Dev" in norm["experience"]
    assert len(norm["experience"]) == 2
    
    assert "Degree: BTech CS | Institution: MIT | Year: 2024" in norm["education"]
    assert "High School" in norm["education"]
    assert len(norm["education"]) == 2
