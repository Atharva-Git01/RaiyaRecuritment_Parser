"""
Resume Extraction & Normalization — CLI Entry Point.

Pipeline:
  1. Resume PDF → docstrange (cloud API) → structured JSON (custom schema)
  2. Content hash for caching
  3. Save JSON output + hash metadata
  4. Pydantic schema validation & normalization
"""

import json
import sys

from modules import (
    Config,
    get_resume_files,
    display_files_menu,
    hash_and_check,
    store_hash,
    sha256_bytes,
    DocumentExtractor,
    validate_resume,
    ValidatedResumeSchema,
    ValidationReport,
)

# ──────────────────────────────────────────────────────────────────────
# Custom JSON Schema for Resume Extraction
# (mirrors reference_parsed_resume_format.json as a JSON Schema draft-07)
# ──────────────────────────────────────────────────────────────────────
RESUME_EXTRACTION_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object",
    "properties": {
        "pipeline_metadata": {
            "type": "object",
            "properties": {
                "resume_content_hash": {"type": "string"},
                "created_at": {"type": "string", "format": "date-time"},
                "source": {"type": "string"},
            },
            "required": ["resume_content_hash"],
        },
        "name": {"type": "string"},
        "email": {"type": "string", "format": "email"},
        "skills": {
            "type": "array",
            "items": {"type": "string"},
        },
        "experience": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "company": {"type": "string"},
                    "start": {"type": "string"},
                    "end": {"type": "string"},
                    "description": {"type": "string"},
                    "responsibilities": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                },
                "required": ["title", "company"],
            },
        },
        "projects": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "description": {"type": "string"},
                    "technologies": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                },
                "required": ["name"],
            },
        },
        "education": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "degree": {"type": "string"},
                    "institution": {"type": "string"},
                    "start_year": {"type": "string"},
                    "end_year": {"type": "string"},
                    "field_of_study": {"type": "string"},
                    "cgpa": {"type": "string"},
                    "institute_location": {"type": "string"},
                },
                "required": ["degree", "institution"],
            },
        },
        "candidate_achievements": {
            "type": "array",
            "items": {"type": "string"},
        },
        "certifications": {
            "type": "array",
            "items": {"type": "string"},
        },
        "tools": {
            "type": "array",
            "items": {"type": "string"},
        },
        "technologies": {
            "type": "array",
            "items": {"type": "string"},
        },
        "salary_expectation": {
            "type": "object",
            "properties": {
                "value": {"type": "string"},
                "currency": {"type": "string"},
            },
        },
    },
    "required": ["name"],
}


