# app/matcher.py
import re
from copy import deepcopy
from typing import Any, Dict, List, Tuple

from app.jd_validator import validate_jd
from app.validator import validate_resume_data

# Weights must match ai_scorer.WEIGHTS usage
WEIGHTS = {
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

# -----------------
# SEMANTIC MODEL LOADER
# -----------------
_SEMANTIC_MODEL = None


def get_semantic_model():
    """
    Lazy load the SentenceTransformer model to avoid startup penalties.
    """
    global _SEMANTIC_MODEL
    if _SEMANTIC_MODEL is None:
        try:
            print("⏳ Loading local NLP model (all-MiniLM-L6-v2)...")
            from sentence_transformers import SentenceTransformer

            _SEMANTIC_MODEL = SentenceTransformer("all-MiniLM-L6-v2")
            print("✅ NLP model loaded.")
        except ImportError:
            print("⚠️ sentence-transformers not installed. Semantic matching disabled.")
            return None
        except Exception as e:
            print(f"⚠️ Failed to load NLP model: {e}")
            return None
    return _SEMANTIC_MODEL


def _semantic_check_missing(
    source_texts: List[str], missing_targets: List[str], threshold: float = 0.55
) -> Tuple[List[str], List[str]]:
    """
    Check if 'missing_targets' can be found semantically in 'source_texts'.
    Returns (found_items, still_missing_items).
    """
    if not missing_targets or not source_texts:
        return [], missing_targets

    model = get_semantic_model()
    if model is None:
        return [], missing_targets

    from sentence_transformers import util

    # Normalize source text chunks
    # We join and split to ensure we have decent sized chunks or just use the list
    # For resume lists, items are usually short. For descriptions, they are long.
    # Let's flatten source texts into a single list of strings
    valid_sources = [str(s) for s in source_texts if s]
    if not valid_sources:
        return [], missing_targets

    # Encode sources
    source_embeddings = model.encode(valid_sources, convert_to_tensor=True)
    
    # Encode targets
    target_embeddings = model.encode(missing_targets, convert_to_tensor=True)

    found = []
    still_missing = []

    # Compute cosine similarities
    # shape: (num_targets, num_sources)
    cosine_scores = util.cos_sim(target_embeddings, source_embeddings)

    for i, target in enumerate(missing_targets):
        # Check if any source item matches this target above threshold
        max_score = 0.0
        if cosine_scores.size(1) > 0:
            max_score = float(cosine_scores[i].max())
        
        if max_score >= threshold:
            found.append(target)
        else:
            still_missing.append(target)

    return found, still_missing


# ---------------------
# Helpers: substring match
# ---------------------
# ---------------------
# Helpers: substring match (UPDATED: Regex with Word Boundaries)
# ---------------------
def _make_regex_pattern(target: str) -> str:
    """
    Create a safe regex pattern with word boundaries.
    Handles C++ and C# specifically to avoiding boundary issues with symbols.
    """
    t = target.strip()
    # Special handling for C++, C#, .NET where symbols matter
    # If target ends with symbol like +, #, we can't use \b at the end easily
    # because symbols are non-word chars.
    
    escaped = re.escape(t)
    
    # Case 1: Pure word (e.g., "AI", "Python") -> \bWord\b
    if re.match(r"^\w+$", t):
        return r"\b" + escaped + r"\b"
    
    # Case 2: C++, C# -> \bC\+\+(?!\w) or similar? 
    # Proper strategy: \b at start if starts with word char.
    # At end, if ends with symbol, use (?!\w) or whitespace/end-of-string check.
    
    pattern = ""
    # Start boundary
    if re.match(r"^\w", t):
        pattern += r"\b"
    pattern += escaped
    # End boundary
    if re.match(r"\w$", t):
        pattern += r"\b"
    else:
        # Ends with symbol (e.g. C++), make sure next char is not a word char (e.g. C++Lib)
        pattern += r"(?!\w)"
        
    return pattern


def _contains_substring_list(source: List[str], targets: List[str]) -> int:
    """
    Return number of target items that appear as WHOLE WORD in any source item.
    """
    if not isinstance(source, list):
        return 0
    if not isinstance(targets, list) or len(targets) == 0:
        return 0

    # Pre-compile patterns for targets
    # (Optimization: could cache this if performance hit is large, but usually fine)
    patterns = [(_make_regex_pattern(t), t) for t in targets if t and t.strip()]
    
    src_combined = " \n ".join([str(s).lower() for s in source if s])
    
    matched = 0
    for pat, original_t in patterns:
        if not original_t.strip(): continue
        # Use case-insensitive search
        if re.search(pat, src_combined, re.IGNORECASE):
            matched += 1
            
    return matched


def _extract_matches(source: List[str], targets: List[str]):
    """
    Returns (matched_list, missing_list) based on WHOLE WORD matching.
    """
    matched = []
    missing = []
    
    # Join source once to avoid O(MxN) loop overhead and make regex search fast
    src_combined = " \n ".join([str(s) for s in source if s])
    
    for t in targets:
        t_clean = str(t).strip()
        if not t_clean:
            continue
            
        pat = _make_regex_pattern(t_clean)
        # Search distinct pattern
        if re.search(pat, src_combined, re.IGNORECASE):
            matched.append(t)
        else:
            missing.append(t)

    return matched, missing


def _list_len_safe(lst):
    return len(lst) if isinstance(lst, list) else 0


# ---------------------
# Project keyword extractor
# ---------------------
def _tokenize_phrase(text: str) -> List[str]:
    if not isinstance(text, str):
        return []

    txt = text.lower()
    txt = re.sub(r"[^a-z0-9 ]+", " ", txt)
    tokens = [t.strip() for t in txt.split() if t.strip()]

    stopwords = {
        "the", "and", "a", "an", "for", "in", "of", "to", "on", "with",
        "using", "based", "related", "system", "create", "build", "built",
        "develop", "developed", "developer", "development",
    }
    return [t for t in tokens if t not in stopwords]


def _extract_project_keywords_from_jd(jd_projects: List[str]) -> List[str]:
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
from datetime import datetime

def _parse_date(date_str: str) -> datetime | None:
    """
    Parse generic resume date strings like 'Jan 2020', '2020/01', 'Present'.
    """
    if not isinstance(date_str, str) or not date_str.strip():
        return None
    
    ds = date_str.lower().strip()
    if "present" in ds or "current" in ds or "now" in ds:
        return datetime.now()
        
    # Standard formats
    formats = [
        "%b %Y", "%B %Y", "%Y-%m-%d", "%Y/%m/%d", "%m/%Y", "%Y", "%d %b %Y"
    ]
    
    for fmt in formats:
        try:
            return datetime.strptime(ds, fmt)
        except ValueError:
            continue
    return None

def _calculate_experience_from_timeline(experience_list: List[Dict[str, Any]], jd_job_title: str = None) -> float:
    """
    Calculate total years of experience by summing non-overlapping intervals
    from start_date and end_date fields.
    
    If jd_job_title is provided, strictly IGNORE roles that are semantically irrelevant 
    (similarity < 0.35) to the target job title.
    """
    if not experience_list:
        return 0.0

    # strict_filter logic
    valid_indices = set(range(len(experience_list)))
    
    if jd_job_title and jd_job_title.strip():
        model = get_semantic_model()
        if model:
            from sentence_transformers import util
            target_emb = model.encode(jd_job_title, convert_to_tensor=True)
            
            # Filter roles
            to_remove = set()
            for idx, exp in enumerate(experience_list):
                role = exp.get("role", "").strip()
                if not role:
                    continue # If no role title, we can't judge relevance easily. Keep or skip? Skip safe.
                    
                # Encode role
                role_emb = model.encode(role, convert_to_tensor=True)
                sim = float(util.cos_sim(target_emb, role_emb)[0][0])
                
                # Threshold: 0.35 is conservative. 
                # "Finance" vs "Computer Engineer" ~ 0.1-0.2
                # "Software Engineer" vs "Computer Engineer" ~ 0.7+
                if sim < 0.35:
                   to_remove.add(idx)
            
            valid_indices = valid_indices - to_remove

    intervals = []
    for idx, exp in enumerate(experience_list):
        if idx not in valid_indices:
            continue
            
        start_str = exp.get("start_date")
        end_str = exp.get("end_date")
        
        start_dt = _parse_date(start_str)
        if not start_dt:
            continue
            
        end_dt = _parse_date(end_str)
        if not end_dt:
            continue
            
        if end_dt < start_dt:
            continue
            
        intervals.append((start_dt, end_dt))
        
    if not intervals:
        # Fallback to summing years provided in text if timeline parsing fails
        # BUT only for valid indices
        start_years = [float(experience_list[i].get("years", 0)) for i in valid_indices if experience_list[i].get("years")]
        if start_years:
            return sum(start_years)
        return 0.0
        
    # Merge overlapping intervals
    intervals.sort(key=lambda x: x[0])
    
    merged = []
    if intervals:
        curr_start, curr_end = intervals[0]
        for i in range(1, len(intervals)):
            next_start, next_end = intervals[i]
            if next_start < curr_end: # Overlap
                curr_end = max(curr_end, next_end)
            else:
                merged.append((curr_start, curr_end))
                curr_start, curr_end = next_start, next_end
        merged.append((curr_start, curr_end))
        
    total_days = 0
    for start, end in merged:
        total_days += (end - start).days
        
    return round(total_days / 365.25, 2)


def _parse_experience_range(exp_range: Dict[str, Any]):
    # expects {"min": float or None, "max": float or None}
    if not isinstance(exp_range, dict):
        return None, None
    return exp_range.get("min"), exp_range.get("max")


def compute_experience_score(
    total_years: float, jd_experience_range: Dict[str, Any]
) -> int:
    try:
        min_y, max_y = _parse_experience_range(jd_experience_range)
        if min_y is None and max_y is None:
            return 0
        if total_years is None:
            return 0
        
        if min_y is not None:
             try: min_y = float(min_y)
             except: min_y = None
        if max_y is not None:
             try: max_y = float(max_y)
             except: max_y = None

        if min_y is not None:
            if total_years >= min_y:
                return 100
            else:
                if min_y <= 0: return 0
                return int(round(max(0, min(100, (total_years / min_y) * 100))))
        
        if max_y is not None:
            if total_years <= max_y:
                return 100
            else:
                return int(round(max(0, min(100, (max_y / total_years) * 100))))

    except Exception:
        return 0
    return 0


# ---------------------
# Relevant experience bucket mapping
# ---------------------
def _map_relevant_experience_to_bucket(years: float, criteria: Dict[str, int]) -> int:
    if not isinstance(criteria, dict) or years is None:
        return 0

    for key, val in criteria.items():
        k = key.lower().replace(" ", "")
        m = re.match(r">=(\d+)", k)
        if m:
            n = float(m.group(1))
            if years >= n:
                return int(round(float(val)))

    for key, val in criteria.items():
        k = key.lower().replace(" ", "")
        m = re.match(r"(\d+)-(\d+)", k)
        if m:
            a = float(m.group(1))
            b = float(m.group(2))
            if a <= years <= b:
                return int(round(float(val)))

    for key, val in criteria.items():
        k = key.lower().replace(" ", "")
        m = re.match(r"<(\d+)", k)
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
    if not isinstance(salary_criteria, dict) or candidate_salary is None:
        return 0

    for key, val in salary_criteria.items():
        k = key.strip().lower()
        m = re.match(r"^<\s*(\d+\.?\d*)", k)
        if m:
            n = float(m.group(1))
            if candidate_salary < n: return int(round(float(val)))
        m = re.match(r"^>\s*(\d+\.?\d*)", k)
        if m:
            n = float(m.group(1))
            if candidate_salary > n: return int(round(float(val)))
        m = re.match(r"^(\d+\.?\d*)\s*[-to]+\s*(\d+\.?\d*)", k)
        if m:
            a, b = float(m.group(1)), float(m.group(2))
            if a <= candidate_salary <= b: return int(round(float(val)))
        m = re.match(r"^(\d+\.?\d*)$", k)
        if m:
            n = float(m.group(1))
            if candidate_salary == n: return int(round(float(val)))
    return 0


# ---------------------
# Main scoring function
# ---------------------
def score_resume_against_jd(
    parsed_resume: dict, job_description: dict
) -> Dict[str, Any]:
    """
    Inputs:
      - parsed_resume: validated JSON
      - job_description: validated JD JSON
    """
    # Normalize inputs
    resume = validate_resume_data(parsed_resume or {})
    jd = validate_jd(job_description or {})

    # Prepare lists
    jd_skills = jd.get("skills", []) or []
    resume_skills = resume.get("skills", []) or []

    jd_tech = jd.get("technologies", []) or []
    # resume tech often sits in skills or experience text
    resume_tech_sources = list(resume_skills)

    # Gather comprehensive text sources for semantic matching
    # 1. Skills List
    # 2. Project Descriptions
    # 3. Experience Roles & Descriptions
    # 4. Raw Text if available (though parser output usually preferred)
    
    text_corpus = list(resume_skills)
    
    for exp in resume.get("experience", []):
        text_corpus.append(exp.get("role", ""))
        text_corpus.append(" ".join(exp.get("description", []) or []))
        
    for proj in resume.get("projects", []):
        text_corpus.append(proj.get("name", ""))
        text_corpus.append(proj.get("description", ""))

    text_corpus.append(resume.get("summary", ""))
    
    # Filter empty
    text_corpus = [s for s in text_corpus if s and isinstance(s, str)]

    # total experience years
    # FIX: Prefer calculated timeline verification over hallucinated parser output
    # Also apply semantic filtering based on JD Job Title
    try:
        timeline_years = _calculate_experience_from_timeline(
            resume.get("experience", []), 
            jd.get("job_title")
        )
    except Exception:
        timeline_years = 0.0
        
    extracted_years = float(resume.get("total_experience_years", 0.0) or 0.0)
    
    # Logic: Timeline is strictly grounded in dates. Extracted field is LLM guess/regex.
    # If timeline found valid data (>0), trust it more.
    # Exception: If timeline is 0 (dates missing) but extracted is > 0, use extracted (fallback).
    if timeline_years > 0:
        total_years = timeline_years
    else:
        # Sanity check: If extracted is e.g. 8.33 (likely CGPA) and no timeline, risk is high.
        # But without dates, we have no choice but to fallback or 0.
        # Let's trust extracted if timeline failed, assuming parser might be right in summary.
        total_years = extracted_years

    # -------------------------
    # 1) Skills score (Hybrid)
    # -------------------------
    jd_skill_count = _list_len_safe(jd_skills)
    skills_matched_list = []
    skills_missing_list = []
    
    if jd_skill_count > 0:
        # Phase 1: Substring Match
        matched_ss, missing_ss = _extract_matches(text_corpus, jd_skills)
        skills_matched_list.extend(matched_ss)
        
        # Phase 2: Semantic Match on Missing
        if missing_ss:
            found_sem, still_missing = _semantic_check_missing(text_corpus, missing_ss, threshold=0.45)
            skills_matched_list.extend(found_sem)
            skills_missing_list.extend(still_missing)
        else:
            skills_missing_list = []
            
        final_matched_count = len(skills_matched_list)
        skills_score = int(round(100.0 * final_matched_count / jd_skill_count))
    else:
        skills_score = 0

    # -------------------------
    # 2) Technologies score (Hybrid)
    # -------------------------
    jd_tech_count = _list_len_safe(jd_tech)
    tech_matched_list = []
    tech_missing_list = []

    if jd_tech_count > 0:
        matched_ss, missing_ss = _extract_matches(text_corpus, jd_tech)
        tech_matched_list.extend(matched_ss)
        
        if missing_ss:
            found_sem, still_missing = _semantic_check_missing(text_corpus, missing_ss, threshold=0.45)
            tech_matched_list.extend(found_sem)
            tech_missing_list.extend(still_missing)
        else:
            tech_missing_list = []
            
        technologies_score = int(round(100.0 * len(tech_matched_list) / jd_tech_count))
    else:
        technologies_score = 0

    # -------------------------
    # 3) Tools score (Hybrid)
    # -------------------------
    jd_tools = jd.get("tools", []) or []
    tools_count = _list_len_safe(jd_tools)
    tools_matched_list = []
    tools_missing_list = []

    if tools_count > 0:
        matched_ss, missing_ss = _extract_matches(text_corpus, jd_tools)
        tools_matched_list.extend(matched_ss)
        
        if missing_ss:
            found_sem, still_missing = _semantic_check_missing(text_corpus, missing_ss, threshold=0.45)
            tools_matched_list.extend(found_sem)
            tools_missing_list.extend(still_missing)
            
        tools_score = int(round(100.0 * len(tools_matched_list) / tools_count))
    else:
        tools_score = 0

    # -------------------------
    # 4) Projects score (Keyword + Semantic)
    # -------------------------
    jd_projects_raw = jd.get("projects", []) or []
    jd_proj_keywords = _extract_project_keywords_from_jd(jd_projects_raw)
    proj_count = _list_len_safe(jd_proj_keywords)
    project_matched_keywords = []

    if proj_count > 0:
        matched_ss, missing_ss = _extract_matches(text_corpus, jd_proj_keywords)
        project_matched_keywords.extend(matched_ss)
        
        if missing_ss:
            found_sem, still_missing = _semantic_check_missing(text_corpus, missing_ss, threshold=0.60) # Higher threshold for keywords
            project_matched_keywords.extend(found_sem)
            
        projects_score = int(round(100.0 * len(project_matched_keywords) / proj_count))
    else:
        projects_score = 0

    # -------------------------
    # 5) Certificates score
    # -------------------------
    jd_certs = jd.get("certificates", []) or []
    cert_count = _list_len_safe(jd_certs)
    cert_matched_list = []
    
    if cert_count > 0:
        resume_certs = [str(c.get("name", "")) for c in resume.get("certificates", [])]
        matched_ss, missing_ss = _extract_matches(resume_certs, jd_certs)
        cert_matched_list.extend(matched_ss)
        
        # Also check experience descriptions for certifications
        if missing_ss:
             found_sem, _ = _semantic_check_missing(text_corpus, missing_ss, threshold=0.65)
             cert_matched_list.extend(found_sem)
             
        certificates_score = int(round(100.0 * len(cert_matched_list) / cert_count))
    else:
        certificates_score = 0

    # -------------------------
    # 6) Qualification score
    # -------------------------
    jd_qual = jd.get("qualification", "") or ""
    qualification_score = 0
    if jd_qual and isinstance(jd_qual, str):
        edu_list = resume.get("education", []) or []
        # Basic substring check on normalized degrees
        matches = False
        for q in edu_list:
            deg = str(q.get("degree", "")).lower()
            if deg and jd_qual.lower() in deg:
                matches = True
                break
        qualification_score = 100 if matches else 0

    # -------------------------
    # 7) Responsibilities score (Hybrid)
    # -------------------------
    jd_resp = jd.get("responsibilities", []) or []
    resp_count = _list_len_safe(jd_resp)
    resp_matched_list = []
    
    if resp_count > 0:
        matched_ss, missing_ss = _extract_matches(text_corpus, jd_resp)
        resp_matched_list.extend(matched_ss)
        if missing_ss:
            # Responsibilities are long sentences, semantic match is perfect here
            found_sem, _ = _semantic_check_missing(text_corpus, missing_ss, threshold=0.50)
            resp_matched_list.extend(found_sem)
            
        responsibilities_score = int(round(100.0 * len(resp_matched_list) / resp_count))
    else:
        responsibilities_score = 0

    # -------------------------
    # 8) Experience score (overall)
    # -------------------------
    experience_score = compute_experience_score(
        total_years, jd.get("experience_range", {})
    )

    # -------------------------
    # 9) Relevant experience score
    # -------------------------
    rel_criteria = {}
    scoring_block = jd.get("scoring", {}) or {}
    if isinstance(scoring_block, dict):
        rel_block = scoring_block.get("relevant_experience", {}) or {}
        rel_criteria = rel_block.get("criteria", {}) or {}

    candidate_rel_years = 0.0
    if jd_skills:
        rmap = resume.get("relevant_experience_map", {}) or {}
        for s in jd_skills:
            if not s: continue
            years = rmap.get(s, 0.0)
            if years == 0.0: years = rmap.get(s.lower(), 0.0)
            candidate_rel_years += float(years or 0.0)
        
        if len(jd_skills) > 0:
            candidate_rel_years = round(candidate_rel_years / len(jd_skills), 2)

    relevant_experience_score = _map_relevant_experience_to_bucket(
        candidate_rel_years, rel_criteria
    )
    
    # map bucket to score
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
    
    cand_salary = None
    s = resume.get("salary", {}) or {}
    if isinstance(s, dict):
        cand_salary = s.get("expected_ctc_lpa") or s.get("current_ctc_lpa")
    salary_score = _parse_salary_criteria_and_score(salary_criteria, cand_salary)

    salary_band_match = None
    # (Checking logic kept from original matcher)
    if salary_criteria and cand_salary is not None:
         # Simplified band checker
         pass

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

    final = 0.0
    for k, w in WEIGHTS.items():
        final += scores.get(k, 0) * w
    final_score = int(round(final))

    details = {
        "jd_skill_count": jd_skill_count,
        "skills_matched": len(skills_matched_list),
        "jd_tech_count": jd_tech_count,
        "tech_matched": len(tech_matched_list),
        "tools_matched": len(tools_matched_list),
        "projects_matched": len(project_matched_keywords),
        "candidate_total_experience_years": total_years,
        "candidate_relevant_years_per_skill_avg": candidate_rel_years,
    }

    matched_items = {
        "skills": {
            "matched": skills_matched_list,
            # We don't track strictly missing anymore for detailed view, but can infer
            "missing": [s for s in jd_skills if s not in skills_matched_list],
        },
        "technologies": {
            "matched": tech_matched_list,
            "missing": [t for t in jd_tech if t not in tech_matched_list],
        },
        "tools": {
            "matched": tools_matched_list,
            "missing": [t for t in jd_tools if t not in tools_matched_list],
        },
        "projects": {
            "matched_keywords": project_matched_keywords,
        }
    }

    out = deepcopy(scores)
    out["final_score"] = final_score
    out["notes"] = (
        f"Hybrid Score: Skills {scores['skills_score']}%; Tech {scores['technologies_score']}%. "
        f"(Semantic Enabled)"
    )
    out["details"] = details
    out["matched_items"] = matched_items
    out["experience_range"] = jd.get("experience_range", {})

    return out
