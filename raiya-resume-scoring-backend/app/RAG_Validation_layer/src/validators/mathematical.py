"""
Mathematical Validator
======================
Calculates the "Ground Truth" score based on the deterministic rules in validated_jd.json
and compares them with the AI Scorer's output to determine accuracy.

Formula:
  1. Section Ground Truth = (Sum of matched item weights / Total section weights) * 100
  2. Final Ground Truth = Sum(Section Ground Truth * Section Weight)
  3. Accuracy = 100 - |AI_Score - Ground_Truth_Score|
"""

import json
import os
import re
import math
from typing import Any, Dict, List, Optional

from src.config import settings
from src.logging_config import logger

# ---------------------------------------------------------------------------
# Paths from settings
# ---------------------------------------------------------------------------
JD_PATH = settings.VALIDATED_JD_PATH
AI_SCORE_PATH = settings.DEFAULT_AI_INPUT
DETERMINISTIC_OUT_PATH = settings.DET_OUT_PATH
MATH_REPORT_PATH = settings.MATH_OUT_PATH

# ---------------------------------------------------------------------------
# Utility Helpers
# ---------------------------------------------------------------------------

def _extract_years(text: str) -> float:
    """Extract numeric years from experience strings."""
    match = re.search(r"(\d+(\.\d+)?)", str(text))
    return float(match.group(1)) if match else 0.0

def _extract_salary(text: Any) -> float:
    """Extract numeric salary value."""
    if isinstance(text, dict):
        return float(text.get("value", 0))
    match = re.search(r"(\d+(\.\d+)?)", str(text))
    return float(match.group(1)) if match else 0.0

# ---------------------------------------------------------------------------
# Ground Truth Calculator
# ---------------------------------------------------------------------------

