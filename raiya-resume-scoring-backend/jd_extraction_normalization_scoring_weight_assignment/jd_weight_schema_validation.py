"""
JD Weight Schema Validation Agent
===================================
Validates JD weight JSON files (in jd_weight_json_output/ and
hashed_jd_weight_json_output/) against the canonical schema defined in
jd_weights_schema_format.json.

Checks performed:
  1. Structural completeness  — all required top-level & nested keys present
  2. Type conformance         — each field matches expected type (str, list, dict, etc.)
  3. Scoring section integrity:
       a. All 8 scoring sub-sections present with weight + criteria
       b. Salary section present with weight + fallback_score + criteria_based_on_salary_expectation
       c. relevant_experience criteria keys match canonical set
       d. experience criteria keys match canonical set
       e. salary criteria keys match canonical set
  4. Weight sum rule          — scoring weights + salary weight must sum to 100 (±0.5)
  5. Criteria value ranges    — all criteria scores ≥ 0
       Supports both formats:
         • Legacy flat:  criteria["SQL"] = 80  (plain number)
         • Enterprise:   criteria["SQL"] = {"score": 80, "reasoning_label": "...",
                           "multiplier": 0.80, "confidence": 0.91, "evidence": "..."}
  6. No extraneous top-level keys (warning, not failure)
  7. Optional weight_generation_metadata per scoring section — warns if section_importance_factor missing

Usage:
  python jd_weight_schema_validation.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

# ── Paths ────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent                        # jd_extraction_normalization_scoring_weight_assignment/
ROOT_DIR = BASE_DIR.parent                                        # RAIYA_RECRUITING_SOLUTION/
JD_OUTPUT_ROOT = BASE_DIR

WEIGHTS_OUTPUT_DIR = JD_OUTPUT_ROOT / "jd_weight_json_output"
HASHED_WEIGHTS_DIR = JD_OUTPUT_ROOT / "hashed_jd_weight_json_output"
SCHEMA_FILE = WEIGHTS_OUTPUT_DIR / "jd_weights_schema_format.json"


# =====================================================================
# Reference Schema Loader
# =====================================================================

def load_reference_schema() -> dict:
    """Load the canonical JD weights schema format."""
    if not SCHEMA_FILE.exists():
        print(f"  ❌  Schema file not found: {SCHEMA_FILE}")
        sys.exit(1)
    return json.loads(SCHEMA_FILE.read_text(encoding="utf-8"))


# =====================================================================
# Validation Engine
# =====================================================================

# Expected top-level keys and their types
REQUIRED_TOP_LEVEL = {
    "job_title":        str,
    "experience":       str,
    "qualification":    str,
    "technologies":     list,
    "relevant_experience": list,  # UPDATED: Moved from optional to required
    "skills":           list,
    "tools":            list,
    "certifications":   list,     # NEW: Added as required top-level list
    "location":         str,
    "position":         str,
    "job_description":  str,
    "responsibilities": list,
    "employment_type":  str,
    "work_mode":        dict,
    "scoring":          dict,
    "salary":           dict,
}

# Optional top-level keys (allowed but not required)
OPTIONAL_TOP_LEVEL = {"jd_content_hash", "weighting_metadata"}

# The 8 scoring sub-sections (inside "scoring")  # UPDATED
SCORING_SECTIONS = [
    "relevant_experience", "experience", "qualification",
    "technologies", "skills", "position", "tools", "certifications",  # NEW
]

# Fixed criteria keys for specific sections
RELEVANT_EXP_CRITERIA_KEYS = {">=5 years_relevant", "3-4 years_relevant", "1-2 years_relevant", "<1 year_relevant"}
EXPERIENCE_CRITERIA_KEYS    = {">=8 years", "5-7 years", "3-4 years", "<3 years"}
SALARY_CRITERIA_KEYS        = {"3-6", "6-10", ">10"}


class ValidationResult:
    """Collects errors and warnings for a single file."""

    def __init__(self, filename: str):
        self.filename = filename
        self.errors: List[str] = []
        self.warnings: List[str] = []

    def error(self, msg: str) -> None:
        self.errors.append(msg)

    def warn(self, msg: str) -> None:
        self.warnings.append(msg)

    @property
    def passed(self) -> bool:
        return len(self.errors) == 0

    def summary_line(self) -> str:
        if self.passed and not self.warnings:
            return f"  ✅  {self.filename}  — PASSED"
        elif self.passed:
            return f"  ⚠️   {self.filename}  — PASSED with {len(self.warnings)} warning(s)"
        else:
            return f"  ❌  {self.filename}  — FAILED ({len(self.errors)} error(s), {len(self.warnings)} warning(s))"


def validate_weight_file(data: dict, filename: str) -> ValidationResult:
    """Run all validation checks on a parsed weight JSON dict."""
    result = ValidationResult(filename)

    # ── 1. Top-level key presence & types ────────────────────────────
    for key, expected_type in REQUIRED_TOP_LEVEL.items():
        if key not in data:
            result.error(f"Missing required top-level key: '{key}'")
        else:
            if isinstance(expected_type, tuple):
                if not isinstance(data[key], expected_type):
                    result.error(f"Key '{key}': expected {' or '.join(t.__name__ for t in expected_type)}, "
                                 f"got {type(data[key]).__name__}")
            else:
                if not isinstance(data[key], expected_type):
                    result.error(f"Key '{key}': expected {expected_type.__name__}, got {type(data[key]).__name__}")

    # Check for extraneous top-level keys
    allowed = set(REQUIRED_TOP_LEVEL.keys()) | OPTIONAL_TOP_LEVEL
    for key in data:
        if key not in allowed:
            result.warn(f"Unexpected top-level key: '{key}' (will be ignored by scorer)")

    # ── 1b. work_mode sub-key validation ─────────────────────────────
    work_mode = data.get("work_mode")
    if isinstance(work_mode, dict):
        _WORK_MODE_KEYS = {"remote_option", "work_from_office", "hybrid"}
        for wm_key in _WORK_MODE_KEYS:
            if wm_key not in work_mode:
                result.error(f"work_mode: missing key '{wm_key}'")
            elif not isinstance(work_mode[wm_key], bool):
                result.error(f"work_mode.{wm_key}: expected bool, got {type(work_mode[wm_key]).__name__}")
        extra_wm = set(work_mode.keys()) - _WORK_MODE_KEYS
        if extra_wm:
            result.warn(f"work_mode: unexpected keys {extra_wm}")

    # ── 2. Scoring section validation ────────────────────────────────
    scoring = data.get("scoring")
    if not isinstance(scoring, dict):
        result.error("'scoring' is not a dict or is missing")
        return result  # can't continue scoring checks

    for section in SCORING_SECTIONS:
        if section not in scoring:
            result.error(f"scoring: missing sub-section '{section}'")
            continue

        sec_data = scoring[section]
        if not isinstance(sec_data, dict):
            result.error(f"scoring.{section}: expected dict, got {type(sec_data).__name__}")
            continue

        # weight key
        if "weight" not in sec_data:
            result.error(f"scoring.{section}: missing 'weight'")
        elif not isinstance(sec_data["weight"], (int, float)):
            result.error(f"scoring.{section}.weight: expected number, got {type(sec_data['weight']).__name__}")
        elif sec_data["weight"] < 0:
            result.error(f"scoring.{section}.weight: negative value ({sec_data['weight']})")

        # criteria key
        if "criteria" not in sec_data:
            result.error(f"scoring.{section}: missing 'criteria'")
        elif not isinstance(sec_data["criteria"], dict):
            result.error(f"scoring.{section}.criteria: expected dict, got {type(sec_data['criteria']).__name__}")
        else:
            for crit_key, crit_val in sec_data["criteria"].items():
                if isinstance(crit_val, dict):
                    # Enterprise rich format: {"score": float, "reasoning_label": str, "multiplier": float, ...}
                    score = crit_val.get("score")
                    if score is None:
                        result.warn(f"scoring.{section}.criteria['{crit_key}']: rich dict missing 'score' key")
                    elif not isinstance(score, (int, float)):
                        result.error(f"scoring.{section}.criteria['{crit_key}'].score: expected number, got {type(score).__name__}")
                    elif score < 0:
                        result.warn(f"scoring.{section}.criteria['{crit_key}'].score: negative ({score})")
                    # Validate reasoning_label if present
                    label = crit_val.get("reasoning_label")
                    if label is not None and not isinstance(label, str):
                        result.error(f"scoring.{section}.criteria['{crit_key}'].reasoning_label: expected str")
                    # Validate multiplier if present
                    mult = crit_val.get("multiplier")
                    if mult is not None and not isinstance(mult, (int, float)):
                        result.error(f"scoring.{section}.criteria['{crit_key}'].multiplier: expected number")
                    # Validate confidence if present
                    conf = crit_val.get("confidence")
                    if conf is not None:
                        if not isinstance(conf, (int, float)):
                            result.error(f"scoring.{section}.criteria['{crit_key}'].confidence: expected number")
                        elif not (0.0 <= conf <= 1.0):
                            result.warn(f"scoring.{section}.criteria['{crit_key}'].confidence: {conf} out of [0,1]")
                elif isinstance(crit_val, (int, float)):
                    # Legacy flat format: plain number
                    if crit_val < 0:
                        result.warn(f"scoring.{section}.criteria['{crit_key}']: negative score ({crit_val})")
                else:
                    result.error(
                        f"scoring.{section}.criteria['{crit_key}']: expected number or rich dict, "
                        f"got {type(crit_val).__name__}"
                    )

        # Optional weight_generation_metadata: warn if section_importance_factor is missing
        wgm = sec_data.get("weight_generation_metadata")
        if wgm is not None:
            if not isinstance(wgm, dict):
                result.warn(f"scoring.{section}.weight_generation_metadata: expected dict")
            elif "section_importance_factor" not in wgm:
                result.warn(f"scoring.{section}.weight_generation_metadata: missing 'section_importance_factor'")

    # ── 3. Fixed criteria key checks ─────────────────────────────────
    # relevant_experience
    rel_exp = scoring.get("relevant_experience", {})
    if isinstance(rel_exp, dict) and "criteria" in rel_exp and isinstance(rel_exp["criteria"], dict):
        actual_keys = set(rel_exp["criteria"].keys())
        missing = RELEVANT_EXP_CRITERIA_KEYS - actual_keys
        if missing:
            result.warn(f"scoring.relevant_experience.criteria: missing canonical keys {missing}")
        extra = actual_keys - RELEVANT_EXP_CRITERIA_KEYS
        if extra:
            result.warn(f"scoring.relevant_experience.criteria: extra keys {extra}")

    # experience
    exp = scoring.get("experience", {})
    if isinstance(exp, dict) and "criteria" in exp and isinstance(exp["criteria"], dict):
        actual_keys = set(exp["criteria"].keys())
        missing = EXPERIENCE_CRITERIA_KEYS - actual_keys
        if missing:
            result.warn(f"scoring.experience.criteria: missing canonical keys {missing}")
        extra = actual_keys - EXPERIENCE_CRITERIA_KEYS
        if extra:
            result.warn(f"scoring.experience.criteria: extra keys {extra}")

    # ── 4. Salary section validation ─────────────────────────────────
    salary = data.get("salary")
    if not isinstance(salary, dict):
        result.error("'salary' is not a dict or is missing")
    else:
        if "weight" not in salary:
            result.error("salary: missing 'weight'")
        elif not isinstance(salary["weight"], (int, float)):
            result.error(f"salary.weight: expected number, got {type(salary['weight']).__name__}")
        elif salary["weight"] < 0:
            result.error(f"salary.weight: negative value ({salary['weight']})")

        if "fallback_score" not in salary:
            result.warn("salary: missing 'fallback_score'")
        elif not isinstance(salary.get("fallback_score"), (int, float)):
            result.warn(f"salary.fallback_score: expected number, got {type(salary.get('fallback_score')).__name__}")

        sal_criteria_key = "criteria_based_on_salary_expectation"
        if sal_criteria_key not in salary:
            result.error(f"salary: missing '{sal_criteria_key}'")
        elif not isinstance(salary[sal_criteria_key], dict):
            result.error(f"salary.{sal_criteria_key}: expected dict, got {type(salary[sal_criteria_key]).__name__}")
        else:
            actual_keys = set(salary[sal_criteria_key].keys())
            missing = SALARY_CRITERIA_KEYS - actual_keys
            if missing:
                result.warn(f"salary.{sal_criteria_key}: missing canonical keys {missing}")
            extra = actual_keys - SALARY_CRITERIA_KEYS
            if extra:
                result.warn(f"salary.{sal_criteria_key}: extra keys {extra}")
            for crit_key, crit_val in salary[sal_criteria_key].items():
                if not isinstance(crit_val, (int, float)):
                    result.error(f"salary.{sal_criteria_key}['{crit_key}']: expected number, got {type(crit_val).__name__}")

    # ── 5. Weight sum check (Σ = 100 ± 0.5) ─────────────────────────
    try:
        scoring_weights = sum(
            scoring.get(s, {}).get("weight", 0) for s in SCORING_SECTIONS
        )
        salary_weight = salary.get("weight", 0) if isinstance(salary, dict) else 0
        total = scoring_weights + salary_weight
        if total > 0 and abs(total - 100.0) > 0.5:
            result.error(f"Weight sum = {total:.2f}, expected 100 (±0.5)")
        elif total == 0:
            result.warn("All weights are 0 — no scoring differentiation")
    except Exception:
        result.error("Could not compute weight sum (non-numeric weights)")

    return result


# =====================================================================
# File Discovery & Interactive Menu
# =====================================================================

def discover_weight_files() -> List[Tuple[str, Path]]:
    """Find weight JSON files in both output directories.
    
    Returns list of (label, path) tuples.
    """
    files: List[Tuple[str, Path]] = []

    # jd_weight_json_output (exclude the schema file itself)
    if WEIGHTS_OUTPUT_DIR.exists():
        for f in sorted(WEIGHTS_OUTPUT_DIR.iterdir(), key=lambda p: p.name.lower()):
            if f.is_file() and f.suffix.lower() == ".json" and f.name != "jd_weights_schema_format.json":
                files.append((f"[weights]  {f.name}", f))

    # hashed_jd_weight_json_output
    if HASHED_WEIGHTS_DIR.exists():
        for f in sorted(HASHED_WEIGHTS_DIR.iterdir(), key=lambda p: p.name.lower()):
            if f.is_file() and f.suffix.lower() == ".json":
                files.append((f"[hashed]   {f.name}", f))

    return files


def display_menu(files: List[Tuple[str, Path]]) -> List[Tuple[str, Path]]:
    """Interactive menu for selecting weight files to validate."""
    print(f"\n{'=' * 70}")
    print(f"  JD Weight Schema Validation Agent — File Selection")
    print(f"{'=' * 70}")
    print(f"  0)  Validate ALL ({len(files)} files)")
    for idx, (label, fp) in enumerate(files, 1):
        size_kb = fp.stat().st_size / 1024
        print(f"  {idx})  {label}  ({size_kb:.1f} KB)")
    print(f"{'=' * 70}")
    print("  Enter number(s) separated by commas (e.g. 1,3)  |  0 = all  |  q = quit")
    print(f"{'=' * 70}")

    while True:
        choice = input("\n  ▶ Selection: ").strip()
        if choice.lower() in ("q", "quit", "exit"):
            print("  Exiting.")
            sys.exit(0)
        if choice == "0":
            return files
        try:
            indices = [int(x.strip()) for x in choice.split(",")]
        except ValueError:
            print("  ⚠️  Enter numbers separated by commas.")
            continue
        bad = [i for i in indices if i < 1 or i > len(files)]
        if bad:
            print(f"  ⚠️  Invalid: {bad}. Choose 1–{len(files)}.")
            continue
        seen: set = set()
        selected: List[Tuple[str, Path]] = []
        for i in indices:
            if files[i - 1][1] not in seen:
                seen.add(files[i - 1][1])
                selected.append(files[i - 1])
        return selected


# =====================================================================
# Report Printer
# =====================================================================

def print_report(results: List[ValidationResult]) -> None:
    """Print a detailed validation report."""
    total = len(results)
    passed = sum(1 for r in results if r.passed)
    failed = total - passed
    warnings_total = sum(len(r.warnings) for r in results)

    print(f"\n{'═' * 70}")
    print(f"  VALIDATION REPORT")
    print(f"{'═' * 70}")

    for r in results:
        print(f"\n{'─' * 70}")
        print(r.summary_line())
        if r.errors:
            for e in r.errors:
                print(f"      ✗ ERROR:   {e}")
        if r.warnings:
            for w in r.warnings:
                print(f"      ��� WARN:    {w}")

    print(f"\n{'═' * 70}")
    print(f"  SUMMARY:  ✅ {passed} passed  |  ❌ {failed} failed  |  ⚡ {warnings_total} warnings")
    print(f"  Schema ref: {SCHEMA_FILE.name}")
    print(f"{'═' * 70}\n")


# =====================================================================
# Main
# =====================================================================

def main() -> None:
    # Load reference schema (for display, the checks are hard-coded)
    ref_schema = load_reference_schema()
    print(f"\n  📋  Reference schema loaded: {SCHEMA_FILE.name}")
    print(f"      Top-level keys: {len(ref_schema)}")
    print(f"      Scoring sections: {len(ref_schema.get('scoring', {}))}")  # UPDATED: Will now show 8

    files = discover_weight_files()
    if not files:
        print("\n  ⚠️  No weight JSON files found to validate.")
        print(f"      Checked: {WEIGHTS_OUTPUT_DIR}")
        print(f"      Checked: {HASHED_WEIGHTS_DIR}")
        sys.exit(0)

    selected = display_menu(files)
    print(f"\n  Selected {len(selected)} file(s) for validation.\n")

    results: List[ValidationResult] = []

    for label, fp in selected:
        print(f"  Validating: {fp.name} ...")
        try:
            data = json.loads(fp.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            r = ValidationResult(fp.name)
            r.error(f"Invalid JSON: {e}")
            results.append(r)
            continue
        except Exception as e:
            r = ValidationResult(fp.name)
            r.error(f"File read error: {e}")
            results.append(r)
            continue

        if not isinstance(data, dict):
            r = ValidationResult(fp.name)
            r.error(f"Root is not a JSON object, got {type(data).__name__}")
            results.append(r)
            continue

        r = validate_weight_file(data, fp.name)
        results.append(r)

    print_report(results)

    # Exit with non-zero if any failures
    if any(not r.passed for r in results):
        sys.exit(1)


if __name__ == "__main__":
    main()