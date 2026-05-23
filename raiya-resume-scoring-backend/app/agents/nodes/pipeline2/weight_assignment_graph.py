"""
RAIYA Pipeline 2 — LangGraph JD Weight Assignment Sub-Graph.
=============================================================
Implements the 14-phase enterprise weight generation pipeline:

  PHASE  1 — JD PDF Extraction          (upstream, extract_jd.py)
  PHASE  2 — Canonicalization            (upstream, jd_normalize.py)
  PHASE  3 — Section Classification      (upstream, jd_normalize.py)
  PHASE  4 — LLM Reasoning Label Assign  ← LLM (semantic only)
  PHASE  5 — Reasoning Validation        ← Deterministic
  PHASE  6 — Multiplier Assignment       ← Deterministic
  PHASE  7 — Criteria Score Generation   ← Deterministic
  PHASE  8 — Raw Section Weights         ← Deterministic
  PHASE  9 — Section Importance Factors  ← Deterministic
  PHASE 10 — Adjusted Raw Weights        ← Deterministic
  PHASE 11 — Total Raw Weight            ← Deterministic
  PHASE 12 — Global Normalization        ← Deterministic
  PHASE 13 — Mathematical Validation     ← Deterministic
  PHASE 14 — Final Output Assembly       ← Deterministic

Core principle: LLM = semantic reasoning (Phase 4) only.
All mathematical authority belongs to deterministic Python (Phases 5–13).

Architecture: LangGraph StateGraph with TypedDict state.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from langgraph.graph import END, START, StateGraph
from typing_extensions import TypedDict

from app.agents.tools.llm_tool import call_llm, parse_llm_json
from app.core.logging_config import get_logger

logger = get_logger("WeightAssignmentGraph")


# ═══════════════════════════════════════════════════════════════════════
# Constants
# ═══════════════════════════════════════════════════════════════════════

# Phase 4 — Controlled label ontology
LABEL_MULTIPLIERS: Dict[str, float] = {
    "mandatory_core_skill": 1.00,
    "critical_requirement":  0.95,
    "important_skill":       0.80,
    "preferred_skill":       0.70,
    "supporting_skill":      0.55,
    "nice_to_have":          0.35,
    "irrelevant":            0.00,
}

# Ordered from strongest to weakest (used for one-step downgrade in Phase 5)
_LABEL_ORDER = [
    "mandatory_core_skill", "critical_requirement", "important_skill",
    "preferred_skill", "supporting_skill", "nice_to_have", "irrelevant",
]

BASE_SCORE: int = 100

# All scoring sections
SCORING_SECTIONS = [
    "technologies", "skills", "experience", "qualification",
    "position", "tools", "certifications", "relevant_experience",
    "responsibilities",
]

# Fixed criteria keys for deterministic sections
FIXED_CRITERIA = {
    "experience": {">=8 years": None, "5-7 years": None, "3-4 years": None, "<3 years": None},
    "qualification": {
        "PhD": None, "Masters": None, "Bachelors": None,
        "Associate": None, "Diploma": None, "Certification": None,
    },
    "position": {"senior_level": None, "mid_level": None, "entry_level": None},
    "relevant_experience": {
        ">=5 years_relevant": None, "3-4 years_relevant": None,
        "1-2 years_relevant": None, "<1 year_relevant": None,
    },
}

# Phase 9 — Section importance factor tables
# Role criticality per section (technical vs non-technical role type)
SECTION_BASE_FACTORS: Dict[str, Dict[str, float]] = {
    "technical": {
        "technologies": 1.30, "skills": 1.40, "tools": 0.60,
        "relevant_experience": 1.20, "experience": 0.90,
        "qualification": 0.80, "position": 0.70,
        "certifications": 0.55, "responsibilities": 0.80,
    },
    "non_technical": {
        "technologies": 0.60, "skills": 1.40, "tools": 0.50,
        "relevant_experience": 1.10, "experience": 1.10,
        "qualification": 1.00, "position": 0.90,
        "certifications": 0.45, "responsibilities": 1.00,
    },
}

# Fixed business priority per section
_BUSINESS_PRIORITY: Dict[str, float] = {
    "technologies": 0.90, "skills": 0.95, "tools": 0.70,
    "relevant_experience": 0.85, "experience": 0.80,
    "qualification": 0.75, "position": 0.65,
    "certifications": 0.60, "responsibilities": 0.80,
}

# Fixed retrieval importance per section
_RETRIEVAL_IMPORTANCE: Dict[str, float] = {
    "technologies": 0.90, "skills": 0.85, "tools": 0.75,
    "relevant_experience": 0.88, "experience": 0.82,
    "qualification": 0.70, "position": 0.65,
    "certifications": 0.65, "responsibilities": 0.85,
}

# Technical role keywords for role-type detection
_TECHNICAL_KEYWORDS = {
    "engineer", "developer", "architect", "devops", "sre", "data", "ml", "ai",
    "backend", "frontend", "fullstack", "cloud", "platform", "infrastructure",
    "security", "analyst", "scientist", "software", "programmer", "tech",
}

# Salary section defaults (not part of scoring pipeline)
SALARY_CRITERIA = {"3-6": 0.0, "6-10": 0.0, ">10": 0.0}


# ═══════════════════════════════════════════════════════════════════════
# State Definition
# ═══════════════════════════════════════════════════════════════════════

class WeightAssignmentState(TypedDict, total=False):
    """State flowing through the 14-phase weight assignment sub-graph."""
    # Inputs (from assign_weights_node)
    jd_normalized: Dict[str, Any]
    jd_content_hash: str
    batch_id: Optional[str]

    # Step 1 — Extracted JD sections
    extracted_sections: Dict[str, Any]

    # Phase 4 — LLM reasoning labels
    # {sections: {section: {key: {reasoning_label, confidence, evidence}}}, job_info: {...}}
    reasoning_labels_raw: Dict[str, Any]

    # Phase 5 — Validated labels (corrections applied)
    validated_labels: Dict[str, Dict[str, Any]]

    # Phase 6 — Labels with deterministic multipliers added
    labels_with_multipliers: Dict[str, Dict[str, Any]]

    # Phase 7 — Rich criteria scores {section: {key: {score, reasoning_label, multiplier, confidence, evidence}}}
    criteria_scores: Dict[str, Dict[str, Any]]

    # Phase 8 — Raw section weights (avg of criteria scores)
    raw_weights: Dict[str, float]
    raw_weight_metadata: Dict[str, Dict[str, Any]]

    # Phase 9 — Section importance factors
    section_importance_factors: Dict[str, float]

    # Phase 10 — Adjusted raw weights
    adjusted_raw_weights: Dict[str, float]

    # Phase 11 — Total raw weight (sum of adjusted)
    total_raw_weight_value: float

    # Phase 12 — Normalized weights
    normalized_weights: Dict[str, float]
    normalization_factor: float

    # Phase 13 — Math validation
    math_validation: Dict[str, Any]
    validation_passed: bool
    validation_errors: List[str]

    # Phase 14 — Final schema
    final_weights_schema: Dict[str, Any]

    # Internal
    errors: List[str]


# ═══════════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════════

def _detect_role_type(job_title: str) -> str:
    """Return 'technical' or 'non_technical' based on job title keywords."""
    title_lower = job_title.lower()
    for kw in _TECHNICAL_KEYWORDS:
        if kw in title_lower:
            return "technical"
    return "non_technical"


def _downgrade_label(label: str) -> str:
    """Move a label one step weaker in the ontology order."""
    if label not in _LABEL_ORDER:
        return "supporting_skill"
    idx = _LABEL_ORDER.index(label)
    return _LABEL_ORDER[min(idx + 1, len(_LABEL_ORDER) - 1)]


# ═══════════════════════════════════════════════════════════════════════
# STEP 1 — Extract JD Information (Phases 1–3 already done upstream)
# ═══════════════════════════════════════════════════════════════════════

async def step1_extract_jd_info(state: WeightAssignmentState) -> dict:
    """Extract structured sections from normalized JD for use in Phase 4+."""
    jd = state.get("jd_normalized", {})
    extracted = {
        "job_title":              jd.get("job_title", ""),
        "technologies":           jd.get("technologies", []),
        "skills":                 jd.get("skills", []),
        "tools":                  jd.get("tools", []),
        "certifications":         jd.get("certifications", []),
        "responsibilities":       jd.get("responsibilities", []),
        "requirements":           jd.get("requirements", []),
        "preferred_qualifications": jd.get("preferred_qualifications", []),
        "position":               jd.get("position", ""),
        "experience_range":       jd.get("experience_range", {}),
        "minimum_years":          jd.get("minimum_years"),
        "preferred_years":        jd.get("preferred_years"),
        "qualification":          jd.get("qualification", {}),
        "employment_type":        jd.get("employment_type", ""),
        "location":               jd.get("location", ""),
        "work_mode":              jd.get("work_mode", {}),
        "job_description":        jd.get("job_description", ""),
        "_provenance":            jd.get("_provenance", {}),
    }
    logger.info(
        "Step 1: Extracted — techs=%d skills=%d tools=%d",
        len(extracted["technologies"]),
        len(extracted["skills"]),
        len(extracted["tools"]),
    )
    return {**state, "extracted_sections": extracted}


# ═══════════════════════════════════════════════════════════════════════
# PHASE 4 — LLM Reasoning Label Assignment (semantic only)
# ═══════════════════════════════════════════════════════════════════════

REASONING_LABEL_SYSTEM_PROMPT = """You are a JD Semantic Reasoning Agent for a recruiting AI system.

