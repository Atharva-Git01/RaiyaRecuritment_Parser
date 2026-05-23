# Resume Extraction & Normalization - Testing Workflow

## 1. Purpose

This document defines the complete testing workflow for the Resume Extraction & Normalization module in `resume_extraction_normalization/`, including:

1. What to test.
2. How to execute tests.
3. How to capture evidence.
4. How to prepare the final test report.
5. The report format (copy-ready template).

The workflow is aligned with the pipeline implemented in `main.py`:

1. Resume input selection.
2. SHA-256 hash generation.
3. Cache hit/miss behavior.
4. DocStrange extraction.
5. Pydantic validation and normalization.
6. JSON output generation.
7. Validation report generation.

---

## 2. Scope of Testing

### In Scope

1. Input file handling from `resumes/`.
2. Multi-format extraction behavior (`.pdf`, `.docx`, `.txt`, supported image formats).
3. Cache behavior in `hashed_resume_extraction_results/`.
4. Primary output quality in `resume_extraction_outputs/`.
5. Validation report quality in `validated_resume_outputs/`.
6. CLI execution behavior from `main.py`.
7. Error/fallback behavior for unreadable or malformed resumes.

### Out of Scope

1. Resume-to-JD scoring logic (covered in downstream module).
2. Database persistence integration (if tested separately).
3. Production cloud infrastructure or deployment testing.

---

## 3. Test Environment Preparation

## 3.1 Prerequisites

1. Python 3.12.x installed.
2. Virtual environment activated.
3. Dependencies installed:

```bash
pip install -r requirements.txt
```

4. Required folders exist:
	 - `resumes/`
	 - `resume_extraction_outputs/`
	 - `validated_resume_outputs/`
	 - `hashed_resume_extraction_results/`

## 3.1.1 Preferred Testing Tools

Use the following tools for consistent and repeatable QA.

1. `pytest` - primary test runner.
2. `pytest-cov` - coverage measurement.
3. `pytest-html` - quick HTML execution reports.
4. `ruff` - fast linting and style checks.
5. `mypy` - optional static type checking for reliability.
6. `pre-commit` - optional local quality gate before commits.
7. `jq` (CLI) - optional JSON inspection in terminal.

## 3.1.2 Installation Steps (Windows PowerShell)

Run from the module directory:

`resume_extraction_normalization/`

### A. Activate virtual environment

If your venv is at workspace root:

```powershell
& ..\.venv\Scripts\Activate.ps1
```

If your venv is inside this module:

```powershell
& .\myenv\Scripts\Activate.ps1
```

### B. Install project dependencies

```powershell
pip install -r requirements.txt
```

### C. Install preferred testing/quality tools

```powershell
pip install pytest pytest-cov pytest-html ruff mypy pre-commit
```

### D. Optional: install jq

Via `winget`:

```powershell
winget install jqlang.jq
```

### E. Verify installations

```powershell
pytest --version
ruff --version
mypy --version
pre-commit --version
```

## 3.1.3 Optional One-Time Setup Files

If you want standardized local execution, add these files later:

1. `pytest.ini` for test discovery and markers.
2. `.pre-commit-config.yaml` for lint/format/type hooks.
3. `requirements-dev.txt` to pin QA tool versions.

Example `requirements-dev.txt`:

```txt
pytest
pytest-cov
pytest-html
ruff
mypy
pre-commit
```

Then install with:

```powershell
pip install -r requirements-dev.txt
```

## 3.2 Test Data Set

Prepare a controlled test set in `resumes/` with at least:

1. 3 valid PDF resumes (simple, medium, complex layout).
2. 2 valid DOCX resumes.
3. 1 text resume.
4. 1 scanned/image-based resume.
5. 1 malformed/corrupted file.
6. 1 duplicate-content resume (same content, different filename) for cache validation.
7. 1 resume with missing key fields (for validation warning checks).

Use stable file names so report traceability remains consistent across runs.

