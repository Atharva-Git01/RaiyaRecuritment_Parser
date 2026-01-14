# app/schemas.py
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, conlist
from datetime import datetime

# ==========================================
# 1. Deterministic Input Schemas (Facts)
# ==========================================

class Role(BaseModel):
    title: str
    company: str
    duration_months: float
    is_relevant: bool = True

class Education(BaseModel):
    degree: str
    institution: str
    year: str

class MatchDetails(BaseModel):
    matched_skills: List[str]
    missing_skills: List[str]
    experience_gap_years: float = 0.0
    score: float

class CandidateFacts(BaseModel):
    """
    Strictly deterministic facts extracted from the resume.
    Phi-4 treats this as Ground Truth.
    """
    id: str  # Job ID or UUID
    skills: List[str]
    total_experience_years: float
    relevant_experience_years: float
    roles: List[Role]
    education: List[Education]
    match_details: MatchDetails
    flags: List[str] = []  # e.g., ["gap_detected", "short_tenure"]

class JDRequirements(BaseModel):
    """
    Context from the Job Description.
    """
    jd_id: str
    title: str
    must_have_skills: List[str]
    nice_to_have_skills: List[str]
    min_experience_years: float

class SystemContext(BaseModel):
    """
    Combined context sent to Phi-4.
    """
    facts: CandidateFacts
    requirements: JDRequirements
    constraints: List[str] = [
        "Do not calculate scores",
        "Do not infer missing skills",
        "Explain only based on provided facts"
    ]

# ==========================================
# 2. Phi-4 Reasoning Output Schema (AI)
# ==========================================

class Phi4Explanation(BaseModel):
    """
    Structured output from Phi-4.
    """
    summary: str = Field(..., description="Concise 3-sentence summary for recruiter")
    strengths: List[str] = Field(..., max_items=5)
    weaknesses: List[str] = Field(..., max_items=5)
    red_flags: List[str] = Field(default_factory=list, description="Potential inconsistencies detected by AI")
    sentiment: str = Field(..., pattern="^(strong_fit|potential_fit|weak_fit|reject)$")
    reasoning: str = Field(..., description="Internal chain-of-thought, not for display")

# ==========================================
# 3. Learning Ledger Schema
# ==========================================

class LearningEvent(BaseModel):
    """
    Entry for the Learning Ledger DB.
    """
    ledger_id: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)
    prompt_version: str
    job_id: str
    input_hash: str
    context: Optional[Dict[str, Any]] = None
    phi4_response: Dict[str, Any]
    validation_status: str  # PASS / FAIL
    error_tags: List[str] = [] # e.g. ["hallucination", "exaggeration"]
    human_feedback: Optional[bool] = None
