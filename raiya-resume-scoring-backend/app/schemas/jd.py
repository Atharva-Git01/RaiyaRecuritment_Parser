"""
RAIYA JD Extraction Schema — Maps jd_pdf_extraction_schema.json.
Source: reference_json_schema/jd_pdf_extraction_schema.json
"""

from pydantic import BaseModel, Field
from typing import Optional, List


class PipelineMetadataJD(BaseModel):
    jd_content_hash: str               # sha256: of extracted JSON
    created_at: Optional[str] = None
    source: Optional[str] = None


class PositionLevel(BaseModel):
    senior_level: bool = False
    mid_level: bool = False
    entry_level: bool = False


class WorkMode(BaseModel):
    remote_option: bool = False
    work_from_office: bool = False
    hybrid: bool = False


class JobInformation(BaseModel):
    job_title: str
    position: Optional[PositionLevel] = None
    employment_type: Optional[str] = None   # full-time|part-time|contract|internship|temporary|other
    location: Optional[str] = None
    work_mode: Optional[WorkMode] = None


class ExperienceRange(BaseModel):
    less_than_3_years: Optional[bool] = Field(None, alias="<3_years")
    three_4_years: Optional[bool] = Field(None, alias="3_4_years")
    five_7_years: Optional[bool] = Field(None, alias="5_7_years")
    eight_plus_years: Optional[bool] = Field(None, alias="8_plus_years")

    class Config:
        populate_by_name = True


class ExperienceRequirements(BaseModel):
    experience_range: Optional[ExperienceRange] = None
    minimum_years: Optional[float] = None
    preferred_years: Optional[float] = None


class QualificationLevel(BaseModel):
    phd: bool = False
    masters: bool = False
    bachelors: bool = False
    associate: bool = False
    diploma: bool = False
    certification: bool = False


class EducationRequirements(BaseModel):
    qualification: Optional[QualificationLevel] = None
    preferred_field_of_study: List[str] = []


class SkillsAndTechnologies(BaseModel):
    technologies: List[str] = []
    skills: List[str] = []
    tools: List[str] = []
    certifications: List[str] = []


class JobDetails(BaseModel):
    job_description: Optional[str] = None
    responsibilities: List[str] = []
    requirements: List[str] = []
    preferred_qualifications: List[str] = []


class JDExtractionSchema(BaseModel):
    """Canonical JD extraction output schema."""
    pipeline_metadata: PipelineMetadataJD
    job_information: JobInformation
    experience_requirements: Optional[ExperienceRequirements] = None
    education_requirements: Optional[EducationRequirements] = None
    skills_and_technologies: Optional[SkillsAndTechnologies] = None
    job_details: Optional[JobDetails] = None

    class Config:
        from_attributes = True
