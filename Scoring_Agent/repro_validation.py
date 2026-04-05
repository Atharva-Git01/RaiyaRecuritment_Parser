
import sys
import os
import json
import logging

# Setup path
sys.path.append(os.getcwd())

from agent_guardrails import AgentGuardrails

logging.basicConfig(level=logging.INFO)

def load_json(path):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

def run_test():
    try:
        base_dir = os.getcwd()
        resume_path = os.path.join(base_dir, "uploads", "test_parsed_resume")
        
        print(f"Loading resume from: {resume_path}")
        resume_data = load_json(resume_path)
        
        print("Resume Data Keys:", list(resume_data.keys()))
        if "personal_info" in resume_data:
            print("Personal Info:", resume_data["personal_info"])
            print("Type of personal_info:", type(resume_data["personal_info"]))
        
        print("Running validation...")
        AgentGuardrails.validate_resume_schema(resume_data)
        print("Validation PASSED")
        
    except Exception as e:
        print(f"Validation FAILED: {e}")

if __name__ == "__main__":
    run_test()
