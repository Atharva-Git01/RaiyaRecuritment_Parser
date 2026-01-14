import os
import sys
import json
import shutil
from pathlib import Path
from datetime import datetime

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(PROJECT_ROOT))

# Import pipeline components
from main import run_full_pipeline, load_default_jd, TMP_DIR, RESULTS_DIR, REPORTS_DIR
try:
    from app.saas_db import create_batch, create_job, save_resume_result, get_or_create_tenant, get_or_create_business_unit, create_job_description, check_and_update_batch_status
    DB_AVAILABLE = True
except Exception as e:
    print(f"⚠️ Database module import failed or DB not connected: {e}")
    DB_AVAILABLE = False

# Configuration
SNAPSHOT_ROOT = PROJECT_ROOT / "baseline_snapshots"
SINGLE_RUN_DIR = SNAPSHOT_ROOT / "single_run"
BATCH_RUN_DIR = SNAPSHOT_ROOT / "batch_run"
UPLOADS_DIR = PROJECT_ROOT / "uploads"

# Detailed Resumes
SINGLE_RESUME = "ResumePriyankaAgarwal.pdf"
BATCH_RESUMES = [
    "152090014 Harshita Sanjay Sathe.pdf",
    "152090023 Sagar Shrinivas Somani.pdf"
]

def setup_dirs():
    if SNAPSHOT_ROOT.exists():
        shutil.rmtree(SNAPSHOT_ROOT)
    SINGLE_RUN_DIR.mkdir(parents=True, exist_ok=True)
    BATCH_RUN_DIR.mkdir(parents=True, exist_ok=True)
    print(f"📁 Created snapshot directory: {SNAPSHOT_ROOT}")

def copy_artifacts(resume_name, dest_dir):
    """Copy all related artifacts for a given resume to the destination directory."""
    print(f"   📋 Copying artifacts for {resume_name}...")
    
    # Files to look for (stem based)
    stem = Path(resume_name).stem
    
    # 1. TMP Files
    for f in TMP_DIR.glob(f"{stem}__*"):
        shutil.copy2(f, dest_dir / f.name)
        
    # 2. Results Files
    for f in RESULTS_DIR.glob(f"{stem}__*"):
        shutil.copy2(f, dest_dir / f.name)
        
    # 3. Reports (PDFs) - may have timestamps
    for f in REPORTS_DIR.glob(f"{stem}__*"):
        shutil.copy2(f, dest_dir / f.name)

def run_single_snapshot():
    print("\n📸 STARTING SINGLE RESUME SNAPSHOT")
    resume_path = UPLOADS_DIR / SINGLE_RESUME
    if not resume_path.exists():
        print(f"❌ Resume not found: {resume_path}")
        return

    # DB Setup (if available)
    job_id = None
    if DB_AVAILABLE:
        try:
            tenant_id = get_or_create_tenant("Snapshot_Tenant")
            bu_id = get_or_create_business_unit(tenant_id, "Snapshot_BU")
            
            # Using default JD
            jd_data = load_default_jd()
            jd_id = create_job_description(bu_id, "Default JD", jd_data)
            
            batch_id = create_batch(bu_id, batch_guid="snapshot_single_" + datetime.now().strftime("%Y%m%d%H%M%S"))
            job_id = create_job(batch_id, jd_id, resume_filename=SINGLE_RESUME)
            print(f"   🗄️  Created DB Job ID: {job_id}")
        except Exception as e:
            print(f"   ⚠️ DB Setup failed: {e}")

    # Run Pipeline
    try:
        result = run_full_pipeline(str(resume_path), job_id=job_id)
        
        # Save return value
        with open(SINGLE_RUN_DIR / "pipeline_return.json", "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, default=str)
            
        copy_artifacts(SINGLE_RESUME, SINGLE_RUN_DIR)
        print("✅ Single run snapshot complete.")
        
    except Exception as e:
        print(f"❌ Single run failed: {e}")

def run_batch_snapshot():
    print("\n📸 STARTING BATCH RESUME SNAPSHOT")
    
    batch_id = None
    if DB_AVAILABLE:
        try:
            tenant_id = get_or_create_tenant("Snapshot_Tenant")
            bu_id = get_or_create_business_unit(tenant_id, "Snapshot_BU")
            batch_id = create_batch(bu_id, batch_guid="snapshot_batch_" + datetime.now().strftime("%Y%m%d%H%M%S"))
            print(f"   🗄️  Created DB Batch ID: {batch_id}")
        except Exception as e:
            print(f"   ⚠️ DB Setup failed: {e}")

    jd_data = load_default_jd()
    # If DB used, we need a jd_id, but run_full_pipeline doesn't need jd_id arg, only job_id.
    # However, to create a job we need jd_id.
    jd_id = 1 # Fallback dummy
    if DB_AVAILABLE:
        try:
           jd_id = create_job_description(bu_id, "Default JD Batch", jd_data)
        except:
           pass

    for resume_file in BATCH_RESUMES:
        resume_path = UPLOADS_DIR / resume_file
        if not resume_path.exists():
            print(f"⚠️ Skipping missing file: {resume_file}")
            continue
            
        print(f"   ▶️  Processing {resume_file}...")
        
        job_id = None
        if DB_AVAILABLE and batch_id:
            try:
                job_id = create_job(batch_id, jd_id, resume_filename=resume_file)
            except Exception as e:
                 print(f"   ⚠️ DB Job creation failed: {e}")
                 
        # Create subfolder for this resume in batch snapshot
        resume_snapshot_dir = BATCH_RUN_DIR / Path(resume_file).stem
        resume_snapshot_dir.mkdir(parents=True, exist_ok=True)
        
        try:
            result = run_full_pipeline(str(resume_path), jd=jd_data, job_id=job_id)
            
            with open(resume_snapshot_dir / "pipeline_return.json", "w", encoding="utf-8") as f:
                json.dump(result, f, indent=2, default=str)
                
            copy_artifacts(resume_file, resume_snapshot_dir)
            
        except Exception as e:
            print(f"   ❌ Failed to process {resume_file}: {e}")

    if DB_AVAILABLE and batch_id:
        check_and_update_batch_status(batch_id)
        print(f"   updated batch status for {batch_id}")

    print("✅ Batch run snapshot complete.")

if __name__ == "__main__":
    setup_dirs()
    run_single_snapshot()
    run_batch_snapshot()
    print("\n🎉 ALL SNAPSHOTS COMPLETED.")
