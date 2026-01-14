from app.db_manager import get_db_connection


def create_job(resume_filename: str):
    """
    Inserts a new job record into the 'jobs' table.
    Returns the job_id if successful.
    """
    connection = get_db_connection()
    if not connection:
        print("❌ Database connection failed. Cannot create job.")
        return None

    try:
        cursor = connection.cursor()

        sql = """
        INSERT INTO jobs (resume_filename, status, last_step, progress, attempts)
        VALUES (%s, 'queued', NULL, 0, 0);
        """
        cursor.execute(sql, (resume_filename,))
        connection.commit()

        job_id = cursor.lastrowid
        print(f"✅ Job created successfully! job_id={job_id}, file='{resume_filename}'")
        return job_id

    except Exception as e:
        print(f"❌ Failed to create job: {e}")
        connection.rollback()
        return None
    finally:
        cursor.close()
        connection.close()
