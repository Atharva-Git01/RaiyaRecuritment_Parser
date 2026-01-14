
import os
import sys

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

import json
import csv
import glob
import time
from app.ai_scorer import ai_score_resume, load_jd_file

# Candidates to benchmark (based on user image + key files found)
TARGET_CANDIDATES = [
    "Harshita Sanjay Sathe",
    "Swaroopa Anil Ingle",
    "Sagar Shrinivas Somani",
    "Gourav Sushil Ghuge",
    "Lalit Dansingh Rautela",
    "My Resume Jayesh 1F2 new",
    "Gladwyn Joseph",
    "ResumeSANDESHDHAWALE",
    "Neha_Borase_Resume",
    "Sarvajit Vinay Bhoyate"
]

def get_file_by_partial_name(directory, partial, suffix):
    """Finds valid file path given a partial name."""
    # Pattern: directory/*partial*suffix
    pattern = os.path.join(directory, f"*{partial}*{suffix}")
    files = glob.glob(pattern)
    if files:
        return files[0]
    return None

def run_benchmark():
    print("🚀 Starting Accuracy Benchmark on Golden Dataset...")
    
    jd = load_jd_file("job_description.json")
    
    results = []
    
    # Header for report
    results.append([
        "Candidate", 
        "Old Local Score", "Old AI Score", 
        "NEW AI Score", "NEW AI Exp Score", 
        "Delta (New AI - Old AI)", "Status"
    ])
    
    for name in TARGET_CANDIDATES:
        print(f"\nProcessing: {name}...")
        
        # 1. Load parsed JSON (Input)
        parsed_path = get_file_by_partial_name("storage/tmp", name, "__parsed.json")
        if not parsed_path:
            print(f"❌ Parsed JSON not found for {name}")
            continue
            
        with open(parsed_path, 'r', encoding='utf-8') as f:
            parsed_resume = json.load(f)
            
        # 2. Load Old Scores (for comparison)
        old_local_path = get_file_by_partial_name("storage/results", name, "__local_score.json")
        old_ai_path = get_file_by_partial_name("storage/results", name, "__ai_score.json")
        
        old_local_score = "N/A"
        if old_local_path and os.path.exists(old_local_path):
            with open(old_local_path, 'r', encoding='utf-8') as f:
                d = json.load(f)
                old_local_score = d.get("final_score", 0)

        old_ai_score = "N/A"
        if old_ai_path and os.path.exists(old_ai_path):
             with open(old_ai_path, 'r', encoding='utf-8') as f:
                d = json.load(f)
                if "ai_score" in d:
                    old_ai_score = d["ai_score"].get("final_score", 0)

        # 3. Run New AI Scorer
        # Note: ai_score_resume now has the FIX built-in to ignore 'total_experience'
        res = ai_score_resume(parsed_resume, jd)
        
        if not res.get("ai_ok"):
            print(f"❌ AI Error: {res.get('error')}")
            results.append([name, old_local_score, old_ai_score, "ERR", "ERR", "0", "Failed"])
            continue
            
        new_score = res["ai_score"].get("final_score", 0)
        new_exp_score = res["ai_score"].get("experience_score", 0)
        
        delta = 0
        if isinstance(old_ai_score, int):
            delta = new_score - old_ai_score
            
        status = "Stable"
        if isinstance(old_ai_score, int) and abs(delta) > 5:
            status = "Changed"
        
        print(f"✅ Scored: {new_score} (Exp: {new_exp_score}) | Old AI: {old_ai_score}")
        
        results.append([
            name, 
            old_local_score, old_ai_score, 
            new_score, new_exp_score, 
            delta, status
        ])
        
        # Rate limit to avoid 429s (just in case)
        time.sleep(1)

    # 4. Save Report
    output_path = "accuracy_report.csv"
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerows(results)
        
    print(f"\n✨ Benchmark Complete. Report saved to {output_path}")

if __name__ == "__main__":
    run_benchmark()
