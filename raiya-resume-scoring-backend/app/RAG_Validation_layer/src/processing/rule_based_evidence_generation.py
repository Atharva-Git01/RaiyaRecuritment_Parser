"""
Rule-Based Evidence Generation
================================
Processes each scoring section from the **normalized JD** (validated_jd.json)
against the **AI scorer output** to produce per-criterion evidence.

DYNAMIC RULE GENERATION:
Instead of loading external rules, this script ANALYZES the JD and Resume 
to DYNAMICALLY CREATE rules that flag potential issues (e.g., intern bias, 
short tenure, missing summary). These rules follow the evidence_rules.json schema.

"""

from __future__ import annotations

import json
import os
import re
import uuid
import datetime
from typing import Any, Dict, List, Optional, Tuple

from src.config import settings
from src.logging_config import logger

# ---------------------------------------------------------------------------
# Default paths from settings
# ---------------------------------------------------------------------------
DEFAULT_VALIDATED_JD   = settings.VALIDATED_JD_PATH
DEFAULT_AI_SCORE_INPUT = settings.DEFAULT_AI_INPUT
DEFAULT_OUT_DIR        = settings.OUTPUT_DIR
DEFAULT_OUT_PATH       = settings.RULE_EVD_OUT_PATH

# Scoring accuracy tolerance — delta within this range is "accurate"
ACCURACY_TOLERANCE = 10.0

# ---------------------------------------------------------------------------
# Resume extraction helpers
# ---------------------------------------------------------------------------

_SECTION_RESUME_MAP: Dict[str, List[str]] = {
    "skills":           ["skills", "projects", "experience"],
    "technologies":     ["technologies", "skills", "projects", "experience"],
    "tools":            ["tools", "skills", "projects"],
    "projects":         ["projects"],
    "certificates":     ["certifications"],
    "responsibilities": ["experience"],
}


def _flatten_resume_field(resume: Dict[str, Any], field: str) -> List[str]:
    """Flatten a single resume field into a list of text tokens."""
    val = resume.get(field)
    if val is None:
        return []
    items: List[str] = []
    if isinstance(val, list):
        for item in val:
            if isinstance(item, str):
                items.append(item)
            elif isinstance(item, dict):
                for sub in ("name", "title", "description", "degree", "normalized_degree", "institution", "normalized_role"):
                    sv = item.get(sub, "")
                    if sv: items.append(str(sv))
                for resp in item.get("responsibilities", []):
                    items.append(str(resp))
                for tech in item.get("technologies", []):
                    items.append(str(tech))
    elif isinstance(val, dict):
        items.extend(str(v) for v in val.values() if v)
    elif isinstance(val, str) and val:
        items.append(val)
    return items


def _collect_resume_items(section: str, resume: Dict[str, Any]) -> List[str]:
    """Collect all relevant resume text items for a given scoring section."""
    fields = _SECTION_RESUME_MAP.get(section, [section])
    items: List[str] = []
    for field in fields:
        items.extend(_flatten_resume_field(resume, field))
    return items


# ---------------------------------------------------------------------------
# Matching & Math Helpers
# ---------------------------------------------------------------------------

def _match_keyword(criterion: str, resume_items: List[str]) -> Tuple[bool, Optional[str]]:
    c_lower = criterion.lower().strip()
    for item in resume_items:
        item_lower = item.lower().strip()
        if c_lower == item_lower:
            return True, f"Exact match: '{item}'"
        pattern = r"\b" + re.escape(c_lower) + r"\b"
        if re.search(pattern, item_lower):
            return True, f"Found '{criterion}' in '{item}'"
    return False, None


