# app/matcher.py
import re
from copy import deepcopy
from typing import Any, Dict, List

from app.jd_validator import validate_jd
from app.validator import validate_resume_data

# Weights must match ai_scorer.WEIGHTS usage (but matcher returns component scores;
# ai_scorer will still recompute final_weighted if used there).
# Weights must match ai_scorer.WEIGHTS usage
def get_weights():
    return {
        "skills_score": 0.30,
        "experience_score": 0.25,
        "relevant_experience_score": 0.10,
        "projects_score": 0.10,
        "certificates_score": 0.05,
        "tools_score": 0.05,
        "technologies_score": 0.05,
        "qualification_score": 0.05,
        "responsibilities_score": 0.03,
        "salary_score": 0.02,
    }

WEIGHTS = get_weights()


# ---------------------
# Helpers: substring match
# ---------------------
def _contains_substring_list(source: List[str], targets: List[str]) -> int:
    """
    Return number of target items that appear as substring in any source item.
    Case-insensitive, substring-based.
    """
    if not isinstance(source, list):
        return 0
    if not isinstance(targets, list) or len(targets) == 0:
        return 0

    src = [str(s).lower() for s in source if s]
    matched = 0
    for t in targets:
        t = str(t).lower().strip()
        if not t:
            continue
        for s in src:
            if t in s:
                matched += 1
                break
    return matched


def _extract_matches(source: List[str], targets: List[str]):
    """
    Returns (matched_list, missing_list) based on substring matching.
    """
    matched = []
    missing = []
    src = [str(s).lower() for s in source if s]

    for t in targets:
        t_low = str(t).lower().strip()
        if not t_low:
            continue
        found = any(t_low in s for s in src)
        if found:
            matched.append(t)
        else:
            missing.append(t)

    return matched, missing


def _list_len_safe(lst):
    return len(lst) if isinstance(lst, list) else 0


# ---------------------
# Project keyword extractor (NEW)
# ---------------------
def _tokenize_phrase(text: str) -> List[str]:
    """
    Tokenize JD project description text into meaningful keywords.
    Removes filler words, punctuation, numbers.
    Fully deterministic, no semantic guessing.
    """
    if not isinstance(text, str):
        return []

    txt = text.lower()
    txt = re.sub(r"[^a-z0-9 ]+", " ", txt)

    tokens = [t.strip() for t in txt.split() if t.strip()]

    stopwords = {
        "the",
        "and",
        "a",
        "an",
        "for",
        "in",
        "of",
        "to",
        "on",
        "with",
        "using",
        "based",
        "related",
        "system",
        "create",
        "build",
        "built",
        "develop",
        "developed",
        "developer",
        "development",
    }

    return [t for t in tokens if t not in stopwords]


def _extract_project_keywords_from_jd(jd_projects: List[str]) -> List[str]:
    """
    Convert JD project descriptions into a clean keyword list.
    E.g. ["API development", "Payment gateway"]
        → ["api","payment","gateway"]
    """
    if not isinstance(jd_projects, list):
        return []

    keywords = []
    for item in jd_projects:
        if not item:
            continue
        for tok in _tokenize_phrase(str(item)):
            if tok not in keywords:
                keywords.append(tok)

    return keywords


# ---------------------
# Experience utilities
# ---------------------
def _parse_experience_range(exp_range: Dict[str, Any]):
    # expects {"min": float or None, "max": float or None}
    if not isinstance(exp_range, dict):
        return None, None
    return exp_range.get("min"), exp_range.get("max")


