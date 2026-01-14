"""
saas_db.py — Database Access Layer for SaaS Schema

This module provides repository functions for interacting with the multi-tenant
saas_db database tables: tenants, business_units, job_descriptions, batches,
jobs, and resume_results.
"""

import json
import os
from contextlib import contextmanager
from datetime import datetime
from typing import Any, Dict, List, Optional

import mysql.connector
from mysql.connector import Error, pooling
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# =========================
# CONNECTION POOL
# =========================

_connection_pool = None


def get_connection_pool():
    """Get or create the connection pool."""
    global _connection_pool
    if _connection_pool is None:
        try:
            _connection_pool = pooling.MySQLConnectionPool(
                pool_name="saas_pool",
                pool_size=5,
                pool_reset_session=True,
                host=os.getenv("DB_HOST", "localhost"),
                port=int(os.getenv("DB_PORT", 3306)),
                user=os.getenv("DB_USER", "root"),
                password=os.getenv("DB_PASSWORD", ""),
                database=os.getenv("DB_NAME", "saas_db"),
            )
            print("✅ Database connection pool created.")
        except Error as e:
            print(f"❌ Failed to create connection pool: {e}")
            raise
    return _connection_pool


@contextmanager
def get_db_connection():
    """Context manager for database connections from the pool."""
    pool = get_connection_pool()
    connection = None
    try:
        connection = pool.get_connection()
        yield connection
    except Error as e:
        print(f"❌ Database error: {e}")
        raise
    finally:
        if connection and connection.is_connected():
            connection.close()


# =========================
# TENANT OPERATIONS
# =========================

def get_or_create_tenant(tenant_name: str) -> int:
    """
    Get an existing tenant by name or create a new one.
    Returns the tenant_id.
    """
    with get_db_connection() as conn:
        cursor = conn.cursor(dictionary=True)
        
        # Check if tenant exists
        cursor.execute(
            "SELECT tenant_id FROM tenants WHERE tenant_name = %s",
            (tenant_name,)
        )
        result = cursor.fetchone()
        
        if result:
            return result["tenant_id"]
        
        # Create new tenant
        cursor.execute(
            "INSERT INTO tenants (tenant_name, status) VALUES (%s, 'active')",
            (tenant_name,)
        )
        conn.commit()
        tenant_id = cursor.lastrowid
        print(f"✅ Created tenant '{tenant_name}' with ID {tenant_id}")
        return tenant_id


def get_tenant(tenant_id: int) -> Optional[Dict]:
    """Get tenant by ID."""
    with get_db_connection() as conn:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            "SELECT * FROM tenants WHERE tenant_id = %s",
            (tenant_id,)
        )
        return cursor.fetchone()


# =========================
# BUSINESS UNIT OPERATIONS
# =========================

def get_or_create_business_unit(tenant_id: int, bu_name: str) -> int:
    """
    Get an existing business unit by name or create a new one.
    Returns the bu_id.
    """
    with get_db_connection() as conn:
        cursor = conn.cursor(dictionary=True)
        
        # Check if BU exists
        cursor.execute(
            "SELECT bu_id FROM business_units WHERE tenant_id = %s AND bu_name = %s",
            (tenant_id, bu_name)
        )
        result = cursor.fetchone()
        
        if result:
            return result["bu_id"]
        
        # Create new business unit
        cursor.execute(
            "INSERT INTO business_units (tenant_id, bu_name) VALUES (%s, %s)",
            (tenant_id, bu_name)
        )
        conn.commit()
        bu_id = cursor.lastrowid
        print(f"✅ Created business unit '{bu_name}' with ID {bu_id}")
        return bu_id


# =========================
# JOB DESCRIPTION OPERATIONS
# =========================

def create_job_description(bu_id: int, jd_title: str, jd_data: Dict) -> int:
    """
    Create a new job description entry.
    Returns the jd_id.
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO job_descriptions (bu_id, jd_title, jd_data_json)
            VALUES (%s, %s, %s)
            """,
            (bu_id, jd_title, json.dumps(jd_data))
        )
        conn.commit()
        jd_id = cursor.lastrowid
        print(f"✅ Created job description '{jd_title}' with ID {jd_id}")
        return jd_id


def get_job_description(jd_id: int) -> Optional[Dict]:
    """Get job description by ID."""
    with get_db_connection() as conn:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            "SELECT * FROM job_descriptions WHERE jd_id = %s",
            (jd_id,)
        )
        result = cursor.fetchone()
        if result and result.get("jd_data_json"):
            result["jd_data"] = json.loads(result["jd_data_json"])
        return result


# =========================
# BATCH OPERATIONS
# =========================


def create_batch(bu_id: int, uploader_user_id: Optional[int] = None, batch_guid: str = None) -> int:
    """
    Create a new processing batch.
    Returns the batch_id.
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO batches (bu_id, uploader_user_id, status, batch_guid)
            VALUES (%s, %s, 'pending', %s)
            """,
            (bu_id, uploader_user_id, batch_guid)
        )
        conn.commit()
        batch_id = cursor.lastrowid
        print(f"✅ Created batch {batch_guid} with ID {batch_id}")
        return batch_id