def process_single_resume(resume_path, output_dir, hashed_dir, status_callback=None):
    """
    Full pipeline for one resume:
      1. Compute file-level SHA-256 for traceability.
      2. Check hash cache for duplicate content.
         • Cache HIT  → load cached JSON, skip docstrange.
         • Cache MISS → proceed with extraction.
      3. Extract structured JSON via docstrange with custom schema (PDF → JSON).
      4. Inject the real content hash into pipeline_metadata.
      5. Store result in hash cache and save .json.
    """
    file_name = resume_path.name
    stem = resume_path.stem

    def log(msg):
        # Safe print for Windows consoles that don't support UTF-8 (charmap error)
        try:
            print(msg)
        except UnicodeEncodeError:
            # Strip or replace non-encodable characters for the console print
            safe_msg = msg.encode(sys.stdout.encoding, errors="replace").decode(sys.stdout.encoding)
            print(safe_msg)
            
        if status_callback:
            status_callback(msg)

    # ── Step 1: File-level SHA-256 (binary fingerprint) ───────────
    file_bytes = resume_path.read_bytes()
    file_hash = sha256_bytes(file_bytes)
    log(f"   Key File hash: {file_hash[:16]}…")

    # ── Step 2: Cache check ───────────────────────────────────────
    content_digest, cache_hit, cached_json_str = hash_and_check(
        file_hash, file_name, hashed_dir
    )

    if cache_hit:
        log("   ♻  Cache HIT — skipping docstrange extraction.")
        json_data = json.loads(cached_json_str)

        json_path = output_dir / f"{stem}.json"
        output_dir.mkdir(parents=True, exist_ok=True)
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(json_data, f, indent=4, ensure_ascii=False)
        log(f"   ✅ Saved JSON → {json_path}  (from cache)")
        return True, json_data
    else:
        # ── Step 3: Extract structured JSON via docstrange + schema ───
        raw_json = None
        try:
            extractor = DocumentExtractor(gpu=False)
            result = extractor.extract(str(resume_path))
            raw_json = result.extract_data(json_schema=RESUME_EXTRACTION_SCHEMA)
            log("   ✅ docstrange extraction completed.")
        except Exception as exc:
            log(f"   ⚠  docstrange JSON extraction failed: {exc}")

        if not raw_json:
            raw_json = {
                "document": {"error": "No extractable content found in document"},
                "format": "extraction_failed",
            }
            log(f"   ❌ Extraction failed for '{file_name}'.")

        # ── Step 4: Schema Validation & Normalization ────────────────
        validated_resume, report = validate_resume(raw_json)
        
        # Decide which data to store as primary: validated (preferred) or raw (fallback)
        if validated_resume:
            final_data = validated_resume.model_dump(exclude_none=True)
            log(f"   🛡️  Validation PASSED [{report.source_format}] ({report.populated_fields}/{report.total_fields} fields)")
        else:
            final_data = raw_json
            log(f"   ⚠  Validation FAILED — falling back to raw JSON")
            for e in report.errors:
                log(f"      ✖  {e}")

        # ── Step 5: Inject real hash into pipeline_metadata ───────────
        if isinstance(final_data, dict):
            # Navigate to the right nested level if it's already a docstrange format
            # (only applies to fallback/raw; validated is already flat)
            content = final_data
            if not validated_resume:
                if "structured_data" in content and isinstance(content["structured_data"], dict):
                    inner = content["structured_data"]
                    if "content" in inner and isinstance(inner["content"], dict):
                        content = inner["content"]
                    else:
                        content = inner

            if "pipeline_metadata" in content and isinstance(content["pipeline_metadata"], dict):
                content["pipeline_metadata"]["resume_content_hash"] = file_hash
            else:
                content["pipeline_metadata"] = {
                    "resume_content_hash": file_hash,
                    "source": file_name,
                }

        # ── Step 6: Store in hash cache + save primary JSON ───────────
        json_str = json.dumps(final_data, ensure_ascii=False, indent=4)

        store_hash(
            file_hash, json_str, file_name, hashed_dir,
            extracted_text=json_str,
        )
        log(f"   🆕 Cached result (hash: {file_hash[:16]}…)")

        json_path = output_dir / f"{stem}.json"
        output_dir.mkdir(parents=True, exist_ok=True)
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(final_data, f, indent=4, ensure_ascii=False)

        log(f"   ✅ Saved primary JSON → {json_path}")

        # ── Step 7: Save validation report ────────────────────────────
        report_dir = output_dir.parent / "validated_resume_outputs" # Keep separate for audit reports
        report_dir.mkdir(parents=True, exist_ok=True)
        report_path = report_dir / f"{stem}_validation_report.json"
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report.model_dump(), f, indent=4, ensure_ascii=False)

        for w in report.warnings:
            log(f"      ⚠  {w}")

    return True, final_data


# ── main ─────────────────────────────────────────────────────────────


def main():
    Config.ensure_directories()

    # Ensure validation report directory exists
    report_dir = Config.OUTPUT_DIR.parent / "validated_resume_outputs"
    report_dir.mkdir(parents=True, exist_ok=True)

    resume_files = get_resume_files()
    if not resume_files:
        print("\n(!) No supported resume files found in the input directory.")
        return

    selected = display_files_menu(resume_files)
    if selected is None:
        return

    print(f"\n{'=' * 60}")
    print(f"  Processing {len(selected)} resume(s)...")
    print(f"{'=' * 60}")

    success = 0
    for idx, path in enumerate(selected, 1):
        print(f"\n-- [{idx}/{len(selected)}] {path.name} --")
        if process_single_resume(path, Config.OUTPUT_DIR, Config.HASHED_OUTPUT_DIR):
            success += 1

    print(f"\n{'=' * 60}")
    print(f"  Done! {success}/{len(selected)} resume(s) extracted + validated.")
    print(f"  Primary outputs:     {Config.OUTPUT_DIR}")
    print(f"  Validation reports:  {report_dir}")
    print(f"{'=' * 60}\n")


if __name__ == "__main__":
    main()

