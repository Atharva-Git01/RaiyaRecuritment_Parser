"""
JD Weight Assignment — Enterprise 14-Phase Pipeline (CLI + HITL)
=================================================================
Loads a DocStrange flat JSON extraction, runs the full enterprise
weight assignment pipeline, and saves the final audit-safe output.

Pipeline Architecture:
  Phase 4  ── LLM Reasoning Label Assignment (semantic only)
                 ↓
  HITL     ── Human review & approval of reasoning labels
                 ↓
  Phase 5  ── Reasoning Validation Engine
  Phase 6  ── Deterministic Multiplier Assignment
  Phase 7  ── Criteria Score Generation         (score = BASE × multiplier)
  Phase 8  ── Raw Section Weight Calculation    (avg of criteria scores)
  Phase 9  ── Section Importance Factor         (role-aware composite)
  Phase 10 ── Adjusted Raw Weight               (raw × factor)
  Phase 11 ── Total Raw Weight                  (sum of adjusted)
  Phase 12 ── Global Weight Normalization       (normalized to 100)
  Phase 13 ── Mathematical Validation Engine
  Phase 14 ── Audit Metadata Injection → FINAL JD WEIGHT JSON

Core Principle:
  LLM performs semantic reasoning ONLY.
  All scoring, normalization, and validation is deterministic Python.

Usage:
  python jd_weight_assignment.py                  # interactive CLI menu
  python jd_weight_assignment.py <path/to/jd.json> # direct file path
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from dotenv import load_dotenv

# ──────────────────────────────────────────────────────────────────────
# Paths
# ──────────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent
ROOT_DIR = BASE_DIR.parent

HASHED_JD_DIR     = BASE_DIR / "hashed_jd_extraction_results"
JD_JSON_DIR       = BASE_DIR / "jd_extraction_outputs"
WEIGHTS_OUTPUT_DIR = BASE_DIR / "jd_weight_json_output"
HASHED_WEIGHTS_DIR = BASE_DIR / "hashed_jd_weight_json_output"
LLM_METADATA_DIR  = BASE_DIR / "jd_weight_assignment_llm_metadata"

for _d in [WEIGHTS_OUTPUT_DIR, HASHED_WEIGHTS_DIR, LLM_METADATA_DIR]:
    _d.mkdir(parents=True, exist_ok=True)

load_dotenv(ROOT_DIR / ".env")

AZURE_ENDPOINT  = os.getenv("AZURE_OPENAI_ENDPOINT", "")
AZURE_API_KEY   = os.getenv("AZURE_OPENAI_API_KEY", "")
AZURE_DEPLOYMENT = os.getenv("AZURE_OPENAI_DEPLOYMENT", "mmresumeparser")
AZURE_API_VER   = os.getenv("AZURE_OPENAI_API_VERSION", "2024-12-01-preview")
AZURE_MODEL_NAME = os.getenv("AZURE_OPENAI_MODEL_NAME", "phi4")


# ======================================================================
# Phase 4 — Controlled Label Ontology
# ======================================================================

LABEL_MULTIPLIERS: Dict[str, float] = {
    "mandatory_core_skill": 1.00,
    "critical_requirement": 0.95,
    "important_skill":      0.80,
    "preferred_skill":      0.70,
    "supporting_skill":     0.55,
    "nice_to_have":         0.35,
    "irrelevant":           0.00,
}

_LABEL_ORDER: List[str] = [
    "mandatory_core_skill",
    "critical_requirement",
    "important_skill",
    "preferred_skill",
    "supporting_skill",
    "nice_to_have",
    "irrelevant",
]

BASE_SCORE: int = 100

# ── Phase 9 — Role-criticality table ──────────────────────────────────
_ROLE_CRITICALITY: Dict[str, Dict[str, float]] = {
    "technical": {
        "technologies":        0.90,
        "skills":              0.95,
        "tools":               0.65,
        "relevant_experience": 0.85,
        "experience":          0.70,
        "qualification":       0.65,
        "position":            0.60,
        "certifications":      0.55,
        "responsibilities":    0.70,
    },
    "non_technical": {
        "technologies":        0.50,
        "skills":              0.95,
        "tools":               0.45,
        "relevant_experience": 0.80,
        "experience":          0.85,
        "qualification":       0.80,
        "position":            0.75,
        "certifications":      0.45,
        "responsibilities":    0.85,
    },
}

_BUSINESS_PRIORITY: Dict[str, float] = {
    "technologies":        0.90,
    "skills":              0.95,
    "tools":               0.70,
    "relevant_experience": 0.85,
    "experience":          0.75,
    "qualification":       0.70,
    "position":            0.65,
    "certifications":      0.55,
    "responsibilities":    0.75,
}

_RETRIEVAL_IMPORTANCE: Dict[str, float] = {
    "technologies":        0.90,
    "skills":              0.85,
    "tools":               0.75,
    "relevant_experience": 0.80,
    "experience":          0.70,
    "qualification":       0.65,
    "position":            0.60,
    "certifications":      0.55,
    "responsibilities":    0.80,
}

_TECHNICAL_KEYWORDS = {
    "engineer", "developer", "architect", "analyst", "data", "software",
    "backend", "frontend", "fullstack", "devops", "ml", "ai", "cloud",
    "security", "qa", "test", "sre", "platform", "infrastructure",
}

# All pipeline sections (salary handled separately)
_PIPELINE_SECTIONS = {
    "technologies", "skills", "tools", "certifications",
    "responsibilities", "experience", "qualification",
    "position", "relevant_experience",
}


# ======================================================================
# Phase 4 — LLM System Prompt (semantic reasoning labels ONLY)
# ======================================================================

_SYSTEM_PROMPT = """\
You are a Recruitment Semantic Reasoning Agent.

