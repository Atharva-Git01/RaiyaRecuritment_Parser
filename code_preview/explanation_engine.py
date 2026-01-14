# app/explanation_engine.py
"""
Explanation Engine (Phase 5.3)

Generates:
 - recruiter_text_summary: concise, factual paragraph(s) for recruiters
 - candidate_feedback: actionable, friendly improvement hints
 - structured_explanation: JSON object with summary, strengths, gaps, and
   project/skill/tool/responsibility breakdowns.

This module is deterministic and purely rule-based: it only uses the matcher
output (scores, matched_items, details) and produces human-readable text.
"""

import json
import math
from typing import Any, Dict, List, Tuple

SUMMARY_SCORE_KEYS = [
    "skills_score",
    "experience_score",
    "relevant_experience_score",
    "projects_score",
    "technologies_score",
    "tools_score",
    "certificates_score",
    "qualification_score",
    "responsibilities_score",
    "salary_score",
    "final_score",
]


def _safe_get(d: Dict, *keys, default=None):
    v = d
    for k in keys:
        if not isinstance(v, dict) or k not in v:
            return default
        v = v[k]
    return v


def _list_preview(lst: List[str], limit: int = 5) -> str:
    if not lst:
        return ""
    if len(lst) <= limit:
        return ", ".join(lst)
    return ", ".join(lst[:limit]) + f", +{len(lst)-limit} more"


def _qty_label(n: int, singular: str, plural: str = None) -> str:
    if n == 1:
        return singular
    return plural or (singular + "s")


def generate_recruiter_summary(matcher_out: Dict[str, Any]) -> str:
    """
    Returns a short, factual recruiter-friendly summary (1-3 sentences).
    """
    scores = {
        k: matcher_out.get(k, 0)
        for k in [
            "skills_score",
            "experience_score",
            "relevant_experience_score",
            "projects_score",
            "technologies_score",
            "tools_score",
            "certificates_score",
            "qualification_score",
            "responsibilities_score",
            "salary_score",
            "final_score",
        ]
    }

    details = matcher_out.get("details", {}) or {}
    matched = matcher_out.get("matched_items", {}) or {}

    jd_skill_count = details.get("jd_skill_count", 0)
    skills_matched = details.get("skills_matched", 0)

    # Skills line
    if jd_skill_count > 0:
        skills_line = f"Skills: matched {skills_matched}/{jd_skill_count} ({scores['skills_score']}%)."
    else:
        skills_line = "Skills: no JD skills provided."

    # Experience line
    exp_score = scores.get("experience_score", 0)
    exp_years = details.get("candidate_total_experience_years", None)
    if exp_years is not None:
        exp_line = f"Experience: {exp_years} years (score {exp_score}%)."
    else:
        exp_line = f"Experience score: {exp_score}%."

    # Projects & tech
    proj_score = scores.get("projects_score", 0)
    tech_score = scores.get("technologies_score", 0)
    proj_line = f"Projects: {proj_score}% match; Technologies: {tech_score}% match."

    # Final
    final = scores.get("final_score", 0)
    final_line = f"Overall fit score: {final}."

    # Short note about salary if present
    salary_obj = _safe_get(matcher_out, "matched_items", "salary", default={})
    cand_salary = salary_obj.get("candidate_salary")
    matched_band = salary_obj.get("matched_band")
    if cand_salary is None:
        salary_line = "Salary expectation: not provided."
    else:
        salary_line = f"Salary expectation: {cand_salary} LPA; JD band match: {matched_band or 'none'}."

    summary = " ".join([skills_line, exp_line, proj_line, salary_line, final_line])
    return summary


