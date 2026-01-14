import os
import shutil
import json
from pathlib import Path
from typing import List, Optional

from fastapi import FastAPI, File, UploadFile, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

# Import existing logic
from main import run_full_pipeline, UPLOADS_DIR, RESULTS_DIR

# Import SaaS database layer
from app.saas_db import (
    get_default_context,
    create_job_description,
    create_batch,
    create_job,
    update_job_status,
    update_batch_status,
    get_all_jobs,
    get_job_with_result,
    get_batch_history,
    get_batch_history,
    test_connection as test_db_connection,
    get_all_tenants,
    get_all_business_units,
    get_all_job_descriptions,
    get_all_batches_raw,
    get_all_resume_results_summary,
    check_and_update_batch_status
)

app = FastAPI()

# Allow CORS for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ensure directories exist
os.makedirs(UPLOADS_DIR, exist_ok=True)
os.makedirs(RESULTS_DIR, exist_ok=True)

# Mount frontend static files
app.mount("/frontend", StaticFiles(directory="frontend"), name="frontend")
# We also need to serve app.js and index.css if they are in the root or referenced relatively
# Based on the file structure, app.js is in root.
# To serve root files, we can add a specific route or mount.
# Let's serve static assets
app.mount("/assets", StaticFiles(directory="assets"), name="assets")

@app.get("/")
async def read_root():
    return FileResponse("frontend/recruiter-platform.html")

@app.get("/app.js")
async def read_app_js():
    return FileResponse("app.js")

@app.get("/styles.css")
async def read_styles_css():
    return FileResponse("frontend/styles.css")

@app.get("/recruiter-results.html")
async def read_recruiter_results():
    return FileResponse("frontend/recruiter-results.html")

@app.get("/screening-results.html")
async def read_screening_results():
    return FileResponse("frontend/screening-results.html")

@app.get("/bulk-processing.html")
async def read_bulk_processing():
    return FileResponse("frontend/bulk-processing.html")

@app.get("/recruiter-platform.html")
async def read_recruiter_platform():
    return FileResponse("frontend/recruiter-platform.html")

@app.get("/settings.html")
async def read_settings():
    return FileResponse("frontend/settings.html")

@app.get("/history.html")
async def read_history():
    return FileResponse("frontend/history.html")

@app.get("/database-monitor.html")
async def read_database_monitor():
    return FileResponse("frontend/database-monitor.html")


@app.get("/api/batch-history")
async def get_batch_history_api():
    """Get batch processing history for the history page."""
    try:
        history = get_batch_history(limit=50)
        # Convert datetime objects to ISO strings for JSON serialization
        for batch in history:
            if batch.get("created_at"):
                batch["created_at"] = batch["created_at"].isoformat()
        return history
    except Exception as e:
        print(f"Error fetching batch history: {e}")
        return []

@app.get("/api/database-monitor")
async def get_database_monitor_data():
    """Get all database tables for the monitor UI."""
    try:
        # Fetch data with datetime serialization handling
        data = {
            "tenants": get_all_tenants(),
            "business_units": get_all_business_units(),
            "job_descriptions": get_all_job_descriptions(),
            "batches": get_all_batches_raw(),
            "jobs": get_all_jobs(limit=200),
            "resume_results": get_all_resume_results_summary(limit=100)
        }
        
        # Helper to serialize datetimes
        def serialize_dates(obj_list):
            for item in obj_list:
                for k, v in item.items():
                    if hasattr(v, 'isoformat'):
                        item[k] = v.isoformat()
            return obj_list

        for key in data:
            if isinstance(data[key], list):
                serialize_dates(data[key])
                
        return data
    except Exception as e:
        print(f"Error fetching DB monitor data: {e}")
        return {"error": str(e)}

# Settings Management
SETTINGS_FILE = Path("settings.json")

def load_settings():
    if SETTINGS_FILE.exists():
        try:
            return json.loads(SETTINGS_FILE.read_text())
        except:
            pass
    return {
        "fullName": "Recruiter Admin",
        "email": "admin@raiyasolutions.com",
        "emailNotifications": True,
        "darkMode": False,
        "apiKey": "",
        "retentionPeriod": "1 Year"
    }

def save_settings(settings):
    SETTINGS_FILE.write_text(json.dumps(settings, indent=2))

@app.get("/api/settings")
async def get_settings():
    return load_settings()

@app.post("/api/settings")
async def update_settings(settings: dict):
    current = load_settings()
    current.update(settings)
    save_settings(current)
    return {"status": "success", "settings": current}


