"""
RAIYA Pipeline 2 Node — JD Normalize (Phase 2 + Phase 3).
==========================================================
Performs two critical enterprise workflow phases:

Phase 2 — Canonicalization & Ontology Mapping:
    - Normalize aliases, abbreviations, semantic duplicates
    - Map raw terms to canonical forms (e.g., PowerBI → Power BI, Agile/Scrum → Agile)

Phase 3 — Section Classification:
    - Classify extracted entities into: technologies, skills, tools,
      certifications, responsibilities, experience, qualification

Handles BOTH input formats:
    - Standard DocStrange output (job_details, required_skills_and_competencies, ...)
    - Legacy custom schema (job_information, skills_and_technologies, ...)
"""

from typing import Dict, Any, List

from langgraph.runtime import Runtime

from app.agents import PipelineContext, PipelineState
from app.core.logging_config import get_logger

logger = get_logger("JDNormalizeNode")

# ═══════════════════════════════════════════════════════════════════════
# Alias Map — Ontology Canonicalization (Phase 2)
# ═══════════════════════════════════════════════════════════════════════

CANONICAL_ALIASES = {
    # ── Programming Languages ──
    "js": "javascript", "ts": "typescript", "py": "python",
    "c#": "csharp", "c++": "cpp", "golang": "go",

    # ── Frameworks & Libraries ──
    "react.js": "react", "reactjs": "react",
    "node.js": "nodejs", "node": "nodejs",
    "next.js": "nextjs", "vue.js": "vue", "vuejs": "vue",
    "express.js": "express", "expressjs": "express",
    "angular.js": "angular", "angularjs": "angular",

    # ── Databases ──
    "mongo": "mongodb", "postgres": "postgresql",
    "pg": "postgresql", "mssql": "sql server",
    "mysql db": "mysql",

    # ── Cloud & DevOps ──
    "k8s": "kubernetes", "tf": "terraform",
    "aws lambda": "aws lambda",
    "gcp": "google cloud platform",

    # ── AI/ML ──
    "ml": "machine learning", "ai": "artificial intelligence",
    "dl": "deep learning", "nlp": "natural language processing",
    "cv": "computer vision", "llm": "large language models",
    "genai": "generative ai", "gen ai": "generative ai",

    # ── Tools ──
    "powerbi": "power bi", "ms excel": "excel",
    "ms word": "word", "ms office": "microsoft office",
    "vs code": "visual studio code", "vscode": "visual studio code",
    "github actions": "github actions",

    # ── Methodologies ──
    "agile/scrum": "agile", "scrum/agile": "agile",
    "agile methodology": "agile", "agile methodologies": "agile",
    "sdlc": "software development lifecycle",
    "ci/cd": "ci cd", "cicd": "ci cd",
    "devops": "devops",

    # ── Certifications ──
    "aws certified": "aws certification",
    "azure certified": "azure certification",
    "pmp certified": "pmp certification",
    "csm": "certified scrum master",
}

# ═══════════════════════════════════════════════════════════════════════
# Section Classification Keywords (Phase 3)
# ═══════════════════════════════════════════════════════════════════════

TECHNOLOGY_KEYWORDS = {
    "python", "java", "javascript", "typescript", "react", "nodejs",
    "nextjs", "vue", "angular", "sql", "mongodb", "postgresql",
    "mysql", "redis", "kafka", "elasticsearch", "docker", "kubernetes",
    "terraform", "aws", "azure", "gcp", "google cloud platform",
    "go", "rust", "csharp", "cpp", "swift", "kotlin", "flutter",
    "django", "flask", "spring", "spring boot", "fastapi", ".net",
    "graphql", "rest api", "html", "css", "sass", "tailwind",
    "machine learning", "deep learning", "tensorflow", "pytorch",
    "hadoop", "spark", "airflow", "snowflake", "databricks",
    "power bi", "tableau", "excel", "r", "scala",
}

