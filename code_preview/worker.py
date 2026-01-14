import json
import os
import time
import traceback
from pathlib import Path

from app.db_manager import get_db_connection
from main import run_full_pipeline

UPLOAD_DIR = Path("uploads")

def get_next_queued_job():
    """Fetch the next job that is in 'queued' status."""
    connection = get_db_connection()
    if not connection:
        print("❌ Failed to connect to database.")
        return None

    cursor = connection.cursor(dictionary=True)
    cursor.execute(
        "SELECT * FROM jobs WHERE status = 'queued' ORDER BY created_at ASC LIMIT 1;"
    )
    job = cursor.fetchone()

    cursor.close()
    connection.close()
    return job


def update_job_status(job_id, status, progress, error_message=None):
    """Update the job's status and progress."""
    connection = get_db_connection()
    cursor = connection.cursor()

    sql = "UPDATE jobs SET status = %s, progress = %s, error_message = %s, updated_at = NOW() WHERE job_id = %s;"
    cursor.execute(sql, (status, progress, error_message, job_id))
    connection.commit()

    cursor.close()
    connection.close()
    print(f"🔄 Job {job_id} → status='{status}', progress={progress}%")


def save_results_to_db(job_id, result):
    """Save paths to results table."""
    connection = get_db_connection()
    cursor = connection.cursor()
    
    parsed_path = str(result.get("parsed_path", ""))
    score_path = str(result.get("score_path", ""))
    
    sql = """
        INSERT INTO results (job_id, parsed_json_path, score_json_path)
        VALUES (%s, %s, %s)
    """
    cursor.execute(sql, (job_id, parsed_path, score_path))
    connection.commit()
    cursor.close()
    connection.close()


def process_job(job):
    """Run the actual resume parsing pipeline."""
    job_id = job["job_id"]
    resume_filename = job["resume_filename"]
    jd_filename = job.get("jd_filename")
    
    print(f"🚀 Starting job {job_id} for file '{resume_filename}'")
    update_job_status(job_id, "in_progress", 10)

    try:
        resume_path = UPLOAD_DIR / resume_filename
        
        # Load JD
        jd_data = None
        if jd_filename:
            jd_path = UPLOAD_DIR / jd_filename
            if jd_path.exists():
                with open(jd_path, "r", encoding="utf-8") as f:
                    jd_data = json.load(f)
        
        # Run Pipeline
        # We need to modify run_full_pipeline to return paths or we extract them from result
        # For now, let's assume run_full_pipeline returns a dict with paths or data
        result = run_full_pipeline(str(resume_path), jd=jd_data)
        
        # Extract paths from result (we need to ensure main.py returns these)
        # Based on main.py analysis, it returns a dict with data, but also prints paths.
        # We should update main.py to return paths in the dict.
        
        # Mocking paths for now if main.py isn't updated yet, but we will update main.py next.
        # Let's assume result has 'score_path' and 'parsed_path' keys.
        
        save_results_to_db(job_id, result)
        
        update_job_status(job_id, "completed", 100)
        print(f"✅ Job {job_id} completed successfully!\n")
        
    except Exception as e:
        print(f"❌ Job {job_id} failed: {e}")
        traceback.print_exc()
        update_job_status(job_id, "failed", 0, str(e))


def run_worker():
    """Continuously fetch and process queued jobs."""
    print("👷 Worker started. Polling for jobs...")
    while True:
        try:
            job = get_next_queued_job()
            if job:
                process_job(job)
            else:
                time.sleep(2) # Wait before next poll
        except Exception as e:
            print(f"⚠️ Worker loop error: {e}")
            time.sleep(5)

if __name__ == "__main__":
    run_worker()
