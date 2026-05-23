"""
RAIYA ORM Models — Resume (file_id PK, no raw_text, no candidate_name/email columns, no org_id)
                    and JobDescription.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, String, Float, Integer, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from app.db.database import Base


class Resume(Base):
    """
    Resume table. 
    CRITICAL: PK is file_id (NOT id).
    No raw_text — Nanonets returns structured JSON directly.
    No candidate_name or candidate_email — read from parsed_json at query time.
    No org_id — access via batch → jd → org join.
    """
    __tablename__ = "resumes"

    file_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    batch_id = Column(UUID(as_uuid=True), nullable=True)
    file_name = Column(String(500), nullable=True)
    file_hash = Column(String(80), nullable=False)       # sha256: of file bytes
    content_hash = Column(String(80), nullable=False)     # sha256: of extracted JSON
    parsed_json = Column(JSONB, nullable=True)            # resume_pdf_extraction_schema output
    extraction_hash = Column(String(80), nullable=True)
    ocr_confidence = Column(Float, nullable=True)
    status = Column(String(30), default="uploaded")       # uploaded|processing|completed|failed
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # Relationships
    match_results = relationship("MatchResult", back_populates="resume", foreign_keys="MatchResult.resume_file_id")

    @property
    def candidate_name(self) -> str:
        """Read candidate name from parsed_json."""
        if self.parsed_json and isinstance(self.parsed_json, dict):
            return self.parsed_json.get("name", "Unknown")
        return "Unknown"

    @property
    def candidate_email(self) -> str:
        """Read candidate email from parsed_json."""
        if self.parsed_json and isinstance(self.parsed_json, dict):
            return self.parsed_json.get("email", "")
        return ""


class JobDescription(Base):
    __tablename__ = "job_descriptions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=True)
    uploaded_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    file_name = Column(String(500), nullable=True)
    file_hash = Column(String(80), nullable=False)
    content_hash = Column(String(80), nullable=False)
    # jd_pdf_extraction_schema output (no raw_text)
    extracted_json = Column(JSONB, nullable=True)
    extraction_hash = Column(String(80), nullable=True)
    ocr_confidence = Column(Float, nullable=True)
    # jd_weights_schema_format output (includes weight_generation_metadata)
    normalized_json = Column(JSONB, nullable=True)
    normalized_hash = Column(String(80), nullable=True)
    weights_json = Column(JSONB, nullable=True)
    weights_hash_pre_hitl = Column(String(80), nullable=True)
    weights_hash = Column(String(80), nullable=True)
    weight_strategy = Column(String(80), default="criteria_average_normalized")
    weight_generation_metadata = Column(JSONB, nullable=True)
    normalization_factor = Column(Float, nullable=True)
    total_raw_weight = Column(Float, nullable=True)
    hitl_verified = Column(Boolean, default=False)
    hitl_verified_at = Column(DateTime(timezone=True), nullable=True)
    hitl_verified_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    version = Column(Integer, default=1)
    status = Column(String(30), default="uploaded")  # uploaded|extracting|weights_assigned|hitl_pending|verified|active
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # Relationships
    organization = relationship("Organization", back_populates="job_descriptions")
    batches = relationship("Batch", back_populates="job_description")