def generate_candidate_feedback(matcher_out: Dict[str, Any], max_items: int = 6) -> str:
    """
    Returns an actionable, polite candidate-oriented feedback paragraph.
    Prioritizes skill gaps, project evidence, responsibilities and tools.
    """
    matched = matcher_out.get("matched_items", {}) or {}
    scores = matcher_out or {}
    missing_skills = matched.get("skills", {}).get("missing", []) or []
    missing_tech = matched.get("technologies", {}).get("missing", []) or []
    missing_tools = matched.get("tools", {}).get("missing", []) or []
    missing_resp = matched.get("responsibilities", {}).get("missing", []) or []
    proj_missing = matched.get("projects", {}).get("missing_keywords", []) or []
    rel_exp = matched.get("relevant_experience", {}) or {}
    salary_info = matched.get("salary", {}) or {}

    tips: List[str] = []

    # Prioritize missing skills
    if missing_skills:
        tips.append(
            f"Highlight experience or projects showing: {_list_preview(missing_skills, 4)}."
        )

    # Projects evidence
    if proj_missing:
        tips.append(
            f"If you worked on related projects, mention keywords: {_list_preview(proj_missing, 6)}."
        )

    # Responsibilities
    if missing_resp:
        tips.append(
            f"Add clear bullets that show: {_list_preview(missing_resp, 4)} (use verbs + outcomes)."
        )

    # Tools
    if missing_tools:
        tips.append(f"List tools used (e.g., {_list_preview(missing_tools, 4)}).")

    # Relevant experience hints
    # find low relevant values
    low_rel = [k for k, v in rel_exp.items() if (v or 0) < 1.0]
    if low_rel:
        tips.append(
            f"Provide more context for relevant skills: mention duration and responsibilities for { _list_preview(low_rel, 4)}."
        )

    # Salary hint
    if salary_info.get("candidate_salary") is not None and not salary_info.get(
        "matched_band"
    ):
        tips.append(
            "If salary expectation is flexible, indicate the range or remove it to improve matching."
        )

    if not tips:
        return "Good alignment — your resume already matches the JD well. Consider adding more detail on measurable outcomes (metrics, scale, impact)."

    # Keep candidate feedback concise and prioritized
    feedback = " ".join(tips[:max_items])
    # ensure short sentences and polite tone
    return feedback


def _percent_label(n: int) -> str:
    try:
        return f"{int(round(n))}%"
    except Exception:
        return f"{n}"


def generate_structured_explanation(matcher_out: Dict[str, Any]) -> Dict[str, Any]:
    """
    Build a structured explanation JSON suitable for UI.
    Keys:
      - summary (short string)
      - strengths (list)
      - improvements (list)
      - skill_gaps, tech_gaps, tool_gaps, responsibility_gaps (lists)
      - project_keyword_match: { matched: [...], missing: [...], matched_pct: float }
      - scores: original component scores
      - matched_items: original matched_items block (kept for convenience)
    """
    scores = {
        k: matcher_out.get(k, 0)
        for k in [
            "skills_score",
            "experience_score",
            "relevant_experience_score",
            "projects_score",
            "certificates_score",
            "tools_score",
            "technologies_score",
            "qualification_score",
            "responsibilities_score",
            "salary_score",
            "final_score",
        ]
    }

    matched = matcher_out.get("matched_items", {}) or {}
    details = matcher_out.get("details", {}) or {}

    # strengths: high scoring areas (>=80)
    strengths = []
    for k, v in scores.items():
        if v >= 80 and k != "final_score":
            strengths.append({"category": k, "score": v})

    # gaps
    skill_gaps = matched.get("skills", {}).get("missing", []) or []
    tech_gaps = matched.get("technologies", {}).get("missing", []) or []
    tool_gaps = matched.get("tools", {}).get("missing", []) or []
    resp_gaps = matched.get("responsibilities", {}).get("missing", []) or []

    proj = matched.get("projects", {}) or {}
    proj_matched = proj.get("matched_keywords", []) or []
    proj_missing = proj.get("missing_keywords", []) or []
    proj_total = len(proj_matched) + len(proj_missing)
    proj_pct = (
        round((len(proj_matched) / proj_total) * 100, 1) if proj_total > 0 else 0.0
    )

    # short structured summary
    jd_skill_count = details.get("jd_skill_count", 0)
    skills_matched = details.get("skills_matched", 0)
    candidate_total_experience_years = details.get(
        "candidate_total_experience_years", 0
    )

    summary = {
        "short": generate_recruiter_summary(matcher_out),
        "one_line": f"Matched {skills_matched}/{jd_skill_count} skills; overall fit {scores.get('final_score', 0)}%.",
        "experience_years": candidate_total_experience_years,
    }

    # Compose improvement bullets (structured)
    improvements = []

    if skill_gaps:
        improvements.append(
            {"type": "skills", "why": "Missing required skills", "items": skill_gaps}
        )
    if proj_missing:
        improvements.append(
            {
                "type": "projects",
                "why": "Project keywords not present or not visible",
                "missing_keywords": proj_missing,
            }
        )
    if tool_gaps:
        improvements.append(
            {"type": "tools", "why": "Tools not mentioned", "items": tool_gaps}
        )
    if resp_gaps:
        improvements.append(
            {
                "type": "responsibilities",
                "why": "Responsibilities not clearly described",
                "items": resp_gaps,
            }
        )

    # Strength text for UI
    strength_texts = [f"{s['category']} ({s['score']}%)" for s in strengths]

    structured = {
        "summary": summary,
        "strengths": strength_texts,
        "improvements": improvements,
        "skill_gaps": skill_gaps,
        "tech_gaps": tech_gaps,
        "tool_gaps": tool_gaps,
        "responsibility_gaps": resp_gaps,
        "project_keyword_match": {
            "matched": proj_matched,
            "missing": proj_missing,
            "matched_pct": proj_pct,
            "total_keywords": proj_total,
        },
        "scores": scores,
        "matched_items": matched,
    }

    return structured