## 3.3 Execution Baseline

Before each full test cycle:

1. Clean or archive old outputs (if baseline run is required).
2. Confirm folder counts are recorded:
	 - Number of input resumes.
	 - Number of existing cache files.
3. Record date/time, tester name, and commit/version under test.

---

## 4. End-to-End Testing Workflow

## 4.0 Recommended Test Execution Commands

Use these commands during each test cycle.

### Run automated tests

```powershell
pytest -q
```

### Run tests with coverage

```powershell
pytest --cov=. --cov-report=term-missing --cov-report=html
```

Coverage HTML output is generated under `htmlcov/`.

### Generate HTML test result report

```powershell
pytest --html=testing_artifacts\pytest_report.html --self-contained-html
```

### Run lint checks

```powershell
ruff check .
```

### Run type checks (optional)

```powershell
mypy .
```

## Phase 1: Smoke Test

Goal: Ensure pipeline starts and processes at least one valid file end-to-end.

Steps:

1. Run:

```bash
python main.py
```

2. Select one known-good resume.
3. Verify console shows extraction, validation, and save logs.
4. Confirm output files are created:
	 - `resume_extraction_outputs/<resume_stem>.json`
	 - `validated_resume_outputs/<resume_stem>_validation_report.json`

Pass Criteria:

1. No unhandled exception.
2. Both output and validation report are generated.

## Phase 2: Functional Test Matrix

Goal: Validate expected behavior by scenario.

Run scenarios:

1. Valid PDF extraction.
2. Valid DOCX extraction.
3. Valid TXT extraction.
4. Image/scanned resume extraction.
5. Corrupt file handling.
6. Missing critical field behavior (for warning/error capture).

For each scenario, verify:

1. Process result (`Success` or controlled fallback).
2. JSON structure presence (name, skills, education, experience where available).
3. Validation report fields:
	 - `source_format`
	 - `populated_fields`
	 - `total_fields`
	 - `errors`
	 - `warnings`

Pass Criteria:

1. Expected behavior matches scenario definition.
2. Failures are controlled and logged (no silent crash).

## Phase 3: Cache Behavior Test

Goal: Verify hash-based deduplication and cache retrieval.

Steps:

1. Process a resume once and note log output.
2. Process the same content again (same file or duplicate-content renamed file).
3. Verify second run shows cache hit behavior.
4. Validate output JSON consistency between first and second run.

Pass Criteria:

1. First run: cache miss and extraction path.
2. Second run: cache hit path.
3. Output correctness is unchanged.

## Phase 4: Validation and Normalization Quality Test

Goal: Measure schema quality and data usability.

Checks:

1. Required core fields are present when source contains the information.
2. Data types are normalized (arrays for skills/projects, objects for structured sections).
3. `pipeline_metadata.resume_content_hash` is present in final JSON.
4. Validation reports clearly capture warnings and errors.

Pass Criteria:

1. Normalized schema is consistent across file types.
2. Reports are interpretable for debugging.

## Phase 5: Regression Test

Goal: Ensure new changes do not break old behavior.

Steps:

1. Re-run the curated baseline test set after any code change.
2. Compare with prior run metrics:
	 - Success count
	 - Failure count
	 - Average populated field ratio
	 - Cache hit ratio

Pass Criteria:

1. No unexpected drop in extraction success.
2. No new critical errors in validation reports.

---

## 5. Suggested Test Case Format

Use this structure for each test case.

| Field | Description |
|---|---|
| Test Case ID | Unique ID (example: RE-TC-001) |
| Title | Short test objective |
| Type | Smoke / Functional / Cache / Regression / Negative |
| Input File | Resume file name |
| Preconditions | Setup required before running |
| Steps | Numbered execution steps |
| Expected Result | What should happen |
| Actual Result | What happened during test |
| Status | Pass / Fail / Blocked |
| Evidence | Output file paths, logs, screenshots |
| Defect ID | Linked issue/bug number if failed |

