"""
RAIYA Extracted Rules Schema — Maps extracted_rules_schema.json.
"""

from pydantic import BaseModel
from typing import List, Dict


class ExtractedSectionRule(BaseModel):
    weight: float
    min_score: float
    max_score: float
    allowed_scores: List[float]
    criteria: Dict[str, float]          # criterion label → score
    jd_items: List[str]
    required: bool
    description: str


# ExtractedRules is dynamic: dict[section_name, ExtractedSectionRule]
ExtractedRules = Dict[str, ExtractedSectionRule]
