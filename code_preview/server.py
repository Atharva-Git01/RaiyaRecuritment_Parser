import os
import shutil
import uuid
from typing import List

from fastapi import FastAPI, File, UploadFile, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.db_manager import get_db_connection

app = FastAPI(title="Raiya Resume Parser API")

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Directories
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

class JobResponse(BaseModel):
    job_id: int
    status: str
    message: str

@app.post("/api/upload", response_model=JobResponse)
async def upload_files(
    background_tasks: BackgroundTasks,
    jd_files: List[UploadFile] = File(...),
    resume_files: List[UploadFile] = File(...)
):
    """
    Upload JDs and Resumes. For simplicity in this version, we'll assume 
    one JD (or the first one) is used for all resumes in this batch.
    In a real scenario, you might map specific resumes to specific JDs.
    """
    if not jd_files or not resume_files:
        raise HTTPException(status_code=400, detail="Both JD and Resume files are required.")

    # Save JD (taking the first one for now as the 'active' JD for this batch)
    # In a more complex app, we'd store JDs in a table and link them.
    jd_file = jd_files[0]
    jd_filename = f"jd_{uuid.uuid4()}_{jd_file.filename}"
    jd_path = os.path.join(UPLOAD_DIR, jd_filename)
    
    with open(jd_path, "wb") as buffer:
        shutil.copyfileobj(jd_file.file, buffer)
        
    # Save Resumes and create Jobs
    connection = get_db_connection()
    if not connection:
        raise HTTPException(status_code=500, detail="Database connection failed")
    
    cursor = connection.cursor()
    
    created_jobs = []
    
    try:
        for resume in resume_files:
            resume_filename = f"resume_{uuid.uuid4()}_{resume.filename}"
            resume_path = os.path.join(UPLOAD_DIR, resume_filename)
            
            with open(resume_path, "wb") as buffer:
                shutil.copyfileobj(resume.file, buffer)
            
            # Insert into DB
            sql = """
                INSERT INTO jobs (resume_filename, status, progress, created_at)
                VALUES (%s, 'queued', 0, NOW())
            """
            cursor.execute(sql, (resume_filename,))
            job_id = cursor.lastrowid
            created_jobs.append(job_id)
            
            # Store JD path association if needed, or just rely on a convention/default for now.
            # For this implementation, we'll save the JD path in a separate table or 
            # just pass it to the worker if we were triggering directly.
            # Since the worker pulls from 'jobs', we might need a column for 'jd_filename' in 'jobs' 
            # or a separate 'batches' table.
            # Let's add 'jd_filename' to the jobs table via a migration or update the schema in db_manager.
            # For now, we will assume the worker picks up the *latest* JD or we update the job row.
            
            # Let's update the job with metadata if possible, or just use a side-channel.
            # To keep it simple and robust: We will add a 'jd_filename' column to the jobs table 
            # in a separate step (db_manager update). 
            # For now, we'll assume the worker can find the JD. 
            # actually, let's just write a metadata file for the job.
            
            # Better approach: Update db_manager.py to include jd_filename in jobs table.
            # I will do that in the next step.
            
    except Exception as e:
        connection.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create jobs: {str(e)}")
    finally:
        connection.commit()
        cursor.close()
        connection.close()

    return JSONResponse(content={
        "message": f"Successfully queued {len(created_jobs)} resumes.",
        "job_ids": created_jobs,
        "jd_saved": jd_filename
    })

@app.get("/api/jobs/{job_id}")
async def get_job_status(job_id: int):
    connection = get_db_connection()
    if not connection:
        raise HTTPException(status_code=500, detail="Database connection failed")
    
    cursor = connection.cursor(dictionary=True)
    cursor.execute("SELECT * FROM jobs WHERE job_id = %s", (job_id,))
    job = cursor.fetchone()
    cursor.close()
    connection.close()
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
        
    return job

@app.get("/api/results")
async def get_all_results():
    connection = get_db_connection()
    if not connection:
        raise HTTPException(status_code=500, detail="Database connection failed")
    
    cursor = connection.cursor(dictionary=True)
    # Join jobs and results to get full details
    sql = """
        SELECT j.job_id, j.resume_filename, j.status, j.progress, 
               r.score_json_path, r.parsed_json_path
        FROM jobs j
        LEFT JOIN results r ON j.job_id = r.job_id
        ORDER BY j.created_at DESC
    """
    cursor.execute(sql)
    rows = cursor.fetchall()
    cursor.close()
    connection.close()
    
    # Enrich with actual JSON data if needed, or just return paths/metadata
    # For the dashboard, we might want some high-level scores.
    # We can read the score_json_path if it exists.
    
    results = []
    for row in rows:
        score_data = None
        if row.get("score_json_path") and os.path.exists(row["score_json_path"]):
            try:
                import json
                with open(row["score_json_path"], "r", encoding="utf-8") as f:
                    score_data = json.load(f)
            except:
                pass
        
        row["score_data"] = score_data
        results.append(row)
        
    return results

@app.get("/api/stats")
async def get_dashboard_stats():
    connection = get_db_connection()
    if not connection:
        raise HTTPException(status_code=500, detail="Database connection failed")
    
    cursor = connection.cursor(dictionary=True)
    
    # Total candidates
    cursor.execute("SELECT COUNT(*) as count FROM jobs")
    total = cursor.fetchone()["count"]
    
    # Completed
    cursor.execute("SELECT COUNT(*) as count FROM jobs WHERE status='completed'")
    completed = cursor.fetchone()["count"]
    
    # In Progress
    cursor.execute("SELECT COUNT(*) as count FROM jobs WHERE status='in_progress'")
    in_progress = cursor.fetchone()["count"]
    
    cursor.close()
    connection.close()
    
    return {
        "total_candidates": total,
        "completed": completed,
        "in_progress": in_progress,
        "this_month": total # Placeholder logic
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