Your ONLY task is to classify JD criteria into sections and assign reasoning
labels from the controlled ontology below. You do NOT calculate scores,
weights, or percentages — those are handled by a deterministic downstream
pipeline.

────────────────────────────────────────────────────────────
CONTROLLED LABEL ONTOLOGY  (use ONLY these 7 labels)
────────────────────────────────────────────────────────────
  mandatory_core_skill  — absolutely required; core to the role
  critical_requirement  — strongly required; nearly mandatory
  important_skill       — important but not blocking
  preferred_skill       — preferred / nice-to-have advantage
  supporting_skill      — secondary / complementary capability
  nice_to_have          — optional bonus
  irrelevant            — negligible or non-applicable

GROUNDING RULES
───────────────
1. Items in required_skills_and_competencies → use labels:
   mandatory_core_skill / critical_requirement / important_skill
2. Items in preferred_added_advantage → use labels:
   preferred_skill / supporting_skill / nice_to_have
3. Never label a preferred item as mandatory_core_skill or critical_requirement.
4. confidence must be between 0.0 and 1.0.
5. evidence must be a short quote or paraphrase from the JD text.
6. If confidence < 0.75 you MUST use a lower label (preferred_skill or below).
7. For fixed-bucket sections (experience, qualification, position,
   relevant_experience): assign labels to the canonical bucket keys based on
   the JD's stated requirements. Non-applicable buckets → irrelevant.

────────────────────────────────────────────────────────────
EXACT OUTPUT SCHEMA  (raw JSON only — no markdown, no comments)
────────────────────────────────────────────────────────────
{
  "job_info": {
    "job_title": "<string>",
    "experience": "<string>",
    "qualification": "<string>",
    "location": "<string>",
    "employment_type": "<string>",
    "position": "<string>",
    "work_mode": {"remote_option": false, "work_from_office": true, "hybrid": false},
    "responsibilities": ["<string>", ...],
    "job_description": "<brief role summary>"
  },
  "sections": {
    "technologies": {
      "<tech_name>": {"reasoning_label": "<label>", "confidence": 0.91, "evidence": "<quote>"}
    },
    "skills": {
      "<skill_name>": {"reasoning_label": "<label>", "confidence": 0.93, "evidence": "<quote>"}
    },
    "tools": {
      "<tool_name>": {"reasoning_label": "<label>", "confidence": 0.88, "evidence": "<quote>"}
    },
    "certifications": {
      "<cert_name>": {"reasoning_label": "<label>", "confidence": 0.85, "evidence": "<quote>"}
    },
    "responsibilities": {
      "<responsibility_text>": {"reasoning_label": "<label>", "confidence": 0.80, "evidence": "<quote>"}
    },
    "experience": {
      ">=8 years":  {"reasoning_label": "<label>", "confidence": 0.90, "evidence": "<quote>"},
      "5-7 years":  {"reasoning_label": "<label>", "confidence": 0.88, "evidence": "<quote>"},
      "3-4 years":  {"reasoning_label": "<label>", "confidence": 0.85, "evidence": "<quote>"},
      "<3 years":   {"reasoning_label": "<label>", "confidence": 0.92, "evidence": "<quote>"}
    },
    "qualification": {
      "PhD":           {"reasoning_label": "<label>", "confidence": 0.85, "evidence": "<quote>"},
      "Masters":       {"reasoning_label": "<label>", "confidence": 0.90, "evidence": "<quote>"},
      "Bachelors":     {"reasoning_label": "<label>", "confidence": 0.88, "evidence": "<quote>"},
      "Associate":     {"reasoning_label": "<label>", "confidence": 0.80, "evidence": "<quote>"},
      "Diploma":       {"reasoning_label": "<label>", "confidence": 0.82, "evidence": "<quote>"},
      "Certification": {"reasoning_label": "<label>", "confidence": 0.78, "evidence": "<quote>"}
    },
    "position": {
      "senior_level": {"reasoning_label": "<label>", "confidence": 0.88, "evidence": "<quote>"},
      "mid_level":    {"reasoning_label": "<label>", "confidence": 0.85, "evidence": "<quote>"},
      "entry_level":  {"reasoning_label": "<label>", "confidence": 0.90, "evidence": "<quote>"}
    },
    "relevant_experience": {
      ">=5 years_relevant": {"reasoning_label": "<label>", "confidence": 0.88, "evidence": "<quote>"},
      "3-4 years_relevant": {"reasoning_label": "<label>", "confidence": 0.85, "evidence": "<quote>"},
      "1-2 years_relevant": {"reasoning_label": "<label>", "confidence": 0.90, "evidence": "<quote>"},
      "<1 year_relevant":   {"reasoning_label": "<label>", "confidence": 0.92, "evidence": "<quote>"}
    }
  }
}