@app.post("/api/upload")
async def upload_files(files: List[UploadFile] = File(...), type: str = "resume"):
    """
    Upload files to the uploads directory.
    type: 'resume' or 'jd'
    """
    uploaded_files = []
    
    for file in files:
        if not file.filename:
            continue
            
        # Determine destination
        # For simplicity, we just dump everything in UPLOADS_DIR as per existing main.py logic
        # But main.py looks for *.pdf for resumes and job_description.json for JD.
        
        file_location = UPLOADS_DIR / file.filename
        
        # If it's a JD, we might want to standardize the name as main.py expects job_description.json
        # The frontend sends JDs. If the user sends a JD, we should probably save it as job_description.json
        # or handle multiple JDs.
        # The existing main.py `load_default_jd` looks for `job_description.json`.
        
        if type == 'jd':
            # For now, if multiple JDs are uploaded, this logic might overwrite or we need to change main.py
            # Let's save it with original name for now, but also checks if we need to set it as default.
            # If the frontend sends one JD, we can save it as job_description.json.
            if file.filename.endswith('.json'):
                 file_location = UPLOADS_DIR / "job_description.json"
        
        with open(file_location, "wb+") as file_object:
            shutil.copyfileobj(file.file, file_object)
            
        uploaded_files.append({"filename": file.filename, "path": str(file_location)})
        
    return {"message": f"Successfully uploaded {len(uploaded_files)} files", "files": uploaded_files}

# In-memory job store (kept for interim status updates during processing)
# Final status is persisted to database
JOBS = {}

# Current batch ID for tracking
CURRENT_BATCH_ID = None

def process_single_resume(job_id: str, resume_path: Path, jd_data: dict, db_job_id: int = None, batch_id: int = None):
    """
    Background worker to process a single resume.
    
    Args:
        job_id: In-memory job ID for real-time status updates
        resume_path: Path to the resume PDF
        jd_data: Job description dict
        db_job_id: Database job ID for persistence
        batch_id: Batch ID for checking overall batch completion
    """
    try:
        JOBS[job_id]["status"] = "In Progress"
        
        # Update database status
        if db_job_id:
            update_job_status(db_job_id, "running")
        
        # Check if result already exists to skip re-processing
        filename_stem = resume_path.stem
        existing_result_path = RESULTS_DIR / f"{filename_stem}__explanation.json"

        if existing_result_path.exists():
            JOBS[job_id]["step"] = "Result Exists - Skipping"
            JOBS[job_id]["progress"] = 90
            try:
                data = json.loads(existing_result_path.read_text(encoding='utf-8'))
                
                JOBS[job_id]["progress"] = 100
                JOBS[job_id]["status"] = "Completed"
                JOBS[job_id]["step"] = "Loaded from History"
                
                # Extract score for dashboard
                # data is explanation.json content which has final_score at root or inside structured_explanation
                final_score = data.get("final_score")
                if final_score is None:
                    final_score = data.get("structured_explanation", {}).get("scores", {}).get("final_score")
                
                JOBS[job_id]["score"] = final_score
                
                # Update database status
                if db_job_id:
                    update_job_status(db_job_id, "completed")
                    if batch_id:
                        check_and_update_batch_status(batch_id)
                
                # We don't need full result in JOB for list view, just status and score
                return
            except Exception as e:
                print(f"Error reading existing result for {filename_stem}, reprocessing: {e}")
        
        JOBS[job_id]["progress"] = 10
        JOBS[job_id]["step"] = "Analyzing Text"
        JOBS[job_id]["progress"] = 20
        
        # Pass db_job_id to pipeline for database persistence
        pipeline_result = run_full_pipeline(str(resume_path), jd_data, job_id=db_job_id)
        
        JOBS[job_id]["progress"] = 100
        JOBS[job_id]["status"] = "Completed"
        JOBS[job_id]["step"] = "Finished"
        
        # Save results
        summary = {
            "local_score": pipeline_result.get("local_score", {}).get("final_score"),
            "ai_score": pipeline_result.get("ai_score", {}).get("ai_score", {}).get("final_score"),
            "recruiter_summary": pipeline_result.get("explanation", {}).get("recruiter_text_summary", "")
        }
        JOBS[job_id]["result"] = summary
        JOBS[job_id]["score"] = summary["ai_score"]
        JOBS[job_id]["db_job_id"] = db_job_id
        
        # Check batch status
        if batch_id:
            check_and_update_batch_status(batch_id)

    except Exception as e:
        print(f"Error processing job {job_id}: {e}")
        JOBS[job_id]["status"] = "Failed"
        JOBS[job_id]["error"] = str(e)
        JOBS[job_id]["progress"] = 0
        
        # Update database status
        if db_job_id:
            update_job_status(db_job_id, "failed")
            if batch_id:
                check_and_update_batch_status(batch_id)

