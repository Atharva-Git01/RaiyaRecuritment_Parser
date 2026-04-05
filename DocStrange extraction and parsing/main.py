"""
Resume Extraction & Normalization — CLI Entry Point.

Pipeline:
  1. fitz (PyMuPDF) extracts text from text-based PDFs directly.
  2. For image-based / scanned PDFs, fitz renders pages → Tesseract OCR reads text.
  3. Extracted text is saved as a .txt file.
  4. The .txt file is converted to structured JSON via docstrange.
"""

import json
import os
import tempfile

import fitz            # PyMuPDF – text extraction & page rendering
import pytesseract     # Tesseract OCR wrapper
from PIL import Image  # Pillow – image handling for Tesseract

from modules import (
    Config,
    get_resume_files,
    display_files_menu,
    hash_and_check,
    store_hash,
    sha256_text,
    sha256_bytes,
    DocumentExtractor,
)


# ── Tesseract OCR configuration ─────────────────────────────────────
# If tesseract is not on your PATH, uncomment and set the path below:
# pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"


# ── Custom JSON schema for structured resume extraction ─────────────
RESUME_SCHEMA = {
    "name": "string (Required)",
    "email": "string (Optional)",
    "skills": [
        "string"
    ],
    "experience": [
        {
            "title": "string",
            "company": "string",
            "start": "string (ISO8601 or 'Month Year')",
            "end": "string",
            "description": "string (Optional)",
            "responsibilities": [
                "string"
            ]
        }
    ],
    "projects": [
        {
            "name": "string",
            "description": "string",
            "technologies": [
                "string"
            ]
        }
    ],
    "education": [
        {
            "degree": "string",
            "institution": "string",
            "year": "string or int"
        }
    ],
    "certifications": [
        "string"
    ],
    "tools": [
        "string"
    ],
    "technologies": [
        "string"
    ],
    "salary_expectation": {
        "value": "string or number",
        "currency": "string"
    }
}


# ── helpers ──────────────────────────────────────────────────────────

MAX_RENDER_DIM = 2500  # longest-edge cap when rendering pages to images


def extract_text_with_fitz(pdf_path):
    """
    Extract text from a PDF using PyMuPDF's built-in text engine.

    Returns (text, page_count).
    """
    doc = fitz.open(pdf_path)
    pages_text = []
    for page in doc:
        text = page.get_text()
        if text and text.strip():
            pages_text.append(text.strip())
    doc.close()
    return "\n\n".join(pages_text), len(doc) if not doc.is_closed else len(pages_text)


def extract_text_with_ocr(pdf_path):
    """
    Render every PDF page to an image and run Tesseract OCR.

    Handles oversized MediaBox pages by scaling to MAX_RENDER_DIM.
    Returns (text, page_count).
    """
    doc = fitz.open(pdf_path)
    pages_text = []

    for i, page in enumerate(doc, 1):
        # Scale oversized pages to a reasonable pixel size
        w, h = page.rect.width, page.rect.height
        scale = min(MAX_RENDER_DIM / max(w, 1), MAX_RENDER_DIM / max(h, 1), 300 / 72)
        pix = page.get_pixmap(matrix=fitz.Matrix(scale, scale))

        # Save temp image for Tesseract
        tmp_fd, tmp_path = tempfile.mkstemp(suffix=".png")
        os.close(tmp_fd)
        pix.save(tmp_path)

        try:
            img = Image.open(tmp_path)
            page_text = pytesseract.image_to_string(img)
            if page_text.strip():
                pages_text.append(page_text.strip())
                print(f"   📄 Page {i}: {len(page_text)} chars extracted via Tesseract OCR")
            else:
                print(f"   📄 Page {i}: (no text found)")
        except Exception as exc:
            print(f"   ⚠  OCR failed on page {i}: {exc}")
        finally:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass

    page_count = len(doc)
    doc.close()
    return "\n\n".join(pages_text), page_count