Rules:
- Return ONLY raw JSON. No markdown fences, no explanations.
- Every section key in "sections" is required; use empty {} if nothing applies.
- Do not add new top-level keys.
- Do not invent criteria not present in the JD.
"""

_USER_PROMPT_PREFIX = (
    "Analyze the following DocStrange JD extraction JSON and assign "
    "reasoning labels per the ontology:\n\n"
)


# ======================================================================
# Phase 4 — LLM Call
# ======================================================================

def call_llm_for_reasoning_labels(
    jd_text: str,
) -> Tuple[Optional[Dict[str, Any]], Dict[str, Any], Optional[str]]:
    """Phase 4: call LLM and return (llm_output, llm_meta, error_msg).

    llm_output shape: {"job_info": {...}, "sections": {...}}
    """
    try:
        from openai import AzureOpenAI
    except ImportError:
        return None, {}, "openai package not installed. Run: pip install openai"

    if not AZURE_API_KEY or not AZURE_ENDPOINT:
        return None, {}, "AZURE_OPENAI_API_KEY and AZURE_OPENAI_ENDPOINT must be set in .env"

    client = AzureOpenAI(
        azure_endpoint=AZURE_ENDPOINT,
        api_key=AZURE_API_KEY,
        api_version=AZURE_API_VER,
    )

    try:
        response = client.chat.completions.create(
            model=AZURE_DEPLOYMENT,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user",   "content": _USER_PROMPT_PREFIX + jd_text},
            ],
            temperature=0.0,
            max_tokens=4000,
        )
    except Exception as exc:
        return None, {}, f"LLM call failed: {exc}"

    usage = response.usage
    llm_meta: Dict[str, Any] = {
        "prompt_template_version": "jd-reasoning-label-v2.0",
        "model":      AZURE_MODEL_NAME,
        "deployment": AZURE_DEPLOYMENT,
        "usage": {
            "prompt_tokens":     usage.prompt_tokens     if usage else 0,
            "completion_tokens": usage.completion_tokens if usage else 0,
            "total_tokens":      usage.total_tokens      if usage else 0,
        },
        "system_fingerprint": response.system_fingerprint,
        "created_at": response.created or int(time.time()),
    }

    raw = response.choices[0].message.content.strip()
    if raw.startswith("```"):
        lines = raw.splitlines()
        lines = lines[1:] if lines[0].startswith("```") else lines
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        raw = "\n".join(lines).strip()

    try:
        llm_output = json.loads(raw)
    except json.JSONDecodeError as exc:
        return None, llm_meta, f"LLM returned invalid JSON: {exc}"

    return llm_output, llm_meta, None


# ======================================================================
# HITL — Human-in-the-Loop Label Review & Approval
# ======================================================================

_LABEL_SHORT: Dict[str, str] = {
    "mandatory_core_skill": "MANDATORY",
    "critical_requirement": "CRITICAL ",
    "important_skill":      "IMPORTANT",
    "preferred_skill":      "PREFERRED",
    "supporting_skill":     "SUPPORT  ",
    "nice_to_have":         "NICE2HAVE",
    "irrelevant":           "IRRELEVNT",
}

_LABEL_INDICES: Dict[str, int] = {lbl: i + 1 for i, lbl in enumerate(_LABEL_ORDER)}


def _print_labels_table(sections: Dict[str, Any]) -> None:
    """Pretty-print all reasoning labels in a scannable table."""
    SEP = "─" * 90
    print(f"\n{SEP}")
    print(f"  {'SECTION':<22}  {'CRITERION':<35}  {'LABEL':<22}  CONF")
    print(SEP)
    for section in _PIPELINE_SECTIONS:
        criteria = sections.get(section, {})
        if not isinstance(criteria, dict) or not criteria:
            continue
        for crit_key, entry in criteria.items():
            if not isinstance(entry, dict):
                continue
            label = entry.get("reasoning_label", "?")
            conf  = entry.get("confidence", 0.0)
            short = _LABEL_SHORT.get(label, label[:9].upper())
            print(f"  {section:<22}  {crit_key[:35]:<35}  {short:<22}  {conf:.2f}")
    print(SEP)


def _prompt_label_choice(current_label: str) -> str:
    """Interactively prompt the user to choose a new label."""
    print("\n  Available labels:")
    for i, lbl in enumerate(_LABEL_ORDER, 1):
        marker = " ◀ current" if lbl == current_label else ""
        print(f"    [{i}] {lbl}{marker}")
    while True:
        choice = input("  Enter label number (or Enter to keep current): ").strip()
        if not choice:
            return current_label
        if choice.isdigit():
            idx = int(choice) - 1
            if 0 <= idx < len(_LABEL_ORDER):
                return _LABEL_ORDER[idx]
        print("  ✗  Invalid. Enter a number 1–7 or press Enter.")


def hitl_review_labels(
    sections: Dict[str, Any],
    job_info: Dict[str, Any],
) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    """HITL checkpoint: human reviews and approves/modifies LLM reasoning labels.

    Returns:
        approved_sections — the (possibly modified) sections dict
        audit_log         — list of {section, criterion, original_label,
                                     approved_label, modified_by, timestamp}
    """
    audit_log: List[Dict[str, Any]] = []
    working = {s: dict(v) if isinstance(v, dict) else {} for s, v in sections.items()}

    # Deep-copy criteria entries so we can track changes
    for section in working:
        working[section] = {
            k: dict(v) if isinstance(v, dict) else v
            for k, v in working[section].items()
        }

    print("\n" + "=" * 90)
    print("  HITL — HUMAN-IN-THE-LOOP LABEL REVIEW")
    print("  Job: " + job_info.get("job_title", "Unknown"))
    print("=" * 90)
    print(
        "\n  The LLM has assigned reasoning labels to all JD criteria.\n"
        "  Review the labels below and approve or edit before scoring proceeds.\n"
    )

    while True:
        _print_labels_table(working)

        print(
            "\n  Options:\n"
            "    [a] Approve all labels and proceed\n"
            "    [e] Edit a specific label\n"
            "    [s] Edit all labels in a section\n"
            "    [r] Re-run LLM (discard edits and regenerate)\n"
            "    [v] View evidence for a criterion\n"
        )
        choice = input("  ▶ Choice: ").strip().lower()

        # ── Approve ──────────────────────────────────────────────────
        if choice == "a":
            total_edited = len(audit_log)
            print(
                f"\n  ✅  Labels approved"
                + (f" ({total_edited} manual edit(s) recorded)" if total_edited else " — no changes")
                + "\n"
            )
            break

        # ── Edit a single label ───────────────────────────────────────
        elif choice == "e":
            print("\n  Available sections:")
            active_sections = [s for s in _PIPELINE_SECTIONS if working.get(s)]
            for i, sec in enumerate(active_sections, 1):
                print(f"    [{i}] {sec}")
            sec_choice = input("  Section number: ").strip()
            if not sec_choice.isdigit() or not (1 <= int(sec_choice) <= len(active_sections)):
                print("  ✗  Invalid section.")
                continue
            section = active_sections[int(sec_choice) - 1]

            crit_keys = list(working[section].keys())
            print(f"\n  Criteria in '{section}':")
            for i, ck in enumerate(crit_keys, 1):
                entry = working[section][ck]
                lbl   = entry.get("reasoning_label", "?") if isinstance(entry, dict) else "?"
                print(f"    [{i}] {ck:<40}  {lbl}")
            crit_choice = input("  Criterion number: ").strip()
            if not crit_choice.isdigit() or not (1 <= int(crit_choice) <= len(crit_keys)):
                print("  ✗  Invalid criterion.")
                continue
            crit_key = crit_keys[int(crit_choice) - 1]
            entry    = working[section][crit_key]
            if not isinstance(entry, dict):
                continue
            original_label = entry.get("reasoning_label", "supporting_skill")

            print(f"\n  Editing: [{section}] → [{crit_key}]")
            print(f"  Current label: {original_label}  (confidence: {entry.get('confidence', 0):.2f})")
            print(f"  Evidence: {entry.get('evidence', 'N/A')}")
            new_label = _prompt_label_choice(original_label)

            if new_label != original_label:
                entry["reasoning_label"] = new_label
                entry["confidence"]      = 1.0
                entry["evidence"]        = entry.get("evidence", "") + " [HITL-modified]"
                working[section][crit_key] = entry
                audit_log.append({
                    "section":        section,
                    "criterion":      crit_key,
                    "original_label": original_label,
                    "approved_label": new_label,
                    "modified_by":    "human",
                    "timestamp":      datetime.now(timezone.utc).isoformat(),
                })
                print(f"  ✅  Updated: {original_label} → {new_label}")

        # ── Edit entire section ───────────────────────────────────────
        elif choice == "s":
            print("\n  Available sections:")
            active_sections = [s for s in _PIPELINE_SECTIONS if working.get(s)]
            for i, sec in enumerate(active_sections, 1):
                print(f"    [{i}] {sec}")
            sec_choice = input("  Section number: ").strip()
            if not sec_choice.isdigit() or not (1 <= int(sec_choice) <= len(active_sections)):
                print("  ✗  Invalid section.")
                continue
            section = active_sections[int(sec_choice) - 1]

            print(f"\n  Editing all criteria in '{section}':")
            for crit_key, entry in working[section].items():
                if not isinstance(entry, dict):
                    continue
                original_label = entry.get("reasoning_label", "supporting_skill")
                print(f"\n  → {crit_key}  (current: {original_label})")
                new_label = _prompt_label_choice(original_label)
                if new_label != original_label:
                    entry["reasoning_label"] = new_label
                    entry["confidence"]      = 1.0
                    entry["evidence"]        = entry.get("evidence", "") + " [HITL-modified]"
                    working[section][crit_key] = entry
                    audit_log.append({
                        "section":        section,
                        "criterion":      crit_key,
                        "original_label": original_label,
                        "approved_label": new_label,
                        "modified_by":    "human",
                        "timestamp":      datetime.now(timezone.utc).isoformat(),
                    })
                    print(f"  ✅  Updated: {original_label} → {new_label}")

        # ── View evidence ─────────────────────────────────────────────
        elif choice == "v":
            active_sections = [s for s in _PIPELINE_SECTIONS if working.get(s)]
            print("\n  Available sections:")
            for i, sec in enumerate(active_sections, 1):
                print(f"    [{i}] {sec}")
            sec_choice = input("  Section number: ").strip()
            if not sec_choice.isdigit() or not (1 <= int(sec_choice) <= len(active_sections)):
                print("  ✗  Invalid section.")
                continue
            section = active_sections[int(sec_choice) - 1]
            print(f"\n  Evidence for '{section}':")
            for crit_key, entry in working[section].items():
                if isinstance(entry, dict):
                    print(f"  • {crit_key}")
                    print(f"    Label:    {entry.get('reasoning_label', '?')}")
                    print(f"    Evidence: {entry.get('evidence', 'N/A')}\n")

        # ── Re-run LLM ────────────────────────────────────────────────
        elif choice == "r":
            print("\n  ↩  Signalling re-run — returning None to trigger LLM retry.\n")
            return {}, [{"action": "rerun", "timestamp": datetime.now(timezone.utc).isoformat()}]

        else:
            print("  ✗  Unknown option. Enter a, e, s, r, or v.")

    return working, audit_log


# ======================================================================
# Deterministic Pipeline — Phases 5–14
# ======================================================================

def _downgrade_label(label: str) -> str:
    try:
        idx = _LABEL_ORDER.index(label)
        return _LABEL_ORDER[min(idx + 1, len(_LABEL_ORDER) - 1)]
    except ValueError:
        return "supporting_skill"


def validate_reasoning_labels(sections: Dict[str, Any]) -> Dict[str, Any]:
    """Phase 5 — Validate and auto-correct labels after HITL approval."""
    corrected: Dict[str, Any] = {}
    for section, criteria in sections.items():
        corrected[section] = {}
        for key, entry in criteria.items():
            if not isinstance(entry, dict):
                continue
            label      = entry.get("reasoning_label", "supporting_skill")
            confidence = entry.get("confidence", 0.5)
            evidence   = entry.get("evidence", "")

            if label not in LABEL_MULTIPLIERS:
                label = "supporting_skill"
            if isinstance(confidence, (int, float)) and confidence < 0.75:
                label = _downgrade_label(label)
            if not isinstance(evidence, str) or len(evidence.strip()) < 5:
                label = _downgrade_label(label)
                evidence = "evidence not provided"

            corrected[section][key] = {
                "reasoning_label": label,
                "confidence":      float(confidence) if isinstance(confidence, (int, float)) else 0.5,
                "evidence":        evidence,
            }
    return corrected


def assign_multipliers(validated_sections: Dict[str, Any]) -> Dict[str, Any]:
    """Phase 6 — Map each reasoning_label → deterministic multiplier."""
    result: Dict[str, Any] = {}
    for section, criteria in validated_sections.items():
        result[section] = {}
        for key, entry in criteria.items():
            multiplier = LABEL_MULTIPLIERS.get(entry.get("reasoning_label", "supporting_skill"), 0.55)
            result[section][key] = {**entry, "multiplier": multiplier}
    return result


def compute_criteria_scores(sections_with_multipliers: Dict[str, Any]) -> Dict[str, Any]:
    """Phase 7 — CriteriaScore = BASE_SCORE × multiplier."""
    result: Dict[str, Any] = {}
    for section, criteria in sections_with_multipliers.items():
        result[section] = {}
        for key, entry in criteria.items():
            score = round(BASE_SCORE * entry.get("multiplier", 0.0), 4)
            result[section][key] = {**entry, "score": score}
    return result


def compute_raw_section_weights(scored_sections: Dict[str, Any]) -> Dict[str, float]:
    """Phase 8 — RawSectionWeight = sum(CriteriaScores) / CriteriaCount."""
    raw: Dict[str, float] = {}
    for section, criteria in scored_sections.items():
        scores = [v["score"] for v in criteria.values() if isinstance(v, dict) and "score" in v]
        raw[section] = sum(scores) / len(scores) if scores else 0.0
    return raw


def _is_technical_role(job_title: str) -> bool:
    return any(kw in job_title.lower() for kw in _TECHNICAL_KEYWORDS)


def compute_section_importance_factors(
    sections: Dict[str, Any],
    job_title: str,
    raw_weights: Dict[str, float],
) -> Dict[str, float]:
    """Phase 9 — SectionFactor = 0.4×RoleCriticality + 0.25×DensityScore
                                + 0.2×BusinessPriority + 0.15×RetrievalImportance.
    """
    role_type  = "technical" if _is_technical_role(job_title) else "non_technical"
    rc_map     = _ROLE_CRITICALITY[role_type]
    total_crit = sum(len(v) for v in sections.values() if isinstance(v, dict))

    factors: Dict[str, float] = {}
    for section in sections:
        count   = len(sections[section]) if isinstance(sections[section], dict) else 0
        density = count / total_crit if total_crit > 0 else 0.0
        rc = rc_map.get(section, 0.60)
        bp = _BUSINESS_PRIORITY.get(section, 0.65)
        ri = _RETRIEVAL_IMPORTANCE.get(section, 0.65)
        factors[section] = round(0.40 * rc + 0.25 * density + 0.20 * bp + 0.15 * ri, 4)
    return factors


def compute_adjusted_raw_weights(
    raw_weights: Dict[str, float],
    importance_factors: Dict[str, float],
) -> Dict[str, float]:
    """Phase 10 — AdjustedRawWeight = RawSectionWeight × SectionImportanceFactor."""
    return {
        s: round(raw_weights.get(s, 0.0) * importance_factors.get(s, 1.0), 4)
        for s in raw_weights
    }


def compute_total_raw_weight(adjusted_weights: Dict[str, float]) -> float:
    """Phase 11 — TotalRawWeight = sum of all AdjustedRawWeights."""
    return round(sum(adjusted_weights.values()), 4)


def normalize_weights(
    adjusted_weights: Dict[str, float],
    total_raw: float,
) -> Dict[str, float]:
    """Phase 12 — NormalizedWeight = (AdjustedRawWeight / TotalRawWeight) × 100.

    Rounding correction applied to the largest section so the sum is exactly 100.
    """
    if total_raw == 0:
        n = len(adjusted_weights)
        return {s: round(100.0 / n, 4) if n else 0.0 for s in adjusted_weights}

    normalized = {
        s: round((w / total_raw) * 100, 4)
        for s, w in adjusted_weights.items()
    }
    diff = round(100.0 - sum(normalized.values()), 4)
    if diff != 0 and normalized:
        largest = max(normalized, key=normalized.__getitem__)
        normalized[largest] = round(normalized[largest] + diff, 4)
    return normalized


def validate_math(normalized_weights: Dict[str, float]) -> Dict[str, Any]:
    """Phase 13 — Mathematical validation engine."""
    errors:   List[str] = []
    warnings: List[str] = []

    total = round(sum(normalized_weights.values()), 4)
    if abs(total - 100.0) > 0.5:
        errors.append(f"Normalized total = {total:.4f}, expected 100 (±0.5)")

    for section, w in normalized_weights.items():
        if w < 0:
            errors.append(f"Negative weight: {section} = {w:.4f}")

    values = list(normalized_weights.values())
    if len(values) > 1 and len({round(v, 2) for v in values}) == 1:
        warnings.append("Score collapse — all sections share identical weights")

    for section, w in normalized_weights.items():
        if w > 50.0:
            warnings.append(f"Section '{section}' dominates at {w:.2f}% (>50%)")

    if all(v == 0 for v in values):
        errors.append("All weights are zero — invalid distribution")

    mean     = sum(values) / len(values) if values else 0.0
    variance = sum((v - mean) ** 2 for v in values) / len(values) if values else 0.0

    return {
        "is_valid":              len(errors) == 0,
        "normalized_total_weight": total,
        "variance_score":        round(variance, 4),
        "section_balance_valid": len(warnings) == 0,
        "errors":                errors,
        "warnings":              warnings,
    }


def build_final_weight_json(
    sections_with_scores:  Dict[str, Any],
    normalized_weights:    Dict[str, float],
    adjusted_raw_weights:  Dict[str, float],
    raw_section_weights:   Dict[str, float],
    importance_factors:    Dict[str, float],
    total_raw_weight:      float,
    math_validation:       Dict[str, Any],
    job_info:              Dict[str, Any],
    jd_content_hash:       str,
    hitl_audit_log:        List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Phase 14 — Assemble final enterprise output JSON."""

    scoring: Dict[str, Any] = {}
    for section, criteria in sections_with_scores.items():
        criteria_out: Dict[str, Any] = {}
        for key, entry in criteria.items():
            criteria_out[key] = {
                "score":           entry.get("score", 0.0),
                "reasoning_label": entry.get("reasoning_label", "supporting_skill"),
                "multiplier":      entry.get("multiplier", 0.0),
                "confidence":      entry.get("confidence", 0.5),
                "evidence":        entry.get("evidence", ""),
            }
        scoring[section] = {
            "weight": normalized_weights.get(section, 0.0),
            "weight_generation_metadata": {
                "raw_weight":               round(raw_section_weights.get(section, 0.0), 4),
                "criteria_count":           len(criteria),
                "section_importance_factor": round(importance_factors.get(section, 1.0), 4),
                "normalization_factor":     total_raw_weight,
            },
            "criteria": criteria_out,
        }

    # Ensure all canonical scoring sections exist
    for sec in ["relevant_experience", "experience", "qualification",
                "technologies", "skills", "position", "tools",
                "certifications", "responsibilities"]:
        if sec not in scoring:
            scoring[sec] = {
                "weight": 0.0,
                "weight_generation_metadata": {
                    "raw_weight": 0.0, "criteria_count": 0,
                    "section_importance_factor": 0.0,
                    "normalization_factor": total_raw_weight,
                },
                "criteria": {},
            }

    wm = job_info.get("work_mode", {})
    if not isinstance(wm, dict):
        wm = {"remote_option": False, "work_from_office": True, "hybrid": False}

    responsibilities_list = job_info.get("responsibilities", [])
    if not isinstance(responsibilities_list, list):
        responsibilities_list = []

    return {
        "jd_content_hash": jd_content_hash,

        "weighting_metadata": {
            "weight_generation_strategy": "ontology_label_criteria_average_normalized",
            "normalization_applied":       True,
            "total_raw_weight":            total_raw_weight,
            "normalized_total_weight":     math_validation.get("normalized_total_weight", 100.0),
            "hitl_review": {
                "reviewed_by_human":   True,
                "labels_modified":     len([e for e in hitl_audit_log if e.get("modified_by") == "human"]),
                "audit_log":           hitl_audit_log,
            },
            "mathematical_validation": {
                "is_valid":                math_validation.get("is_valid", False),
                "section_balance_valid":   math_validation.get("section_balance_valid", True),
                "score_distribution_valid": len(math_validation.get("errors", [])) == 0,
                "variance_score":          math_validation.get("variance_score", 0.0),
            },
        },

        "job_title":        job_info.get("job_title", "Not specified"),
        "experience":       job_info.get("experience", "Not specified"),
        "qualification":    job_info.get("qualification", "Not specified"),
        "technologies":     list(sections_with_scores.get("technologies", {}).keys()),
        "relevant_experience": [],
        "skills":           list(sections_with_scores.get("skills", {}).keys()),
        "tools":            list(sections_with_scores.get("tools", {}).keys()),
        "certifications":   list(sections_with_scores.get("certifications", {}).keys()),
        "location":         job_info.get("location", "Not specified"),
        "position":         job_info.get("position", "Not specified"),
        "job_description":  job_info.get("job_description", "Not specified"),
        "responsibilities": responsibilities_list,
        "employment_type":  job_info.get("employment_type", "Not specified"),
        "work_mode": {
            "remote_option":    bool(wm.get("remote_option", False)),
            "work_from_office": bool(wm.get("work_from_office", True)),
            "hybrid":           bool(wm.get("hybrid", False)),
        },

        "scoring": scoring,

        "salary": {
            "weight": 0.0,
            "fallback_score": 50.0,
            "criteria_based_on_salary_expectation": {
                "3-6": 0.0, "6-10": 0.0, ">10": 0.0,
            },
        },
    }


