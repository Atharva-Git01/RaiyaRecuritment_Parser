import re
from copy import deepcopy

from app.ai_scorer import _scale_criteria_dict
from app.jd_normalizer import normalize_jd

REQUIRED_SCORING_FIELDS = [
    "skills",
    "experience",
    "relevant_experience",
    "projects",
    "certificates",
    "tools",
    "technologies",
    "qualification",
    "responsibilities",
    "salary",
]


def ensure_scoring_block(block: dict) -> dict:
    """
    Ensures a scoring block has a valid structure:
    {
        "weight": int,
        "criteria": dict
    }
    """
    if not isinstance(block, dict):
        return {"weight": 0, "criteria": {}}

    # Weight
    try:
        weight = int(block.get("weight", 0))
    except:
        weight = 0

    # Criteria must be dict
    criteria = block.get("criteria", {})
    if not isinstance(criteria, dict):
        criteria = {}

    return {"weight": weight, "criteria": criteria}


def validate_scoring_structure(scoring: dict) -> dict:
    """
    Ensures every scoring field exists and has valid block structure.
    Missing sections get auto-filled with safe zero-weight blocks.
    """
    if not isinstance(scoring, dict):
        scoring = {}

    out = {}

    for field in REQUIRED_SCORING_FIELDS:
        if field in scoring:
            out[field] = ensure_scoring_block(scoring[field])
        else:
            # Auto-fill safe scoring block
            out[field] = {"weight": 0, "criteria": {}}

    return out


def scale_all_criteria(scoring: dict) -> dict:
    """
    Scale all scoring criteria to 0-100.
    Uses ai_scorer._scale_criteria_dict for consistency.
    """
    out = deepcopy(scoring)

    for section, block in out.items():
        criteria = block.get("criteria", {})
        if isinstance(criteria, dict):
            out[section]["criteria"] = _scale_criteria_dict(criteria)

    return out


def validate_weights_sum(scoring: dict) -> dict:
    """
    Ensures total weight approx. 100.
    If not, auto-normalize weights proportionally.
    """
    weights = {k: v["weight"] for k, v in scoring.items()}
    total = sum(weights.values())

    if total == 100:
        return scoring

    if total == 0:
        # All zero weights → assign default importance distribution
        default = {
            "skills": 30,
            "experience": 25,
            "relevant_experience": 10,
            "projects": 10,
            "certificates": 5,
            "tools": 5,
            "technologies": 5,
            "qualification": 5,
            "responsibilities": 3,
            "salary": 2,
        }
        out = deepcopy(scoring)
        for k, v in default.items():
            out[k]["weight"] = v
        return out

    # Normalize proportionally
    out = deepcopy(scoring)
    for k in out:
        out[k]["weight"] = int(round((out[k]["weight"] / total) * 100))

    return out


def validate_jd(jd_raw: dict) -> dict:
    """
    MASTER FUNCTION
    - Normalizes JD
    - Sanitizes structure
    - Fixes scoring blocks
    - Scales criteria 0–100
    - Normalizes weights to total 100
    """

    jd = normalize_jd(jd_raw)
    jd = deepcopy(jd)

    # Ensure scoring exists
    scoring = jd.get("scoring", {})
    scoring = validate_scoring_structure(scoring)

    # Scale criteria 0–100
    scoring = scale_all_criteria(scoring)

    # Ensure total weights ~ 100
    scoring = validate_weights_sum(scoring)

    jd["scoring"] = scoring
    return jd