def compute_experience_score(
    total_years: float, jd_experience_range: Dict[str, Any]
) -> int:
    """
    Compute experience_score (0-100) using JD experience range.
    Rules:
    - If JD has min and max: if total_years >= min => 100 ; else proportion = total_years/min*100
    - If JD has only min: if total_years >= min => 100 else proportion
    - If JD has only max: if total_years <= max => 100 else proportion = max/total_years * 100 (capped)
    - If JD has no experience requirement: 0
    """
    try:
        min_y, max_y = _parse_experience_range(jd_experience_range)
        if min_y is None and max_y is None:
            return 0
        if total_years is None:
            return 0
        # min+max case
        if min_y is not None:
            try:
                min_y = float(min_y)
            except:
                min_y = None
        if max_y is not None:
            try:
                max_y = float(max_y)
            except:
                max_y = None

        # If min exists:
        if min_y is not None:
            if total_years >= min_y:
                return 100
            else:
                # proportion to min (0..100)
                if min_y <= 0:
                    return 0
                return int(round(max(0, min(100, (total_years / min_y) * 100))))
        # If only max exists:
        if max_y is not None:
            if total_years <= max_y:
                return 100
            else:
                # if candidate exceeds max, score decreases proportionally
                return int(round(max(0, min(100, (max_y / total_years) * 100))))
    except Exception:
        return 0
    return 0


# ---------------------
# Relevant experience bucket mapping
# ---------------------
def _map_relevant_experience_to_bucket(years: float, criteria: Dict[str, int]) -> int:
    """
    Criteria keys are strings like ">=5 years_relevant", "3-4 years_relevant", "<1 year_relevant"
    But validator scaled criteria values to 0-100. We interpret the keys as ranges and
    return the corresponding scaled criteria value for the bucket the 'years' falls into.
    If no bucket matches, return 0.
    """
    if not isinstance(criteria, dict) or years is None:
        return 0

    # Normalize keys ordering: prefer >=, then ranges, then <.
    for key, val in criteria.items():
        k = key.lower().replace(" ", "")
        # >=N
        m = re.match(r">=(\d+)(?:years_relevant|years|y)?", k)
        if m:
            n = float(m.group(1))
            if years >= n:
                return int(round(float(val)))

    # ranges like "3-4years_relevant" or "3-4years"
    for key, val in criteria.items():
        k = key.lower().replace(" ", "")
        m = re.match(r"(\d+)-(\d+)(?:years_relevant|years|y)?", k)
        if m:
            a = float(m.group(1))
            b = float(m.group(2))
            if a <= years <= b:
                return int(round(float(val)))

    # <N
    for key, val in criteria.items():
        k = key.lower().replace(" ", "")
        m = re.match(r"<(\d+)(?:years_relevant|years|y)?", k)
        if m:
            n = float(m.group(1))
            if years < n:
                return int(round(float(val)))

    return 0


# ---------------------
# Salary scoring helper
# ---------------------
def _parse_salary_criteria_and_score(
    salary_criteria: Dict[str, int], candidate_salary: float
) -> int:
    """
    Salary criteria keys might be "<3", "3-6", ">10", etc. Validator scaled their values to 0-100.
    We parse the key into numeric interval and check candidate_salary against it.
    If match found return criteria value (already scaled 0-100 by jd_validator). Else 0.
    """
    if not isinstance(salary_criteria, dict) or candidate_salary is None:
        return 0

    for key, val in salary_criteria.items():
        k = key.strip().lower()
        # patterns:
        # "<3" or "<3lpa" etc
        m = re.match(r"^<\s*(\d+\.?\d*)", k)
        if m:
            n = float(m.group(1))
            if candidate_salary < n:
                return int(round(float(val)))
        m = re.match(r"^>\s*(\d+\.?\d*)", k)
        if m:
            n = float(m.group(1))
            if candidate_salary > n:
                return int(round(float(val)))
        m = re.match(r"^(\d+\.?\d*)\s*[-to]+\s*(\d+\.?\d*)", k)
        if m:
            a = float(m.group(1))
            b = float(m.group(2))
            if a <= candidate_salary <= b:
                return int(round(float(val)))
        # direct number
        m = re.match(r"^(\d+\.?\d*)$", k)
        if m:
            n = float(m.group(1))
            if candidate_salary == n:
                return int(round(float(val)))
    return 0


