"""
RAIYA Resume Extraction Schema — Maps resume_pdf_extraction_schema.json.
Source: reference_json_schema/resume_pdf_extraction_schema.json
"""

from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List


class PipelineMetadata(BaseModel):
    resume_content_hash: str            # sha256: of extracted JSON
    created_at: Optional[str] = None
    source: Optional[str] = None


class ExperienceEntry(BaseModel):
    title: str
    company: str
    start: Optional[str] = None
    end: Optional[str] = None
    description: Optional[str] = None
    responsibilities: List[str] = []


class ProjectEntry(BaseModel):
    name: str
    description: Optional[str] = None
    technologies: List[str] = []


class EducationEntry(BaseModel):
    degree: str
    institution: str
    start_year: Optional[str] = None
    end_year: Optional[str] = None
    field_of_study: Optional[str] = None
    cgpa: Optional[str] = None
    institute_location: Optional[str] = None


class SalaryExpectation(BaseModel):
    value: Optional[str] = None
    currency: Optional[str] = None


class ResumeExtractionSchema(BaseModel):
    """Canonical resume extraction output schema."""
    pipeline_metadata: PipelineMetadata
    name: str = Field(..., min_length=1)
    email: Optional[EmailStr] = None
    skills: List[str] = []
    experience: List[ExperienceEntry] = []
    projects: List[ProjectEntry] = []
    education: List[EducationEntry] = []
    candidate_achievements: List[str] = []
    certifications: List[str] = []
    tools: List[str] = []
    technologies: List[str] = []
    salary_expectation: Optional[SalaryExpectation] = None

    class Config:
        from_attributes = True
