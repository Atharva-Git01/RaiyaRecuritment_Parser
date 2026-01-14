# ======================================================
# main.py — FULL ORCHESTRATOR (Single Resume Pipeline)
# ======================================================

import json
import os
import sys
from datetime import datetime
from pathlib import Path

from app.ai_scorer import ai_score_resume
from app.explanation_engine import generate_full_report

# -------------------------
# Import pipeline modules (from app/)
# -------------------------
from app.extractor import extract_resume_text
from app.matcher import score_resume_against_jd
from app.normalizer import normalize_resume_text
from app.normalizer_pre_score import normalize_for_scoring
from app.parser import parse_resume
from app.pdf_report import generate_pdf_report
from app.validator import validate_resume_data

# ================
# PROJECT ROOT PATH
# ================
ROOT_DIR = Path(__file__).resolve().parent

UPLOADS_DIR = ROOT_DIR / "uploads"
BASE_DIR = ROOT_DIR / "storage"
RESULTS_DIR = BASE_DIR / "results"
ERROR_DIR = BASE_DIR / "errors"
REPORTS_DIR = BASE_DIR / "reports"
TMP_DIR = BASE_DIR / "tmp"


# Ensure consoles can print Unicode safely on Windows terminals
def _configure_console_encoding():
    try:
        for stream in (sys.stdout, sys.stderr):
            if hasattr(stream, "reconfigure"):
                stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


_configure_console_encoding()

# Ensure directories exist
for d in [RESULTS_DIR, ERROR_DIR, REPORTS_DIR, TMP_DIR]:
    d.mkdir(parents=True, exist_ok=True)


# ======================
# LOAD DEFAULT JD
# ======================
def load_default_jd():
    jd_path = UPLOADS_DIR / "job_description.json"
    if jd_path.exists():
        with open(jd_path, "r", encoding="utf-8") as f:
            return json.load(f)
    else:
        print("⚠️ No JD file found at uploads/job_description.json")
        return None


# ======================
# ORCHESTRATOR FUNCTION
# ======================
def run_full_pipeline(resume_path: str, jd: dict = None):
    """
    Full end-to-end orchestrator:
    Extract → Normalize → Parse (Azure) → Validate → Score → Explain → PDF
    """
    resume_path = Path(resume_path)

    if not resume_path.exists():
        raise FileNotFoundError(f"❌ Resume not found: {resume_path}")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    resume_name = resume_path.stem

    print("\n========================================")
    print("     🚀 RUNNING FULL PIPELINE")
    print("========================================\n")

    if jd is None:
        jd = load_default_jd()
        if jd is None:
            raise ValueError("No JD provided and default JD not found.")

    # ---------------------------------
    # 1. EXTRACTION
    # ---------------------------------
    print("1️⃣  Extracting text...")
    extracted_text = extract_resume_text(str(resume_path))
    pdf_type = "unknown"  # OR remove pdf_type entirely
    extracted_path = TMP_DIR / f"{resume_name}__extracted.txt"
    extracted_path.write_text(extracted_text, encoding="utf-8")

    # ---------------------------------
    # 2. NORMALIZATION
    # ---------------------------------
    print("2️⃣  Normalizing text...")
    normalized_text = normalize_resume_text(extracted_text, TMP_DIR)
    normalized_path = TMP_DIR / f"{resume_name}__normalized.md"
    normalized_path.write_text(normalized_text, encoding="utf-8")

    # ---------------------------------
    # 3. PARSING (Azure LLM → JSON)
    # ---------------------------------
    print("3️⃣  Parsing with Azure Phi-4...")
    parsed_json = parse_resume(normalized_text)

    parsed_path = TMP_DIR / f"{resume_name}__parsed.json"
    parsed_path.write_text(json.dumps(parsed_json, indent=2), encoding="utf-8")

    # ---------------------------------
    # 4. VALIDATION
    # ---------------------------------
    print("4️⃣  Validating parsed output...")
    # validator only accepts 1 argument
    validated_json = validate_resume_data(parsed_json)

    validated_path = TMP_DIR / f"{resume_name}__validated.json"
    validated_path.write_text(json.dumps(validated_json, indent=2), encoding="utf-8")

    # ---------------------------------
    # 5. SCORING NORMALIZATION
    # ---------------------------------
    print("5️⃣  Preparing data for scoring...")
    scoring_ready = normalize_for_scoring(validated_json)

    scoring_path = TMP_DIR / f"{resume_name}__scoring_ready.json"
    scoring_path.write_text(json.dumps(scoring_ready, indent=2), encoding="utf-8")

    # ---------------------------------
    # 6. MATCHER SCORE
    # ---------------------------------
    print("6️⃣  Running local matcher...")
    local_score = score_resume_against_jd(scoring_ready, jd)

    score_path = RESULTS_DIR / f"{resume_name}__local_score.json"
    score_path.write_text(json.dumps(local_score, indent=2), encoding="utf-8")

    # ---------------------------------
    # 7. AI SCORE (Phi-4)
    # ---------------------------------
    print("7️⃣  Running AI Scorer...")
    ai_score = ai_score_resume(
        scoring_ready, jd, timeout=30, fallback_local_scores=local_score
    )

    ai_path = RESULTS_DIR / f"{resume_name}__ai_score.json"
    ai_path.write_text(json.dumps(ai_score, indent=2), encoding="utf-8")

    # ---------------------------------
    # 8. EXPLANATION ENGINE
    # ---------------------------------
    print("8️⃣  Generating explanation...")
    matcher_output_combined = (
        local_score  # local_score already contains all matcher_out fields
    )

    explanation = generate_full_report(matcher_output_combined)

    explanation_path = RESULTS_DIR / f"{resume_name}__explanation.json"
    explanation_path.write_text(json.dumps(explanation, indent=2), encoding="utf-8")

    # ---------------------------------
    # 9. PDF REPORT
    # ---------------------------------
    print("9️⃣  Creating PDF report...")
    pdf_path = REPORTS_DIR / f"{resume_name}__report_{timestamp}.pdf"
    generate_pdf_report(explanation, str(pdf_path))

    # ---------------------------------
    # SUMMARY
    # ---------------------------------
    print("\n========================================")
    print("        🎉 PIPELINE COMPLETED")
    print("========================================")
    print(f"📄 Extracted:         {extracted_path}")
    print(f"📝 Normalized:        {normalized_path}")
    print(f"🤖 Parsed JSON:       {parsed_path}")
    print(f"✔️ Validated JSON:    {validated_path}")
    print(f"📊 Local Score:       {score_path}")
    print(f"🧠 AI Score:          {ai_path}")
    print(f"💬 Explanation:       {explanation_path}")
    print(f"📘 PDF Report:        {pdf_path}")
    print("========================================\n")

    return {
        "parsed": parsed_json,
        "validated": validated_json,
        "local_score": local_score,
        "ai_score": ai_score,
        "explanation": explanation,
        "pdf_report": str(pdf_path),
        # Paths for DB
        "parsed_path": str(parsed_path),
        "score_path": str(ai_path), # Prefer AI score path, or local if AI failed
        "local_score_path": str(score_path),
        "explanation_path": str(explanation_path)
    }


