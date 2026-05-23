"""
RAIYA ORM Model — InterviewInvitation.
Stores interview notification email records sent to HR.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from app.db.database import Base


class InterviewInvitation(Base):
    """
    Interview invitation email log.
    Each row represents a single notification email sent to the HR recruiter
    for a batch of top-ranked candidates.
    """
    __tablename__ = "interview_invitations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    batch_id = Column(UUID(as_uuid=True), ForeignKey("batches.id"), nullable=True)
    hr_email = Column(String(255), nullable=False)
    hr_name = Column(String(255), nullable=True)
    job_title = Column(String(500), nullable=True)
    candidates_count = Column(Integer, default=0)
    email_subject = Column(String(500), nullable=True)
    status = Column(String(30), default="queued")  # queued|sent|failed
    smtp_response = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0)
    # Snapshot of candidates included in the email
    candidates_json = Column(JSONB, nullable=True)
    sent_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # Relationships
    batch = relationship("Batch", backref="interview_invitations")
