"""
RAIYA Reasoning Phase 2 — Evidence Classifier.
Python-based (no LLM) classification of evidence per section.
Classifies each section as EXPLICIT, PARTIAL, or ABSENT based on JD criteria matching.
"""

from typing import Dict, Any, List
from app.core.logging_config import get_logger

logger = get_logger("EvidenceClassifier")

# Section-to-resume-field mapping
SECTION_FIELD_MAP = {
    "skills": ["skills"],
    "technologies": ["technologies", "skills"],
    "tools": ["tools"],
    "experience": ["experience"],
    "relevant_experience": ["experience"],
    "qualification": ["education"],
    "certifications": ["certifications"],
    "responsibilities": ["experience", "projects"],
    "position": ["experience"],
    "salary": ["salary_expectation"],
}


def classify_evidence(
    resume_parsed: Dict[str, Any],
    jd_weights: Dict[str, Any],
    section_similarities: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Phase 2: Evidence Classification (deterministic, no LLM).
    For each JD scoring section, classify resume evidence as:
      EXPLICIT  — clear match found (similarity >= 0.65 or direct token match)
      PARTIAL   — some match found (similarity >= 0.40)
      ABSENT    — no evidence found
    
    Returns:
        Dict with entries per section, counts of each classification.
    """
    scoring = jd_weights.get("scoring", {})
    entries = {}
    total_explicit = 0
    total_partial = 0
    total_absent = 0

    for section_name, section_data in scoring.items():
        criteria = section_data.get("criteria", {})
        jd_items = list(criteria.keys()) if criteria else []
        resume_fields = SECTION_FIELD_MAP.get(section_name, ["skills"])
        resume_items = _collect_resume_items(resume_parsed, resume_fields)

        # Use section similarities if available
        sim_data = section_similarities.get(section_name, {})
        hybrid_score = sim_data.get("hybrid_score", 0.0)

        # Token overlap check
        jd_tokens = set(" ".join(jd_items).lower().split()) if jd_items else set()
        resume_tokens = set(" ".join(resume_items).lower().split()) if resume_items else set()
        overlap = len(jd_tokens & resume_tokens) / max(len(jd_tokens), 1)

        # Match items based on substring containment
        matched = []
        missing = []
        for item in jd_items:
            item_lower = item.lower()
            found = any(item_lower in ri.lower() or ri.lower() in item_lower for ri in resume_items)
            if found:
                matched.append(item)
            else:
                missing.append(item)

        # Classify
        if hybrid_score >= 0.65 or overlap >= 0.5 or (len(matched) >= len(jd_items) * 0.6):
            classification = "EXPLICIT"
            total_explicit += 1
        elif hybrid_score >= 0.40 or overlap >= 0.25 or len(matched) > 0:
            classification = "PARTIAL"
            total_partial += 1
        else:
            classification = "ABSENT"
            total_absent += 1

        confidence = max(hybrid_score, overlap)

        entries[section_name] = {
            "section": section_name,
            "classification": classification,
            "matched_items": matched,
            "missing_items": missing,
            "confidence": round(confidence, 4),
        }

    logger.info(
        f"Phase 2 complete: EXPLICIT={total_explicit}, "
        f"PARTIAL={total_partial}, ABSENT={total_absent}"
    )

    return {
        "entries": entries,
        "total_explicit": total_explicit,
        "total_partial": total_partial,
        "total_absent": total_absent,
    }


def _collect_resume_items(resume: Dict[str, Any], fields: List[str]) -> List[str]:
    """Collect text items from resume for given fields."""
    items = []
    for field in fields:
        val = resume.get(field)
        if val is None:
            continue
        if isinstance(val, list):
            for entry in val:
                if isinstance(entry, str):
                    items.append(entry)
                elif isinstance(entry, dict):
                    for sub_key in ("title", "name", "description", "degree", "institution", "company"):
                        sv = entry.get(sub_key, "")
                        if sv:
                            items.append(str(sv))
                    # Also add responsibilities
                    resps = entry.get("responsibilities", [])
                    if isinstance(resps, list):
                        items.extend([str(r) for r in resps if r])
        elif isinstance(val, str):
            items.append(val)
        elif isinstance(val, dict):
            items.extend([str(v) for v in val.values() if v])
    return [i.strip() for i in items if i.strip()]
