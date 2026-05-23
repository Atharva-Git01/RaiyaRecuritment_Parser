from copy import deepcopy

from src.processing.jd_normalizer import normalize_jd
from src.config import settings
from src.logging_config import logger

# All scoring sections expected from the JD (including 'position')
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
    "position",
]

# Default weight distribution when all weights are zero
DEFAULT_WEIGHTS = {
    "skills": 10,
    "experience": 10,
    "relevant_experience": 30,
    "projects": 0,
    "certificates": 0,
    "tools": 2,
    "technologies": 20,
    "qualification": 10,
    "responsibilities": 0,
    "salary": 15,
    "position": 3,
}


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _scale_criteria_dict(criteria: dict) -> dict:
    """
    Scale all numeric criteria values so the maximum equals 100.
    Non-numeric values are left as-is.
    """
    if not isinstance(criteria, dict) or not criteria:
        return criteria

    numeric_vals = [v for v in criteria.values() if isinstance(v, (int, float))]
    if not numeric_vals:
        return criteria

    max_val = max(numeric_vals)
    if max_val == 0:
        return criteria

    scaled = {}
    for k, v in criteria.items():
        if isinstance(v, (int, float)):
            scaled[k] = round((v / max_val) * 100)
        else:
            scaled[k] = v
    return scaled


def ensure_scoring_block(block: dict) -> dict:
    """
    Ensures a scoring block has valid structure:
        {"weight": int, "criteria": dict, ...extra keys preserved}
    """
    if not isinstance(block, dict):
        return {"weight": 0, "criteria": {}}

    try:
        weight = int(block.get("weight", 0))
    except (TypeError, ValueError):
        weight = 0

    criteria = block.get("criteria", {})
    if not isinstance(criteria, dict):
        criteria = {}

    out = deepcopy(block)
    out["weight"] = weight
    out["criteria"] = criteria
    return out


def validate_scoring_structure(scoring: dict) -> dict:
    """
    Ensures every required scoring field exists and has valid block structure.
    Missing sections get auto-filled with safe zero-weight blocks.
    Extra sections present in the JD are also preserved.
    """
    if not isinstance(scoring, dict):
        scoring = {}

    out = {}

    # Ensure all required fields
    for field in REQUIRED_SCORING_FIELDS:
        if field in scoring:
            out[field] = ensure_scoring_block(scoring[field])
        else:
            out[field] = {"weight": 0, "criteria": {}}

    # Preserve any extra scoring sections from the JD not in the required list
    for field, block in scoring.items():
        if field not in out:
            out[field] = ensure_scoring_block(block)

    return out


def scale_all_criteria(scoring: dict) -> dict:
    """Scale all scoring criteria values to 0–100."""
    out = deepcopy(scoring)
    for section, block in out.items():
        criteria = block.get("criteria", {})
        if isinstance(criteria, dict):
            out[section]["criteria"] = _scale_criteria_dict(criteria)
    return out


def validate_weights_sum(scoring: dict) -> dict:
    """
    Ensures total weight ≈ 100.
    If not, auto-normalize weights proportionally.
    """
    weights = {k: v.get("weight", 0) for k, v in scoring.items()}
    total = sum(weights.values())

    if total == 100:
        return scoring

    if total == 0:
        out = deepcopy(scoring)
        for k, default_w in DEFAULT_WEIGHTS.items():
            if k in out:
                out[k]["weight"] = default_w
        return out

    # Normalize proportionally
    out = deepcopy(scoring)
    for k in out:
        out[k]["weight"] = int(round((out[k].get("weight", 0) / total) * 100))
    return out


# ---------------------------------------------------------------------------
# Master validator
# ---------------------------------------------------------------------------

def validate_jd(jd_raw: dict) -> dict:
    """
    MASTER FUNCTION — produces a fully validated & normalized JD dict.

    Steps:
        1. Normalize all JD sections (alias maps, string cleaning, experience_range)
        2. Sanitize and complete scoring block structure
        3. Scale criteria values to 0–100
        4. Normalize weights to total ~100
        5. Return the complete JD with ALL original sections preserved
    """
    # Step 1 – normalize all fields
    jd = normalize_jd(jd_raw)

    # Step 2 – validate scoring structure
    scoring = jd.get("scoring", {})
    scoring = validate_scoring_structure(scoring)

    # Step 3 – scale criteria
    scoring = scale_all_criteria(scoring)

    # Step 4 – normalize weights
    scoring = validate_weights_sum(scoring)

    jd["scoring"] = scoring

    return jd


if __name__ == "__main__":
    import json
    
    _input = settings.DEFAULT_JD_INPUT
    _output = settings.VALIDATED_JD_PATH

    if not _input.exists():
        logger.error(f"Input file not found: {_input}")
    else:
        with open(_input, "r", encoding="utf-8") as _f:
            _jd_raw = json.load(_f)

        _validated = validate_jd(_jd_raw)

        os.makedirs(_output.parent, exist_ok=True)
        with open(_output, "w", encoding="utf-8") as _f:
            json.dump(_validated, _f, indent=2, ensure_ascii=False)

        logger.info(f"Saved validated JD to: {_output}")