def generate_visual_payload(matcher_out: Dict[str, Any]) -> Dict[str, Any]:
    """
    Creates visual payload for frontend dashboards:
    - radar chart
    - project keyword heatmap
    - coverage bars
    - experience fit bar
    - salary gauge
    """
    scores = {
        k: matcher_out.get(k, 0)
        for k in [
            "skills_score",
            "experience_score",
            "relevant_experience_score",
            "projects_score",
            "certificates_score",
            "tools_score",
            "technologies_score",
            "qualification_score",
            "responsibilities_score",
            "salary_score",
        ]
    }

    matched = matcher_out.get("matched_items", {}) or {}
    details = matcher_out.get("details", {}) or {}

    # ----- Improved Radar Chart Order -----
    radar_labels = [
        "Experience",
        "Skills",
        "Technologies",
        "Tools",
        "Projects",
        "Certificates",
        "Responsibilities",
        "Relevant Exp",
    ]

    radar_keys = [
        "experience_score",
        "skills_score",
        "technologies_score",
        "tools_score",
        "projects_score",
        "certificates_score",
        "responsibilities_score",
        "relevant_experience_score",
    ]

    radar_values = [scores.get(k, 0) for k in radar_keys]

    # ----- Project keyword heatmap -----
    proj = matched.get("projects", {})
    proj_matched = proj.get("matched_keywords", []) or []
    proj_missing = proj.get("missing_keywords", []) or []
    total_kw = len(proj_matched) + len(proj_missing)
    proj_pct = round((len(proj_matched) / total_kw) * 100, 1) if total_kw > 0 else 0.0

    # Candidate total experience
    candidate_years = details.get("candidate_total_experience_years", 0)

    # ----- Experience fit -----

    jd_min = matcher_out.get("experience_range", {}).get("min", None)
    jd_max = matcher_out.get("experience_range", {}).get("max", None)

    if jd_min:
        exp_fit_pct = min(100, round((candidate_years / jd_min) * 100, 1))
    else:
        exp_fit_pct = None

    # ----- Improved Coverage Order -----
    coverage_bars = [
        {
            "category": "Experience",
            "matched": candidate_years,
            "total": (
                jd_min
                if jd_min is not None
                else (jd_max if jd_max is not None else max(candidate_years, 1))
            ),
        },
        {
            "category": "Skills",
            "matched": len(matched.get("skills", {}).get("matched", [])),
            "total": details.get("jd_skill_count", 1),
        },
        {
            "category": "Technologies",
            "matched": len(matched.get("technologies", {}).get("matched", [])),
            "total": details.get("jd_tech_count", 1),
        },
        {
            "category": "Tools",
            "matched": len(matched.get("tools", {}).get("matched", [])),
            "total": (
                len(matched.get("tools", {}).get("matched", []))
                + len(matched.get("tools", {}).get("missing", []))
            )
            or 1,
        },
        {
            "category": "Projects",
            "matched": len(proj_matched),
            "total": total_kw or 1,
        },
        {
            "category": "Certificates",
            "matched": len(matched.get("certificates", {}).get("matched", [])),
            "total": (
                len(matched.get("certificates", {}).get("matched", []))
                + len(matched.get("certificates", {}).get("missing", []))
            )
            or 1,
        },
        {
            "category": "Responsibilities",
            "matched": len(matched.get("responsibilities", {}).get("matched", [])),
            "total": (
                len(matched.get("responsibilities", {}).get("matched", []))
                + len(matched.get("responsibilities", {}).get("missing", []))
            )
            or 1,
        },
        {
            "category": "Relevant Exp",
            "matched": scores.get("relevant_experience_score", 0),
            "total": 100,
        },
    ]

    # ----- Salary gauge -----
    salary_obj = matched.get("salary", {}) or {}
    salary_gauge = {
        "score": scores.get("salary_score", 0),
        "candidate_salary": salary_obj.get("candidate_salary"),
        "matched_band": salary_obj.get("matched_band"),
    }

    return {
        "radar": {"labels": radar_labels, "values": radar_values},
        "project_keyword_heatmap": {
            "matched": proj_matched,
            "missing": proj_missing,
            "matched_pct": proj_pct,
            "total": total_kw,
        },
        "coverage_bars": coverage_bars,
        "experience_fit": {
            "candidate_years": candidate_years,
            "jd_min": jd_min,
            "jd_max": jd_max,
            "fit_pct_vs_min": exp_fit_pct,
        },
        "salary_gauge": salary_gauge,
        "summary_scores": scores,
    }