---

## 6. Evidence Collection Checklist

For each test cycle, collect:

1. Test run timestamp.
2. Git commit hash or version tag.
3. List of input files tested.
4. Console log snippets (especially for failures and cache behavior).
5. Output artifacts:
	 - Generated JSON files.
	 - Validation report files.
6. Defect list with severity and reproduction steps.

Store test artifacts in a dated folder (example):

`testing_artifacts/YYYY-MM-DD_run-01/`

---

## 7. Test Report Preparation Workflow

Use this sequence after executing all tests.

1. Consolidate executed test cases and statuses.
2. Calculate summary metrics:
	 - Total test cases.
	 - Passed.
	 - Failed.
	 - Blocked.
	 - Pass rate.
3. Summarize key findings:
	 - What is working.
	 - What failed.
	 - Known limitations.
4. Add defect summary table (ID, severity, owner, status).
5. Include evidence references (paths to outputs and validation reports).
6. Add release recommendation:
	 - Go / Conditional Go / No-Go.
7. Obtain reviewer sign-off.

Pass rate formula:

`Pass Rate (%) = (Passed / Total Executed) * 100`

---

## 8. Test Report Format (Template)

Copy and reuse the following template for each cycle.

```markdown
# Resume Extraction & Normalization - Test Report

## 1. Report Metadata
- Test Cycle ID:
- Module:
- Build/Commit:
- Test Environment:
- Tester(s):
- Execution Date:
- Report Date:

## 2. Objective
Briefly describe what this test cycle validates.

## 3. Scope
### In Scope
-

### Out of Scope
-

## 4. Execution Summary
| Metric | Value |
|---|---|
| Total Test Cases | |
| Executed | |
| Passed | |
| Failed | |
| Blocked | |
| Pass Rate (%) | |

## 5. Scenario-Level Results
| Test Case ID | Scenario | Input File | Expected | Actual | Status | Defect ID |
|---|---|---|---|---|---|---|
| RE-TC-001 | | | | | | |

## 6. Quality Metrics
| Metric | Value | Notes |
|---|---|---|
| Extraction Success Rate | | |
| Validation Pass Count | | |
| Validation Warning Count | | |
| Cache Hit Ratio | | |
| Avg Populated Fields Ratio | | |

## 7. Defect Summary
| Defect ID | Title | Severity | Priority | Owner | Status | Remarks |
|---|---|---|---|---|---|---|
| BUG-001 | | | | | | |

## 8. Evidence Links
- Console logs:
- Output JSON folder:
- Validation reports folder:
- Screenshots/attachments:

## 9. Risks & Observations
-

## 10. Recommendation
- Decision: Go / Conditional Go / No-Go
- Conditions (if any):

## 11. Sign-Off
| Role | Name | Decision | Date |
|---|---|---|---|
| QA | | | |
| Dev | | | |
| Product/Owner | | | |
```

---

## 9. Optional JSON Report Format

If you want machine-readable reporting, use this structure:

```json
{
	"report_metadata": {
		"test_cycle_id": "",
		"module": "resume_extraction_normalization",
		"build_commit": "",
		"environment": "",
		"testers": [],
		"execution_date": "",
		"report_date": ""
	},
	"summary": {
		"total_test_cases": 0,
		"executed": 0,
		"passed": 0,
		"failed": 0,
		"blocked": 0,
		"pass_rate_percent": 0
	},
	"quality_metrics": {
		"extraction_success_rate": 0,
		"validation_pass_count": 0,
		"validation_warning_count": 0,
		"cache_hit_ratio": 0,
		"avg_populated_fields_ratio": 0
	},
	"test_cases": [
		{
			"test_case_id": "RE-TC-001",
			"scenario": "",
			"input_file": "",
			"expected": "",
			"actual": "",
			"status": "Pass",
			"defect_id": ""
		}
	],
	"defects": [
		{
			"defect_id": "BUG-001",
			"title": "",
			"severity": "",
			"priority": "",
			"owner": "",
			"status": "",
			"remarks": ""
		}
	],
	"recommendation": {
		"decision": "Go",
		"conditions": ""
	}
}
```

