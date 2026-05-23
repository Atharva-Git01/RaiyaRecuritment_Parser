"""
RAIYA ORM Models — Batch and MatchResult.
MatchResult stores all 9 canonical schema outputs as JSONB.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, String, Float, Integer, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from app.db.database import Base


class Batch(Base):
    __tablename__ = "batches"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=True)
    jd_id = Column(UUID(as_uuid=True), ForeignKey("job_descriptions.id"), nullable=True)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    name = Column(String(255), nullable=True)
    total_resumes = Column(Integer, default=0)
    completed = Column(Integer, default=0)
    failed = Column(Integer, default=0)
    status = Column(String(30), default="queued")  # queued|processing|completed|failed|partial
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    completed_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    organization = relationship("Organization", back_populates="batches")
    job_description = relationship("JobDescription", back_populates="batches")
    match_results = relationship("MatchResult", back_populates="batch", cascade="all, delete-orphan")


class MatchResult(Base):
    """Stores all pipeline output schemas for a single resume-JD match."""
    __tablename__ = "match_results"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    batch_id = Column(UUID(as_uuid=True), ForeignKey("batches.id"), nullable=True)
    resume_file_id = Column(UUID(as_uuid=True), ForeignKey("resumes.file_id"), nullable=True)
    jd_id = Column(UUID(as_uuid=True), ForeignKey("job_descriptions.id"), nullable=True)
    output_hash = Column(String(80), nullable=True)

    # final_result_scoring_agent_schema
    final_result_json = Column(JSONB, nullable=True)
    final_score = Column(Float, nullable=True)

    # deterministic_validator_output_schema
    deterministic_report = Column(JSONB, nullable=True)

    # mathematical_validator_report_schema
    mathematical_report = Column(JSONB, nullable=True)

    # rule_based_evidence_schema
    rule_based_evidence = Column(JSONB, nullable=True)

    # final_validation_report_schema
    rag_final_verdict = Column(JSONB, nullable=True)

    # Reasoning engine outputs
    reasoning_labels = Column(JSONB, nullable=True)
    reasoning_context = Column(Text, nullable=True)
    reasoning_hash = Column(String(80), nullable=True)

    # LLM explanation
    llm_explanation = Column(Text, nullable=True)
    explanation_hash = Column(String(80), nullable=True)

    # Guardrails metadata
    guardrails_applied = Column(JSONB, nullable=True)

    # Verdicts
    recommendation = Column(String(30), nullable=True)
    is_valid = Column(Boolean, default=False)
    hallucinations_detected = Column(Boolean, default=False)
    is_confident = Column(Boolean, default=False)
    math_accuracy = Column(Float, nullable=True)
    mae = Column(Float, nullable=True)

    # Ranking
    rank = Column(Integer, nullable=True)
    percentile = Column(Float, nullable=True)
    cache_hit = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # Relationships
    batch = relationship("Batch", back_populates="match_results")
    resume = relationship("Resume", back_populates="match_results", foreign_keys=[resume_file_id])