def generate_ui_blocks(matcher_out: Dict[str, Any]) -> Dict[str, Any]:
    scores = matcher_out
    matched = matcher_out.get("matched_items", {}) or {}
    details = matcher_out.get("details", {}) or {}

    # Quick access
    missing_skills = matched.get("skills", {}).get("missing", [])
    missing_tools = matched.get("tools", {}).get("missing", [])
    missing_tech = matched.get("technologies", {}).get("missing", [])
    missing_resp = matched.get("responsibilities", {}).get("missing", [])
    missing_proj = matched.get("projects", {}).get("missing_keywords", [])

    # Helper for KPI tags
    def classify(score):
        if score >= 80:
            return "good"
        if score >= 40:
            return "medium"
        return "bad"

    return {
        "sections": [
            {"id": "summary", "label": "Profile Summary", "icon": "mdi-account"},
            {"id": "skills", "label": "Skills Match", "icon": "mdi-star"},
            {"id": "technologies", "label": "Technologies", "icon": "mdi-chip"},
            {"id": "tools", "label": "Tools", "icon": "mdi-hammer-wrench"},
            {"id": "projects", "label": "Projects", "icon": "mdi-folder"},
            {
                "id": "responsibilities",
                "label": "Responsibilities",
                "icon": "mdi-clipboard-check",
            },
            {"id": "certificates", "label": "Certificates", "icon": "mdi-certificate"},
            {"id": "experience", "label": "Experience", "icon": "mdi-briefcase"},
            {"id": "salary", "label": "Salary", "icon": "mdi-currency-inr"},
        ],
        "score_tags": {
            "skills": classify(scores.get("skills_score", 0)),
            "technologies": classify(scores.get("technologies_score", 0)),
            "tools": classify(scores.get("tools_score", 0)),
            "projects": classify(scores.get("projects_score", 0)),
            "responsibilities": classify(scores.get("responsibilities_score", 0)),
            "experience": classify(scores.get("experience_score", 0)),
            "certificates": classify(scores.get("certificates_score", 0)),
            "salary": classify(scores.get("salary_score", 0)),
        },
        "filters": {
            "strengths": details.get("skills_matched", 0),
            "gaps": {
                "skills": missing_skills,
                "projects": missing_proj,
                "tools": missing_tools,
                "technologies": missing_tech,
                "responsibilities": missing_resp,
            },
        },
        "chart_types": {
            "radar": "radar",
            "project_heatmap": "heatmap",
            "coverage": "bar",
            "experience": "bar",
            "salary": "gauge",
        },
    }


