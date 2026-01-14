
import os
import sys
import json
import re
import glob

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from app.matcher import _calculate_experience_from_timeline

# Candidates to check
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
    pattern = os.path.join(directory, f"*{partial}*{suffix}")
    files = glob.glob(pattern)
    if files:
        return files[0]
    return None

def check_hallucination_pattern(value, chunks):
    """
    Check if the numeric value appears in text near 'CGPA', 'Score', 'Grade', 'Phone'.
    """
    if not value or value == 0:
        return None
        
    s_val = str(value)
    # If it's a float like 8.33, trim to 8.33
    if "." in s_val and s_val.endswith(".0"):
        s_val = s_val.replace(".0", "")
        
    for chunk in chunks:
        if not chunk: continue
        # Simple proximity check
        if s_val in chunk:
            # Check context window around the value
            idx = chunk.find(s_val)
            start = max(0, idx - 30)
            end = min(len(chunk), idx + len(s_val) + 30)
            context = chunk[start:end].lower()
            
            danger_words = ["cgpa", "sgpa", "grade", "score", "percent", "%", "mobile", "phone", "call"]
            for w in danger_words:
                if w in context:
                    return f"Found '{s_val}' near '{w}'"
    return None

def run_check():
    print("🚀 Verifying Experience Extraction & Hallucinations...\n")
    print(f"{'Candidate':<25} | {'Extracted (LLM)':<15} | {'Calculated (Timeline)':<20} | {'Status':<15} | {'Notes'}")
    print("-" * 110)
    
    for name in TARGET_CANDIDATES:
        parsed_path = get_file_by_partial_name("storage/tmp", name, "__parsed.json")
        if not parsed_path:
            continue
            
        with open(parsed_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        # 1. Get Extracted Value (The potential hallucination)
        extracted = data.get("total_experience_years", 0)
        
        # 2. Get Calculated Value (The strict check)
        calculated = _calculate_experience_from_timeline(data.get("experience", []))
        
        # 3. Detect Hallucination
        hallucination_warning = ""
        status = "OK"
        
        # Check specific known bad patterns
        if extracted > 0 and calculated == 0:
            status = "⚠️ SUSPICIOUS"
            # Dig deeper: Is extracted value in resume text near "CGPA"?
            raw_text = data.get("raw_text", "")
            # Also check text corpus from sections
            corpus = [raw_text]
            for e in data.get("experience", []): corpus.extend(e.get("description", []))
            
            reason = check_hallucination_pattern(extracted, corpus)
            if reason:
                status = "❌ HALLUCINATED"
                hallucination_warning = reason
            else:
                hallucination_warning = "Extracted > 0 but Timeline = 0"
        
        elif abs(extracted - calculated) > 2:
             status = "⚠️ MISMATCH"
             hallucination_warning = f"Diff: {round(extracted - calculated, 2)}y"
             
        # Print Row
        print(f"{name[:25]:<25} | {str(extracted):<15} | {str(calculated):<20} | {status:<15} | {hallucination_warning}")

if __name__ == "__main__":
    run_check()