def _extract_years(resume: Dict[str, Any]) -> float:
    exp_list = resume.get("experience", [])
    if not isinstance(exp_list, list): return 0.0
    total = 0.0
    for entry in exp_list:
        if not isinstance(entry, dict): continue
        start, end = entry.get("start", ""), entry.get("end", "")
        if start:
            try:
                s_parts = str(start).split("-")
                s_year, s_month = int(s_parts[0]), int(s_parts[1]) if len(s_parts) > 1 else 1
                if end and str(end).lower() not in ("present", "current", ""):
                    e_parts = str(end).split("-")
                    e_year, e_month = int(e_parts[0]), int(e_parts[1]) if len(e_parts) > 1 else 12
                else:
                    now = datetime.datetime.now()
                    e_year, e_month = now.year, now.month
                months = (e_year - s_year) * 12 + (e_month - s_month)
                total += max(months / 12.0, 0.0)
                continue
            except (ValueError, IndexError): pass
        total += 0.5
    return round(total, 2)


def _avg_duration_months(resume: Dict[str, Any]) -> float:
    exp_list = resume.get("experience", [])
    if not isinstance(exp_list, list) or not exp_list: return 0.0
    durations: List[float] = []
    for entry in exp_list:
        if not isinstance(entry, dict): continue
        start, end = entry.get("start", ""), entry.get("end", "")
        if start:
            try:
                s_parts = str(start).split("-")
                s_year, s_month = int(s_parts[0]), int(s_parts[1]) if len(s_parts) > 1 else 1
                if end and str(end).lower() not in ("present", "current", ""):
                    e_parts = str(end).split("-")
                    e_year, e_month = int(e_parts[0]), int(e_parts[1]) if len(e_parts) > 1 else 12
                else:
                    now = datetime.datetime.now()
                    e_year, e_month = now.year, now.month
                months = (e_year - s_year) * 12 + (e_month - s_month)
                durations.append(max(months, 0.0))
                continue
            except (ValueError, IndexError): pass
        durations.append(6.0)
    return round(sum(durations) / len(durations), 2) if durations else 0.0


def _extract_salary_lpa(resume: Dict[str, Any]) -> float:
    """Extract salary in LPA from the resume."""
    sal = resume.get("salary_expectation", 0)
    if isinstance(sal, dict):
        val = float(sal.get("value", 0))
    else:
        m = re.search(r"(\d+(\.\d+)?)", str(sal))
        val = float(m.group(1)) if m else 0.0
    # Convert to LPA if looks like raw INR (e.g. 500,000 -> 5.0)
    return val / 100000 if val > 1000 else val


# ---------------------------------------------------------------------------
# DYNAMIC RULE GENERATORS (Detectors)
# ---------------------------------------------------------------------------