# ======================================================================
# Master Orchestrator
# ======================================================================

def assign_jd_weights(
    jd_json:        Dict[str, Any],
    jd_content_hash: str = "",
    skip_hitl:      bool = False,
) -> Tuple[Optional[Dict[str, Any]], Dict[str, Any], Optional[str]]:
    """Run the full 14-phase pipeline for a given JD extraction JSON.

    Args:
        jd_json:         DocStrange flat JSON extraction result.
        jd_content_hash: SHA-256 of the source JD file (injected into output).
        skip_hitl:       If True, auto-approve labels without CLI interaction.

    Returns:
        (final_weight_json, llm_meta_and_audit, error_msg)
    """
    jd_text = json.dumps(jd_json, indent=2, ensure_ascii=False)

    max_llm_retries = 3
    llm_output: Optional[Dict[str, Any]] = None
    llm_meta:   Dict[str, Any]           = {}

    for attempt in range(1, max_llm_retries + 1):
        print(f"\n  [Phase 4] Calling LLM for reasoning labels (attempt {attempt}/{max_llm_retries})...")
        llm_output, llm_meta, err = call_llm_for_reasoning_labels(jd_text)
        if err:
            print(f"  [!] LLM error: {err}")
            if attempt == max_llm_retries:
                return None, llm_meta, err
            continue

        sections = llm_output.get("sections", {})  # type: ignore[union-attr]
        job_info = llm_output.get("job_info", {})   # type: ignore[union-attr]
        print(f"  [✓] LLM returned labels for {len(sections)} section(s).")

        # ── HITL ──────────────────────────────────────────────────────
        if skip_hitl:
            print("  [Phase HITL] Auto-approving labels (skip_hitl=True).")
            approved_sections = sections
            hitl_audit_log: List[Dict[str, Any]] = []
        else:
            approved_sections, hitl_audit_log = hitl_review_labels(sections, job_info)
            # If user chose to re-run LLM
            if hitl_audit_log and hitl_audit_log[0].get("action") == "rerun":
                print("  [↩] Re-running LLM as requested...")
                continue

        # Break retry loop — labels approved
        break
    else:
        return None, llm_meta, "LLM failed after maximum retries."

    # Keep only pipeline sections
    pipeline_sections = {
        k: v for k, v in approved_sections.items()
        if k in _PIPELINE_SECTIONS and isinstance(v, dict) and v
    }

    job_title = job_info.get("job_title", "")  # type: ignore[union-attr]

    print(f"\n  [Phase 5]  Validating reasoning labels...")
    validated = validate_reasoning_labels(pipeline_sections)

    print(f"  [Phase 6]  Assigning multipliers...")
    with_multipliers = assign_multipliers(validated)

    print(f"  [Phase 7]  Computing criteria scores...")
    with_scores = compute_criteria_scores(with_multipliers)

    print(f"  [Phase 8]  Computing raw section weights...")
    raw_weights = compute_raw_section_weights(with_scores)

    print(f"  [Phase 9]  Computing section importance factors...")
    importance_factors = compute_section_importance_factors(
        pipeline_sections, job_title, raw_weights
    )

    print(f"  [Phase 10] Computing adjusted raw weights...")
    adjusted = compute_adjusted_raw_weights(raw_weights, importance_factors)

    print(f"  [Phase 11] Computing total raw weight...")
    total_raw = compute_total_raw_weight(adjusted)

    print(f"  [Phase 12] Normalizing weights to 100...")
    normalized = normalize_weights(adjusted, total_raw)

    print(f"  [Phase 13] Running mathematical validation...")
    math_val = validate_math(normalized)

    if math_val["is_valid"]:
        print(f"  [✓] Math validation PASSED — total={math_val['normalized_total_weight']:.4f}, "
              f"variance={math_val['variance_score']:.4f}")
    else:
        print(f"  [!] Math validation ISSUES: {math_val['errors']}")

    print(f"  [Phase 14] Assembling final output JSON...")
    final_json = build_final_weight_json(
        sections_with_scores=with_scores,
        normalized_weights=normalized,
        adjusted_raw_weights=adjusted,
        raw_section_weights=raw_weights,
        importance_factors=importance_factors,
        total_raw_weight=total_raw,
        math_validation=math_val,
        job_info=job_info,  # type: ignore[arg-type]
        jd_content_hash=jd_content_hash,
        hitl_audit_log=hitl_audit_log,
    )

    llm_meta["phases_executed"]   = "4-HITL-5-14"
    llm_meta["math_validation"]   = math_val
    llm_meta["hitl_labels_modified"] = len(
        [e for e in hitl_audit_log if e.get("modified_by") == "human"]
    )

    return final_json, llm_meta, None


