from pydantic import BaseModel, Field, field_validator
from typing import List, Dict, Optional, Any

class ScoringWeights(BaseModel):
    skills_score: float = 0.30
    experience_score: float = 0.25
    relevant_experience_score: float = 0.10
    projects_score: float = 0.10
    certificates_score: float = 0.05
    tools_score: float = 0.05
    technologies_score: float = 0.05
    qualification_score: float = 0.05
    responsibilities_score: float = 0.03
    salary_score: float = 0.02
    
    @field_validator('*', mode='before')
    def set_default_if_none(cls, v):
        return v if v is not None else 0.0

class ResumeFacts(BaseModel):
    # Depending on what comes from "scoring_ready" (normalize_for_scoring output)
    # We'll allow arbitrary dict for now to be flexible, or define specific fields if known.
    # Given the "do not modify parsing/validation" constraint, we should probably wrap the dict 
    # but ensure it's structurally sound for what the AI needs.
    
    # Common expected fields in a resume for scoring:
    skills: List[str] = Field(default_factory=list)
    experience: List[Dict[str, Any]] = Field(default_factory=list)
    education: List[Dict[str, Any]] = Field(default_factory=list)
    projects: List[Dict[str, Any]] = Field(default_factory=list)
    certifications: List[str] = Field(default_factory=list)
    
    # Allow extra fields because the pipeline might pass more context
    class Config:
        extra = "allow"

class JDRequirements(BaseModel):
    job_title: str = Field(default="Unknown Role")
    skills_required: List[str] = Field(default_factory=list)
    experience_required: Optional[str] = None
    # Depending on JD structure, typically it has a 'weights' dict or we extract it.
    weights: Optional[Dict[str, float]] = None
    
    # Allow extra fields 
    class Config:
        extra = "allow"

class AIScorerInput(BaseModel):
    resume: ResumeFacts
    jd: JDRequirements
    weights: ScoringWeights
