import json
import os
import sys
from unittest.mock import patch, MagicMock

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.ai_scorer import ai_score_resume
from app.scoring_contracts import ResumeFacts, JDRequirements, ScoringWeights

def test_ai_scorer_prompt_injection():
    print("\n--- Testing AI Scorer Prompt Injection ---")

    # Mock Data
    resume_data = {
        "skills": ["Python", "Docker"],
        "experience": [],
        "relevant_experience_map": {
            "Python": 5.0,  # 5 years
            "Docker": 1.0   # 1 year
        }
    }
    
    jd_data = {
        "job_title": "Software Engineer",
        "skills": ["Python", "Docker"],
        "weights": {
            "skills_score": 0.5,
            "technologies_score": 0.5
        }
    }

    # Mock requests.post to avoid real API call and capture payload
    with patch("requests.post") as mock_post:
        # Setup mock response
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "choices": [{"message": {"content": json.dumps({
                "final_score": 80,
                "skills_score": 80, 
                "technologies_score": 80,
                "notes": "Mock response"
            })}}]
        }
        mock_post.return_value = mock_response

        # Run Scorer
        print("Running ai_score_resume...")
        result = ai_score_resume(resume_data, jd_data)

        # Verify Code Execution
        if not result["ai_ok"]:
            print(f"❌ AI Scorer failed: {result.get('error')}")
            return

        # Inspect usage of relevant_experience_map in the PROMPT
        # Args passed to requests.post
        args, kwargs = mock_post.call_args
        payload = kwargs.get("json", {})
        messages = payload.get("messages", [])
        
        user_content = ""
        for m in messages:
            if m["role"] == "user":
                user_content = m["content"]
                break
        
        print("\n--- Captured User Prompt ---")
        # print(user_content[:500] + "...") # Print snippet

        # Check for specific instructions
        instruction_snippet = "Skills with higher years of experience in this map MUST receive higher relevance scores."
        if instruction_snippet in user_content:
            print(f"✅ FOUND instruction snippet: '{instruction_snippet}'")
            
            # Check if the map values are actually in the JSON dump
            if '"Python": 5.0' in user_content or '"Python": 5' in user_content:
                print("✅ Found Python experience (5 years) in prompt JSON.")
            else:
                print("❌ Python experience NOT found in prompt JSON.")
                
            if '"Docker": 1.0' in user_content or '"Docker": 1' in user_content:
                 print("✅ Found Docker experience (1 year) in prompt JSON.")
            else:
                 print("❌ Docker experience NOT found in prompt JSON.")

        else:
            print(f"❌ Instruction snippet NOT found in prompt.")
            print("Prompt content snippet:\n", user_content[-1000:])

if __name__ == "__main__":
    test_ai_scorer_prompt_injection()
