"""
Resume Schema Validation — Pydantic-based
==========================================
Validates and normalizes the raw docstrange extraction output into the
canonical resume schema defined in ``reference_parsed_resume_format.json``.

Why Pydantic (not Guardrails AI)?
  • The extraction pipeline is *offline* — no LLM re-prompting is needed.
  • Pydantic gives strict type coercion, nested validators, and custom
    pre-processing hooks which are exactly what we need to normalise the
    3-4 different wrapper formats that docstrange can return.
  • Zero external API cost; sub-millisecond validation.

Supported docstrange wrapper formats:
  1. ``structured_json``   → ``structured_data.content.{fields}``
  2. ``cloud_flat_json``   → ``document.{flat_fields}`` (non-schema keys)
  3. ``specified_fields``  → ``extracted_fields.content._raw_response`` (stringified JSON)
  4. ``extraction_failed`` → ``document.error`` (graceful failure path)
"""

from __future__ import annotations

import json
import re
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from pydantic import (
    BaseModel,
    Field,
    ValidationError,
    field_validator)


# =====================================================================
# Sub-models (mirror reference_parsed_resume_format.json)
# =====================================================================

class ExperienceEntry(BaseModel):
    """A single work-experience entry."""
    title: str = Field(default="", description="Job title / role")
    company: str = Field(default="", description="Company name")
    start: str = Field(default="", description="Start date (ISO8601 or 'Month Year')")
    end: str = Field(default="", description="End date")
    description: Optional[str] = Field(default=None, description="Role description")
    responsibilities: Optional[List[str]] = Field(default=None, description="List of responsibilities")

    @field_validator("responsibilities", mode="before")
    @classmethod
    def coerce_responsibilities(cls, v: Any) -> Optional[List[str]]:
        if v is None:
            return None
        if isinstance(v, str):
            return [v]
        if isinstance(v, list):
            return [str(item) for item in v if item]
        return None


class ProjectEntry(BaseModel):
    """A single project entry."""
    name: str = Field(default="", description="Project name")
    description: Optional[str] = Field(default=None, description="Project description")
    technologies: Optional[List[str]] = Field(default=None, description="Technologies used")

    @field_validator("technologies", mode="before")
    @classmethod
    def coerce_technologies(cls, v: Any) -> Optional[List[str]]:
        if v is None:
            return None
        if isinstance(v, str):
            return [t.strip() for t in v.split(",") if t.strip()]
        if isinstance(v, list):
            return [str(item) for item in v if item]
        return None


class EducationEntry(BaseModel):
    """A single education entry."""
    degree: str = Field(default="", description="Degree obtained")
    institution: str = Field(default="", description="Institution name")
    start_year: Optional[str] = Field(default=None, description="Start year")
    end_year: Optional[str] = Field(default=None, description="End year")
    field_of_study: Optional[str] = Field(default=None, description="Field of study")
    cgpa: Optional[str] = Field(default=None, description="CGPA or grade")
    institute_location: Optional[str] = Field(default=None, description="Location")

    @field_validator("start_year", "end_year", mode="before")
    @classmethod
    def coerce_year_to_string(cls, v: Any) -> Optional[str]:
        """Accept int or float years and convert to string."""
        if v is None:
            return None
        return str(v).strip()

    @field_validator("cgpa", mode="before")
    @classmethod
    def coerce_cgpa(cls, v: Any) -> Optional[str]:
        if v is None:
            return None
        return str(v).strip()


class SalaryExpectation(BaseModel):
    """Salary expectation block."""
    value: Optional[str] = Field(default=None, description="Salary value")
    currency: Optional[str] = Field(default=None, description="Currency code")

    @field_validator("value", mode="before")
    @classmethod
    def coerce_value(cls, v: Any) -> Optional[str]:
        if v is None:
            return None
        return str(v).strip()


class PipelineMetadata(BaseModel):
    """Internal pipeline metadata injected during extraction."""
    resume_content_hash: str = Field(default="", description="SHA-256 hash of the source file")
    created_at: Optional[str] = Field(default=None, description="ISO8601 timestamp")
    source: Optional[str] = Field(default=None, description="Source filename")


# =====================================================================
# Canonical Resume Schema (the validated output)
# =====================================================================