def update_batch_status(batch_id: int, status: str) -> None:
    """Update batch status. Valid statuses: pending, processing, completed, failed."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE batches SET status = %s WHERE batch_id = %s",
            (status, batch_id)
        )
        conn.commit()


def check_and_update_batch_status(batch_id: int) -> None:
    """
    Check if all jobs in a batch are completed or failed, 
    and update the batch status accordingly.
    """
    with get_db_connection() as conn:
        cursor = conn.cursor(dictionary=True)
        # Count statuses for this batch
        cursor.execute(
            """
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN status IN ('completed', 'failed') THEN 1 ELSE 0 END) as done_count,
                SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed_count
            FROM jobs 
            WHERE batch_id = %s
            """,
            (batch_id,)
        )
        counts = cursor.fetchone()
        
        if not counts or counts['total'] == 0:
            return 
            
        total = counts['total']
        done = counts['done_count'] or 0
        failed = counts['failed_count'] or 0
        
        # If all jobs are done
        if done == total:
            new_status = 'completed'
            # If any job failed, mark batch as failed per user request
            if failed > 0:
                new_status = 'failed'
            
            # Update batch status
            # We call the existing update function, but we need to avoid circular or nested transaction issues if reusing connection.
            # update_batch_status uses its own connection context, which is fine.
            # But we are inside `with get_db_connection()`.
            # safer to just execute update here or close this conn first.
            
            cursor.execute(
                "UPDATE batches SET status = %s WHERE batch_id = %s",
                (new_status, batch_id)
            )
            conn.commit()
            print(f"🔄 Batch {batch_id} status updated to {new_status}")


def get_batch(batch_id: int) -> Optional[Dict]:
    """Get batch by ID."""
    with get_db_connection() as conn:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            "SELECT * FROM batches WHERE batch_id = %s",
            (batch_id,)
        )
        return cursor.fetchone()


def get_batch_history(limit: int = 50) -> List[Dict]:
    """
    Get batch history with job counts and status summaries.
    Returns list of batches with resume_count for history display.
    """
    with get_db_connection() as conn:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            """
            SELECT 
                b.batch_id,
                b.bu_id,
                b.status,
                b.created_at,
                COUNT(j.job_id) as resume_count,
                SUM(CASE WHEN j.status = 'completed' THEN 1 ELSE 0 END) as completed_count,
                SUM(CASE WHEN j.status = 'failed' THEN 1 ELSE 0 END) as failed_count,
                SUM(CASE WHEN j.status = 'running' THEN 1 ELSE 0 END) as running_count
            FROM batches b
            LEFT JOIN jobs j ON b.batch_id = j.batch_id
            GROUP BY b.batch_id, b.bu_id, b.status, b.created_at
            ORDER BY b.created_at DESC
            LIMIT %s
            """,
            (limit,)
        )
        return cursor.fetchall()

# =========================
# JOB OPERATIONS
# =========================

def create_job(
    batch_id: int,
    jd_id: int,
    requester_user_id: Optional[int] = None,
    resume_filename: Optional[str] = None
) -> int:
    """
    Create a new job entry.
    Returns the job_id.
    
    Note: The `jobs` table in saas_db has batch_id, jd_id, requester_user_id, status.
    We'll store resume_filename in resume_results.parsed_resume_json later.
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO jobs (batch_id, jd_id, requester_user_id, status)
            VALUES (%s, %s, %s, 'queued')
            """,
            (batch_id, jd_id, requester_user_id)
        )
        conn.commit()
        job_id = cursor.lastrowid
        print(f"✅ Created job with ID {job_id}")
        return job_id


def update_job_status(job_id: int, status: str) -> None:
    """Update job status. Valid statuses: queued, running, completed, failed."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE jobs SET status = %s WHERE job_id = %s",
            (status, job_id)
        )
        conn.commit()


def get_job(job_id: int) -> Optional[Dict]:
    """Get job by ID."""
    with get_db_connection() as conn:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            "SELECT * FROM jobs WHERE job_id = %s",
            (job_id,)
        )
        return cursor.fetchone()


def get_jobs_by_batch(batch_id: int) -> List[Dict]:
    """Get all jobs for a given batch."""
    with get_db_connection() as conn:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            """
            SELECT j.*, rr.result_id, rr.scores_json, rr.report_url
            FROM jobs j
            LEFT JOIN resume_results rr ON j.job_id = rr.job_id
            WHERE j.batch_id = %s
            ORDER BY j.created_at DESC
            """,
            (batch_id,)
        )
        results = cursor.fetchall()
        # Parse JSON fields
        for row in results:
            if row.get("scores_json"):
                try:
                    row["scores"] = json.loads(row["scores_json"])
                except:
                    row["scores"] = None
        return results