def generate_full_report(matcher_out: Dict[str, Any]) -> Dict[str, Any]:
    """
    Returns a combined report with:
      - recruiter_text_summary
      - candidate_feedback
      - structured_explanation
    """
    recruiter_text = generate_recruiter_summary(matcher_out)
    candidate_text = generate_candidate_feedback(matcher_out)
    structured = generate_structured_explanation(matcher_out)
    summary_scores = {k: matcher_out.get(k, 0) for k in SUMMARY_SCORE_KEYS}

    return {
        "recruiter_text_summary": recruiter_text,
        "candidate_feedback": candidate_text,
        "structured_explanation": structured,
        "visual_payload": generate_visual_payload(matcher_out),
        "ui_components": generate_ui_blocks(matcher_out),
        "matched_items": matcher_out.get("matched_items", {}) or {},
        "details": matcher_out.get("details", {}) or {},
        "summary_scores": summary_scores,
        "experience_range": matcher_out.get("experience_range", {}) or {},
        "final_score": matcher_out.get("final_score", summary_scores.get("final_score", 0)),
    }


# ----------------------------
# Quick demo / smoke test
# ----------------------------
if __name__ == "__main__":
    # Example: if run directly, use a simple matcher-like object for demo
    demo_matcher_output = {
        "skills_score": 67,
        "experience_score": 100,
        "relevant_experience_score": 30,
        "projects_score": 44,
        "certificates_score": 100,
        "tools_score": 50,
        "technologies_score": 100,
        "qualification_score": 100,
        "responsibilities_score": 0,
        "salary_score": 0,
        "final_score": 70,
        "notes": "Skills matched 2/3; Relevant exp avg 0.0 yrs; Salary score 0.",
        "details": {
            "jd_skill_count": 3,
            "skills_matched": 2,
            "jd_tech_count": 2,
            "tech_matched": 2,
            "tools_matched": 1,
            "projects_matched": 4,
            "certificates_matched": 2,
            "candidate_total_experience_years": 2.0,
            "candidate_relevant_years_per_skill_avg": 0.0,
        },
        "matched_items": {
            "skills": {"matched": ["Python", "Django"], "missing": ["API Development"]},
            "technologies": {"matched": ["Python", "Django"], "missing": []},
            "tools": {"matched": ["GitHub"], "missing": ["Postman"]},
            "projects": {
                "matched_keywords": ["api", "microservices", "payment", "gateway"],
                "missing_keywords": [
                    "integration",
                    "authentication",
                    "module",
                    "token",
                    "handling",
                ],
            },
            "certificates": {"matched": ["AWS", "Python Certification"], "missing": []},
            "responsibilities": {
                "matched": [],
                "missing": [
                    "Build APIs",
                    "Write optimized backend logic",
                    "Work with databases",
                ],
            },
            "relevant_experience": {
                "Python": 0.0,
                "Django": 0.0,
                "API Development": 0.0,
            },
            "salary": {"candidate_salary": None, "matched_band": None},
        },
    }

    report = generate_full_report(demo_matcher_output)
    print("\n--- Recruiter Summary ---\n")
    print(report["recruiter_text_summary"])
    print("\n--- Candidate Feedback ---\n")
    print(report["candidate_feedback"])
    print("\n--- Structured Explanation (JSON) ---\n")
    print(json.dumps(report["structured_explanation"], indent=2))
