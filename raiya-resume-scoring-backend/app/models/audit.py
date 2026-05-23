"""
RAIYA ORM Models — Audit tables: HashChainLog, TokenUsageLog, ReasoningLog.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, String, Float, Integer, Boolean, DateTime, ForeignKey, Text, BigInteger, Numeric
from sqlalchemy.dialects.postgresql import UUID, JSONB

from app.db.database import Base


class HashChainLog(Base):
    """Append-only hash chain for audit integrity."""
    __tablename__ = "hash_chain_log"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    session_id = Column(String(80), nullable=True)
    stage = Column(String(80), nullable=True)
    artifact_type = Column(String(80), nullable=True)
    artifact_id = Column(String(255), nullable=True)
    content_hash = Column(String(80), nullable=True)
    chain_hash = Column(String(80), nullable=False)
    previous_chain_hash = Column(String(80), nullable=True)
    actor = Column(String(20), default="system")
    metadata_json = Column("metadata", JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class TokenUsageLog(Base):
    """Token usage tracking for every LLM call."""
    __tablename__ = "token_usage_log"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    batch_id = Column(UUID(as_uuid=True), nullable=True)
    resume_file_id = Column(UUID(as_uuid=True), nullable=True)
    model = Column(String(100), nullable=True)
    prompt_tokens = Column(Integer, nullable=True)
    completion_tokens = Column(Integer, nullable=True)
    total_tokens = Column(Integer, nullable=True)
    est_cost_usd = Column(Numeric(10, 6), nullable=True)
    pipeline_stage = Column(String(80), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class ReasoningLog(Base):
    """Detailed reasoning engine log per resume-JD pair."""
    __tablename__ = "reasoning_log"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    batch_id = Column(UUID(as_uuid=True), ForeignKey("batches.id"), nullable=True)
    resume_file_id = Column(UUID(as_uuid=True), ForeignKey("resumes.file_id"), nullable=True)
    jd_id = Column(UUID(as_uuid=True), ForeignKey("job_descriptions.id"), nullable=True)
    structural_facts = Column(JSONB, nullable=True)
    evidence_map = Column(JSONB, nullable=True)
    reasoning_labels = Column(JSONB, nullable=True)
    verification_report = Column(JSONB, nullable=True)
    reasoning_context = Column(Text, nullable=True)
    phases_completed = Column(Integer, default=5)
    corrections_applied = Column(Integer, default=0)
    cache_hit = Column(Boolean, default=False)
    reasoning_hash = Column(String(80), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