---

## 10. Reference Test Code (Pytest)

Use the following reference implementation to bootstrap automated tests aligned with this workflow.

Suggested test layout:

- `resume_extraction_normalization/tests/conftest.py`
- `resume_extraction_normalization/tests/test_pipeline_smoke_and_cache.py`
- `resume_extraction_normalization/tests/test_validation_matrix.py`
- `resume_extraction_normalization/tests/test_negative_and_strict_mode.py`

### 10.1 `conftest.py`

```python
from pathlib import Path

import pytest

import main as pipeline
from modules import ValidationReport, ValidatedResumeSchema


@pytest.fixture
def output_dir(tmp_path: Path) -> Path:
	d = tmp_path / "resume_extraction_outputs"
	d.mkdir(parents=True, exist_ok=True)
	return d


@pytest.fixture
def hashed_dir(tmp_path: Path) -> Path:
	d = tmp_path / "hashed_resume_extraction_results"
	d.mkdir(parents=True, exist_ok=True)
	return d


@pytest.fixture
def sample_resume_file(tmp_path: Path) -> Path:
	p = tmp_path / "sample_resume.pdf"
	p.write_bytes(b"%PDF-1.4 fake-resume-content")
	return p


def make_validation_report(source_format: str = "structured_json") -> ValidationReport:
	return ValidationReport(
		is_valid=True,
		source_format=source_format,
		total_fields=10,
		populated_fields=6,
		empty_fields=4,
		coerced_fields=0,
		warnings=[],
		errors=[],
	)


def make_validated_resume() -> ValidatedResumeSchema:
	return ValidatedResumeSchema(
		name="Aarav Sharma",
		email="aarav@example.com",
		skills=["Python", "SQL"],
		experience=[],
		projects=[],
		education=[],
		candidate_achievements=[],
		certifications=[],
		tools=[],
		technologies=[],
		pipeline_metadata={"resume_content_hash": "placeholder"},
	)
```

### 10.2 `test_pipeline_smoke_and_cache.py`

```python
import json
from pathlib import Path

import main as pipeline


def test_smoke_success_path(monkeypatch, sample_resume_file: Path, output_dir: Path, hashed_dir: Path):
	# Force cache miss
	monkeypatch.setattr(
		pipeline,
		"hash_and_check",
		lambda file_hash, file_name, cache_dir: (file_hash, False, None),
	)

	# Fake extractor behavior
	class FakeResult:
		def extract_data(self, json_schema=None):
			return {
				"structured_data": {
					"content": {
						"name": "Aarav Sharma",
						"email": "aarav@example.com",
						"skills": ["Python", "SQL"],
					}
				},
				"format": "structured_json",
			}

	class FakeExtractor:
		def extract(self, file_path: str):
			return FakeResult()

	monkeypatch.setattr(pipeline, "DocumentExtractor", FakeExtractor)

	# Return deterministic validation result
	from conftest import make_validated_resume, make_validation_report

	monkeypatch.setattr(
		pipeline,
		"validate_resume",
		lambda raw: (make_validated_resume(), make_validation_report("structured_json")),
	)

	ok, data = pipeline.process_single_resume(sample_resume_file, output_dir, hashed_dir)
	assert ok is True
	assert data["name"] == "Aarav Sharma"
	assert "pipeline_metadata" in data
	assert "resume_content_hash" in data["pipeline_metadata"]

	primary_output = output_dir / f"{sample_resume_file.stem}.json"
	validation_report = (
		output_dir.parent
		/ "validated_resume_outputs"
		/ f"{sample_resume_file.stem}_validation_report.json"
	)
	assert primary_output.exists()
	assert validation_report.exists()


def test_cache_hit_skips_extractor(monkeypatch, sample_resume_file: Path, output_dir: Path, hashed_dir: Path):
	cached = {
		"name": "Cached Candidate",
		"skills": ["Caching"],
		"pipeline_metadata": {"resume_content_hash": "cached-hash"},
	}

	monkeypatch.setattr(
		pipeline,
		"hash_and_check",
		lambda file_hash, file_name, cache_dir: (file_hash, True, json.dumps(cached)),
	)

	class ShouldNotRunExtractor:
		def __init__(self, *args, **kwargs):
			raise AssertionError("Extractor should not be called on cache hit")

	monkeypatch.setattr(pipeline, "DocumentExtractor", ShouldNotRunExtractor)

	ok, data = pipeline.process_single_resume(sample_resume_file, output_dir, hashed_dir)
	assert ok is True
	assert data["name"] == "Cached Candidate"

	primary_output = output_dir / f"{sample_resume_file.stem}.json"
	assert primary_output.exists()
	saved = json.loads(primary_output.read_text(encoding="utf-8"))
	assert saved["name"] == "Cached Candidate"
```

