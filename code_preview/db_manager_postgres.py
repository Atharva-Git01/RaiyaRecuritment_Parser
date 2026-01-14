import os
import psycopg2
from psycopg2.extras import RealDictCursor, Json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def get_db_connection():
    """Connect to PostgreSQL using .env credentials."""
    try:
        connection = psycopg2.connect(
            host=os.getenv("DB_HOST", "localhost"),
            port=os.getenv("DB_PORT", "5432"),
            user=os.getenv("DB_USER", "postgres"),
            password=os.getenv("DB_PASSWORD", "password"),
            dbname=os.getenv("DB_NAME", "resume_parser_db"),
        )
        return connection
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return None

def initialize_schema(schema_file="database_schema.sql"):
    """Execute the schema.sql file to create tables."""
    connection = get_db_connection()
    if not connection:
        return

    try:
        with connection.cursor() as cursor:
            with open(schema_file, "r") as f:
                sql = f.read()
                cursor.execute(sql)
            connection.commit()
            print("✅ Database schema initialized successfully.")
    except Exception as e:
        print(f"❌ Schema initialization failed: {e}")
        connection.rollback()
    finally:
        connection.close()

# Example helper functions for the new schema

def create_tenant(name, slug, email):
    conn = get_db_connection()
    if not conn: return None
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                "INSERT INTO tenants (name, slug, contact_email) VALUES (%s, %s, %s) RETURNING tenant_id;",
                (name, slug, email)
            )
            tenant_id = cur.fetchone()['tenant_id']
            conn.commit()
            return tenant_id
    except Exception as e:
        print(f"Error creating tenant: {e}")
        conn.rollback()
        return None
    finally:
        conn.close()

def create_batch(tenant_id, name, jd_id=None, created_by=None):
    conn = get_db_connection()
    if not conn: return None
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                INSERT INTO batches (tenant_id, name, jd_id, created_by, status)
                VALUES (%s, %s, %s, %s, 'created')
                RETURNING batch_id;
                """,
                (tenant_id, name, jd_id, created_by)
            )
            batch_id = cur.fetchone()['batch_id']
            conn.commit()
            return batch_id
    except Exception as e:
        print(f"Error creating batch: {e}")
        conn.rollback()
        return None
    finally:
        conn.close()

def claim_job(worker_id):
    """Atomic job claim using UPDATE ... RETURNING."""
    conn = get_db_connection()
    if not conn: return None
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Find and claim a queued job atomically
            cur.execute(
                """
                UPDATE jobs
                SET status = 'in_progress',
                    worker_id = %s,
                    started_at = NOW(),
                    updated_at = NOW()
                WHERE job_id = (
                    SELECT job_id
                    FROM jobs
                    WHERE status = 'queued'
                    ORDER BY created_at ASC
                    FOR UPDATE SKIP LOCKED
                    LIMIT 1
                )
                RETURNING *;
                """,
                (worker_id,)
            )
            job = cur.fetchone()
            conn.commit()
            return job
    except Exception as e:
        print(f"Error claiming job: {e}")
        conn.rollback()
        return None
    finally:
        conn.close()