# ======================================================================
# Utility Helpers
# ======================================================================

def _compute_file_hash(filepath: Path) -> str:
    sha = hashlib.sha256()
    with open(filepath, "rb") as fh:
        for chunk in iter(lambda: fh.read(8192), b""):
            sha.update(chunk)
    return sha.hexdigest()


def _unwrap_jd_data(raw: Dict[str, Any]) -> Dict[str, Any]:
    """Navigate through optional docstrange wrappers to reach flat JD content."""
    if "structured_data" in raw and isinstance(raw["structured_data"], dict):
        sd = raw["structured_data"]
        if "content" in sd and isinstance(sd["content"], dict):
            return sd["content"]
        return sd
    if "document" in raw:
        doc = raw["document"]
        if isinstance(doc, dict):
            return doc
        if isinstance(doc, list):
            merged: Dict[str, Any] = {}
            for item in doc:
                if isinstance(item, dict):
                    merged.update(item)
            return merged
    return raw


def _discover_jd_json_files() -> List[Path]:
    files: List[Path] = []
    for directory in [HASHED_JD_DIR, JD_JSON_DIR]:
        if directory.exists():
            for f in sorted(directory.iterdir(), key=lambda p: p.name.lower()):
                if f.is_file() and f.suffix.lower() == ".json" and not f.name.endswith(".meta.json"):
                    files.append(f)
    return files


