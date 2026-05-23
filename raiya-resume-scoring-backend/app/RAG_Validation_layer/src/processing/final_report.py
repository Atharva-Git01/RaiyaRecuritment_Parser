"""
Final Validation Report Consolidation
=====================================
Consolidates the results from:
  1. deterministic_validator_output.json (JD vs Resume Semantic check)
  2. mathematical_validator_report.json  (AI Score vs Ground Truth Accuracy)

It generates a single 'final_verdict' and detailed 'notes' if any validator fails.
"""

import json
import os
from typing import Any, Dict

from src.config import settings
from src.logging_config import logger

# ---------------------------------------------------------------------------
# Paths from settings
# ---------------------------------------------------------------------------
DET_OUT_PATH = settings.DET_OUT_PATH
MATH_OUT_PATH = settings.MATH_OUT_PATH
FINAL_OUT_PATH = settings.FINAL_OUT_PATH

def generate_final_report():
    # 1. Load inputs
    if not DET_OUT_PATH.exists():
        logger.error(f"Deterministic report not found: {DET_OUT_PATH}")
        return
    if not MATH_OUT_PATH.exists():
        logger.error(f"Mathematical report not found: {MATH_OUT_PATH}")
        return

    with open(DET_OUT_PATH, "r", encoding="utf-8") as f:
        det_report = json.load(f)
    with open(MATH_OUT_PATH, "r", encoding="utf-8") as f:
        math_report = json.load(f)

    # 2. Extract verdicts
    # Note: deterministic_validator_output.json uses "is_valid" at the top level.
    # mathematical_validator_report.json uses "global_metrics.is_valid".
    
    det_valid = det_report.get("is_valid", False)
    math_valid = math_report.get("global_metrics", {}).get("is_valid", False)
    
    final_verdict = det_valid and math_valid
    
    # 3. Generate notes if false
    notes = []
    if not final_verdict:
        if not det_valid:
            notes.append("Deterministic Validation Failed (JD vs Resume Semantic Inconsistency).")
            # Pull specific hallucinations if they exist in section results
            for sec, res in det_report.get("section_results", {}).items():
                if not res.get("valid"):
                    for err in res.get("errors", []):
                        notes.append(f"  - [{sec}]: {err}")
        
        if not math_valid:
            accuracy = math_report.get("global_metrics", {}).get("overall_accuracy", 0.0)
            notes.append(f"Mathematical Validation Failed. Accuracy ({accuracy}%) is below the 80% threshold.")

    # 4. Construct final summary
    final_report = {
        "final_verdict": final_verdict,
        "notes": "\n".join(notes) if notes else "All validation checks passed successfully.",
        "component_verdicts": {
            "deterministic_validator": det_valid,
            "mathematical_validator": math_valid
        },
        "metrics_summary": {
             "accuracy": math_report.get("global_metrics", {}).get("overall_accuracy"),
             "mae": math_report.get("global_metrics", {}).get("mae")
        }
    }

    # 5. Save output
    os.makedirs(FINAL_OUT_PATH.parent, exist_ok=True)
    with open(FINAL_OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(final_report, f, indent=2, ensure_ascii=False)

    # 6. Logging Output
    logger.info("FINAL CONSOLIDATED VALIDATION REPORT")
    logger.info(f"FINAL VERDICT     : {'TRUE (VALID)' if final_verdict else 'FALSE (INVALID)'}")
    if notes:
        for note in notes:
            logger.info(f"Reason: {note}")
    
    logger.info(f"Final report saved to: {FINAL_OUT_PATH}")

if __name__ == "__main__":
    generate_final_report()
