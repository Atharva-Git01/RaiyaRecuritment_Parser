import re
from copy import deepcopy

from app.normalizer_pre_score import edu_aliases, skill_aliases, tech_aliases

# Combine alias maps for JD normalization
ALL_JD_ALIASES = {**tech_aliases, **skill_aliases, **edu_aliases}


def normalize_token(word: str) -> str:
    """Normalize skills/tools/techs in JD using alias map."""
    if not isinstance(word, str):
        return word

    w = word.lower().strip()

    for alias, canonical in ALL_JD_ALIASES.items():
        if alias in w:
            return canonical

    # Capitalize words: e.g. "python developer" → "Python Developer"
    return " ".join([x.capitalize() for x in w.split()])


def normalize_list(items):
    """Normalize any JD list (skills, technologies, tools)."""
    if not isinstance(items, list):
        return []

    out = []
    for item in items:
        if not isinstance(item, str):
            continue
        norm = normalize_token(item)
        if norm not in out:
            out.append(norm)
    return out


def parse_experience_range(exp_str: str) -> dict:
    """
    Extract min/max experience range from JD.experience.
    Example inputs:
        "3-8 years"
        "3 years minimum"
        "5+ years"
        "at least 4 years"
        "up to 10 years"
    Returns:
        {"min": float or None, "max": float or None}
    """
    if not isinstance(exp_str, str):
        return {"min": None, "max": None}

    s = exp_str.lower().strip()

    # Pattern: "3-8 years"
    m = re.search(r"(\d+)\s*[-to]+\s*(\d+)", s)
    if m:
        return {"min": float(m.group(1)), "max": float(m.group(2))}

    # "5+ years"
    m = re.search(r"(\d+)\s*\+", s)
    if m:
        return {"min": float(m.group(1)), "max": None}

    # "minimum 3 years" / "at least 3 years"
    m = re.search(r"(minimum|least)\s*(\d+)", s)
    if m:
        return {"min": float(m.group(2)), "max": None}

    # "up to 10 years"
    m = re.search(r"up to\s*(\d+)", s)
    if m:
        return {"min": None, "max": float(m.group(1))}

    # Single number: "3 years"
    m = re.search(r"(\d+)", s)
    if m:
        return {"min": float(m.group(1)), "max": float(m.group(1))}

    return {"min": None, "max": None}


def validate_scoring_block(block: dict) -> dict:
    """Ensure scoring block has weight + criteria."""
    if not isinstance(block, dict):
        return {"weight": 0, "criteria": {}}

    weight = block.get("weight", 0)
    criteria = block.get("criteria", {})

    if not isinstance(criteria, dict):
        criteria = {}

    return {"weight": weight, "criteria": criteria}


def normalize_jd(jd: dict) -> dict:
    """Main JD normalization orchestrator."""

    jd = deepcopy(jd)

    # Normalize lists
    jd["skills"] = normalize_list(jd.get("skills", []))
    jd["technologies"] = normalize_list(jd.get("technologies", []))
    jd["tools"] = normalize_list(jd.get("tools", []))

    # Experience min/max extraction
    jd["experience_range"] = parse_experience_range(jd.get("experience", ""))

    # Fix scoring blocks
    scoring = jd.get("scoring", {})
    for key, value in scoring.items():
        scoring[key] = validate_scoring_block(value)

    jd["scoring"] = scoring

    return jd