def process_single_resume(resume_path, output_dir, hashed_dir):
    """
    Full pipeline for one resume:
      1. Compute file-level SHA-256 for traceability.
      2. Extract raw text (fitz direct or fitz + Tesseract OCR).
      3. Hash raw extracted text → check cache for duplicate content.
         • Cache HIT  → load cached JSON, skip expensive docstrange step.
         • Cache MISS → proceed with conversion.
      4. Save .txt output.
      5. Convert .txt → structured JSON via docstrange.
      6. Store result in hash cache and save .json.
    """
    file_name = resume_path.name
    stem = resume_path.stem
    is_pdf = resume_path.suffix.lower() == ".pdf"

    # ── Step 1: File-level SHA-256 (binary fingerprint) ───────────
    file_bytes = resume_path.read_bytes()
    file_hash = sha256_bytes(file_bytes)
    print(f"   🔑 File hash: {file_hash[:16]}…")

    # ── Step 2: Extract raw text ──────────────────────────────────
    raw_text = ""
    page_count = 0

    if is_pdf:
        # Try fitz direct text extraction first
        raw_text, page_count = extract_text_with_fitz(str(resume_path))

        if raw_text and len(raw_text.strip()) >= 100:
            print(f"   ✅ Text-based PDF — extracted {len(raw_text)} chars ({page_count} pages)")
        else:
            print("   ⚠  PDF appears image-based — switching to Tesseract OCR…")
            raw_text, page_count = extract_text_with_ocr(str(resume_path))
            if raw_text and raw_text.strip():
                print(f"   ✅ Tesseract OCR extracted {len(raw_text)} chars ({page_count} pages)")
            else:
                print("   ❌ Tesseract OCR could not extract any text.")
    else:
        # Non-PDF: let docstrange handle it directly later
        raw_text = None

    # ── Step 3: Content hash + cache check ────────────────────────
    #   Hash the *raw extracted text* (never JSON/markdown/binary).
    #   If we've already processed identical text, reuse the result.
    content_digest = None
    if raw_text and raw_text.strip():
        content_digest, cache_hit, cached_json_str = hash_and_check(
            raw_text, file_name, hashed_dir
        )
        print(f"   🔐 Content hash: {content_digest[:16]}…")

        if cache_hit:
            print(f"   ♻  Cache HIT — skipping docstrange extraction.")
            # Load cached JSON and save output directly
            json_data = json.loads(cached_json_str)

            # Still save .txt for completeness
            txt_dir = output_dir / "txt"
            txt_dir.mkdir(parents=True, exist_ok=True)
            txt_path = txt_dir / f"{stem}.txt"
            with open(txt_path, "w", encoding="utf-8") as f:
                f.write(raw_text)
            print(f"   📝 Saved TXT → {txt_path}")

            # Save JSON output
            json_path = output_dir / f"{stem}.json"
            output_dir.mkdir(parents=True, exist_ok=True)
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(json_data, f, indent=4, ensure_ascii=False)
            print(f"   ✅ Saved JSON → {json_path}  (from cache)")
            return True

    # ── Step 4: Save .txt ────────────────────────────────────────
    txt_dir = output_dir / "txt"
    txt_dir.mkdir(parents=True, exist_ok=True)
    txt_path = txt_dir / f"{stem}.txt"

    if raw_text and raw_text.strip():
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write(raw_text)
        print(f"   📝 Saved TXT → {txt_path}")
    elif is_pdf:
        print(f"   ⚠  No text extracted — skipping TXT save.")
        # Still save an empty marker so we know we tried
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write("")

    # ── Step 5: Convert to JSON via docstrange ────────────────────
    json_data = None
    try:
        extractor = DocumentExtractor()
        if raw_text and raw_text.strip():
            # Feed the .txt file to docstrange for structured extraction
            result = extractor.extract(str(txt_path))
        else:
            # Non-PDF files: let docstrange handle the original file
            result = extractor.extract(str(resume_path))

        json_data = result.extract_data(json_schema=RESUME_SCHEMA)
        print("   ✅ Structured JSON extraction succeeded.")
    except Exception as exc:
        print(f"   ⚠  docstrange JSON conversion failed: {exc}")

    # Validate
    has_error = (
        not json_data
        or (isinstance(json_data, dict) and "error" in json_data.get("document", {}))
    )

    if has_error and raw_text and raw_text.strip():
        # Fallback: wrap the raw text as JSON
        json_data = {
            "document": {"raw_text": raw_text},
            "format": "raw_text_fallback",
        }
        print("   ⚠  Using raw text as JSON fallback.")

    if not json_data:
        json_data = {
            "document": {"error": "No extractable content found in document"},
            "format": "extraction_failed",
        }
        print(f"   ❌ All extraction methods failed for '{file_name}'.")

    # ── Step 6: Store in hash cache + save JSON ──────────────────
    json_str = json.dumps(json_data, ensure_ascii=False, indent=4)

    if content_digest:
        # Cache the JSON output keyed by the raw-text content hash
        store_hash(
            content_digest, json_str, file_name, hashed_dir,
            extracted_text=raw_text,
        )
        print(f"   🆕 Cached new result (hash: {content_digest[:16]}…)")
    else:
        # No raw text available (non-PDF, etc.) — hash the JSON itself
        fallback_digest = sha256_text(json_str)
        store_hash(
            fallback_digest, json_str, file_name, hashed_dir,
            extracted_text=json_str,
        )
        print(f"   🆕 Cached new result (hash: {fallback_digest[:16]}…)")

    json_path = output_dir / f"{stem}.json"
    output_dir.mkdir(parents=True, exist_ok=True)
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(json_data, f, indent=4, ensure_ascii=False)

    print(f"   ✅ Saved JSON → {json_path}")
    return True


def run_bulk_extraction():
    """Non-interactive bulk extraction for all resumes in INPUT_DIR."""
    Config.ensure_directories()
    resume_files = get_resume_files()
    if not resume_files:
        return {"status": "no_files", "count": 0}

    success = 0
    for path in resume_files:
        if process_single_resume(path, Config.OUTPUT_DIR, Config.HASHED_OUTPUT_DIR):
            success += 1
    return {"status": "completed", "count": len(resume_files), "success": success}


# ── main ─────────────────────────────────────────────────────────────


def main():
    Config.ensure_directories()

    resume_files = get_resume_files()
    if not resume_files:
        print("\n⚠  No supported resume files found in the input directory.")
        return

    selected = display_files_menu(resume_files)
    if selected is None:
        return

    print(f"\n{'=' * 60}")
    print(f"  Processing {len(selected)} resume(s)…")
    print(f"{'=' * 60}")

    success = 0
    for idx, path in enumerate(selected, 1):
        print(f"\n── [{idx}/{len(selected)}] {path.name} ──")
        if process_single_resume(path, Config.OUTPUT_DIR, Config.HASHED_OUTPUT_DIR):
            success += 1

    print(f"\n{'=' * 60}")
    print(f"  Done! {success}/{len(selected)} resume(s) processed successfully.")
    print(f"{'=' * 60}\n")


if __name__ == "__main__":
    import sys
    if "--bulk" in sys.argv:
        run_bulk_extraction()
    else:
        main()
