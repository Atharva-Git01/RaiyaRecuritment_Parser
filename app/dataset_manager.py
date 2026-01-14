# app/dataset_manager.py
import json
import os
from datetime import datetime
from typing import List

from app.saas_db import get_db_connection

DATASET_PATH = "storage/datasets/golden_dataset.json"

def load_gold_dataset():
    if os.path.exists(DATASET_PATH):
        with open(DATASET_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def save_gold_dataset(data):
    os.makedirs(os.path.dirname(DATASET_PATH), exist_ok=True)
    with open(DATASET_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

def promote_verified_entries(limit: int = 10):
    """
    Promotes 'PASS' entries from Ledger to Golden Dataset.
    Ideally this should check for 'human_feedback=True' (Verified by Human).
    For auto-loop, we take 'PASS' status + maybe high confidence score.
    """
    sql = """
    SELECT * FROM learning_ledger 
    WHERE validation_status = 'PASS' 
    AND (human_feedback IS TRUE OR human_feedback IS NULL)
    ORDER BY created_at DESC
    LIMIT %s
    """
    
    events = []
    with get_db_connection() as conn:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(sql, (limit,))
        events = cursor.fetchall()
        
    gold = load_gold_dataset()
    existing_hashes = {g["input_hash"] for g in gold}
    
    promoted_count = 0
    for e in events:
        if e["input_hash"] in existing_hashes:
            continue
            
        # Parse JSONs
        try:
            resp = json.loads(e["phi4_response_json"])
            ctx = json.loads(e["context_json"]) if e.get("context_json") else None
            
            entry = {
                "id": str(e["ledger_id"]),
                "input_hash": e["input_hash"],
                "input_context": ctx,
                "output": resp,
                "promoted_at": datetime.now().isoformat(),
                "prompt_version": e["prompt_version"]
            }
            gold.append(entry)
            promoted_count += 1
            existing_hashes.add(e["input_hash"])
        except:
            continue
            
    save_gold_dataset(gold)
    print(f"✅ Promoted {promoted_count} new entries to Golden Dataset.")
    return promoted_count