def _save_output(
    final_json: Dict[str, Any],
    llm_meta:   Dict[str, Any],
    source_file: str,
    jd_hash:    str,
    is_hitl:    bool,
) -> Path:
    """Persist weight JSON + hashed copy + metadata sidecar."""
    stem         = Path(source_file).stem
    out_filename = f"{stem}_weights.json"
    out_path     = WEIGHTS_OUTPUT_DIR / out_filename

    out_path.write_text(json.dumps(final_json, indent=2, ensure_ascii=False), encoding="utf-8")

    weight_hash = hashlib.sha256(
        json.dumps(final_json, sort_keys=True).encode("utf-8")
    ).hexdigest()
    hashed_path = HASHED_WEIGHTS_DIR / f"{jd_hash}.json"
    hashed_path.write_text(json.dumps(final_json, indent=2, ensure_ascii=False), encoding="utf-8")

    meta = {
        "jd_content_hash": jd_hash,
        "weight_hash":     weight_hash,
        "source_file":     source_file,
        "created_at":      datetime.now(timezone.utc).isoformat(),
        "workflow_mode":   "llm_enterprise_pipeline_hitl" if is_hitl else "llm_enterprise_pipeline",
        "phases_executed": "4-HITL-5-14",
    }
    (HASHED_WEIGHTS_DIR / f"{jd_hash}.meta.json").write_text(
        json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    llm_meta["jd_content_hash"] = jd_hash
    llm_meta["source_file"]     = source_file
    (LLM_METADATA_DIR / f"{jd_hash}.meta.json").write_text(
        json.dumps(llm_meta, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    return out_path


# ======================================================================
# CLI Entry Point
# ======================================================================

def _print_header() -> None:
    print("\n" + "=" * 70)
    print("  JD WEIGHT ASSIGNMENT — Enterprise 14-Phase Pipeline")
    print("  LLM Semantic Reasoning + HITL Approval + Deterministic Scoring")
    print("=" * 70)


def main(argv: Optional[List[str]] = None) -> None:  # noqa: C901
    args = argv or sys.argv[1:]

    _print_header()

    # ── Resolve input file ────────────────────────────────────────────
    if args:
        jd_path = Path(args[0])
        if not jd_path.exists():
            print(f"\n  [x] File not found: {jd_path}")
            sys.exit(1)
    else:
        jd_files = _discover_jd_json_files()
        if not jd_files:
            print(f"\n  [x] No JD JSON files found in {HASHED_JD_DIR} or {JD_JSON_DIR}")
            sys.exit(1)

        print(f"\n  Available JD extraction files:\n")
        for idx, f in enumerate(jd_files, 1):
            size_kb = f.stat().st_size / 1024
            print(f"    [{idx:2}]  {f.name:<55}  ({size_kb:.1f} KB)")
        print(f"\n    [ 0]  Exit")
        print("-" * 70)

        while True:
            choice = input("\n  ▶ Select file number: ").strip()
            if choice == "0":
                print("  Goodbye!\n")
                sys.exit(0)
            if choice.isdigit() and 1 <= int(choice) <= len(jd_files):
                jd_path = jd_files[int(choice) - 1]
                break
            print("  ✗  Invalid selection. Try again.")

    # ── HITL mode? ────────────────────────────────────────────────────
    hitl_choice = input("\n  Enable HITL label review? [Y/n]: ").strip().lower()
    skip_hitl   = hitl_choice == "n"

    # ── Load + unwrap ─────────────────────────────────────────────────
    print(f"\n  Loading: {jd_path.name}")
    try:
        raw = json.loads(jd_path.read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"  [x] Failed to read file: {exc}")
        sys.exit(1)

    jd_data = _unwrap_jd_data(raw)

    # Use stored hash if present, otherwise compute from file
    jd_hash = (
        raw.get("pipeline_metadata", {}).get("jd_content_hash", "")
        or _compute_file_hash(jd_path)
    )
    print(f"  SHA-256: {jd_hash[:32]}…")

    # ── Run pipeline ──────────────────────────────────────────────────
    final_json, llm_meta, error = assign_jd_weights(
        jd_json=jd_data,
        jd_content_hash=jd_hash,
        skip_hitl=skip_hitl,
    )

    if error:
        print(f"\n  [x] Pipeline failed: {error}\n")
        sys.exit(1)

    # ── Print weight summary ──────────────────────────────────────────
    print("\n" + "─" * 70)
    print("  FINAL NORMALIZED WEIGHTS")
    print("─" * 70)
    scoring = final_json.get("scoring", {})  # type: ignore[union-attr]
    total   = 0.0
    for sec_name, sec_data in scoring.items():
        w = sec_data.get("weight", 0.0)
        total += w
        n_criteria = len(sec_data.get("criteria", {}))
        bar        = "█" * int(w / 3)
        print(f"  {sec_name:<25}  {w:6.2f}%  {bar}  ({n_criteria} criteria)")
    print(f"  {'TOTAL':<25}  {total:6.2f}%")

    mv = final_json.get("weighting_metadata", {}).get("mathematical_validation", {})  # type: ignore[union-attr]
    status = "✅ VALID" if mv.get("is_valid") else "⚠️  ISSUES"
    print(f"\n  Math validation: {status}")

    hitl_info = final_json.get("weighting_metadata", {}).get("hitl_review", {})  # type: ignore[union-attr]
    if not skip_hitl:
        print(f"  HITL labels modified: {hitl_info.get('labels_modified', 0)}")

    # ── Save ──────────────────────────────────────────────────────────
    save_choice = input("\n  Save output? [Y/n]: ").strip().lower()
    if save_choice != "n":
        out_path = _save_output(
            final_json=final_json,  # type: ignore[arg-type]
            llm_meta=llm_meta,
            source_file=jd_path.name,
            jd_hash=jd_hash,
            is_hitl=not skip_hitl,
        )
        print(f"\n  [✓] Saved → {out_path}")
        print(f"  [✓] Hashed → {HASHED_WEIGHTS_DIR.name}/{jd_hash[:16]}….json")
        print(f"  [✓] LLM metadata → {LLM_METADATA_DIR.name}/{jd_hash[:16]}….meta.json\n")
    else:
        print("  (Not saved.)\n")


if __name__ == "__main__":
    main()
