"""
JD Extraction — Menu-Driven CLI with Hashed Output Caching
===========================================================
Scans the sample_jd/ directory for PDF files, lets the user pick one,
extracts structured data using DocStrange standard flat JSON output
(no custom schema enforced), then persists the result under a SHA-256
content hash so identical files are never re-processed.

Architecture:
    JD PDF → DocStrange extract_data() → Flat JSON → Pipeline metadata injection

DocStrange's extract_data() (called without json_schema) returns its
native structured flat JSON with all detected entities. This output is
passed directly to the downstream weight assignment pipeline (Phase 2+),
which applies ontology mapping and reasoning label assignment.

Output directory:
    hashed_jd_extraction_results/
        <sha256>.json       — extracted flat JSON (standard DocStrange output)
        <sha256>.meta.json  — pipeline metadata (hash, source file, timestamp)
"""

import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from docstrange import DocumentExtractor

# ──────────────────────────────────────────────
# Paths (relative to project root)
# ──────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent                       # jd_extraction_normalization/
PROJECT_ROOT = BASE_DIR.parents[2]                               # RAIYA_RECRUITING_SOLUTION/
SAMPLE_JD_DIR = PROJECT_ROOT / "modularized_resume_scoring_agent" / "sample_jd"
HASHED_OUTPUT_DIR = BASE_DIR / "hashed_jd_extraction_results"

# Ensure output dir exists
HASHED_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# ──────────────────────────────────────────────
# Utility helpers
# ──────────────────────────────────────────────
def compute_file_hash(filepath: Path) -> str:
    """Return the SHA-256 hex digest of a file's contents."""
    sha256 = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256.update(chunk)
    return sha256.hexdigest()


def discover_pdfs(directory: Path) -> list[Path]:
    """Return a sorted list of PDF files in *directory*."""
    if not directory.exists():
        return []
    return sorted(p for p in directory.iterdir() if p.suffix.lower() == ".pdf")


def print_menu(pdfs: list[Path]) -> None:
    """Display a numbered menu of available JD PDFs."""
    print("\n" + "=" * 60)
    print("  JD EXTRACTION — Standard DocStrange Pipeline (with Hashing)")
    print("=" * 60)
    print(f"\n  Source directory: {SAMPLE_JD_DIR}\n")
    for idx, pdf in enumerate(pdfs, start=1):
        print(f"    [{idx}]  {pdf.name}")
    print(f"\n    [0]  Exit")
    print("-" * 60)


def extract_jd(pdf_path: Path, extractor: DocumentExtractor) -> None:
    """Run extraction for a single JD PDF with hash-based caching.

    Calls extract_data() WITHOUT a json_schema argument so DocStrange returns
    its native flat structured JSON.  The downstream weight assignment pipeline
    (Phases 2–14) handles ontology mapping and reasoning label assignment.
    """

    # 1. Compute content hash
    file_hash = compute_file_hash(pdf_path)
    print(f"\n  [->] File:  {pdf_path.name}")
    print(f"  [->] SHA-256: {file_hash}")

    result_path = HASHED_OUTPUT_DIR / f"{file_hash}.json"
    meta_path = HASHED_OUTPUT_DIR / f"{file_hash}.meta.json"

    # 2. Cache check
    if result_path.exists():
        print(f"\n  [v] Cache HIT — extraction already exists at:")
        print(f"    {result_path}")
        print(f"    Skipping re-extraction.\n")
        return

    # 3. Extract via DocStrange — standard flat JSON (no custom schema imposed)
    print(f"\n  [wait] Extracting with DocStrange (standard flat JSON output)...")
    result = extractor.extract(str(pdf_path))
    structured_data = result.extract_data()  # standard flat JSON — no schema constraint

    # 4. Inject pipeline metadata with the content hash
    if isinstance(structured_data, dict):
        content = structured_data.get("structured_data", structured_data)
        if isinstance(content, dict) and "content" in content:
            inner = content["content"]
        else:
            inner = content

        if isinstance(inner, dict):
            inner["pipeline_metadata"] = {
                "jd_content_hash": file_hash,
                "extraction_method": "docstrange_standard",
                "schema_type": "standard_docstrange_output",
                "created_at": datetime.now(timezone.utc).isoformat(),
            }

    # 5. Persist extraction result
    with open(result_path, "w", encoding="utf-8") as f:
        json.dump(structured_data, f, indent=2, ensure_ascii=False)

    # 6. Persist metadata sidecar
    meta = {
        "jd_content_hash": file_hash,
        "source_file": pdf_path.name,
        "source_path": str(pdf_path),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "extraction_method": "docstrange_standard",
        "schema_type": "standard_docstrange_output",
    }
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2, ensure_ascii=False)

    print(f"  [v] Extraction saved  → {result_path.name}")
    print(f"  [v] Metadata  saved   → {meta_path.name}\n")


# ──────────────────────────────────────────────
# Main menu loop
# ──────────────────────────────────────────────
def main() -> None:
    pdfs = discover_pdfs(SAMPLE_JD_DIR)
    if not pdfs:
        print(f"\n  [x] No PDF files found in {SAMPLE_JD_DIR}")
        sys.exit(1)

    # Initialise extractor once (expensive)
    print("\n  [wait] Initialising DocStrange extractor (CPU mode)...")
    extractor = DocumentExtractor(gpu=False)
    print("  [v] Extractor ready.\n")

    while True:
        print_menu(pdfs)
        choice = input("  Select a JD file number (or 0 to exit): ").strip()

        if choice == "0":
            print("\n  Goodbye!\n")
            break

        if not choice.isdigit() or int(choice) < 1 or int(choice) > len(pdfs):
            print("\n  [!] Invalid selection. Please try again.")
            continue

        selected_pdf = pdfs[int(choice) - 1]
        extract_jd(selected_pdf, extractor)

        input("  Press Enter to continue...")


if __name__ == "__main__":
    main()