def _generate_dynamic_rules(
    validated_jd: Dict[str, Any],
    resume: Dict[str, Any],
    ai_result: Dict[str, Any],
    base_evals: Dict[str, Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    Analyzes JD, Resume, and AI Scorer result to generate evidence rules
    dynamically. Returns a list of rules in evidence_rules.json format.

    Detectors
    ---------
     1. Internship Bias
     2. Missing Summary
     3. Job Hopping (Short Tenure)
     4. AI Over-estimation (per-section)
     5. Experience Below JD Minimum
     6. Qualification Gap
     7. Low Skill Coverage
     8. Zero-Weight Section Non-Zero Score
     9. Salary Mismatch
    10. Missing Certifications
    11. Missing Projects
    12. Low Tool Coverage
    13. Position Level Mismatch
    14. Single Employer Bias
    """
    rules: List[Dict[str, Any]] = []
    scoring = validated_jd.get("scoring", {})
    exp_entries = resume.get("experience", [])
    if not isinstance(exp_entries, list):
        exp_entries = []
    total_years = _extract_years(resume)

    # ── 1. Internship Bias Detector ──────────────────────────────────────
    if exp_entries:
        intern_keywords = {"intern", "trainee", "steward", "apprentice",
                           "fresher", "junior trainee"}
        intern_count = 0
        for e in exp_entries:
            title = str(e.get("title", "")).lower()
            role  = str(e.get("normalized_role", "")).lower()
            if any(k in title or k in role for k in intern_keywords):
                intern_count += 1
        ratio = intern_count / len(exp_entries)
        if ratio >= 0.5:
            rules.append({
                "id": "rule_intern_experience",
                "description": (
                    f"Candidate's experience is {ratio*100:.0f}% Intern/Trainee "
                    f"roles. AI might be over-valuing seniority."
                ),
                "condition": {
                    "field": "resume.experience",
                    "operator": "contains_keyword_ratio",
                    "keyword": "intern|trainee",
                    "threshold": 0.5
                },
                "action": {
                    "target": "experience_score",
                    "operation": "cap",
                    "value": 50
                }
            })

    # ── 2. Missing Summary Detector ──────────────────────────────────────
    summary_txt = resume.get("summary", "")
    if not summary_txt or len(str(summary_txt).strip()) < 10:
        rules.append({
            "id": "rule_missing_summary",
            "description": (
                "Professional summary is missing or too short. "
                "Impacting responsibilities/soft-skills validation."
            ),
            "condition": {
                "field": "resume.summary",
                "operator": "empty"
            },
            "action": {
                "target": "responsibilities_score",
                "operation": "cap",
                "value": 40
            }
        })

    # ── 3. Job Hopping (Short Tenure) Detector ───────────────────────────
    avg_tenure = _avg_duration_months(resume)
    if avg_tenure > 0 and avg_tenure < 7:
        rules.append({
            "id": "rule_short_tenure",
            "description": (
                f"Average job duration is only {avg_tenure:.1f} months. "
                f"Possible job hopping risk."
            ),
            "condition": {
                "field": "resume.experience",
                "operator": "avg_duration_months_lt",
                "value": 7
            },
            "action": {
                "target": "experience_score",
                "operation": "multiply",
                "value": 0.8
            }
        })

    # ── 4. AI Over-estimation Detector (per section) ─────────────────────
    for section, eval_res in base_evals.items():
        ai_val = float(ai_result.get(f"{section}_score", 0))
        gt_val = float(eval_res.get("coverage_pct", 0))
        delta  = ai_val - gt_val
        if delta > 40:
            rules.append({
                "id": f"rule_ai_overestimation_{section}",
                "description": (
                    f"AI {section} score ({ai_val}) is significantly higher "
                    f"than exact keyword match ({gt_val}%). "
                    f"High hallucination risk."
                ),
                "condition": {
                    "field": f"ai_result.{section}_score",
                    "operator": "value_gt",
                    "value": gt_val + 30
                },
                "action": {
                    "target": f"{section}_score",
                    "operation": "subtract",
                    "value": round(delta * 0.5, 2)
                }
            })

    # ── 5. Experience Below JD Minimum ───────────────────────────────────
    exp_range = validated_jd.get("experience_range", {})
    jd_min_years = float(exp_range.get("min", 0))
    if jd_min_years > 0 and total_years < jd_min_years:
        gap = round(jd_min_years - total_years, 1)
        # Penalty proportional to how far below the minimum
        penalty_factor = max(0.5, 1.0 - (gap / jd_min_years))
        rules.append({
            "id": "rule_experience_below_minimum",
            "description": (
                f"JD requires minimum {jd_min_years} years but candidate "
                f"has only {total_years} years ({gap} years short). "
                f"Experience score should be penalised."
            ),
            "condition": {
                "field": "resume.total_years",
                "operator": "value_lt",
                "value": jd_min_years
            },
            "action": {
                "target": "experience_score",
                "operation": "multiply",
                "value": round(penalty_factor, 2)
            }
        })

    # ── 6. Qualification Gap Detector ────────────────────────────────────
    jd_qual = str(validated_jd.get("qualification", "")).lower()
    edu_list = resume.get("education", [])
    candidate_degrees = []
    for e in edu_list:
        if isinstance(e, dict):
            nd = e.get("normalized_degree", "") or e.get("degree", "")
            if nd:
                candidate_degrees.append(str(nd).lower())

    if "master" in jd_qual or "m.tech" in jd_qual or "mca" in jd_qual:
        has_master = any("master" in d for d in candidate_degrees)
        if not has_master:
            rules.append({
                "id": "rule_qualification_gap",
                "description": (
                    f"JD prefers Master's level qualification but candidate "
                    f"has: {candidate_degrees or ['no degree listed']}. "
                    f"Qualification score may be inflated."
                ),
                "condition": {
                    "field": "resume.education",
                    "operator": "missing_degree_level",
                    "required": "master"
                },
                "action": {
                    "target": "qualification_score",
                    "operation": "cap",
                    "value": 80
                }
            })

    # ── 7. Low Skill Coverage Detector ───────────────────────────────────
    skills_eval = base_evals.get("skills", {})
    skills_total = skills_eval.get("total_criteria", 0)
    skills_matched = skills_eval.get("matched_count", 0)
    if skills_total > 0:
        skill_match_ratio = skills_matched / skills_total
        if skill_match_ratio < 0.25:
            rules.append({
                "id": "rule_low_skill_coverage",
                "description": (
                    f"Only {skills_matched}/{skills_total} JD skills "
                    f"({skill_match_ratio*100:.0f}%) matched in resume. "
                    f"Coverage is critically low."
                ),
                "condition": {
                    "field": "eval.skills.match_ratio",
                    "operator": "value_lt",
                    "value": 0.25
                },
                "action": {
                    "target": "skills_score",
                    "operation": "cap",
                    "value": 40
                }
            })

    # ── 8. Zero-Weight Section Non-Zero Score Detector ────────────────────
    for section, sec_rules in scoring.items():
        sec_weight = float(sec_rules.get("weight", 0))
        ai_sec_score = float(ai_result.get(f"{section}_score", 0))
        if sec_weight == 0 and ai_sec_score > 0:
            rules.append({
                "id": f"rule_zero_weight_nonzero_score_{section}",
                "description": (
                    f"Section '{section}' has weight=0 in JD but AI assigned "
                    f"score={ai_sec_score}. Score should be 0."
                ),
                "condition": {
                    "field": f"scoring.{section}.weight",
                    "operator": "value_eq",
                    "value": 0
                },
                "action": {
                    "target": f"{section}_score",
                    "operation": "cap",
                    "value": 0
                }
            })

    # ── 9. Salary Mismatch Detector ──────────────────────────────────────
    candidate_lpa = _extract_salary_lpa(resume)
    salary_eval = base_evals.get("salary", {})
    salary_bracket = salary_eval.get("matched_bracket", "")
    salary_coverage = salary_eval.get("coverage_pct", 0)
    ai_salary = float(ai_result.get("salary_score", 0))
    # If AI gave high salary score but bracket coverage is low
    if candidate_lpa > 0 and ai_salary > salary_coverage + 30:
        rules.append({
            "id": "rule_salary_mismatch",
            "description": (
                f"Candidate salary {candidate_lpa} LPA (bracket: '{salary_bracket}', "
                f"coverage={salary_coverage}%) but AI scored {ai_salary}. "
                f"Potential salary score inflation."
            ),
            "condition": {
                "field": "resume.salary_expectation",
                "operator": "bracket_delta_gt",
                "value": 30
            },
            "action": {
                "target": "salary_score",
                "operation": "cap",
                "value": round(salary_coverage + 10, 2)
            }
        })

    # ── 10. Missing Certifications Detector ──────────────────────────────
    cert_criteria = scoring.get("certificates", {}).get("criteria", {})
    cert_weight = float(scoring.get("certificates", {}).get("weight", 0))
    resume_certs = resume.get("certifications", resume.get("certificates", []))
    if cert_weight > 0 and cert_criteria and not resume_certs:
        rules.append({
            "id": "rule_missing_certifications",
            "description": (
                f"JD requires certifications (weight={cert_weight}) with "
                f"{len(cert_criteria)} criteria, but resume lists none."
            ),
            "condition": {
                "field": "resume.certifications",
                "operator": "empty"
            },
            "action": {
                "target": "certificates_score",
                "operation": "cap",
                "value": 0
            }
        })

    # ── 11. Missing Projects Detector ────────────────────────────────────
    proj_criteria = scoring.get("projects", {}).get("criteria", {})
    proj_weight = float(scoring.get("projects", {}).get("weight", 0))
    resume_projects = resume.get("projects", [])
    if proj_weight > 0 and not resume_projects:
        rules.append({
            "id": "rule_missing_projects",
            "description": (
                f"JD values projects (weight={proj_weight}) but resume "
                f"lists no projects."
            ),
            "condition": {
                "field": "resume.projects",
                "operator": "empty"
            },
            "action": {
                "target": "projects_score",
                "operation": "cap",
                "value": 10
            }
        })

    # ── 12. Low Tool Coverage Detector ───────────────────────────────────
    tools_eval = base_evals.get("tools", {})
    tools_total = tools_eval.get("total_criteria", 0)
    tools_matched = tools_eval.get("matched_count", 0)
    tools_weight = float(scoring.get("tools", {}).get("weight", 0))
    if tools_weight > 0 and tools_total > 0:
        tool_ratio = tools_matched / tools_total
        if tool_ratio < 0.2:
            rules.append({
                "id": "rule_low_tool_coverage",
                "description": (
                    f"Only {tools_matched}/{tools_total} JD tools "
                    f"({tool_ratio*100:.0f}%) matched in resume. "
                    f"Candidate lacks required tooling proficiency."
                ),
                "condition": {
                    "field": "eval.tools.match_ratio",
                    "operator": "value_lt",
                    "value": 0.2
                },
                "action": {
                    "target": "tools_score",
                    "operation": "cap",
                    "value": 25
                }
            })

    # ── 13. Position Level Mismatch Detector ─────────────────────────────
    jd_position = str(validated_jd.get("position", "")).lower()
    candidate_pos = ""
    if exp_entries:
        first_exp = exp_entries[0] if isinstance(exp_entries[0], dict) else {}
        candidate_pos = str(
            first_exp.get("title", first_exp.get("normalized_role", ""))
        ).lower()

    # JD wants a lead/manager but candidate is junior
    jd_wants_lead = any(k in jd_position for k in ("lead", "manager", "senior", "director"))
    candidate_is_junior = any(
        k in candidate_pos
        for k in ("intern", "trainee", "junior", "fresher", "entry")
    )
    if jd_wants_lead and candidate_is_junior:
        rules.append({
            "id": "rule_position_level_mismatch",
            "description": (
                f"JD requires '{validated_jd.get('position', '')}' level "
                f"but candidate's role is '{candidate_pos}'. "
                f"Significant seniority gap detected."
            ),
            "condition": {
                "field": "resume.experience.title",
                "operator": "level_mismatch",
                "jd_level": "lead/senior",
                "candidate_level": "junior/trainee"
            },
            "action": {
                "target": "position_score",
                "operation": "cap",
                "value": 30
            }
        })

    # ── 14. Single Employer Bias ─────────────────────────────────────────
    if len(exp_entries) == 1 and total_years < 2:
        rules.append({
            "id": "rule_single_employer_limited",
            "description": (
                f"Candidate has only 1 employer with {total_years} years. "
                f"Limited breadth of experience — AI may over-score "
                f"relevant experience confidence."
            ),
            "condition": {
                "field": "resume.experience",
                "operator": "count_eq",
                "value": 1
            },
            "action": {
                "target": "relevant_experience_score",
                "operation": "multiply",
                "value": 0.85
            }
        })

    return rules


# ---------------------------------------------------------------------------
# Section type classifier
# ---------------------------------------------------------------------------
_KEYWORD_SECTIONS = {"skills", "technologies", "tools", "projects",
                     "certificates", "responsibilities"}
_BRACKET_SECTIONS = {"experience", "relevant_experience"}


# ---------------------------------------------------------------------------
# Section Evaluators (Re-used for base coverage)
# ---------------------------------------------------------------------------

def _evaluate_keyword_section(section: str, criteria: Dict[str, float], resume: Dict[str, Any]) -> Dict[str, Any]:
    resume_items = _collect_resume_items(section, resume)
    evaled, total_w, match_w, count = [], 0.0, 0.0, 0
    for crit, w in criteria.items():
        weight = float(w); total_w += weight
        matched, env_txt = _match_keyword(crit, resume_items)
        if matched:
            count += 1; match_w += weight
            evaled.append({"criterion": crit, "criterion_weight": weight, "matched": True, "evidence": env_txt})
        else:
            evaled.append({"criterion": crit, "criterion_weight": weight, "matched": False, "evidence": "No match found"})
    return {"rule_type": "keyword_match", "criteria_evaluated": evaled, "total_criteria": len(criteria), "matched_count": count, "coverage_pct": round((match_w/total_w*100) if total_w > 0 else 0.0, 2)}

# ... (rest of bracket evaluators - simplified for rule-based base reference) ...
def _evaluate_experience_section(section: str, criteria: Dict[str, Any], resume: Dict[str, Any]) -> Dict[str, Any]:
    yrs = _extract_years(resume)
    if section == "experience":
        bracket = ">=8 years" if yrs >= 8 else "5-7 years" if yrs >= 5 else "3-4 years" if yrs >= 3 else "<3 years"
    else:
        bracket = ">=5 years_relevant" if yrs >= 5 else "3-4 years_relevant" if yrs >= 3 else "1-2 years_relevant" if yrs >= 1 else "<1 year_relevant"
    score = float(criteria.get(bracket, 0))
    return {"rule_type": "bracket_match", "candidate_years": yrs, "matched_bracket": bracket, "criteria_evaluated": [{"criterion": bracket, "matched": True, "evidence": f"Found {yrs} years", "criterion_weight": score}], "total_criteria": len(criteria), "matched_count": 1, "coverage_pct": score}

def _evaluate_salary_section(criteria: Dict[str, Any], resume: Dict[str, Any]) -> Dict[str, Any]:
    lpa = _extract_salary_lpa(resume)
    bracket = "<3" if lpa < 3 else "3-6" if lpa <= 6 else "6-10" if lpa <= 10 else ">10"
    score = float(criteria.get(bracket, 0))
    return {"rule_type": "bracket_match", "candidate_salary_lpa": lpa, "matched_bracket": bracket, "total_criteria": len(criteria), "matched_count": 1, "coverage_pct": score, "criteria_evaluated": [{"criterion": bracket, "matched": True, "evidence": f"Candidate needs {lpa} LPA", "criterion_weight": score}]}

def _evaluate_qualification_section(criteria: Dict[str, Any], resume: Dict[str, Any]) -> Dict[str, Any]:
    edu = resume.get("education", [])
    best_s, best_m = 0.0, "Other"
    for e in edu:
        d = str(e.get("degree", "") or e.get("normalized_degree", "")).lower()
        if "master" in d:
            for k, v in criteria.items():
                if "master" in k.lower():
                    val = float(v)
                    if val > best_s: (best_s, best_m) = (val, k)
        elif any(kw in d for kw in ("bachelor", "be ", "btech")):
            for k, v in criteria.items():
                if "bachelor" in k.lower():
                    val = float(v)
                    if val > best_s: (best_s, best_m) = (val, k)
    if best_s == 0.0: best_s = float(criteria.get("Other", 0))
    return {"rule_type": "qualification_match", "best_match": best_m, "criteria_evaluated": [{"criterion": best_m, "matched": True, "evidence": f"Matched {best_m}", "criterion_weight": best_s}], "coverage_pct": best_s, "total_criteria": len(criteria), "matched_count": 1}

def _evaluate_position_section(criteria: Dict[str, Any], resume: Dict[str, Any]) -> Dict[str, Any]:
    pos = str(resume.get("position", "")).lower()
    m_key = next((k for k in criteria if "lead" in k.lower()), "Individual Contributor") if any(k in pos for k in ("lead", "manager")) else next((k for k in criteria if "individual" in k.lower()), "Individual Contributor")
    s = float(criteria.get(m_key, 0))
    return {"rule_type": "position_match", "matched_key": m_key, "coverage_pct": s, "total_criteria": len(criteria), "matched_count": 1, "criteria_evaluated": [{"criterion": m_key, "matched": True, "evidence": f"Role: {pos}", "criterion_weight": s}]}


# ---------------------------------------------------------------------------
# Rule Application Internal Engine
# ---------------------------------------------------------------------------

def _internal_apply_rule(
    rule: Dict[str, Any],
    resume: Dict[str, Any],
    ai_res: Dict[str, Any],
    scores: Dict[str, float],
) -> Tuple[bool, str, float, str]:
    """Apply a dynamically generated rule.

    Since every rule is only generated when its condition is already verified
    true, all rules fire unconditionally. The operator field is used here
    purely for descriptive logging.
    """
    cond = rule.get("condition", {})
    act  = rule.get("action", {})
    op   = cond.get("operator", "")

    # Map operator → human-readable reason
    _REASON_MAP = {
        "contains_keyword_ratio":  "Keyword ratio threshold met during analysis",
        "empty":                   "Field is empty / missing in resume",
        "avg_duration_months_lt":  "Average tenure below threshold",
        "value_gt":                "AI score exceeds rule-based ground truth",
        "value_lt":                "Field value is below required minimum",
        "value_eq":                "Field value matches exact condition",
        "missing_degree_level":    "Required degree level not found in resume",
        "bracket_delta_gt":        "Salary bracket delta exceeds threshold",
        "level_mismatch":          "Candidate seniority is below JD requirement",
        "count_eq":                "Experience entry count matches condition",
    }
    reason = _REASON_MAP.get(op, f"Condition '{op}' verified during generation")

    # Apply the action
    target  = str(act.get("target", "")).replace("_score", "")
    current = scores.get(target, 0.0)
    v       = float(act.get("value", 0))
    a_op    = act.get("operation", "")

    if a_op == "cap":
        new = min(current, v)
        msg = f"Capped {current:.2f} → {new:.2f} (max={v})"
    elif a_op == "multiply":
        new = round(current * v, 2)
        msg = f"Multiplied {current:.2f} × {v} = {new:.2f}"
    elif a_op == "subtract":
        new = round(max(current - v, 0), 2)
        msg = f"Subtracted {v} from {current:.2f} → {new:.2f}"
    elif a_op == "add":
        new = round(current + v, 2)
        msg = f"Added {v} to {current:.2f} → {new:.2f}"
    elif a_op == "override":
        new = v
        msg = f"Overridden {current:.2f} → {new:.2f}"
    else:
        new = current
        msg = f"Unknown operation '{a_op}' — score unchanged"

    return True, reason, new, msg


# ---------------------------------------------------------------------------
# Main Generator
# ---------------------------------------------------------------------------

def generate_rule_based_evidence(validated_jd: Dict[str, Any], ai_score: Dict[str, Any]) -> Dict[str, Any]:
    scoring, resume, result_block = validated_jd.get("scoring", {}), ai_score.get("inputs", {}).get("resume", {}), ai_score.get("result", {})
    
    # 1. First Pass: Base Evaluation (Coverage)
    base_evals = {}
    for section, rules in scoring.items():
        criteria = rules.get("criteria", {})
        if section in _KEYWORD_SECTIONS: base_evals[section] = _evaluate_keyword_section(section, criteria, resume)
        elif section in ("experience", "relevant_experience"): base_evals[section] = _evaluate_experience_section(section, criteria, resume)
        elif section == "salary": base_evals[section] = _evaluate_salary_section(criteria, resume)
        elif section == "qualification": base_evals[section] = _evaluate_qualification_section(criteria, resume)
        elif section == "position": base_evals[section] = _evaluate_position_section(criteria, resume)

    # 2. Dynamic Rule Generation
    generated_rules = _generate_dynamic_rules(validated_jd, resume, result_block, base_evals)
    
    # 3. Apply Generated Rules to Scores
    adjusted_scores = {s: res.get("coverage_pct", 0.0) for s, res in base_evals.items()}
    rule_log = []
    for r in generated_rules:
        fired, cond_msg, new_val, act_msg = _internal_apply_rule(r, resume, result_block, adjusted_scores)
        target_sec = r["action"]["target"].replace("_score", "")
        adjusted_scores[target_sec] = new_val
        rule_log.append({
            "rule_id": r["id"], 
            "description": r["description"], 
            "fired": fired, 
            "condition_evaluation": cond_msg, 
            "action_applied": {"explanation": act_msg, "score_after": new_val} if fired else None
        })

    # 4. Build Final Evidence
    section_evidences = []
    total_w, total_gt_w = 0.0, 0.0
    over, under, accurate = 0, 0, 0
    
    for section, rules in scoring.items():
        sw = float(rules.get("weight", 0)); total_w += sw
        base_res = base_evals.get(section, {"coverage_pct": 0, "criteria_evaluated": []})
        adj_gt = adjusted_scores.get(section, base_res["coverage_pct"])
        ai_val = float(result_block.get(f"{section}_score", 0))
        delta = round(ai_val - adj_gt, 2)
        
        if abs(delta) <= ACCURACY_TOLERANCE: accurate += 1; verdict = "ACCURATE"
        elif delta > 0: over += 1; verdict = "OVERESTIMATED"
        else: under += 1; verdict = "UNDERESTIMATED"
        
        section_evidences.append({
            "section_name": section, "section_weight": sw, **base_res,
            "base_coverage_pct": base_res["coverage_pct"], "coverage_pct": adj_gt,
            "ai_score": ai_val, "ground_truth_score": adj_gt, "score_delta": delta, "verdict": verdict,
            "applied_rules": [rl for rl in rule_log if rl["fired"] and rl["rule_id"].endswith(section) or (rl["fired"] and "experience" in rl["rule_id"] and section == "experience")]
        })
        total_gt_w += adj_gt * sw

    rule_final = round(total_gt_w / total_w, 2) if total_w > 0 else 0.0
    ai_final = float(result_block.get("final_score", 0))
    now = datetime.datetime.now(datetime.timezone.utc)
    
    # Also save the generated rules to data/outputs/evidence_rules.json
    rules_out_path = settings.OUTPUT_DIR / "evidence_rules.json"
    with open(rules_out_path, "w", encoding="utf-8") as f:
        json.dump(generated_rules, f, indent=2)

    return {
        "evidence_id": f"RULE_EVD_{now.strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}",
        "timestamp": now.isoformat(),
        "job_id": validated_jd.get("job_id", "Unknown"), "job_title": validated_jd.get("job_title", "Unknown"),
        "section_evidences": section_evidences,
        "overall_summary": {
            "total_sections": len(scoring), "sections_with_overestimation": over, "sections_with_underestimation": under, "sections_accurate": accurate,
            "ai_final_score": ai_final, "rule_based_final_score": rule_final, "delta": round(ai_final - rule_final, 2)
        },
        "rule_applications": {"total_rules_generated": len(generated_rules), "rule_log": rule_log}
    }


def save_rule_based_evidence(evidence: Dict[str, Any], path: str = DEFAULT_OUT_PATH) -> str:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f: json.dump(evidence, f, indent=2, ensure_ascii=False)
    return path


if __name__ == "__main__":
    if not DEFAULT_VALIDATED_JD.exists():
        logger.error(f"validated_jd.json not found at {DEFAULT_VALIDATED_JD}")
        exit(1)
        
    if not DEFAULT_AI_SCORE_INPUT.exists():
        logger.error(f"AI score file not found at {DEFAULT_AI_SCORE_INPUT}")
        exit(1)

    with open(DEFAULT_VALIDATED_JD, "r", encoding="utf-8") as f:
        validated_jd = json.load(f)
    
    with open(DEFAULT_AI_SCORE_INPUT, "r", encoding="utf-8") as f:
        ai_score = json.load(f)

    evidence = generate_rule_based_evidence(validated_jd, ai_score)
    out = save_rule_based_evidence(evidence)
    logger.info(f"Generated {len(evidence['rule_applications']['rule_log'])} dynamic rules.")
    logger.info(f"Saved evidence to {out}")