class ValidatedResumeSchema(BaseModel):
    """
    The canonical validated resume schema.
    Mirrors ``reference_parsed_resume_format.json`` exactly.
    """
    name: str = Field(default="", description="Candidate full name (Required)")
    email: Optional[str] = Field(default=None, description="Candidate email")
    skills: List[str] = Field(default_factory=list, description="Skill keywords")
    experience: List[ExperienceEntry] = Field(default_factory=list, description="Work experience")
    projects: List[ProjectEntry] = Field(default_factory=list, description="Projects")
    education: List[EducationEntry] = Field(default_factory=list, description="Education history")
    candidate_achievements: List[str] = Field(default_factory=list, description="Achievements / awards")
    certifications: List[str] = Field(default_factory=list, description="Certifications")
    tools: List[str] = Field(default_factory=list, description="Tools known")
    technologies: List[str] = Field(default_factory=list, description="Technologies known")
    salary_expectation: Optional[SalaryExpectation] = Field(default=None, description="Salary expectation")

    # ── Internal metadata (preserved but not part of the scoring schema) ──
    pipeline_metadata: Optional[PipelineMetadata] = Field(default=None, description="Pipeline metadata")

    # ------------------------------------------------------------------
    # Field-level validators
    # ------------------------------------------------------------------

    @field_validator("skills", "candidate_achievements", "certifications", "tools", "technologies", mode="before")
    @classmethod
    def coerce_string_list(cls, v: Any) -> List[str]:
        """Accept None, a single string, or a list and normalise to List[str]."""
        if v is None:
            return []
        if isinstance(v, str):
            return [v]
        if isinstance(v, list):
            result = []
            for item in v:
                if item is None:
                    continue
                if isinstance(item, dict):
                    # Handle {name: "...", line: N} objects from specified_fields format
                    name = item.get("name") or item.get("value") or item.get("title", "")
                    if name:
                        result.append(str(name))
                else:
                    result.append(str(item))
            return result
        return []

    @field_validator("experience", mode="before")
    @classmethod
    def coerce_experience_list(cls, v: Any) -> List[Any]:
        if v is None:
            return []
        if isinstance(v, dict):
            return [v]
        if isinstance(v, list):
            return v
        return []

    @field_validator("projects", mode="before")
    @classmethod
    def coerce_projects_list(cls, v: Any) -> List[Any]:
        if v is None:
            return []
        if isinstance(v, dict):
            return [v]
        if isinstance(v, list):
            return v
        return []

    @field_validator("education", mode="before")
    @classmethod
    def coerce_education_list(cls, v: Any) -> List[Any]:
        if v is None:
            return []
        if isinstance(v, dict):
            return [v]
        if isinstance(v, list):
            return v
        return []

    @field_validator("salary_expectation", mode="before")
    @classmethod
    def coerce_salary(cls, v: Any) -> Optional[Dict[str, Any]]:
        if v is None:
            return None
        if isinstance(v, dict):
            return v
        return None


# =====================================================================
# Validation Report
# =====================================================================

class FieldStatus(str, Enum):
    """Status of an individual schema field after validation."""
    OK = "ok"
    COERCED = "coerced"
    MISSING = "missing"
    EMPTY = "empty"
    INVALID = "invalid"


class FieldReport(BaseModel):
    """Report for a single field."""
    field: str
    status: FieldStatus
    message: str = ""


class ValidationReport(BaseModel):
    """Full validation report for a single resume."""
    is_valid: bool = True
    source_format: str = "unknown"
    total_fields: int = 0
    populated_fields: int = 0
    empty_fields: int = 0
    coerced_fields: int = 0
    missing_required_fields: List[str] = Field(default_factory=list)
    field_reports: List[FieldReport] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)
    validated_at: str = Field(default_factory=lambda: datetime.now().isoformat())


# =====================================================================
# Format-Specific Unwrappers
# =====================================================================

def _unwrap_structured_json(raw: Dict[str, Any]) -> Dict[str, Any]:
    """Unwrap ``structured_data.content.{fields}`` format."""
    sd = raw.get("structured_data", {})
    if isinstance(sd, dict):
        content = sd.get("content", sd)
        if isinstance(content, dict):
            return content
    return raw


