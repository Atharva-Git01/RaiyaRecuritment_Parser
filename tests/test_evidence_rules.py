import json
import os
import sys
from unittest.mock import patch, MagicMock

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.ai_scorer import ai_score_resume

def test_evidence_rules_injection():
    print("\n--- Testing Evidence Rules Injection ---")

    jd_data = {
        "job_title": "Software Engineer",
        "skills": ["Python"],
        "weights": {"skills_score": 1.0}
    }

    # CASE 1: Intern Heavy Resume (Should Trigger rule_intern_experience)
    print("\n1️⃣ Testing 'Intern Experience' Rule...")
    resume_intern = {
        "experience": [
            {"role": "Software Intern", "company": "A", "start_date": "2020-01", "end_date": "2020-06"},
            {"role": "Intern Developer", "company": "B", "start_date": "2021-01", "end_date": "2021-06"}
        ],
        "summary": "Filled summary",
        "skills": ["Python"]
    }

    with patch("requests.post") as mock_post:
        mock_response = MagicMock()
        mock_response.json.return_value = {"choices": [{"message": {"content": "{}"}}]}
        mock_post.return_value = mock_response

        # Run
        ai_score_resume(resume_intern, jd_data)

        # Inspect Prompt
        args, kwargs = mock_post.call_args
        payload = kwargs.get("json", {})
        messages = payload.get("messages", [])
        user_content = next((m["content"] for m in messages if m["role"] == "user"), "")
        
        if "If most experience is 'Intern', punish Seniority scores." in user_content:
            print("✅ 'Intern' Constraint DETECTED in prompt.")
        else:
            print("❌ 'Intern' Constraint MISSING in prompt.")
            # print(user_content[-1000:])

    # CASE 2: Missing Summary (Should Trigger rule_missing_summary)
    print("\n2️⃣ Testing 'Missing Summary' Rule...")
    resume_no_summary = {
        "experience": [{"role": "Senior Dev", "company": "A", "start_date": "2010-01", "end_date": "2020-01"}],
        "summary": "", # EMPTY
        "skills": ["Python"]
    }

    with patch("requests.post") as mock_post:
        mock_response = MagicMock()
        mock_response.json.return_value = {"choices": [{"message": {"content": "{}"}}]}
        mock_post.return_value = mock_response

        ai_score_resume(resume_no_summary, jd_data)

        args, kwargs = mock_post.call_args
        payload = kwargs.get("json", {})
        messages = payload.get("messages", [])
        user_content = next((m["content"] for m in messages if m["role"] == "user"), "")

        if "If summary is missing, max out soft skills score at 50." in user_content:
            print("✅ 'Missing Summary' Constraint DETECTED in prompt.")
        else:
            print("❌ 'Missing Summary' Constraint MISSING.")

    # CASE 3: Clean Resume
    print("\n3️⃣ Testing Clean Resume (No Triggers)...")
    resume_clean = {
        "experience": [{"role": "Senior Dev", "company": "A", "start_date": "2015-01", "end_date": "2020-01"}],
        "summary": "Im a pro",
        "skills": ["Python"]
    }

    with patch("requests.post") as mock_post:
        mock_response = MagicMock()
        mock_response.json.return_value = {"choices": [{"message": {"content": "{}"}}]}
        mock_post.return_value = mock_response

        ai_score_resume(resume_clean, jd_data)

        args, kwargs = mock_post.call_args
        payload = kwargs.get("json", {})
        messages = payload.get("messages", [])
        user_content = next((m["content"] for m in messages if m["role"] == "user"), "")

        if "MANDATORY SCORING CONSTRAINTS" not in user_content:
            print("✅ Constraints correctly ABSENT from prompt.")
        else:
            print("❌ Unexpected constraints found in prompt.")
            print(user_content)

if __name__ == "__main__":
    test_evidence_rules_injection()
