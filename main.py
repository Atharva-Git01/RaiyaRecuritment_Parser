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
def run_full_pipeline(resume_path: str, jd: dict = None, job_id: int = None):
    """
    Full end-to-end orchestrator:
    Extract → Normalize → Parse (Azure) → Validate → Score → Explain → PDF
    
    Args:
        resume_path: Path to the resume PDF
        jd: Job description dict (optional, loads default if not provided)
        job_id: Database job ID for persistence (optional)
    """
    resume_path = Path(resume_path)

    if not resume_path.exists():
        raise FileNotFoundError(f"❌ Resume not found: {resume_path}")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    resume_name = resume_path.stem

    print("\n========================================")
    print("     🚀 RUNNING FULL PIPELINE (STAGED)")
    print("========================================\n")

    if jd is None:
        jd = load_default_jd()
        if jd is None:
            raise ValueError("No JD provided and default JD not found.")

    # Define Output Directories
    output_dirs = {
        "tmp": TMP_DIR,
        "results": RESULTS_DIR,
        "reports": REPORTS_DIR
    }

    # Initialize Pipeline
    from app.pipeline.stages import ResumePipeline
    pipeline = ResumePipeline()
    
    # Execute Pipeline
    try:
        results = pipeline.run(
            resume_path=resume_path,
            jd=jd,
            output_dirs=output_dirs,
            job_id=job_id
        )
    except Exception as e:
        print(f"❌ Pipeline Execution Failed: {e}")
        # Re-raise to ensure calling scripts know it failed
        raise e

    # Extract results for backward compatibility return
    parsed_json = results["parsed"]
    validated_json = results["validated"]
    local_score = results["local_score"]
    ai_score = results["ai_score"]
    explanation = results["explanation"]
    pdf_path = results["pdf_report"]

    extracted_path = TMP_DIR / f"{resume_path.stem}__extracted.txt"
    normalized_path = TMP_DIR / f"{resume_path.stem}__normalized.md"
    parsed_path = TMP_DIR / f"{resume_path.stem}__parsed.json"
    validated_path = TMP_DIR / f"{resume_path.stem}__validated.json"
    score_path = RESULTS_DIR / f"{resume_path.stem}__local_score.json"
    ai_path = RESULTS_DIR / f"{resume_path.stem}__ai_score.json"
    explanation_path = RESULTS_DIR / f"{resume_path.stem}__explanation.json"

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

    # ---------------------------------
    # 10. DATABASE PERSISTENCE (Optional)
    # ---------------------------------
    if job_id:
        print("🔟  Saving to database...")
        try:
            from app.saas_db import save_resume_result, update_job_status
            save_resume_result(
                job_id=job_id,
                parsed_json=validated_json,
                scores_json={
                    "local_score": local_score,
                    "ai_score": ai_score,
                    "final_score": explanation.get("final_score") or local_score.get("final_score", 0)
                },
                report_url=str(pdf_path)
            )
            update_job_status(job_id, "completed")
            print(f"💾 Database:          Job {job_id} saved")
        except Exception as e:
            print(f"⚠️ Database save failed: {e}")

    return {
        "parsed": parsed_json,
        "validated": validated_json,
        "local_score": local_score,
        "ai_score": ai_score,
        "explanation": explanation,
        "pdf_report": str(pdf_path),
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
