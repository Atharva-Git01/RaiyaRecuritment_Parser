
import sys
import os
import unittest

# Ensure we can import from app/
sys.path.append(os.getcwd())

from app.matcher import score_resume_against_jd, get_semantic_model

class TestHybridMatcher(unittest.TestCase):
    
    @classmethod
    def setUpClass(cls):
        print("\n⏳ Loading Model for Test Suite...")
        get_semantic_model() # Preload
        print("✅ Model Loaded.\n")

    def test_01_exact_match(self):
        """Test that exact keyword matches still work 100%"""
        jd = {
            "skills": ["Python", "Docker"],
            "scoring": {}
        }
        resume = {
            "skills": ["Python", "Docker"],
            "experience": []
        }
        print("Expected: 100% (Exact Match)")
        result = score_resume_against_jd(resume, jd)
        self.assertEqual(result["skills_score"], 100)
        print(f"Actual: {result['skills_score']}%\n")

    def test_02_semantic_synonym(self):
        """Test that 'AI' matches 'Artificial Intelligence' semantically"""
        jd = {
            "skills": ["Artificial Intelligence"],
            "scoring": {}
        }
        resume = {
            "skills": ["AI", "Algorithms"],
            "experience": []
        }
        print("Expected: 100% (Semantic Match: AI -> Artificial Intelligence)")
        result = score_resume_against_jd(resume, jd)
        # Should match if threshold <= 0.8 (AI/Artificial Intelligence usually high)
        self.assertGreater(result["skills_score"], 0, "Failed to match AI to Artificial Intelligence")
        print(f"Actual: {result['skills_score']}%\n")

    def test_03_description_discovery(self):
        """Test finding a skill hidden in experience description"""
        jd = {
            "skills": ["Kubernetes"],
            "scoring": {}
        }
        resume = {
            "skills": ["Java"],
            "experience": [
                {
                    "role": "Backend Engineer",
                    "description": ["Orchestrated containers using K8s clusters for high availability."]
                }
            ]
        }
        # "K8s" is a strong semantic match for "Kubernetes"
        print("Expected: 100% (Hidden Description: K8s -> Kubernetes)")
        result = score_resume_against_jd(resume, jd)
        self.assertGreater(result["skills_score"], 0, "Failed to find Kubernetes via K8s in description")
        print(f"Actual: {result['skills_score']}%\n")

    def test_04_no_match(self):
        """Test that unrelated skills do NOT match"""
        jd = {
            "skills": ["React"],
            "scoring": {}
        }
        resume = {
            "skills": ["Excel", "Microsoft Word"],
            "experience": []
        }
        print("Expected: 0% (No Relation)")
        result = score_resume_against_jd(resume, jd)
        self.assertEqual(result["skills_score"], 0)
        print(f"Actual: {result['skills_score']}%\n")

    def test_05_technologies_semantic(self):
        """Test technologies field specifically"""
        jd = {
            "technologies": ["AWS"],
            "scoring": {}
        }
        resume = {
           "experience": [
               {
                   "description": ["Deployed on Amazon Cloud Services."]
               }
           ]
        }
        # "Amazon Cloud Services" ~ "AWS"
        print("Expected: 100% (Tech Match: Amazon Cloud Services -> AWS)")
        result = score_resume_against_jd(resume, jd)
        self.assertGreater(result["technologies_score"], 0)
        print(f"Actual: {result['technologies_score']}%\n")

if __name__ == '__main__':
    unittest.main()
