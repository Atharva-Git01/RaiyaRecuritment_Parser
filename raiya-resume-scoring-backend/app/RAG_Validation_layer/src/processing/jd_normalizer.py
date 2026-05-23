import re
from copy import deepcopy
from src.logging_config import logger

from src.processing.normalizer_pre_score import edu_aliases, skill_aliases, tech_aliases

# Combine alias maps for JD normalization
# NOTE: edu_aliases intentionally excluded from skills matching to avoid
#       false positives (e.g. "be" in edu_aliases matching inside "cyber")
TECH_SKILL_ALIASES = {**tech_aliases, **skill_aliases}
ALL_JD_ALIASES = {**tech_aliases, **skill_aliases, **edu_aliases}

# Fields whose items should be normalized token-by-token using alias maps
LIST_FIELDS = ["technologies", "skills", "tools", "projects", "certificates"]

# Fields that are text sentences — keep as-is, only clean whitespace
SENTENCE_FIELDS = ["responsibilities"]

# Fields that are plain strings — clean whitespace but no alias mapping
STRING_FIELDS = [
    "experience", "qualification", "position", "location",
    "job_description", "employment_type", "remote_option",
    "job_title", "job_id",
]

# Sections skipped from generic processing
SKIP_FIELDS = {"scoring", "experience_range"}


# ---------------------------------------------------------------------------
# Token-level helpers
# ---------------------------------------------------------------------------

# Pre-compute canonical value sets for fast lookup (avoid re-casing correct items)
_TECH_SKILL_CANONICALS: set = set()
_ALL_CANONICALS: set = set()


def _build_canonical_sets() -> None:
    """Populate canonical lookup sets (called once at module load)."""
    global _TECH_SKILL_CANONICALS, _ALL_CANONICALS
    _TECH_SKILL_CANONICALS = set(TECH_SKILL_ALIASES.values())
    _ALL_CANONICALS = set(ALL_JD_ALIASES.values())


def _match_alias(word: str, alias_map: dict) -> str:
    """
    Match a single token against an alias map using whole-word boundary matching
    to avoid false positives like 'be' matching inside 'cyber'.
    If the word is already a canonical value (e.g. 'HTML5', 'VS Code'),
    it is returned unchanged to prevent incorrect title-casing.
    Falls back to title-case if no alias found.
    """
    if not isinstance(word, str):
        return str(word)

    stripped = word.strip()

    # Fast-path: word already IS a canonical value — keep it as-is
    canonical_set = set(alias_map.values())
    if stripped in canonical_set:
        return stripped

    w = stripped.lower()

    for alias, canonical in alias_map.items():
        # Use word-boundary regex to avoid partial-word collisions
        pattern = r"\b" + re.escape(alias) + r"\b"
        if re.search(pattern, w):
            return canonical

    # Title-case fallback
    return " ".join([x.capitalize() for x in w.split()])


def normalize_token(word: str) -> str:
    """Normalize a single tech/skill/tool token for list fields."""
    return _match_alias(word, TECH_SKILL_ALIASES)


def normalize_edu_token(word: str) -> str:
    """Normalize a single education token (uses edu aliases too)."""
    return _match_alias(word, ALL_JD_ALIASES)


def normalize_list(items: list, alias_map: dict = None) -> list:
    """
    Normalize a list of JD items.
    Deduplicates results while preserving order.
    """
    if not isinstance(items, list):
        return []

    if alias_map is None:
        alias_map = TECH_SKILL_ALIASES

    out = []
    for item in items:
        if not isinstance(item, str) or not item.strip():
            continue
        norm = _match_alias(item, alias_map)
        if norm and norm not in out:
            out.append(norm)
    return out


def normalize_sentence_list(items: list) -> list:
    """
    Clean a list of sentence-style strings (e.g. responsibilities).
    Only strips/normalizes whitespace — does NOT alias-map tokens.
    """
    if not isinstance(items, list):
        return []
    out = []
    for item in items:
        if isinstance(item, str) and item.strip():
            cleaned = re.sub(r"\s+", " ", item).strip()
            out.append(cleaned)
    return out


def normalize_string_field(value: str) -> str:
    """Clean a plain string JD field (collapse whitespace, strip)."""
    if not isinstance(value, str):
        return value
    return re.sub(r"\s+", " ", value).strip()