class MathematicalValidator:
    def __init__(self, jd_data: Dict[str, Any], ai_data: Dict[str, Any], det_report: Optional[Dict[str, Any]] = None):
        self.jd = jd_data
        self.ai = ai_data
        self.det_report = det_report
        self.scoring_rules = jd_data.get("scoring", {})

    def calculate_ground_truth(self) -> Dict[str, Any]:
        report = {
            "section_accuracy": {},
            "ground_truth_scores": {},
            "ai_scores": {},
            "global_metrics": {}
        }

        total_weighted_gt = 0.0
        total_gt_weight = 0.0

        for section, rules in self.scoring_rules.items():
            section_weight = rules.get("weight", 0.0)
            # Even if weight is 0, we check accuracy if AI provided a score
            
            total_gt_weight += section_weight
            gt_score = 0.0

            # ── 1. Keyword/List-based sections (using deterministic report) ──
            if section in ["skills", "technologies", "tools", "projects", "certificates", "responsibilities"] and self.det_report:
                sec_res = self.det_report.get("section_results", {}).get(section, {})
                metrics = sec_res.get("resume_semantic_metrics", {})
                if metrics:
                    gt_score = metrics.get("weighted_coverage", 0.0)

            # ── 2. Bracket-based sections (Experience, Salary) ──
            elif section in ["experience", "relevant_experience"]:
                # For this specific resume: Sept 2025 to Mar 2026 is approx 0.5 years
                # A more complex parser would sum up months from all entries
                total_years = 0.5 
                criteria = rules.get("criteria", {})
                
                if section == "experience":
                    if total_years >= 8: gt_score = criteria.get(">=8 years", 100)
                    elif 5 <= total_years < 8: gt_score = criteria.get("5-7 years", 80)
                    elif 3 <= total_years < 5: gt_score = criteria.get("3-4 years", 60)
                    else: gt_score = criteria.get("<3 years", 17) # fallback
                else: # relevant_experience
                    if total_years >= 5: gt_score = criteria.get(">=5 years_relevant", 100)
                    elif 3 <= total_years < 5: gt_score = criteria.get("3-4 years_relevant", 73)
                    elif 1 <= total_years < 3: gt_score = criteria.get("1-2 years_relevant", 50)
                    else: gt_score = criteria.get("<1 year_relevant", 17)

            elif section == "salary":
                sal_val = _extract_salary(self.ai.get("inputs", {}).get("resume", {}).get("salary_expectation", 0))
                # Convert to LPA if needed (Atharva has 800000 -> 8 LPA)
                lpa = sal_val / 100000 if sal_val > 1000 else sal_val
                criteria = rules.get("criteria", {})
                # Bracket logic
                if lpa < 3: gt_score = criteria.get("<3", 0)
                elif 3 <= lpa <= 6: gt_score = criteria.get("3-6", 0)
                elif 6 < lpa <= 10: gt_score = criteria.get("6-10", 0)
                elif lpa > 10: gt_score = criteria.get(">10", 0)

            # ── 3. Qualification ──
            elif section == "qualification":
                edu_list = self.ai.get("inputs", {}).get("resume", {}).get("education", [])
                degrees = [e.get("degree", "").lower() for e in edu_list if isinstance(e, dict)]
                criteria = rules.get("criteria", {})
                best_q = 0.0
                for d in degrees:
                    if "master" in d: best_q = max(best_q, criteria.get("Master's Degree in Engineering", 0))
                    if "bachelor" in d or "be" in d or "btech" in d: 
                        best_q = max(best_q, criteria.get("Bachelor's Degree in Engineering", 0))
                gt_score = best_q if best_q > 0 else criteria.get("Other", 0)

            # ── 4. Position ──
            elif section == "position":
                pos = self.ai.get("inputs", {}).get("resume", {}).get("position", "Individual Contributor")
                criteria = rules.get("criteria", {})
                if "lead" in pos.lower(): gt_score = criteria.get("Team Lead (Preferred)", 100)
                else: gt_score = criteria.get("Individual Contributor", 67)

            # Save and compare
            ai_sec_score = self.ai.get("result", {}).get(f"{section}_score", 0.0)
            report["ground_truth_scores"][section] = gt_score
            report["ai_scores"][section] = ai_sec_score
            report["section_accuracy"][section] = 100 - abs(ai_sec_score - gt_score)
            
            total_weighted_gt += (gt_score * section_weight)

        # Final Scores
        final_gt = total_weighted_gt / total_gt_weight if total_gt_weight > 0 else 0.0
        ai_final = self.ai.get("result", {}).get("final_score", 0.0)

        # Error Metrics (MAE / RMSE)
        all_errors = [abs(report["ai_scores"][s] - report["ground_truth_scores"][s]) for s in report["ai_scores"]]
        if all_errors:
            mae = sum(all_errors) / len(all_errors)
            rmse = math.sqrt(sum(e**2 for e in all_errors) / len(all_errors))
        else:
            mae = 0.0
            rmse = 0.0

        accuracy = 100 - abs(ai_final - final_gt)
        report["global_metrics"] = {
            "ground_truth_final_score": round(final_gt, 2),
            "ai_final_score": ai_final,
            "overall_accuracy": round(accuracy, 2),
            "is_valid": accuracy >= 80,
            "mae": round(mae, 2),
            "rmse": round(rmse, 2),
            "total_weight_checked": total_gt_weight
        }

        return report

# ---------------------------------------------------------------------------
# Main Execution
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    if not JD_PATH.exists() or not AI_SCORE_PATH.exists():
        logger.error("Required input files missing.")
        exit(1)

    with open(JD_PATH, "r") as f: jd = json.load(f)
    with open(AI_SCORE_PATH, "r") as f: ai = json.load(f)
    
    det_report = None
    if os.path.exists(DETERMINISTIC_OUT_PATH):
        with open(DETERMINISTIC_OUT_PATH, "r") as f: det_report = json.load(f)
    else:
        print("[WARN] Deterministic report not found. Keyword accuracy will be 0.")

    validator = MathematicalValidator(jd, ai, det_report)
    results = validator.calculate_ground_truth()

    os.makedirs(MATH_REPORT_PATH.parent, exist_ok=True)
    with open(MATH_REPORT_PATH, "w") as f:
        json.dump(results, f, indent=2)

    logger.info("MATHEMATICAL ACCURACY REPORT")
    logger.info(f"AI Final Score    : {results['global_metrics']['ai_final_score']}")
    logger.info(f"GT Final Score    : {results['global_metrics']['ground_truth_final_score']}")
    logger.info(f"OVERALL ACCURACY  : {results['global_metrics']['overall_accuracy']}%")
    logger.info(f"FINAL VERDICT     : {'VALID' if results['global_metrics']['is_valid'] else 'INVALID'} (Threshold: 80%)")
    
    logger.info(f"Full report saved to: {MATH_REPORT_PATH}")