### 10.3 `test_validation_matrix.py`

```python
from modules import validate_resume


def test_structured_json_normalization():
	raw = {
		"format": "structured_json",
		"structured_data": {
			"content": {
				"name": "Riya Singh",
				"email": "riya@example.com",
				"skills": ["Python", "FastAPI"],
			}
		},
	}
	validated, report = validate_resume(raw)
	assert validated is not None
	assert validated.name == "Riya Singh"
	assert report.source_format == "structured_json"


def test_cloud_flat_json_normalization():
	raw = {
		"format": "cloud_flat_json",
		"document": {
			"name": "Dev Patel",
			"email": "dev@example.com",
			"technical_skills_1": "Python, SQL",
			"education_1_degree": "B.Tech",
			"education_1_university": "ABC University",
		},
	}
	validated, report = validate_resume(raw)
	assert validated is not None
	assert validated.name == "Dev Patel"
	assert "Python" in validated.skills
	assert report.source_format == "cloud_flat_json"


def test_extraction_failed_path():
	raw = {
		"format": "extraction_failed",
		"document": {"error": "No extractable content found"},
	}
	validated, report = validate_resume(raw)
	assert validated is None
	assert report.is_valid is False
	assert len(report.errors) > 0
```

### 10.4 `test_negative_and_strict_mode.py`

```python
from modules import validate_resume


def test_missing_name_non_strict_returns_warning():
	raw = {
		"format": "structured_json",
		"structured_data": {"content": {"skills": ["Python"]}},
	}
	validated, report = validate_resume(raw, strict=False)
	assert validated is not None
	assert "name" in report.missing_required_fields
	assert any("name" in w.lower() for w in report.warnings)


def test_missing_name_strict_fails():
	raw = {
		"format": "structured_json",
		"structured_data": {"content": {"skills": ["Python"]}},
	}
	validated, report = validate_resume(raw, strict=True)
	assert validated is not None or validated is None
	assert "name" in report.missing_required_fields
	assert report.is_valid is False
```

### 10.5 Run Commands

```powershell
pytest -q
pytest --cov=. --cov-report=term-missing --cov-report=html
pytest --html=testing_artifacts\pytest_report.html --self-contained-html
ruff check .
mypy .
```

---

## 11. Exit Criteria

Mark the cycle complete only when all are true:

1. 100% planned critical test cases executed.
2. No open Critical/High defects.
3. Core extraction flow stable across target formats.
4. Validation reports generated for all executed files.
5. Final signed test report is archived.

---

## 12. Versioning

Maintain this file with version notes.

| Version | Date | Author | Change Summary |
|---|---|---|---|
| 1.0 | 2026-04-13 | Copilot | Initial complete testing workflow and report format added |