# ---------------------------------------------------------------------------
# Experience range extraction
# ---------------------------------------------------------------------------

def parse_experience_range(exp_str: str) -> dict:
    """
    Extract min/max years from a JD experience string.
    Examples:
        "3-8 years"       → {"min": 3.0, "max": 8.0}
        "5+ years"        → {"min": 5.0, "max": None}
        "3 years minimum" → {"min": 3.0, "max": None}
    """
    if not isinstance(exp_str, str):
        return {"min": None, "max": None}

    s = exp_str.lower().strip()

    m = re.search(r"(\d+)\s*[-to]+\s*(\d+)", s)
    if m:
        return {"min": float(m.group(1)), "max": float(m.group(2))}

    m = re.search(r"(\d+)\s*\+", s)
    if m:
        return {"min": float(m.group(1)), "max": None}

    m = re.search(r"(minimum|least)\s*(\d+)", s)
    if m:
        return {"min": float(m.group(2)), "max": None}

    m = re.search(r"up to\s*(\d+)", s)
    if m:
        return {"min": None, "max": float(m.group(1))}

    m = re.search(r"(\d+)", s)
    if m:
        return {"min": float(m.group(1)), "max": float(m.group(1))}

    return {"min": None, "max": None}


# ---------------------------------------------------------------------------
# Scoring block helpers
# ---------------------------------------------------------------------------

def validate_scoring_block(block: dict) -> dict:
    """Ensure a scoring block has valid `weight` and `criteria` keys."""
    if not isinstance(block, dict):
        return {"weight": 0, "criteria": {}}

    try:
        weight = int(block.get("weight", 0))
    except (TypeError, ValueError):
        weight = 0

    criteria = block.get("criteria", {})
    if not isinstance(criteria, dict):
        criteria = {}

    # Preserve any extra keys (e.g. fallback_score)
    out = deepcopy(block)
    out["weight"] = weight
    out["criteria"] = criteria
    return out


# ---------------------------------------------------------------------------
# Master normalizer
# ---------------------------------------------------------------------------

def normalize_jd(jd: dict) -> dict:
    """
    Main JD normalization orchestrator.

    Processes ALL sections of the JD:
      • List fields (technologies, skills, tools, etc.)
            → each item is alias-normalized with word-boundary matching
      • Sentence list fields (responsibilities)
            → items are whitespace-cleaned but NOT alias-mapped
      • String fields (qualification, position, experience, location …)
            → whitespace is normalized; value is kept as-is
      • Scoring block
            → each section validated for weight + criteria structure
      • experience_range
            → derived from the 'experience' string and always included
      • All other fields
            → passed through unchanged
    """
    if not isinstance(jd, dict):
        logger.error("Invalid JD data passed to normalize_jd (not a dict)")
        return {}
    
    logger.info("Normalizing JD data...")

    jd = deepcopy(jd)

    # --- Normalize known list fields (tech/skill alias mapping) -----------
    for field in LIST_FIELDS:
        if field in jd:
            jd[field] = normalize_list(jd[field], TECH_SKILL_ALIASES)

    # --- Normalize sentence list fields (no alias mapping) ---------------
    for field in SENTENCE_FIELDS:
        if field in jd:
            jd[field] = normalize_sentence_list(jd[field])

    # --- Normalize any OTHER unknown list fields --------------------------
    for key, value in jd.items():
        if key in SKIP_FIELDS or key in LIST_FIELDS or key in SENTENCE_FIELDS or key in STRING_FIELDS:
            continue
        if isinstance(value, list):
            jd[key] = normalize_list(value, TECH_SKILL_ALIASES)

    # --- Normalize plain string fields -----------------------------------
    for field in STRING_FIELDS:
        if field in jd:
            jd[field] = normalize_string_field(jd[field])

    # --- Derive experience_range -----------------------------------------
    jd["experience_range"] = parse_experience_range(jd.get("experience", ""))

    # --- Normalize scoring block -----------------------------------------
    scoring = jd.get("scoring", {})
    if isinstance(scoring, dict):
        jd["scoring"] = {
            section: validate_scoring_block(block)
            for section, block in scoring.items()
        }

    return jd