TOOL_KEYWORDS = {
    "jira", "confluence", "slack", "trello", "asana",
    "git", "github", "gitlab", "bitbucket",
    "visual studio code", "intellij", "eclipse",
    "postman", "swagger", "figma", "sketch", "adobe xd",
    "jenkins", "circleci", "travis ci", "github actions",
    "datadog", "grafana", "prometheus", "new relic",
    "microsoft office", "word", "excel", "powerpoint",
    "notion", "miro", "lucidchart",
}

CERTIFICATION_KEYWORDS = {
    "aws certification", "azure certification", "gcp certification",
    "pmp certification", "certified scrum master", "cissp",
    "comptia", "oracle certified", "cisco certified",
    "six sigma", "itil", "prince2",
}


async def jd_normalize_node(
    state: PipelineState,
    runtime: Runtime[PipelineContext],
) -> dict:
    """
    Normalize JD extracted JSON — Phase 2 (Ontology Mapping) + Phase 3 (Section Classification).

    Handles both standard DocStrange output and legacy custom schema.
    """
    jd_extracted = state.get("jd_extracted", {})

    try:
        normalized = _normalize_jd(jd_extracted)
        logger.info(
            f"JD normalization complete — "
            f"techs={len(normalized.get('technologies', []))}, "
            f"skills={len(normalized.get('skills', []))}, "
            f"tools={len(normalized.get('tools', []))}, "
            f"certs={len(normalized.get('certifications', []))}"
        )
        return {"jd_normalized": normalized}
    except Exception as e:
        logger.error(f"JD normalization failed: {e}")
        return {"jd_normalized": jd_extracted}


def _normalize_jd(jd: Dict[str, Any]) -> Dict[str, Any]:
    """
    Flatten and normalize JD structure.
    
    Detects whether input is standard DocStrange output or legacy format,
    then performs:
        Phase 2 — Canonicalization & ontology mapping
        Phase 3 — Section classification (technologies, skills, tools, certs, etc.)
    """
    # ── Detect input format ──────────────────────────────────────────
    is_standard_docstrange = "job_details" in jd and (
        "required_skills_and_competencies" in jd or
        "preferred_added_advantage" in jd
    )
    
    if is_standard_docstrange:
        return _normalize_standard_docstrange(jd)
    else:
        return _normalize_legacy_format(jd)