# ---------------------
# Main scoring function
# ---------------------
def score_resume_against_jd(
    parsed_resume: dict, job_description: dict
) -> Dict[str, Any]:
    """
    Inputs:
      - parsed_resume: raw parsed JSON (unvalidated)
      - job_description: raw JD JSON (unvalidated)
    Returns:
      {
        component scores..., final_score, details...
      }
    """
    # Normalize inputs
    resume = validate_resume_data(parsed_resume or {})
    jd = validate_jd(job_description or {})

    # Prepare lists
    jd_skills = jd.get("skills", []) or []
    resume_skills = resume.get("skills", []) or []

    jd_tech = jd.get("technologies", []) or []
    resume_tech = resume.get("skills", []) or resume.get(
        "experience", []
    )  # prefer skills list, fallback to experience descriptions

    # For technologies/tools/projects/certs, prefer dedicated fields in resume if present
    resume_tools = resume.get("skills", []) or []
    resume_projects = [p.get("name", "") for p in resume.get("projects", [])] or []
    resume_certificates = resume.get("certificates", []) or []

    # total experience years (validator provided)
    total_years = resume.get("total_experience_years", 0.0)

    # -------------------------
    # 1) Skills score
    # -------------------------
    jd_skill_count = _list_len_safe(jd_skills)
    skills_matched = 0
    if jd_skill_count > 0:
        # match JD.skills against resume.skills list + experience role/desc
        # create a combined source for resume text
        resume_sources = list(resume_skills)
        # also include roles and experience descriptions
        for exp in resume.get("experience", []):
            role = exp.get("role", "")
            desc = " ".join(exp.get("description", []) or [])
            if role:
                resume_sources.append(role)
            if desc:
                resume_sources.append(desc)
        skills_matched = _contains_substring_list(resume_sources, jd_skills)
        skills_matched_list, skills_missing_list = _extract_matches(
            resume_sources, jd_skills
        )
        skills_score = int(round(100.0 * skills_matched / jd_skill_count))
    else:
        skills_score = 0
        skills_matched_list, skills_missing_list = [], []

    # -------------------------
    # 2) Technologies score
    # -------------------------
    jd_tech_count = _list_len_safe(jd_tech)
    tech_matched = 0
    if jd_tech_count > 0:
        # match JD technologies against resume.skills + experience desc
        resume_sources = list(resume_skills)
        for exp in resume.get("experience", []):
            desc = " ".join(exp.get("description", []) or [])
            role = exp.get("role", "")
            if role:
                resume_sources.append(role)
            if desc:
                resume_sources.append(desc)
        tech_matched = _contains_substring_list(resume_sources, jd_tech)
        tech_matched_list, tech_missing_list = _extract_matches(resume_sources, jd_tech)
        technologies_score = int(round(100.0 * tech_matched / jd_tech_count))
    else:
        technologies_score = 0
        tech_matched_list, tech_missing_list = [], []

    # -------------------------
    # 3) Tools score
    # -------------------------
    jd_tools = jd.get("tools", []) or []
    tools_count = _list_len_safe(jd_tools)
    tools_matched = 0
    if tools_count > 0:
        resume_sources = list(resume_skills)
        for exp in resume.get("experience", []):
            desc = " ".join(exp.get("description", []) or [])
            if desc:
                resume_sources.append(desc)
        tools_matched = _contains_substring_list(resume_sources, jd_tools)
        tools_matched_list, tools_missing_list = _extract_matches(
            resume_sources, jd_tools
        )
        tools_score = int(round(100.0 * tools_matched / tools_count))
    else:
        tools_score = 0
        tools_matched_list, tools_missing_list = [], []

    # -------------------------
    # 4) Projects score (Improved keyword-based matcher)
    # -------------------------
    jd_projects_raw = jd.get("projects", []) or []
    jd_proj_keywords = _extract_project_keywords_from_jd(jd_projects_raw)
    proj_count = _list_len_safe(jd_proj_keywords)

    proj_matched = 0
    project_matched_keywords = []
    project_missing_keywords = []

    if proj_count > 0:
        resume_proj_sources = []

        # Resume project names & descriptions
        for p in resume.get("projects", []):
            resume_proj_sources.append(str(p.get("name", "")).lower())
            resume_proj_sources.append(str(p.get("description", "")).lower())

        # Experience roles & descriptions (projects often hidden here)
        for exp in resume.get("experience", []):
            resume_proj_sources.append(str(exp.get("role", "")).lower())
            exp_desc = exp.get("description", [])
            if not isinstance(exp_desc, list):
                exp_desc = [exp_desc]
            resume_proj_sources.append(" ".join([str(x) for x in exp_desc]).lower())

        # Skills sometimes indicate project type too
        resume_proj_sources.extend([s.lower() for s in resume.get("skills", [])])

        proj_matched = _contains_substring_list(resume_proj_sources, jd_proj_keywords)
        project_matched_keywords, project_missing_keywords = _extract_matches(
            resume_proj_sources, jd_proj_keywords
        )
        projects_score = int(round(100.0 * proj_matched / proj_count))
    else:
        projects_score = 0
        project_matched_keywords, project_missing_keywords = [], []

    # -------------------------
    # 5) Certificates score
    # -------------------------
    jd_certs = jd.get("certificates", []) or []
    cert_count = _list_len_safe(jd_certs)
    cert_matched = 0
    if cert_count > 0:
        resume_cert_sources = resume.get("certificates", []) or []
        cert_matched = _contains_substring_list(resume_cert_sources, jd_certs)
        cert_matched_list, cert_missing_list = _extract_matches(
            resume_cert_sources, jd_certs
        )
        certificates_score = int(round(100.0 * cert_matched / cert_count))
    else:
        certificates_score = 0
        cert_matched_list, cert_missing_list = [], []

    # -------------------------
    # 6) Qualification score
    # -------------------------
    jd_qual = jd.get("qualification", "") or ""
    qualification_score = 0
    if jd_qual and isinstance(jd_qual, str):
        # If qualification string contains degree token, match against resume.education degrees
        edu_list = resume.get("education", []) or []
        if edu_list:
            matches = 0
            for q in edu_list:
                deg = str(q.get("degree", "")).lower()
                if deg and jd_qual.lower() in deg:
                    matches = 1
                    break
            qualification_score = 100 if matches else 0
        else:
            qualification_score = 0

    # -------------------------
    # 7) Responsibilities score
    # -------------------------
    jd_resp = jd.get("responsibilities", []) or []
    resp_count = _list_len_safe(jd_resp)
    resp_matched = 0
    if resp_count > 0:
        # match JD responsibilities against resume experience descriptions
        resume_sources = []
        for exp in resume.get("experience", []):
            resume_sources.append(exp.get("role", ""))
            resume_sources.append(" ".join(exp.get("description", []) or []))
        resp_matched = _contains_substring_list(resume_sources, jd_resp)
        resp_matched_list, resp_missing_list = _extract_matches(resume_sources, jd_resp)
        responsibilities_score = int(round(100.0 * resp_matched / resp_count))
    else:
        responsibilities_score = 0
        resp_matched_list, resp_missing_list = [], []

    # -------------------------
    # 8) Experience score (overall)
    # -------------------------
    experience_score = compute_experience_score(
        total_years, jd.get("experience_range", {})
    )

    # -------------------------
    # 9) Relevant experience score
    # -------------------------
    # JD scoring.relevant_experience.criteria contains scaled values (0-100) keyed by buckets
    rel_criteria = {}
    scoring_block = jd.get("scoring", {}) or {}
    if isinstance(scoring_block, dict):
        rel_block = scoring_block.get("relevant_experience", {}) or {}
        rel_criteria = rel_block.get("criteria", {}) or {}

    # compute candidate relevant years for JD skills: sum years for skills present in jd_skills
    candidate_rel_years = 0.0
    if jd_skills:
        rmap = resume.get("relevant_experience_map", {}) or {}
        # sum years for each JD skill found in rmap
        for s in jd_skills:
            if not s:
                continue
            years = rmap.get(s, 0.0)
            # also try lowercase keys if rmap stores canonical differently
            if years == 0.0:
                years = rmap.get(s.lower(), 0.0)
            candidate_rel_years += float(years or 0.0)
        # If multiple skills, average them (so years per skill)
        if len(jd_skills) > 0:
            candidate_rel_years = round(candidate_rel_years / len(jd_skills), 2)

    relevant_experience_score = _map_relevant_experience_to_bucket(
        candidate_rel_years, rel_criteria
    )
    relevant_exp_map = {}
    rmap = resume.get("relevant_experience_map", {}) or {}
    for s in jd_skills:
        relevant_exp_map[s] = rmap.get(s, rmap.get(s.lower(), 0.0))

    # -------------------------
    # 10) Salary score
    # -------------------------
    salary_score = 0
    salary_block = scoring_block.get("salary", {}) or {}
    salary_criteria = salary_block.get("criteria", {}) or {}
    # candidate preferred: expected else current
    cand_salary = None
    s = resume.get("salary", {}) or {}
    if isinstance(s, dict):
        cand_salary = s.get("expected_ctc_lpa") or s.get("current_ctc_lpa")
    salary_score = _parse_salary_criteria_and_score(salary_criteria, cand_salary)

    salary_band_match = None
    if salary_criteria and cand_salary is not None:
        for key, val in salary_criteria.items():
            k = key.strip().lower()
            if "<" in k:
                if cand_salary < float(k.replace("<", "")):
                    salary_band_match = key
            elif ">" in k:
                if cand_salary > float(k.replace(">", "")):
                    salary_band_match = key
            elif "-" in k or "to" in k:
                parts = re.split(r"[-to]+", k)
                a = float(parts[0])
                b = float(parts[1])
                if a <= cand_salary <= b:
                    salary_band_match = key

    # -------------------------
    # Compose final map
    # -------------------------
    scores = {
        "skills_score": int(max(0, min(100, skills_score))),
        "experience_score": int(max(0, min(100, experience_score))),
        "relevant_experience_score": int(max(0, min(100, relevant_experience_score))),
        "projects_score": int(max(0, min(100, projects_score))),
        "certificates_score": int(max(0, min(100, certificates_score))),
        "tools_score": int(max(0, min(100, tools_score))),
        "technologies_score": int(max(0, min(100, technologies_score))),
        "qualification_score": int(max(0, min(100, qualification_score))),
        "responsibilities_score": int(max(0, min(100, responsibilities_score))),
        "salary_score": int(max(0, min(100, salary_score))),
    }

    # compute final weighted score (same formula ai_scorer uses)
    final = 0.0
    for k, w in WEIGHTS.items():
        final += scores.get(k, 0) * w
    final_score = int(round(final))

    # Details for debugging / explanation
    details = {
        "jd_skill_count": jd_skill_count,
        "skills_matched": skills_matched,
        "jd_tech_count": jd_tech_count,
        "tech_matched": tech_matched,
        "tools_matched": tools_matched,
        "projects_matched": proj_matched,
        "certificates_matched": cert_matched,
        "candidate_total_experience_years": total_years,
        "candidate_relevant_years_per_skill_avg": candidate_rel_years,
    }

    matched_items = {
        "skills": {
            "matched": skills_matched_list,
            "missing": skills_missing_list,
        },
        "technologies": {
            "matched": tech_matched_list,
            "missing": tech_missing_list,
        },
        "tools": {
            "matched": tools_matched_list,
            "missing": tools_missing_list,
        },
        "projects": {
            "matched_keywords": project_matched_keywords,
            "missing_keywords": project_missing_keywords,
        },
        "certificates": {
            "matched": cert_matched_list,
            "missing": cert_missing_list,
        },
        "responsibilities": {
            "matched": resp_matched_list,
            "missing": resp_missing_list,
        },
        "relevant_experience": relevant_exp_map,
        "salary": {
            "candidate_salary": cand_salary,
            "matched_band": salary_band_match,
        },
    }

    out = deepcopy(scores)
    out["final_score"] = final_score
    out["notes"] = (
        f"Skills matched {skills_matched}/{jd_skill_count}; Relevant exp avg {candidate_rel_years} yrs; Salary score {salary_score}."
    )
    out["details"] = details
    out["matched_items"] = matched_items

    # ✅ FIX: attach JD experience range for visual payload
    out["experience_range"] = jd.get("experience_range", {})

    return out
