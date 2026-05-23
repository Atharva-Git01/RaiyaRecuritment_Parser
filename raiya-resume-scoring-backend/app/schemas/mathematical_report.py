"""
RAIYA Mathematical Validator Report Schema — Maps mathematical_validator_report_schema.json.
Updated: importance_weighted_mae + jd_weights_math_valid cross-reference.
"""

from pydantic import BaseModel, Field
from typing import Dict


class GlobalMetrics(BaseModel):
    ground_truth_final_score: float
    ai_final_score: float
    # max(0, 100 − flat_mae). Passes when ≥ 80.
    overall_accuracy: float
    is_valid: bool                           # overall_accuracy >= 80
    mae: float                               # flat |ai_total − gt_total|
    # Σ(importance_factor × |ai − gt|) / Σ(importance_factor); falls back to flat MAE
    importance_weighted_mae: float = 0.0
    rmse: float
    total_weight_checked: float
    # Cross-reference: jd_weights.weighting_metadata.mathematical_validation.is_valid
    jd_weights_math_valid: bool = True


class MathematicalValidatorReport(BaseModel):
    """Canonical mathematical validator report schema (enterprise-aware)."""
    # section → accuracy % comparing AI (hybrid × weight) vs ground truth (label_weighted_coverage × weight)
    section_accuracy: Dict[str, float] = Field(default_factory=dict)
    # section → deterministic ground truth score = label_weighted_coverage × weight / 100
    ground_truth_scores: Dict[str, float] = Field(default_factory=dict)
    # section → AI-generated score = hybrid_score × weight
    ai_scores: Dict[str, float] = Field(default_factory=dict)
    global_metrics: GlobalMetrics
