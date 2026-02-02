
import json
import os
import sys

# Ensure app imports work
sys.path.append(os.getcwd())

from app.matcher import score_resume_against_jd, compute_experience_score
from app.ai_scorer import load_jd_file

def test_matcher_experience():
    print("🚀 Verifying Matcher Experience Fix for Harshita...")
    
    resume_path = "storage/tmp/152090014 Harshita Sanjay Sathe__scoring_ready.json"
    jd_path = "job_description.json"
    
    if not os.path.exists(resume_path):
        print(f"❌ Resume file not found: {resume_path}")
        return

    with open(resume_path, "r", encoding="utf-8") as f:
        resume_data = json.load(f)
        
    original_exp = resume_data.get("total_experience_years")
    print(f"📄 JSON 'total_experience_years' (Bad Value): {original_exp}")
    print(f"📄 Raw Experience Data: {json.dumps(resume_data.get('experience', []), indent=2)}")
    
    jd = load_jd_file(jd_path)
    
    # Run Matcher
    result = score_resume_against_jd(resume_data, jd)
    
    calc_exp = result["details"]["candidate_total_experience_years"]
    exp_score = result["experience_score"]
    
    print(f"\n✅ Calculated Experience: {calc_exp} Years")
    print(f"✅ Experience Score: {exp_score}/100")
    
    # Assertions
    if 4.0 <= calc_exp <= 5.0:
        print("\nSUCCESS: Calculated experience is within expected range (~4.3 years). Fix working.")
    elif calc_exp == 8.33:
        print("\n❌ FAILURE: Matcher still using the 8.33 value.")
    else:
        print(f"\n⚠️ WARNING: Calculated experience {calc_exp} is unexpected (neither 8.33 nor ~4.3). Check timeline logic.")

    # Check Experience Score Logic
    # JD likely requires 3-8 years. 4.3 years should satisfy min=3.
    # Score should be ~60-100 depending on linear scaling or thresholds.
    
if __name__ == "__main__":
    test_matcher_experience()
