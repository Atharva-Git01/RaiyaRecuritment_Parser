from pydantic import BaseModel
from typing import Dict, Any, Optional

class ScoringWeights(BaseModel):
    skills_score: float = 1.0
    experience_score: float = 1.0
    relevant_experience_score: float = 1.0
    projects_score: float = 1.0
    certificates_score: float = 1.0
    tools_score: float = 1.0
    technologies_score: float = 1.0
    qualification_score: float = 1.0
    responsibilities_score: float = 1.0
    salary_score: float = 1.0
    position_score: float = 0.0   # JD defines Team Lead vs IC scoring weight
    
    class Config:
        extra = "ignore"

class ResumeFacts(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    skills: Optional[list] = None
    experience: Optional[list] = None
    projects: Optional[list] = None
    education: Optional[list] = None
    certifications: Optional[list] = None
    tools: Optional[list] = None
    technologies: Optional[list] = None
    salary_expectation: Optional[dict] = None
    
    class Config:
        extra = "allow"

class JDRequirements(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    requirements: Optional[list] = None
    weights: Optional[Dict[str, float]] = None
    
    class Config:
        extra = "allow"

class AIScorerInput(BaseModel):
    resume: ResumeFacts
    jd: JDRequirements
    weights: Optional[ScoringWeights] = None
