# Product/RAG - Evidence/mathematical_validator.py
from typing import Dict, Any

class MathematicalValidator:
    """
    Calculates the Ground Truth score mathematically based on deterministic evidence metrics.
    Compares the calculated truth against the AI's heuristic score to generate Accuracy % and MAE.
    """
    
    def __init__(self, jd_data: Dict[str, Any], ai_payload: Dict[str, Any], deterministic_report: Dict[str, Any]):
        self.jd_data = jd_data
        self.ai_payload = ai_payload
        self.deterministic_report = deterministic_report
        
    def _calculate_ground_truth_score(self) -> float:
        """
        Derives an algorithmic score mostly based on strict rule adherence metrics.
        Returns a score out of 100.
        """
        adherence = self.deterministic_report.get("rule_adherence", {})
        
        hard_met = adherence.get("hard_rules_met", 0)
        hard_total = adherence.get("total_hard_rules", 0)
        
        soft_met = adherence.get("soft_rules_met", 0)
        soft_total = adherence.get("total_soft_rules", 0)
        
        tools_found = len(adherence.get("required_tools_found", []))
        # We roughly estimate total tools required from JD text, or just cap it at a reasonable number if missing
        tools_weight = min(tools_found * 5, 20) # 20 points max for tools
        
        score = 0.0
        
        if hard_total > 0:
            # Hard rules account for 60% of the possible score
            score += (hard_met / hard_total) * 60
        else:
            score += 60 # Free points if JD doesn't specify hard rules
            
        if soft_total > 0:
            # Soft rules account for 40% (minus tool weight)
            score += (soft_met / soft_total) * (40 - tools_weight)
        else:
            score += (40 - tools_weight)
            
        score += tools_weight
        
        return round(min(max(score, 0.0), 100.0), 2)

    def calculate_ground_truth(self) -> Dict[str, Any]:
        """
        Calculates ground truth, returns Global Metrics (Accuracy, MAE) 
        and updates the final verdict.
        """
        ai_score = self.ai_payload.get("ai_score", {})
        
        # AI score might be nested depending on the agent structure
        if isinstance(ai_score, dict):
            # Attempt to find the overall score
            ai_numeric_score = float(ai_score.get("overall_score", ai_score.get("score", 0)))
        else:
            try:
                ai_numeric_score = float(ai_score)
            except (ValueError, TypeError):
                ai_numeric_score = 0.0
                
        calculated_truth = self._calculate_ground_truth_score()
        
        # Mean Absolute Error
        mae = abs(calculated_truth - ai_numeric_score)
        
        # Accuracy % (100 - MAE), bounded between 0 and 100
        accuracy = max(100.0 - mae, 0.0)
        
        return {
            "calculated_ground_truth": calculated_truth,
            "ai_score": ai_numeric_score,
            "global_metrics": {
                "mae": round(mae, 2),
                "accuracy": round(accuracy, 2)
            },
            "verdict": {
                "hallucinations_present": len(self.deterministic_report.get("hallucinations", [])) > 0,
                "is_confident": accuracy > 85.0 # If model prediction is within 15 points of ground truth, we trust it
            }
        }