def get_all_jobs(limit: int = 100) -> List[Dict]:
    """Get all jobs with their results."""
    with get_db_connection() as conn:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            """
            SELECT j.*, rr.result_id, rr.scores_json, rr.report_url,
                   rr.parsed_resume_json
            FROM jobs j
            LEFT JOIN resume_results rr ON j.job_id = rr.job_id
            ORDER BY j.created_at DESC
            LIMIT %s
            """,
            (limit,)
        )
        results = cursor.fetchall()
        # Parse JSON fields
        for row in results:
            if row.get("scores_json"):
                try:
                    row["scores"] = json.loads(row["scores_json"])
                except:
                    row["scores"] = None
            if row.get("parsed_resume_json"):
                try:
                    row["parsed_resume"] = json.loads(row["parsed_resume_json"])
                except:
                    row["parsed_resume"] = None
        return results


# =========================
# RESUME RESULTS OPERATIONS
# =========================

def save_resume_result(
    job_id: int,
    parsed_json: Dict,
    scores_json: Dict,
    report_url: str
) -> int:
    """
    Save the resume processing result.
    Returns the result_id.
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO resume_results (job_id, parsed_resume_json, scores_json, report_url, processed_at)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (
                job_id,
                json.dumps(parsed_json),
                json.dumps(scores_json),
                report_url,
                datetime.now()
            )
        )
        conn.commit()
        result_id = cursor.lastrowid
        print(f"✅ Saved resume result with ID {result_id}")
        return result_id


def get_resume_result(job_id: int) -> Optional[Dict]:
    """Get resume result by job_id."""
    with get_db_connection() as conn:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            "SELECT * FROM resume_results WHERE job_id = %s",
            (job_id,)
        )
        result = cursor.fetchone()
        if result:
            if result.get("parsed_resume_json"):
                try:
                    result["parsed_resume"] = json.loads(result["parsed_resume_json"])
                except:
                    result["parsed_resume"] = None
            if result.get("scores_json"):
                try:
                    result["scores"] = json.loads(result["scores_json"])
                except:
                    result["scores"] = None
        return result


def get_job_with_result(job_id: int) -> Optional[Dict]:
    """Get job with its associated result."""
    with get_db_connection() as conn:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            """
            SELECT j.*, rr.result_id, rr.parsed_resume_json, rr.scores_json, 
                   rr.report_url, rr.processed_at
            FROM jobs j
            LEFT JOIN resume_results rr ON j.job_id = rr.job_id
            WHERE j.job_id = %s
            """,
            (job_id,)
        )
        result = cursor.fetchone()
        if result:
            if result.get("parsed_resume_json"):
                try:
                    result["parsed_resume"] = json.loads(result["parsed_resume_json"])
                except:
                    result["parsed_resume"] = None
            if result.get("scores_json"):
                try:
                    result["scores"] = json.loads(result["scores_json"])
                except:
                    result["scores"] = None
        return result


# =========================
# GENERIC GETTERS (FOR ADMIN UI)
# =========================

def get_all_tenants() -> List[Dict]:
    """Get all tenants."""
    with get_db_connection() as conn:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM tenants")
        return cursor.fetchall()

def get_all_business_units() -> List[Dict]:
    """Get all business units."""
    with get_db_connection() as conn:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM business_units")
        return cursor.fetchall()

def get_all_job_descriptions() -> List[Dict]:
    """Get all job descriptions (metadata only, no large JSON)."""
    with get_db_connection() as conn:
        cursor = conn.cursor(dictionary=True)
        # Exclude jd_data_json to save bandwidth
        cursor.execute("SELECT jd_id, bu_id, jd_title, created_at FROM job_descriptions")
        return cursor.fetchall()

def get_all_batches_raw() -> List[Dict]:
    """Get all batches raw table data."""
    with get_db_connection() as conn:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM batches ORDER BY created_at DESC")
        return cursor.fetchall()

def get_all_resume_results_summary(limit: int = 100) -> List[Dict]:
    """Get partial resume results (avoiding huge JSON payloads)."""
    with get_db_connection() as conn:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            """
            SELECT result_id, job_id, report_url, processed_at 
            FROM resume_results 
            ORDER BY processed_at DESC 
            LIMIT %s
            """, 
            (limit,)
        )
        return cursor.fetchall()


# =========================
# UTILITY FUNCTIONS
# =========================

def test_connection() -> bool:
    """Test database connection."""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            return result is not None
    except Exception as e:
        print(f"❌ Connection test failed: {e}")
        return False


def get_default_context() -> Dict[str, int]:
    """
    Get or create a default tenant and business unit for simple usage.
    Returns dict with 'tenant_id' and 'bu_id'.
    """
    tenant_id = get_or_create_tenant("Default Tenant")
    bu_id = get_or_create_business_unit(tenant_id, "Default Business Unit")
    return {
        "tenant_id": tenant_id,
        "bu_id": bu_id
    }


# =========================
# TEST BLOCK
# =========================

if __name__ == "__main__":
    print("\n🔍 Testing saas_db.py...")
    
    if test_connection():
        print("✅ Database connection successful!")
        
        # Test default context
        ctx = get_default_context()
        print(f"📌 Default context: {ctx}")
    else:
        print("❌ Database connection failed!")