@app.post("/api/process")
async def process_resumes(background_tasks: BackgroundTasks):
    """
    Trigger the processing of all resumes in the uploads folder against the default JD.
    Creates database records for batch and jobs for persistence.
    """
    global CURRENT_BATCH_ID
    import uuid
    
    # Check for JD
    jd_path = UPLOADS_DIR / "job_description.json"
    if not jd_path.exists():
         # Fallback: try to find any json file
         jsons = list(UPLOADS_DIR.glob("*.json"))
         if jsons:
             jd_path = jsons[0]
         else:
            raise HTTPException(status_code=400, detail="No Job Description found.")

    try:
        with open(jd_path, "r", encoding="utf-8") as f:
            jd_data = json.load(f)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid JD JSON: {str(e)}")

    # Find resumes
    pdfs = list(UPLOADS_DIR.glob("*.pdf"))
    if not pdfs:
        raise HTTPException(status_code=400, detail="No PDF resumes found in uploads directory.")

    tasks_started = []
    
    # Clear previous in-memory jobs
    JOBS.clear()
    
    # DATABASE INTEGRATION: Create batch and jobs in database
    try:
        # Get default tenant/BU context
        ctx = get_default_context()
        bu_id = ctx["bu_id"]
        
        # Create JD record in database
        jd_title = jd_data.get("title", jd_path.stem)
        db_jd_id = create_job_description(bu_id, jd_title, jd_data)
        
        # Create batch
        batch_guid = str(uuid.uuid4())
        batch_id = create_batch(bu_id, uploader_user_id=None, batch_guid=batch_guid)
        CURRENT_BATCH_ID = batch_id
        update_batch_status(batch_id, "processing")
        
        print(f"📦 Created batch {batch_id} with JD {db_jd_id}")
        
    except Exception as e:
        print(f"⚠️ Database setup failed, continuing without persistence: {e}")
        db_jd_id = None
        batch_id = None

    for resume_path in pdfs:
        # Create database job if DB is available
        db_job_id = None
        if batch_id and db_jd_id:
            try:
                db_job_id = create_job(batch_id, db_jd_id, requester_user_id=None)
            except Exception as e:
                print(f"⚠️ Failed to create DB job for {resume_path.name}: {e}")
        
        # Create in-memory job for real-time status
        job_id = f"JOB-{str(uuid.uuid4())[:8]}"
        JOBS[job_id] = {
            "id": job_id,
            "db_job_id": db_job_id,
            "filename": resume_path.name,
            "status": "Queued",
            "progress": 0,
            "step": "Waiting",
            "score": None,
            "result": None
        }
        
        # Pass both in-memory and database job IDs
        background_tasks.add_task(process_single_resume, job_id, resume_path, jd_data, db_job_id, batch_id)
        tasks_started.append(job_id)

    return {
        "status": "started", 
        "jobs": tasks_started, 
        "batch_id": batch_id,
        "message": f"Started processing {len(tasks_started)} resumes."
    }

@app.get("/api/jobs")
async def get_jobs():
    """
    Return the current status of all jobs.
    """
    return list(JOBS.values())

@app.get("/api/results")
async def get_results():
    # Helper to list generated results from RESULTS_DIR
    results = []
    for f in RESULTS_DIR.glob("*__explanation.json"):
        try:
            data = json.loads(f.read_text(encoding='utf-8'))
            filename_stem = f.name.replace("__explanation.json", "")
            data["candidate_name"] = filename_stem
            
            # Inject local score for list view
            local_file = RESULTS_DIR / f"{filename_stem}__local_score.json"
            if local_file.exists():
                try:
                    local_data = json.loads(local_file.read_text(encoding='utf-8'))
                    data["local_score"] = local_data.get("final_score", 0)
                except:
                    data["local_score"] = 0
            else:
                 data["local_score"] = 0
            
            results.append(data)
        except:
            pass
    return results

@app.get("/api/results/{filename}")
async def get_result_by_filename(filename: str):
    """
    Fetch a specific result by filename. 
    filename should be the stem (e.g. 'Resume_John')
    Returns combined AI and Local data if available.
    """
    # Try to find the file
    # The file is stored as {filename}__explanation.json
    target_file = RESULTS_DIR / f"{filename}__explanation.json"
    local_file = RESULTS_DIR / f"{filename}__local_score.json"
    
    if not target_file.exists():
        raise HTTPException(status_code=404, detail="Result not found")
        
    try:
        data = json.loads(target_file.read_text(encoding='utf-8'))
        data["candidate_name"] = filename
        
        # Try to load local data
        if local_file.exists():
            try:
                local_data = json.loads(local_file.read_text(encoding='utf-8'))
                data["local_data"] = local_data
            except Exception as e:
                print(f"Error reading local data for {filename}: {e}")
                data["local_data"] = None
        else:
             data["local_data"] = None

        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading result: {str(e)}")




if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)