def _normalize_standard_docstrange(jd: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize standard DocStrange output format:
    {
        "job_details": { "job_title": "...", "experience": "...", "education": "..." },
        "required_skills_and_competencies": ["...", ...],
        "preferred_added_advantage": ["...", ...]
    }
    """
    job_details = jd.get("job_details", {})
    if not isinstance(job_details, dict):
        job_details = {}

    # Collect all raw items
    required_items = jd.get("required_skills_and_competencies", [])
    preferred_items = jd.get("preferred_added_advantage", [])
    responsibilities_raw = jd.get("responsibilities", [])
    requirements_raw = jd.get("requirements", [])

    if not isinstance(required_items, list):
        required_items = []
    if not isinstance(preferred_items, list):
        preferred_items = []
    if not isinstance(responsibilities_raw, list):
        responsibilities_raw = []
    if not isinstance(requirements_raw, list):
        requirements_raw = []

    # Phase 2 — Canonicalize all items
    canonical_required = [_canonicalize(item) for item in required_items if isinstance(item, str)]
    canonical_preferred = [_canonicalize(item) for item in preferred_items if isinstance(item, str)]
    canonical_responsibilities = [_canonicalize(item) for item in responsibilities_raw if isinstance(item, str)]
    canonical_requirements = [_canonicalize(item) for item in requirements_raw if isinstance(item, str)]

    # Phase 3 — Classify into sections
    all_items = canonical_required + canonical_preferred + canonical_requirements
    technologies, skills, tools, certifications = _classify_items(all_items)

    # Track which items came from required vs preferred (for reasoning label context)
    required_set = set(canonical_required)
    preferred_set = set(canonical_preferred)

    # Build experience string
    experience_str = job_details.get("experience", "")

    # Build qualification string
    qualification_str = job_details.get("education", "")

    # Build work mode
    work_mode_raw = job_details.get("work_mode", "")
    work_mode = _parse_work_mode(work_mode_raw)

    normalized = {
        "job_title": job_details.get("job_title", ""),
        "position": _infer_position(job_details.get("job_title", ""), experience_str),
        "employment_type": job_details.get("employment_type", ""),
        "location": job_details.get("location", ""),
        "work_mode": work_mode,
        "technologies": list(set(technologies)),
        "skills": list(set(skills)),
        "tools": list(set(tools)),
        "certifications": list(set(certifications)),
        "experience_range": _parse_experience_range(experience_str),
        "minimum_years": _extract_min_years(experience_str),
        "preferred_years": _extract_max_years(experience_str),
        "qualification": _parse_qualification(qualification_str),
        "preferred_field_of_study": [],
        "job_description": job_details.get("job_title", ""),
        "responsibilities": canonical_responsibilities if canonical_responsibilities else [],
        "requirements": canonical_requirements,
        "preferred_qualifications": canonical_preferred,
        "salary_range": job_details.get("salary_range", ""),
        # Provenance tracking for reasoning label validation (Phase 5)
        "_provenance": {
            "required_items": list(required_set),
            "preferred_items": list(preferred_set),
            "extraction_method": "docstrange_standard",
        },
    }
    return normalized


def _normalize_legacy_format(jd: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize legacy custom schema format (backward compatibility)."""
    job_info = jd.get("job_information", {})
    skills_tech = jd.get("skills_and_technologies", {})
    exp_req = jd.get("experience_requirements", {})
    edu_req = jd.get("education_requirements", {})
    job_details = jd.get("job_details", {})

    normalized = {
        "job_title": job_info.get("job_title", ""),
        "position": _extract_position(job_info.get("position", {})),
        "employment_type": job_info.get("employment_type", ""),
        "location": job_info.get("location", ""),
        "work_mode": job_info.get("work_mode", {}),
        "technologies": _normalize_list(skills_tech.get("technologies", [])),
        "skills": _normalize_list(skills_tech.get("skills", [])),
        "tools": _normalize_list(skills_tech.get("tools", [])),
        "certifications": skills_tech.get("certifications", []),
        "experience_range": exp_req.get("experience_range", {}),
        "minimum_years": exp_req.get("minimum_years"),
        "preferred_years": exp_req.get("preferred_years"),
        "qualification": edu_req.get("qualification", {}),
        "preferred_field_of_study": edu_req.get("preferred_field_of_study", []),
        "job_description": job_details.get("job_description", ""),
        "responsibilities": job_details.get("responsibilities", []),
        "requirements": job_details.get("requirements", []),
        "preferred_qualifications": job_details.get("preferred_qualifications", []),
        "_provenance": {
            "required_items": [],
            "preferred_items": [],
            "extraction_method": "legacy_custom_schema",
        },
    }
    return normalized


# ═══════════════════════════════════════════════════════════════════════
# Phase 2 — Canonicalization Helpers
# ═══════════════════════════════════════════════════════════════════════

def _canonicalize(item: str) -> str:
    """Canonicalize a single item using the alias map."""
    lower = item.lower().strip()
    return CANONICAL_ALIASES.get(lower, item.strip())


def _normalize_list(items: list) -> list:
    """Normalize a list of strings using alias map and deduplicate."""
    normalized = []
    for item in items:
        if isinstance(item, str):
            normalized.append(_canonicalize(item))
    return list(set(normalized))


# ═══════════════════════════════════════════════════════════════════════
# Phase 3 — Section Classification Helpers
# ═══════════════════════════════════════════════════════════════════════

def _classify_items(items: List[str]) -> tuple:
    """
    Classify items into technologies, skills, tools, certifications.
    Items that don't match any keyword set are classified as skills (default).
    """
    technologies = []
    skills = []
    tools = []
    certifications = []

    for item in items:
        lower = item.lower().strip()
        if lower in TECHNOLOGY_KEYWORDS or any(tk in lower for tk in TECHNOLOGY_KEYWORDS if len(tk) > 3):
            technologies.append(item)
        elif lower in TOOL_KEYWORDS or any(tk in lower for tk in TOOL_KEYWORDS if len(tk) > 3):
            tools.append(item)
        elif lower in CERTIFICATION_KEYWORDS or any(ck in lower for ck in CERTIFICATION_KEYWORDS if len(ck) > 3):
            certifications.append(item)
        else:
            # Default: classify as skill
            skills.append(item)

    return technologies, skills, tools, certifications


def _extract_position(pos: Any) -> str:
    """Extract position level from position dict or string."""
    if isinstance(pos, dict):
        if pos.get("senior_level"):
            return "senior"
        elif pos.get("mid_level"):
            return "mid"
        elif pos.get("entry_level"):
            return "entry"
    elif isinstance(pos, str):
        return pos
    return ""


def _infer_position(job_title: str, experience: str) -> str:
    """Infer position level from job title and experience."""
    title_lower = job_title.lower()
    
    senior_keywords = ["senior", "lead", "principal", "staff", "architect", "director", "vp", "head"]
    entry_keywords = ["junior", "intern", "trainee", "fresher", "entry", "associate", "graduate"]
    
    for kw in senior_keywords:
        if kw in title_lower:
            return "senior"
    for kw in entry_keywords:
        if kw in title_lower:
            return "entry"

    # Infer from experience
    min_years = _extract_min_years(experience)
    if min_years is not None:
        if min_years >= 8:
            return "senior"
        elif min_years >= 3:
            return "mid"
        else:
            return "entry"

    return "mid"  # Default


def _parse_work_mode(work_mode_raw: str) -> dict:
    """Parse work mode string into structured dict."""
    if isinstance(work_mode_raw, dict):
        return work_mode_raw
    
    lower = str(work_mode_raw).lower() if work_mode_raw else ""
    return {
        "remote_option": "remote" in lower,
        "work_from_office": "office" in lower or "on-site" in lower or "onsite" in lower,
        "hybrid": "hybrid" in lower,
    }


def _parse_experience_range(experience: str) -> dict:
    """Parse experience string to range dict."""
    if not experience or not isinstance(experience, str):
        return {}
    
    lower = experience.lower()
    return {
        "<3_years": "0" in lower or "1" in lower or "2" in lower,
        "3_4_years": "3" in lower or "4" in lower,
        "5_7_years": "5" in lower or "6" in lower or "7" in lower,
        "8_plus_years": "8" in lower or "10" in lower or "+" in lower,
    }


def _extract_min_years(experience: str) -> float:
    """Extract minimum years from experience string."""
    if not experience or not isinstance(experience, str):
        return None
    import re
    match = re.search(r"(\d+)", experience)
    if match:
        return float(match.group(1))
    return None


def _extract_max_years(experience: str) -> float:
    """Extract maximum years from experience string."""
    if not experience or not isinstance(experience, str):
        return None
    import re
    matches = re.findall(r"(\d+)", experience)
    if len(matches) >= 2:
        return float(matches[1])
    elif matches:
        return float(matches[0])
    return None


def _parse_qualification(education: str) -> dict:
    """Parse education string into qualification dict."""
    if isinstance(education, dict):
        return education
    if not education or not isinstance(education, str):
        return {}
    
    lower = education.lower()
    return {
        "phd": "phd" in lower or "ph.d" in lower or "doctorate" in lower,
        "masters": "master" in lower or "mca" in lower or "mba" in lower or "m.tech" in lower or "m.sc" in lower or "ms " in lower,
        "bachelors": "bachelor" in lower or "bca" in lower or "b.tech" in lower or "b.sc" in lower or "b.e" in lower or "bba" in lower,
        "associate": "associate" in lower,
        "diploma": "diploma" in lower,
        "certification": "certif" in lower,
    }
