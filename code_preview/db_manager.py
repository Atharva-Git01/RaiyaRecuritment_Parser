import os

import mysql.connector
from dotenv import load_dotenv
from mysql.connector import Error

# Load environment variables
load_dotenv()


def get_db_connection():
    """Connect to MySQL using .env credentials."""
    try:
        connection = mysql.connector.connect(
            host=os.getenv("DB_HOST"),
            port=os.getenv("DB_PORT"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            database=os.getenv("DB_NAME"),
        )
        if connection.is_connected():
            print("✅ Connected to MySQL database.")
            return connection
    except Error as e:
        print(f"❌ Connection failed: {e}")
        return None


def initialize_tables():
    """Create core tables if they don't already exist."""
    connection = get_db_connection()
    if not connection:
        print("❌ Could not connect to DB.")
        return

    cursor = connection.cursor()
    cursor.execute(f"USE {os.getenv('DB_NAME')}")

    TABLES = {}

    TABLES[
        "jobs"
    ] = """
    CREATE TABLE IF NOT EXISTS jobs (
        job_id INT AUTO_INCREMENT PRIMARY KEY,
        resume_filename VARCHAR(255),
        jd_filename VARCHAR(255),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        status ENUM('queued','in_progress','failed','completed') DEFAULT 'queued',
        last_step VARCHAR(50),
        progress INT DEFAULT 0,
        attempts INT DEFAULT 0,
        worker_id VARCHAR(100),
        error_message TEXT
    );
    """

    TABLES[
        "checkpoints"
    ] = """
    CREATE TABLE IF NOT EXISTS checkpoints (
        id INT AUTO_INCREMENT PRIMARY KEY,
        job_id INT,
        step_name VARCHAR(50),
        payload_path VARCHAR(255),
        payload_hash VARCHAR(64),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (job_id) REFERENCES jobs(job_id)
    );
    """

    TABLES[
        "results"
    ] = """
    CREATE TABLE IF NOT EXISTS results (
        id INT AUTO_INCREMENT PRIMARY KEY,
        job_id INT,
        parsed_json_path VARCHAR(255),
        score_json_path VARCHAR(255),
        excel_row_id INT,
        completed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (job_id) REFERENCES jobs(job_id)
    );
    """

    for name, ddl in TABLES.items():
        cursor.execute(ddl)
        print(f"✅ Table '{name}' created or verified.")

    connection.commit()
    cursor.close()
    connection.close()
    print("✅ Database setup complete.")