## YOUR ROLE
Assign a controlled ontology label to every criterion in each section.
You perform LABEL ASSIGNMENT ONLY — no scoring, no weight calculation, no percentages.

## LABEL ONTOLOGY (use ONLY these 7 labels)
- mandatory_core_skill   : Explicitly required; role cannot function without it
- critical_requirement   : Strongly emphasized, near-mandatory
- important_skill        : Clearly valued, standard expectation
- preferred_skill        : Preferred but not required, added advantage
- supporting_skill       : Helpful, occasionally mentioned
- nice_to_have           : Optional, barely mentioned, bonus
- irrelevant             : Not applicable, or bucket does not match JD requirements

## RULES BY SECTION TYPE

### Dynamic sections (technologies, skills, tools, certifications, responsibilities)
Use the `_provenance` field (required_items vs preferred_items) as your primary signal:
- Items in required_items → mandatory_core_skill / critical_requirement / important_skill
- Items in preferred_items → preferred_skill / supporting_skill / nice_to_have
- Refine further using wording strength in job_description / responsibilities

### Fixed-bucket sections (experience, qualification, position, relevant_experience)
- The bucket matching the JD requirement → mandatory_core_skill or critical_requirement
- Adjacent/close buckets → important_skill or preferred_skill
- Non-applicable buckets → irrelevant

