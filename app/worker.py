import time

from app.db_manager import get_db_connection


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


def update_job_status(job_id, status, progress):
    """Update the job's status and progress."""
    connection = get_db_connection()
    cursor = connection.cursor()

    sql = "UPDATE jobs SET status = %s, progress = %s, updated_at = NOW() WHERE job_id = %s;"
    cursor.execute(sql, (status, progress, job_id))
    connection.commit()

    cursor.close()
    connection.close()
    print(f"🔄 Job {job_id} → status='{status}', progress={progress}%")


def process_job(job):
    """Simulate the resume parsing pipeline."""
    job_id = job["job_id"]
    print(f"🚀 Starting job {job_id} for file '{job['resume_filename']}'")

    update_job_status(job_id, "in_progress", 10)
    time.sleep(1)

    update_job_status(job_id, "in_progress", 30)
    time.sleep(1)

    update_job_status(job_id, "in_progress", 60)
    time.sleep(1)

    update_job_status(job_id, "in_progress", 90)
    time.sleep(1)

    update_job_status(job_id, "completed", 100)
    print(f"✅ Job {job_id} completed successfully!\n")


def run_worker():
    """Continuously fetch and process queued jobs."""
    job = get_next_queued_job()
    if not job:
        print("📭 No queued jobs found.")
        return

    process_job(job)
