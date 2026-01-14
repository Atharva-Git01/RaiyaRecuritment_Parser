# app/ledger_db.py
import json
from datetime import datetime
from typing import Optional

from app.saas_db import get_db_connection
from app.schemas import LearningEvent

def init_ledger_table():
    """
    Creates the learning_ledger table if it doesn't exist.
    """
    create_sql = """
    CREATE TABLE IF NOT EXISTS learning_ledger (
        ledger_id INT AUTO_INCREMENT PRIMARY KEY,
        job_id VARCHAR(50) NOT NULL,
        prompt_version VARCHAR(50) NOT NULL,
        input_hash VARCHAR(64) NOT NULL,
        context_json TEXT,
        phi4_response_json TEXT,
        validation_status VARCHAR(20),
        error_tags_json TEXT,
        human_feedback BOOLEAN,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(create_sql)
        conn.commit()
    print("✅ Verified learning_ledger table.")

def log_learning_event(event: LearningEvent) -> int:
    """
    Logs a LearningEvent to the database.
    Returns the new ledger_id.
    """
    insert_sql = """
    INSERT INTO learning_ledger 
    (job_id, prompt_version, input_hash, context_json, phi4_response_json, validation_status, error_tags_json, human_feedback, created_at)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
    """
    
    val_status = event.validation_status
    # Ensure validation status is truncated if necessary, though schema says 20 chars
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(insert_sql, (
            event.job_id,
            event.prompt_version,
            event.input_hash,
            json.dumps(event.context) if event.context else None,
            json.dumps(event.phi4_response),
            val_status,
            json.dumps(event.error_tags),
            event.human_feedback,
            event.timestamp
        ))
        conn.commit()
        ledger_id = cursor.lastrowid
        return ledger_id

if __name__ == "__main__":
    # Test init
    init_ledger_table()