def pick_resume_file():
    pdfs = list(UPLOADS_DIR.glob("*.pdf"))
    if not pdfs:
        raise FileNotFoundError("❌ No resumes found in /uploads")

    if len(pdfs) == 1:
        print(f"📄 Using resume: {pdfs[0].name}")
        return pdfs[0]

    print("\nMultiple resumes found:")
    for i, p in enumerate(pdfs, start=1):
        print(f"{i}. {p.name}")

    choice = int(input("\nSelect resume number: "))
    return pdfs[choice - 1]


# ======================
# BULK RUN — PROCESS ALL RESUMES
# ======================
if __name__ == "__main__":
    print("\n🔍 Scanning /uploads for resumes...\n")

    # Load JD
    jd_data = load_default_jd()
    if jd_data is None:
        raise ValueError("❌ job_description.json missing in /uploads")

    # Get all PDF resumes
    pdfs = list(UPLOADS_DIR.glob("*.pdf"))

    if not pdfs:
        print("❌ No PDF resumes found in /uploads")
        exit()

    print(f"📄 Found {len(pdfs)} resumes\n")

    first_preview = None

    # Loop over each resume
    for resume_path in pdfs:
        print("\n========================================")
        print(f"Processing: {resume_path.name}")
        print("========================================\n")

        try:
            result = run_full_pipeline(resume_path, jd_data)
            if first_preview is None and isinstance(result, dict):
                local_score = (result.get("local_score") or {}).get("final_score")
                ai_payload = result.get("ai_score") or {}
                if ai_payload.get("ai_ok"):
                    ai_score_value = (ai_payload.get("ai_score") or {}).get(
                        "final_score"
                    )
                else:
                    ai_score_value = None
                recruiter_summary = (result.get("explanation") or {}).get(
                    "recruiter_text_summary", ""
                )
                first_preview = {
                    "resume": resume_path.name,
                    "local_score": local_score,
                    "ai_score": ai_score_value,
                    "recruiter_summary": recruiter_summary,
                }
        except Exception as e:
            print(f"❌ Error processing {resume_path.name}: {e}")
            continue

    if first_preview:
        print("\n----------------------------------------")
        print("👀 Preview of first processed resume")
        print("----------------------------------------")
        print(f"📄 Resume:        {first_preview['resume']}")
        print(f"📊 Local Score:   {first_preview.get('local_score')}")
        if first_preview.get("ai_score") is not None:
            print(f"🧠 AI Score:      {first_preview.get('ai_score')}")
        else:
            print("🧠 AI Score:      (AI scorer unavailable)")
        if first_preview.get("recruiter_summary"):
            print(f"📝 Summary:       {first_preview['recruiter_summary']}")
        print("----------------------------------------\n")

    print("\n🎉 All resumes processed.\n")
