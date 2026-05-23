"""
RAIYA Reasoning Phase 1 — Structural Analyzer.
LLM-based (temp=0.0) analysis of resume structure.
Extracts structural facts: field presence, counts, completeness.
"""

from typing import Dict, Any, List
from app.core.logging_config import get_logger

logger = get_logger("StructuralAnalyzer")

# Fields to check for structural completeness
STRUCTURAL_FIELDS = [
    "name", "email", "skills", "technologies", "tools",
    "experience", "education", "projects", "certifications",
    "candidate_achievements", "salary_expectation",
]


def analyze_structure(resume_parsed: Dict[str, Any]) -> Dict[str, Any]:
    """
    Phase 1: Structural Analysis (Python-based deterministic analysis).
    Extracts structural facts about the resume without LLM.
    
    Returns:
        Dict with facts, total_fields_checked, resume_completeness.
    """
    facts = []
    present_count = 0

    for field in STRUCTURAL_FIELDS:
        val = resume_parsed.get(field)
        present = val is not None and val != [] and val != "" and val != {}
        count = None

        if isinstance(val, list):
            count = len(val)
        elif isinstance(val, dict):
            count = len(val)

        summary = None
        if present:
            present_count += 1
            if field == "experience" and isinstance(val, list):
                summary = f"{count} experience entries"
            elif field == "education" and isinstance(val, list):
                summary = f"{count} education entries"
            elif field == "skills" and isinstance(val, list):
                summary = f"{count} skills listed"
            elif field == "name":
                summary = f"Name: {val}"

        facts.append({
            "field": field,
            "present": present,
            "count": count,
            "summary": summary,
        })

    completeness = present_count / len(STRUCTURAL_FIELDS) if STRUCTURAL_FIELDS else 0.0

    logger.info(
        f"Phase 1 complete: {present_count}/{len(STRUCTURAL_FIELDS)} fields present, "
        f"completeness={completeness:.2f}"
    )

    return {
        "facts": facts,
        "total_fields_checked": len(STRUCTURAL_FIELDS),
        "resume_completeness": round(completeness, 4),
    }