def _unwrap_cloud_flat_json(raw: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalise ``document.{flat_keys}`` (cloud_flat_json) into the
    canonical schema by grouping numbered suffixed keys.

    E.g.  ``education_1_degree``, ``education_1_university``, ``education_2_degree``
    → ``education: [{degree: ..., institution: ...}, {degree: ..., institution: ...}]``
    """
    doc = raw.get("document", raw)
    if not isinstance(doc, dict):
        return raw

    normalised: Dict[str, Any] = {}

    # Direct fields
    normalised["name"] = doc.get("name", "")
    normalised["email"] = doc.get("email")

    # ── Group numbered keys by prefix ─────────────────────────────
    grouped: Dict[str, Dict[int, Dict[str, Any]]] = {}
    numbered_pattern = re.compile(
        r"^(experience|project|education|certification|internship_experience)_(\d+)_(.+)$"
    )

    for key, value in doc.items():
        m = numbered_pattern.match(key)
        if m:
            prefix, idx_str, subfield = m.groups()
            idx = int(idx_str)
            grouped.setdefault(prefix, {}).setdefault(idx, {})[subfield] = value

    # ── Skills (from technical_skills_* keys) ─────────────────────
    skills: List[str] = []
    for k, v in doc.items():
        if k.startswith("technical_skills_") and isinstance(v, str):
            skills.extend([s.strip() for s in v.split(",") if s.strip()])
    if doc.get("skills"):
        if isinstance(doc["skills"], list):
            skills.extend(doc["skills"])
        elif isinstance(doc["skills"], str):
            skills.extend([s.strip() for s in doc["skills"].split(",") if s.strip()])
    normalised["skills"] = list(dict.fromkeys(skills))  # deduplicate, preserve order

    # ── Experience ────────────────────────────────────────────────
    experience_entries = []
    for prefix in ["experience", "internship_experience"]:
        if prefix in grouped:
            for idx in sorted(grouped[prefix]):
                entry = grouped[prefix][idx]
                experience_entries.append({
                    "title": entry.get("role", entry.get("title", "")),
                    "company": entry.get("company_location", entry.get("company", "")),
                    "start": entry.get("start_date", entry.get("start", "")),
                    "end": entry.get("end_date", entry.get("end", "")),
                    "description": entry.get("description", None),
                    "responsibilities": [
                        v for k, v in sorted(entry.items())
                        if k.startswith("detail_") and isinstance(v, str)
                    ] or None,
                })
    normalised["experience"] = experience_entries

    # ── Projects ──────────────────────────────────────────────────
    if "project" in grouped:
        normalised["projects"] = [
            {
                "name": entry.get("name", ""),
                "description": entry.get("type", entry.get("description", "")),
                "technologies": None,
            }
            for idx, entry in sorted(grouped["project"].items())
        ]
        # Append project details as description addendum
        for idx, entry in sorted(grouped["project"].items()):
            details = [v for k, v in sorted(entry.items()) if k.startswith("detail_") and isinstance(v, str)]
            if details and idx - 1 < len(normalised["projects"]):
                existing_desc = normalised["projects"][idx - 1].get("description", "") or ""
                normalised["projects"][idx - 1]["description"] = (
                    existing_desc + "\n" + "\n".join(details)
                ).strip()

    # ── Education ─────────────────────────────────────────────────
    if "education" in grouped:
        normalised["education"] = [
            {
                "degree": entry.get("degree", ""),
                "institution": entry.get("university", entry.get("institution", "")),
                "start_year": str(entry.get("start_year", "")) if entry.get("start_year") else None,
                "end_year": str(entry.get("end_year", "")) if entry.get("end_year") else None,
                "field_of_study": entry.get("field_of_study"),
                "cgpa": str(entry.get("cgpa", entry.get("percentage", ""))) if entry.get("cgpa") or entry.get("percentage") else None,
                "institute_location": entry.get("institute_location"),
            }
            for idx, entry in sorted(grouped["education"].items())
        ]

    # ── Certifications ────────────────────────────────────────────
    if "certification" in grouped:
        normalised["certifications"] = [
            entry.get(list(entry.keys())[0], "") if len(entry) == 1 else str(entry)
            for idx, entry in sorted(grouped["certification"].items())
        ]
    elif doc.get("certifications"):
        normalised["certifications"] = doc["certifications"]

    # ── Fields with no flat equivalent default to empty ───────────
    normalised.setdefault("projects", [])
    normalised.setdefault("education", [])
    normalised.setdefault("certifications", [])
    normalised.setdefault("candidate_achievements", [])
    normalised.setdefault("tools", [])
    normalised.setdefault("technologies", [])
    normalised.setdefault("salary_expectation", None)

    return normalised


def _unwrap_specified_fields(raw: Dict[str, Any]) -> Dict[str, Any]:
    """
    Unwrap ``extracted_fields.content._raw_response`` format.
    The _raw_response is a stringified JSON with {value, line} wrappers.
    """
    ef = raw.get("extracted_fields", {})
    content = ef.get("content", {}) if isinstance(ef, dict) else {}
    raw_str = content.get("_raw_response", "") if isinstance(content, dict) else ""

    if not raw_str:
        return raw

    try:
        parsed = json.loads(raw_str) if isinstance(raw_str, str) else raw_str
    except (json.JSONDecodeError, TypeError):
        return raw

    if not isinstance(parsed, dict):
        return raw

    # Recursively strip {value:, line:} wrappers
    return _strip_value_line_wrappers(parsed)


def _strip_value_line_wrappers(obj: Any) -> Any:
    """
    Recursively collapse ``{value: X, line: N}`` dicts into just ``X``.
    Also renames known field aliases to canonical names.
    """
    if isinstance(obj, dict):
        # Check if this IS a {value, line} wrapper
        if set(obj.keys()) <= {"value", "line"} and "value" in obj:
            return _strip_value_line_wrappers(obj["value"])

        cleaned = {}
        for k, v in obj.items():
            # Rename aliases
            canonical_key = _FIELD_ALIASES.get(k, k)
            cleaned[canonical_key] = _strip_value_line_wrappers(v)
        return cleaned

    if isinstance(obj, list):
        return [_strip_value_line_wrappers(item) for item in obj]

    return obj


# Field-name aliases from various docstrange formats → canonical names
_FIELD_ALIASES: Dict[str, str] = {
    "role": "title",
    "start_date": "start",
    "end_date": "end",
    "university": "institution",
    "company_location": "company",
    "title": "title",       # passthrough
    "name": "name",
    "project_name": "name",
}


# =====================================================================
# Main Validation Engine
# =====================================================================

def detect_format(raw: Dict[str, Any]) -> str:
    """Detect the wrapper format of a raw extraction result."""
    fmt = raw.get("format", "")
    if fmt == "structured_json" or "structured_data" in raw:
        return "structured_json"
    if fmt == "cloud_flat_json" or ("document" in raw and "structured_data" not in raw):
        return "cloud_flat_json"
    if fmt == "specified_fields" or "extracted_fields" in raw:
        return "specified_fields"
    if fmt == "extraction_failed":
        return "extraction_failed"
    # If the top-level has canonical fields directly, treat as already-normalised
    if "name" in raw and ("skills" in raw or "experience" in raw):
        return "already_normalised"
    return "unknown"


def unwrap_to_flat(raw: Dict[str, Any]) -> Tuple[Dict[str, Any], str]:
    """
    Detect format and unwrap the raw extraction output into a
    flat dictionary with canonical field names.

    Returns (flat_dict, detected_format).
    """
    fmt = detect_format(raw)

    if fmt == "structured_json":
        return _unwrap_structured_json(raw), fmt
    if fmt == "cloud_flat_json":
        return _unwrap_cloud_flat_json(raw), fmt
    if fmt == "specified_fields":
        return _unwrap_specified_fields(raw), fmt
    if fmt == "already_normalised":
        return raw, fmt
    if fmt == "extraction_failed":
        return raw, fmt

    # Last resort: return as-is
    return raw, fmt


def _build_field_report(
    validated: ValidatedResumeSchema,
    flat_input: Dict[str, Any],
) -> List[FieldReport]:
    """Generate per-field status reports."""

    reports: List[FieldReport] = []

    # Required field
    name_val = validated.name
    if not name_val or not name_val.strip():
        reports.append(FieldReport(field="name", status=FieldStatus.MISSING, message="Required field is empty"))
    else:
        reports.append(FieldReport(field="name", status=FieldStatus.OK))

    # Optional scalar
    if validated.email:
        reports.append(FieldReport(field="email", status=FieldStatus.OK))
    else:
        reports.append(FieldReport(field="email", status=FieldStatus.EMPTY, message="No email found"))

    # List fields
    list_fields = {
        "skills": validated.skills,
        "experience": validated.experience,
        "projects": validated.projects,
        "education": validated.education,
        "candidate_achievements": validated.candidate_achievements,
        "certifications": validated.certifications,
        "tools": validated.tools,
        "technologies": validated.technologies,
    }

    for field_name, items in list_fields.items():
        if items and len(items) > 0:
            # Check if the data was in a different format in the input (= coerced)
            raw_val = flat_input.get(field_name)
            if raw_val is None:
                reports.append(FieldReport(
                    field=field_name, status=FieldStatus.COERCED,
                    message=f"Populated via format normalisation ({len(items)} items)"
                ))
            else:
                reports.append(FieldReport(
                    field=field_name, status=FieldStatus.OK,
                    message=f"{len(items)} items"
                ))
        else:
            reports.append(FieldReport(
                field=field_name, status=FieldStatus.EMPTY,
                message="No data extracted"
            ))

    # Salary
    if validated.salary_expectation and (
        validated.salary_expectation.value or validated.salary_expectation.currency
    ):
        reports.append(FieldReport(field="salary_expectation", status=FieldStatus.OK))
    else:
        reports.append(FieldReport(field="salary_expectation", status=FieldStatus.EMPTY, message="Not provided"))

    return reports


def validate_resume(
    raw_data: Dict[str, Any],
    *,
    strict: bool = False,
) -> Tuple[Optional[ValidatedResumeSchema], ValidationReport]:
    """
    Validate and normalise a raw extraction result.

    Parameters
    ----------
    raw_data : dict
        The raw JSON output from the extraction pipeline (any docstrange format).
    strict : bool
        If True, fail validation when ``name`` is empty.

    Returns
    -------
    (validated_resume, report)
        ``validated_resume`` is None if validation fails fatally.
        ``report`` always contains detailed diagnostics.
    """
    report = ValidationReport()

    # ── Step 1: Detect & unwrap format ────────────────────────────
    flat, fmt = unwrap_to_flat(raw_data)
    report.source_format = fmt

    if fmt == "extraction_failed":
        report.is_valid = False
        report.errors.append("Extraction failed — no usable content in the source document.")
        report.missing_required_fields.append("name")
        return None, report

    if fmt == "unknown":
        report.warnings.append("Could not detect extraction format; attempting best-effort validation.")

    # ── Step 2: Pydantic validation ───────────────────────────────
    try:
        validated = ValidatedResumeSchema(**flat)
    except ValidationError as exc:
        report.is_valid = False
        for err in exc.errors():
            loc = " → ".join(str(part) for part in err["loc"])
            report.errors.append(f"[{loc}] {err['msg']}")
        return None, report

    # ── Step 3: Build field report ────────────────────────────────
    field_reports = _build_field_report(validated, flat)
    report.field_reports = field_reports

    report.total_fields = len(field_reports)
    report.populated_fields = sum(1 for r in field_reports if r.status == FieldStatus.OK)
    report.empty_fields = sum(1 for r in field_reports if r.status in (FieldStatus.EMPTY, FieldStatus.MISSING))
    report.coerced_fields = sum(1 for r in field_reports if r.status == FieldStatus.COERCED)

    # ── Step 4: Check required fields ─────────────────────────────
    if not validated.name or not validated.name.strip():
        report.missing_required_fields.append("name")
        if strict:
            report.is_valid = False
            report.errors.append("Required field 'name' is empty (strict mode).")
        else:
            report.warnings.append("Required field 'name' is empty — resume may be unusable for scoring.")

    # ── Step 5: Semantic warnings ─────────────────────────────────
    if not validated.skills and not validated.technologies and not validated.tools:
        report.warnings.append("No skills, technologies, or tools found — scoring accuracy will be limited.")

    if not validated.experience:
        report.warnings.append("No experience entries found.")

    if not validated.education:
        report.warnings.append("No education entries found.")

    return validated, report


# =====================================================================
# Convenience: Validate from file path
# =====================================================================

def validate_resume_file(
    json_path: Union[str, Path],
    *,
    strict: bool = False,
) -> Tuple[Optional[ValidatedResumeSchema], ValidationReport]:
    """
    Load a JSON file and validate it against the resume schema.

    Parameters
    ----------
    json_path : str | Path
        Path to the extracted resume JSON file.
    strict : bool
        Passed through to ``validate_resume()``.

    Returns
    -------
    (validated_resume, report)
    """
    path = Path(json_path)
    if not path.exists():
        report = ValidationReport(is_valid=False)
        report.errors.append(f"File not found: {path}")
        return None, report

    with open(path, "r", encoding="utf-8") as f:
        raw_data = json.load(f)

    return validate_resume(raw_data, strict=strict)


# =====================================================================
# Convenience: Validate and save the cleaned output
# =====================================================================

def validate_and_save(
    raw_data: Dict[str, Any],
    output_path: Union[str, Path],
    *,
    strict: bool = False,
    save_report: bool = True,
) -> Tuple[bool, ValidationReport]:
    """
    Validate, normalise, and save the cleaned resume JSON.

    Parameters
    ----------
    raw_data : dict
        Raw extraction output.
    output_path : str | Path
        Where to save the validated JSON.
    strict : bool
        Fail on missing required fields.
    save_report : bool
        If True, also save a ``*_validation_report.json`` alongside.

    Returns
    -------
    (success, report)
    """
    validated, report = validate_resume(raw_data, strict=strict)

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if validated:
        # Save validated resume (exclude None/pipeline_metadata from the scoring schema)
        validated_dict = validated.model_dump(exclude_none=True)

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(validated_dict, f, indent=4, ensure_ascii=False)

        if save_report:
            report_path = output_path.with_name(
                output_path.stem + "_validation_report.json"
            )
            with open(report_path, "w", encoding="utf-8") as f:
                json.dump(report.model_dump(), f, indent=4, ensure_ascii=False)

        return True, report

    else:
        # Save the report even on failure for debugging
        if save_report:
            report_path = output_path.with_name(
                output_path.stem + "_validation_report.json"
            )
            with open(report_path, "w", encoding="utf-8") as f:
                json.dump(report.model_dump(), f, indent=4, ensure_ascii=False)

        return False, report


# =====================================================================
# CLI entry point (batch validate all extraction outputs)
# =====================================================================

def _print(msg: str) -> None:
    """Safe print for Windows consoles that choke on Unicode."""
    import sys as _sys
    try:
        print(msg)
    except UnicodeEncodeError:
        safe = msg.encode(_sys.stdout.encoding or "ascii", errors="replace").decode(
            _sys.stdout.encoding or "ascii"
        )
        print(safe)


def main():
    """Batch-validate all JSON files in ``resume_extraction_outputs/``."""
    from .config import Config

    Config.ensure_directories()

    input_dir = Config.OUTPUT_DIR
    validated_dir = input_dir.parent / "validated_resume_outputs"
    validated_dir.mkdir(parents=True, exist_ok=True)

    json_files = sorted(input_dir.glob("*.json"))
    if not json_files:
        print("\n(!) No extraction output JSON files found.")
        return

    _print(f"\n{'=' * 70}")
    _print(f"  Resume Schema Validation -- {len(json_files)} file(s)")
    _print(f"{'=' * 70}")

    valid_count = 0
    total = len(json_files)

    for idx, json_path in enumerate(json_files, 1):
        _print(f"\n-- [{idx}/{total}] {json_path.name} --")

        with open(json_path, "r", encoding="utf-8") as f:
            raw_data = json.load(f)

        out_path = validated_dir / json_path.name
        success, report = validate_and_save(raw_data, out_path)

        # Pretty-print summary
        fmt_tag = f"[{report.source_format}]"
        if success:
            valid_count += 1
            _print(f"   [PASS] VALID   {fmt_tag}  "
                   f"({report.populated_fields}/{report.total_fields} fields populated)")
        else:
            _print(f"   [FAIL] INVALID {fmt_tag}")

        for w in report.warnings:
            _print(f"      WARN: {w}")
        for e in report.errors:
            _print(f"      ERR:  {e}")

    _print(f"\n{'=' * 70}")
    _print(f"  Done! {valid_count}/{total} resume(s) validated successfully.")
    _print(f"  Validated outputs saved to: {validated_dir}")
    _print(f"{'=' * 70}\n")


if __name__ == "__main__":
    main()