## OUTPUT FORMAT — Return ONLY raw JSON (no markdown, no comments):
{
  "job_info": {
    "job_title": "...",
    "experience": "...",
    "qualification": "...",
    "location": "...",
    "employment_type": "...",
    "position": "...",
    "work_mode": {"remote_option": false, "work_from_office": true, "hybrid": false},
    "responsibilities": [],
    "job_description": "..."
  },
  "sections": {
    "technologies": {
      "<name>": {"reasoning_label": "<label>", "confidence": 0.0, "evidence": "<brief JD ref>"}
    },
    "skills":           { "<name>": {"reasoning_label": "...", "confidence": 0.0, "evidence": "..."} },
    "tools":            { "<name>": {"reasoning_label": "...", "confidence": 0.0, "evidence": "..."} },
    "certifications":   { "<name>": {"reasoning_label": "...", "confidence": 0.0, "evidence": "..."} },
    "responsibilities": { "<theme>": {"reasoning_label": "...", "confidence": 0.0, "evidence": "..."} },
    "experience": {
      ">=8 years":   {"reasoning_label": "...", "confidence": 0.0, "evidence": "..."},
      "5-7 years":   {"reasoning_label": "...", "confidence": 0.0, "evidence": "..."},
      "3-4 years":   {"reasoning_label": "...", "confidence": 0.0, "evidence": "..."},
      "<3 years":    {"reasoning_label": "...", "confidence": 0.0, "evidence": "..."}
    },
    "qualification": {
      "PhD": {"reasoning_label": "...", "confidence": 0.0, "evidence": "..."},
      "Masters": {"reasoning_label": "...", "confidence": 0.0, "evidence": "..."},
      "Bachelors": {"reasoning_label": "...", "confidence": 0.0, "evidence": "..."},
      "Associate": {"reasoning_label": "...", "confidence": 0.0, "evidence": "..."},
      "Diploma": {"reasoning_label": "...", "confidence": 0.0, "evidence": "..."},
      "Certification": {"reasoning_label": "...", "confidence": 0.0, "evidence": "..."}
    },
    "position": {
      "senior_level": {"reasoning_label": "...", "confidence": 0.0, "evidence": "..."},
      "mid_level":    {"reasoning_label": "...", "confidence": 0.0, "evidence": "..."},
      "entry_level":  {"reasoning_label": "...", "confidence": 0.0, "evidence": "..."}
    },
    "relevant_experience": {
      ">=5 years_relevant":  {"reasoning_label": "...", "confidence": 0.0, "evidence": "..."},
      "3-4 years_relevant":  {"reasoning_label": "...", "confidence": 0.0, "evidence": "..."},
      "1-2 years_relevant":  {"reasoning_label": "...", "confidence": 0.0, "evidence": "..."},
      "<1 year_relevant":    {"reasoning_label": "...", "confidence": 0.0, "evidence": "..."}
    }
  }
}
"""


async def phase4_generate_reasoning_labels(state: WeightAssignmentState) -> dict:
    """
    Phase 4: Call LLM to assign reasoning labels per criterion.
    LLM role is SEMANTIC ONLY — it never calculates scores or weights.
    """
    extracted = state.get("extracted_sections", {})
    jd_info_str = json.dumps(extracted, indent=2, default=str)

    result = await call_llm(
        system_prompt=REASONING_LABEL_SYSTEM_PROMPT,
        user_prompt=(
            "Assign reasoning labels for this Job Description:\n\n" + jd_info_str
        ),
        temperature=0.0,
        max_tokens=4000,
        pipeline_stage="phase4_reasoning_labels",
        batch_id=state.get("batch_id"),
    )

    content = result.get("content", "{}")
    labels_data = parse_llm_json(content)

    if not labels_data or not isinstance(labels_data, dict):
        logger.warning("Phase 4: LLM returned invalid labels, using defaults")
        labels_data = _build_default_labels(extracted)

    sections = labels_data.get("sections", {})

    # Ensure fixed-bucket sections have all canonical keys
    for section, fixed_keys in FIXED_CRITERIA.items():
        if section not in sections or not isinstance(sections[section], dict):
            sections[section] = {}
        for k in fixed_keys:
            if k not in sections[section]:
                sections[section][k] = {
                    "reasoning_label": "irrelevant",
                    "confidence": 0.5,
                    "evidence": "not mentioned in JD",
                }

    # Ensure dynamic sections have entries for all extracted items
    for section in ["technologies", "skills", "tools", "certifications"]:
        if section not in sections or not isinstance(sections[section], dict):
            sections[section] = {}
        for item in extracted.get(section, []):
            if isinstance(item, str) and item not in sections[section]:
                sections[section][item] = {
                    "reasoning_label": "important_skill",
                    "confidence": 0.6,
                    "evidence": "listed in JD section",
                }

    if "responsibilities" not in sections or not isinstance(sections["responsibilities"], dict):
        sections["responsibilities"] = {}
    for resp in extracted.get("responsibilities", []):
        if isinstance(resp, str):
            key = resp[:80]
            if key not in sections["responsibilities"]:
                sections["responsibilities"][key] = {
                    "reasoning_label": "important_skill",
                    "confidence": 0.6,
                    "evidence": "listed as responsibility",
                }

    labels_data["sections"] = sections
    logger.info("Phase 4: Reasoning labels generated for %d sections", len(sections))
    return {**state, "reasoning_labels_raw": labels_data}


def _build_default_labels(extracted: dict) -> dict:
    """Fallback labels when LLM is unavailable."""
    sections: Dict[str, Any] = {}

    for section in ["technologies", "skills", "tools", "certifications"]:
        sections[section] = {
            item: {"reasoning_label": "important_skill", "confidence": 0.6, "evidence": "listed in JD"}
            for item in extracted.get(section, [])
            if isinstance(item, str)
        }

    resps = extracted.get("responsibilities", [])
    sections["responsibilities"] = {
        r[:80]: {"reasoning_label": "important_skill", "confidence": 0.6, "evidence": "listed as responsibility"}
        for r in resps if isinstance(r, str)
    }

    # Moderate defaults for fixed-bucket sections
    sections["experience"] = {
        ">=8 years":  {"reasoning_label": "irrelevant",            "confidence": 0.5, "evidence": "default"},
        "5-7 years":  {"reasoning_label": "critical_requirement",  "confidence": 0.5, "evidence": "default"},
        "3-4 years":  {"reasoning_label": "important_skill",       "confidence": 0.5, "evidence": "default"},
        "<3 years":   {"reasoning_label": "supporting_skill",      "confidence": 0.5, "evidence": "default"},
    }
    sections["qualification"] = {
        "PhD":           {"reasoning_label": "irrelevant",           "confidence": 0.5, "evidence": "default"},
        "Masters":       {"reasoning_label": "important_skill",      "confidence": 0.5, "evidence": "default"},
        "Bachelors":     {"reasoning_label": "critical_requirement", "confidence": 0.5, "evidence": "default"},
        "Associate":     {"reasoning_label": "supporting_skill",     "confidence": 0.5, "evidence": "default"},
        "Diploma":       {"reasoning_label": "nice_to_have",         "confidence": 0.5, "evidence": "default"},
        "Certification": {"reasoning_label": "supporting_skill",     "confidence": 0.5, "evidence": "default"},
    }
    sections["position"] = {
        "senior_level": {"reasoning_label": "supporting_skill",     "confidence": 0.5, "evidence": "default"},
        "mid_level":    {"reasoning_label": "critical_requirement",  "confidence": 0.5, "evidence": "default"},
        "entry_level":  {"reasoning_label": "supporting_skill",     "confidence": 0.5, "evidence": "default"},
    }
    sections["relevant_experience"] = {
        ">=5 years_relevant": {"reasoning_label": "irrelevant",           "confidence": 0.5, "evidence": "default"},
        "3-4 years_relevant": {"reasoning_label": "critical_requirement", "confidence": 0.5, "evidence": "default"},
        "1-2 years_relevant": {"reasoning_label": "important_skill",      "confidence": 0.5, "evidence": "default"},
        "<1 year_relevant":   {"reasoning_label": "supporting_skill",     "confidence": 0.5, "evidence": "default"},
    }

    return {
        "job_info": {"job_title": extracted.get("job_title", "")},
        "sections": sections,
    }


# ═══════════════════════════════════════════════════════════════════════
# PHASE 5 — Reasoning Validation Engine
# ═══════════════════════════════════════════════════════════════════════

async def phase5_validate_labels(state: WeightAssignmentState) -> dict:
    """
    Phase 5: Deterministic validation and correction of LLM-assigned labels.
    Correction rules:
      1. Label not in ontology            → downgrade to "supporting_skill"
      2. confidence < 0.75               → downgrade one step
      3. evidence missing or < 5 chars   → downgrade one step
    """
    raw = state.get("reasoning_labels_raw", {})
    sections = raw.get("sections", {})
    validated: Dict[str, Dict[str, Any]] = {}

    for section, criteria in sections.items():
        if not isinstance(criteria, dict):
            continue
        validated[section] = {}
        for key, entry in criteria.items():
            if not isinstance(entry, dict):
                entry = {"reasoning_label": "supporting_skill", "confidence": 0.5, "evidence": ""}

            label = entry.get("reasoning_label", "supporting_skill")
            confidence = entry.get("confidence", 0.5)
            evidence = entry.get("evidence", "") or ""

            # Rule 1 — unknown label
            if label not in LABEL_MULTIPLIERS:
                label = "supporting_skill"

            # Rule 2 — low confidence
            if isinstance(confidence, (int, float)) and confidence < 0.75:
                label = _downgrade_label(label)

            # Rule 3 — missing evidence
            if len(str(evidence).strip()) < 5:
                label = _downgrade_label(label)

            validated[section][key] = {
                "reasoning_label": label,
                "confidence": confidence if isinstance(confidence, (int, float)) else 0.5,
                "evidence": str(evidence),
            }

    logger.info("Phase 5: Labels validated for %d sections", len(validated))
    return {**state, "validated_labels": validated}


# ═══════════════════════════════════════════════════════════════════════
# PHASE 6 — Deterministic Multiplier Assignment
# ═══════════════════════════════════════════════════════════════════════

async def phase6_assign_multipliers(state: WeightAssignmentState) -> dict:
    """
    Phase 6: Map each reasoning_label to its deterministic multiplier.
    Purely deterministic — no LLM involvement.
    """
    validated = state.get("validated_labels", {})
    with_multipliers: Dict[str, Dict[str, Any]] = {}

    for section, criteria in validated.items():
        with_multipliers[section] = {}
        for key, entry in criteria.items():
            label = entry.get("reasoning_label", "supporting_skill")
            multiplier = LABEL_MULTIPLIERS.get(label, 0.55)
            with_multipliers[section][key] = {**entry, "multiplier": multiplier}

    logger.info("Phase 6: Multipliers assigned")
    return {**state, "labels_with_multipliers": with_multipliers}


# ═══════════════════════════════════════════════════════════════════════
# PHASE 7 — Criteria Score Generation
# ═══════════════════════════════════════════════════════════════════════

async def phase7_compute_criteria_scores(state: WeightAssignmentState) -> dict:
    """
    Phase 7: CriteriaScore = BASE_SCORE × multiplier for each criterion.
    Produces the rich criteria dict format: {score, reasoning_label, multiplier, confidence, evidence}.
    """
    with_multipliers = state.get("labels_with_multipliers", {})
    criteria_scores: Dict[str, Dict[str, Any]] = {}

    for section, criteria in with_multipliers.items():
        criteria_scores[section] = {}
        for key, entry in criteria.items():
            multiplier = entry.get("multiplier", 0.55)
            score = round(BASE_SCORE * multiplier, 4)
            criteria_scores[section][key] = {
                "score":           score,
                "reasoning_label": entry.get("reasoning_label", "supporting_skill"),
                "multiplier":      multiplier,
                "confidence":      entry.get("confidence", 0.5),
                "evidence":        entry.get("evidence", ""),
            }

    logger.info("Phase 7: Criteria scores computed")
    return {**state, "criteria_scores": criteria_scores}


# ═══════════════════════════════════════════════════════════════════════
# PHASE 8 — Raw Section Weight Calculation
# ═══════════════════════════════════════════════════════════════════════

async def phase8_compute_raw_weights(state: WeightAssignmentState) -> dict:
    """
    Phase 8: RawSectionWeight = sum(CriteriaScores) / criteria_count.
    Sections with 0 criteria get raw_weight = 0.
    """
    criteria_scores = state.get("criteria_scores", {})
    raw_weights: Dict[str, float] = {}
    raw_weight_metadata: Dict[str, Dict[str, Any]] = {}

    for section in SCORING_SECTIONS:
        criteria = criteria_scores.get(section, {})
        scores = [
            entry["score"]
            for entry in criteria.values()
            if isinstance(entry, dict) and isinstance(entry.get("score"), (int, float))
        ]
        if scores:
            raw_weight = sum(scores) / len(scores)
            criteria_count = len(scores)
        else:
            raw_weight = 0.0
            criteria_count = 0

        raw_weights[section] = round(raw_weight, 4)
        raw_weight_metadata[section] = {
            "raw_weight":    round(raw_weight, 4),
            "criteria_count": criteria_count,
        }

    logger.info("Phase 8: Raw weights — total=%.2f", sum(raw_weights.values()))
    return {**state, "raw_weights": raw_weights, "raw_weight_metadata": raw_weight_metadata}


# ═══════════════════════════════════════════════════════════════════════
# PHASE 9 — Section Importance Factor Generation
# ═══════════════════════════════════════════════════════════════════════

async def phase9_compute_importance_factors(state: WeightAssignmentState) -> dict:
    """
    Phase 9: SectionFactor = 0.4×RoleCriticality + 0.25×DensityScore
                            + 0.2×BusinessPriority + 0.15×RetrievalImportance
    """
    extracted = state.get("extracted_sections", {})
    raw_weight_metadata = state.get("raw_weight_metadata", {})
    job_title = extracted.get("job_title", "")
    role_type = _detect_role_type(job_title)
    role_table = SECTION_BASE_FACTORS[role_type]

    total_criteria = sum(
        m.get("criteria_count", 0) for m in raw_weight_metadata.values()
    ) or 1

    factors: Dict[str, float] = {}
    for section in SCORING_SECTIONS:
        role_criticality = role_table.get(section, 0.70)
        count = raw_weight_metadata.get(section, {}).get("criteria_count", 0)
        density_score = count / total_criteria
        business_priority = _BUSINESS_PRIORITY.get(section, 0.70)
        retrieval_importance = _RETRIEVAL_IMPORTANCE.get(section, 0.70)

        factor = (
            0.40 * role_criticality
            + 0.25 * density_score
            + 0.20 * business_priority
            + 0.15 * retrieval_importance
        )
        factors[section] = round(factor, 6)

    logger.info("Phase 9: Importance factors — role_type=%s", role_type)
    return {**state, "section_importance_factors": factors}


# ═══════════════════════════════════════════════════════════════════════
# PHASE 10 — Adjusted Raw Weight Calculation
# ═══════════════════════════════════════════════════════════════════════

async def phase10_compute_adjusted_weights(state: WeightAssignmentState) -> dict:
    """Phase 10: AdjustedRawWeight = RawSectionWeight × SectionImportanceFactor"""
    raw_weights = state.get("raw_weights", {})
    factors = state.get("section_importance_factors", {})
    raw_weight_metadata = state.get("raw_weight_metadata", {})

    adjusted: Dict[str, float] = {}
    for section in SCORING_SECTIONS:
        adjusted[section] = round(
            raw_weights.get(section, 0.0) * factors.get(section, 1.0), 4
        )
        # Persist section_importance_factor into metadata for Phase 14 audit
        if section in raw_weight_metadata:
            raw_weight_metadata[section]["section_importance_factor"] = factors.get(section, 1.0)

    logger.info("Phase 10: Adjusted weights — total=%.2f", sum(adjusted.values()))
    return {**state, "adjusted_raw_weights": adjusted, "raw_weight_metadata": raw_weight_metadata}


# ═══════════════════════════════════════════════════════════════════════
# PHASE 11 — Total Raw Weight
# ═══════════════════════════════════════════════════════════════════════

async def phase11_compute_total_raw_weight(state: WeightAssignmentState) -> dict:
    """Phase 11: TotalRawWeight = sum(AdjustedRawWeights)"""
    adjusted = state.get("adjusted_raw_weights", {})
    total = round(sum(adjusted.values()), 4)
    logger.info("Phase 11: Total raw weight = %.4f", total)
    return {**state, "total_raw_weight_value": total}


# ═══════════════════════════════════════════════════════════════════════
# PHASE 12 — Global Weight Normalization
# ═══════════════════════════════════════════════════════════════════════

async def phase12_normalize_weights(state: WeightAssignmentState) -> dict:
    """
    Phase 12: NormalizedWeight = (AdjustedRawWeight / TotalRawWeight) × 100
    Rounding correction applied to largest section so sum = exactly 100.0.
    """
    adjusted = state.get("adjusted_raw_weights", {})
    total_raw = state.get("total_raw_weight_value", 0.0)

    if total_raw == 0:
        n = len(adjusted) or 1
        normalized = {s: round(100.0 / n, 2) for s in adjusted}
        normalization_factor = 1.0
    else:
        normalized = {
            s: round((v / total_raw) * 100, 2) for s, v in adjusted.items()
        }
        normalization_factor = total_raw

    # Rounding correction — largest section absorbs residual
    current_sum = sum(normalized.values())
    if abs(current_sum - 100.0) > 0.01:
        diff = 100.0 - current_sum
        largest = max(normalized, key=lambda s: normalized[s])
        normalized[largest] = round(normalized[largest] + diff, 2)

    # Persist normalization_factor into raw_weight_metadata for Phase 14
    raw_weight_metadata = state.get("raw_weight_metadata", {})
    for section in raw_weight_metadata:
        raw_weight_metadata[section]["normalization_factor"] = round(normalization_factor, 4)

    logger.info(
        "Phase 12: Normalized — factor=%.4f sum=%.2f",
        normalization_factor, sum(normalized.values()),
    )
    return {
        **state,
        "normalized_weights": normalized,
        "normalization_factor": normalization_factor,
        "raw_weight_metadata": raw_weight_metadata,
    }


# ═══════════════════════════════════════════════════════════════════════
# PHASE 13 — Mathematical Validation Engine
# ═══════════════════════════════════════════════════════════════════════

async def phase13_validate_math(state: WeightAssignmentState) -> dict:
    """
    Phase 13: Mathematical integrity checks on normalized weights.
    Checks: total ≈ 100 (±0.5), no negatives, score collapse, section inflation.
    """
    normalized = state.get("normalized_weights", {})
    total = sum(normalized.values())
    errors: List[str] = []
    warnings: List[str] = []

    if abs(total - 100.0) > 0.5:
        errors.append(f"Normalized total = {total:.4f}, expected 100 (±0.5)")

    for section, w in normalized.items():
        if w < 0:
            errors.append(f"Negative weight: {section}={w}")

    # Score collapse — all weights equal
    unique_vals = set(normalized.values())
    if len(normalized) > 1 and len(unique_vals) == 1:
        warnings.append("Score collapse: all section weights are equal")

    # Inflation check
    for section, w in normalized.items():
        if w > 50:
            warnings.append(f"Section inflation: {section}={w:.2f}% (>50%)")

    # Variance check
    if len(normalized) > 1:
        mean = total / len(normalized)
        variance = sum((v - mean) ** 2 for v in normalized.values()) / len(normalized)
        variance_score = round(variance ** 0.5, 4)
    else:
        variance_score = 0.0

    passed = len(errors) == 0
    math_validation = {
        "is_valid": passed,
        "normalized_total_weight": round(total, 4),
        "variance_score": variance_score,
        "section_balance_valid": len(warnings) == 0,
        "errors": errors,
        "warnings": warnings,
    }

    if passed:
        logger.info("Phase 13: Math validation PASSED (variance=%.4f)", variance_score)
    else:
        logger.warning("Phase 13: Math validation FAILED — %s", errors)

    return {
        **state,
        "math_validation": math_validation,
        "validation_passed": passed,
        "validation_errors": errors,
    }


# ═══════════════════════════════════════════════════════════════════════
# PHASE 14 — Audit Metadata Injection & Final Output Assembly
# ═══════════════════════════════════════════════════════════════════════

async def phase14_assemble_schema(state: WeightAssignmentState) -> dict:
    """
    Phase 14: Assemble the final enterprise weight JSON with full audit metadata.
    Criteria are stored as rich objects {score, reasoning_label, multiplier, confidence, evidence}.
    """
    extracted         = state.get("extracted_sections", {})
    criteria_scores   = state.get("criteria_scores", {})
    normalized_weights = state.get("normalized_weights", {})
    raw_weight_metadata = state.get("raw_weight_metadata", {})
    total_raw_weight  = state.get("total_raw_weight_value", 0.0)
    normalization_factor = state.get("normalization_factor", total_raw_weight)
    math_validation   = state.get("math_validation", {})
    jd_content_hash   = state.get("jd_content_hash", "")

    # Build scoring block
    scoring: Dict[str, Any] = {}
    for section in SCORING_SECTIONS:
        weight = normalized_weights.get(section, 0.0)
        meta = raw_weight_metadata.get(section, {})
        scoring[section] = {
            "weight": weight,
            "weight_generation_metadata": {
                "raw_weight":               meta.get("raw_weight", 0.0),
                "criteria_count":           meta.get("criteria_count", 0),
                "section_importance_factor": meta.get("section_importance_factor", 1.0),
                "normalization_factor":     round(normalization_factor, 4),
            },
            "criteria": criteria_scores.get(section, {}),
        }

    # Salary section (not part of scoring pipeline)
    scoring["salary"] = {
        "weight": 0.0,
        "fallback_score": 50.0,
        "criteria_based_on_salary_expectation": dict(SALARY_CRITERIA),
    }

    # Resolve position string
    position = extracted.get("position", "")
    if isinstance(position, dict):
        position = (
            "senior" if position.get("senior_level") else
            "mid"    if position.get("mid_level")    else
            "entry"  if position.get("entry_level")  else ""
        )

    # Resolve experience string
    min_years  = extracted.get("minimum_years")
    pref_years = extracted.get("preferred_years")
    exp_range  = extracted.get("experience_range", {})
    if min_years and pref_years:
        experience_str = f"{int(min_years)}-{int(pref_years)} years"
    elif min_years:
        experience_str = f"{int(min_years)}+ years"
    elif isinstance(exp_range, dict):
        if exp_range.get("<3_years") or exp_range.get("less_than_3_years"):
            experience_str = "<3 years"
        elif exp_range.get("3_4_years") or exp_range.get("three_4_years"):
            experience_str = "3-4 years"
        elif exp_range.get("5_7_years") or exp_range.get("five_7_years"):
            experience_str = "5-7 years"
        elif exp_range.get("8_plus_years") or exp_range.get("eight_plus_years"):
            experience_str = "8+ years"
        else:
            experience_str = ""
    else:
        experience_str = ""

    # Resolve qualification string
    qual = extracted.get("qualification", {})
    if isinstance(qual, dict):
        qual_str = ", ".join(
            d.capitalize()
            for d in ["phd", "masters", "bachelors", "associate", "diploma", "certification"]
            if qual.get(d)
        )
    else:
        qual_str = str(qual) if qual else ""

    work_mode = extracted.get("work_mode", {})
    if not isinstance(work_mode, dict):
        work_mode = {}

    final_schema = {
        "jd_content_hash": jd_content_hash,
        "weighting_metadata": {
            "weight_generation_strategy": "ontology_label_criteria_average_normalized",
            "normalization_applied": True,
            "total_raw_weight": round(total_raw_weight, 4),
            "normalized_total_weight": round(sum(normalized_weights.values()), 4),
            "hitl_review": {
                "reviewed_by_human": False,
                "review_stage": "pipeline_hitl_pause",
                "labels_modified": 0,
                "audit_log": [],
            },
            "mathematical_validation": math_validation,
        },
        "job_title":       extracted.get("job_title", ""),
        "experience":      experience_str,
        "qualification":   qual_str,
        "technologies":    extracted.get("technologies", []),
        "skills":          extracted.get("skills", []),
        "tools":           extracted.get("tools", []),
        "certifications":  extracted.get("certifications", []),
        "location":        extracted.get("location", ""),
        "position":        position if isinstance(position, str) else "",
        "job_description": extracted.get("job_description", ""),
        "responsibilities": extracted.get("responsibilities", []),
        "employment_type": extracted.get("employment_type", ""),
        "work_mode": {
            "remote_option":    bool(work_mode.get("remote_option", False)),
            "work_from_office": bool(work_mode.get("work_from_office", False)),
            "hybrid":           bool(work_mode.get("hybrid", False)),
        },
        "relevant_experience": extracted.get("relevant_experience", []),
        "scoring": scoring,
    }

    logger.info("Phase 14: Final schema assembled")
    return {**state, "final_weights_schema": final_schema}


# ═══════════════════════════════════════════════════════════════════════
# Build the Sub-Graph
# ═══════════════════════════════════════════════════════════════════════

def build_weight_assignment_graph():
    """
    Build and compile the 14-phase LangGraph weight assignment sub-graph.

    Flow:
        START → extract_jd_info
              → phase4_labels → phase5_validate → phase6_multipliers
              → phase7_scores → phase8_raw → phase9_factors
              → phase10_adjusted → phase11_total → phase12_normalize
              → phase13_validate → phase14_assemble → END
    """
    g = StateGraph(WeightAssignmentState)

    g.add_node("extract_jd_info",       step1_extract_jd_info)
    g.add_node("phase4_labels",         phase4_generate_reasoning_labels)
    g.add_node("phase5_validate",       phase5_validate_labels)
    g.add_node("phase6_multipliers",    phase6_assign_multipliers)
    g.add_node("phase7_scores",         phase7_compute_criteria_scores)
    g.add_node("phase8_raw",            phase8_compute_raw_weights)
    g.add_node("phase9_factors",        phase9_compute_importance_factors)
    g.add_node("phase10_adjusted",      phase10_compute_adjusted_weights)
    g.add_node("phase11_total",         phase11_compute_total_raw_weight)
    g.add_node("phase12_normalize",     phase12_normalize_weights)
    g.add_node("phase13_validate",      phase13_validate_math)
    g.add_node("phase14_assemble",      phase14_assemble_schema)

    g.add_edge(START,               "extract_jd_info")
    g.add_edge("extract_jd_info",   "phase4_labels")
    g.add_edge("phase4_labels",     "phase5_validate")
    g.add_edge("phase5_validate",   "phase6_multipliers")
    g.add_edge("phase6_multipliers","phase7_scores")
    g.add_edge("phase7_scores",     "phase8_raw")
    g.add_edge("phase8_raw",        "phase9_factors")
    g.add_edge("phase9_factors",    "phase10_adjusted")
    g.add_edge("phase10_adjusted",  "phase11_total")
    g.add_edge("phase11_total",     "phase12_normalize")
    g.add_edge("phase12_normalize", "phase13_validate")
    g.add_edge("phase13_validate",  "phase14_assemble")
    g.add_edge("phase14_assemble",  END)

    compiled = g.compile()
    logger.info("Weight assignment sub-graph compiled (14-phase enterprise pipeline)")
    return compiled


# ═══════════════════════════════════════════════════════════════════════
# Public API — Run the sub-graph
# ═══════════════════════════════════════════════════════════════════════

_weight_graph = None


def _get_weight_graph():
    global _weight_graph
    if _weight_graph is None:
        _weight_graph = build_weight_assignment_graph()
    return _weight_graph


async def run_weight_assignment(
    jd_normalized: Dict[str, Any],
    jd_content_hash: str,
    batch_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Run the 14-phase enterprise weight assignment pipeline.

    Args:
        jd_normalized:   Normalized JD from jd_normalize.py (Phases 2–3)
        jd_content_hash: SHA-256 content hash from extract_jd.py
        batch_id:        Optional batch identifier for token tracking

    Returns:
        final_weights_schema : Complete enterprise output (rich criteria format)
        validation_passed    : Whether Phase 13 math checks passed
        validation_errors    : Phase 13 error list
        raw_weight_metadata  : Per-section audit metadata (raw, factor, normalization)
        normalized_weights   : Per-section normalized weights
        normalization_factor : TotalRawWeight used as divisor in Phase 12
    """
    graph = _get_weight_graph()
    initial_state: WeightAssignmentState = {
        "jd_normalized":  jd_normalized,
        "jd_content_hash": jd_content_hash,
        "batch_id":       batch_id,
    }
    final_state = await graph.ainvoke(initial_state)

    return {
        "final_weights_schema": final_state.get("final_weights_schema", {}),
        "validation_passed":    final_state.get("validation_passed", False),
        "validation_errors":    final_state.get("validation_errors", []),
        "raw_weight_metadata":  final_state.get("raw_weight_metadata", {}),
        "normalized_weights":   final_state.get("normalized_weights", {}),
        "normalization_factor": final_state.get("normalization_factor", 0.0),
        "math_validation":      final_state.get("math_validation", {}),
    }
