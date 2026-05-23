"""
Alembic Migration 003 — Interview Invitations + Pipeline Memory.

Creates:
  - interview_invitations table (email log for HR notifications)
  - pipeline_memory table (node execution tracking)
  - email_notification_status column on batches table
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

# revision identifiers
revision = "003_interview_memory"
down_revision = None  # Update to actual previous revision
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── interview_invitations table ──────────────────────────────
    op.create_table(
        "interview_invitations",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("batch_id", UUID(as_uuid=True), sa.ForeignKey("batches.id"), nullable=True),
        sa.Column("hr_email", sa.String(255), nullable=False),
        sa.Column("hr_name", sa.String(255), nullable=True),
        sa.Column("job_title", sa.String(500), nullable=True),
        sa.Column("candidates_count", sa.Integer(), default=0),
        sa.Column("email_subject", sa.String(500), nullable=True),
        sa.Column("status", sa.String(30), default="queued"),
        sa.Column("smtp_response", sa.Text(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("retry_count", sa.Integer(), default=0),
        sa.Column("candidates_json", JSONB(), nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_index(
        "ix_interview_invitations_batch_id",
        "interview_invitations",
        ["batch_id"],
    )

    # ── pipeline_memory table ────────────────────────────────────
    op.create_table(
        "pipeline_memory",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("session_id", sa.String(80), nullable=False, index=True),
        sa.Column("batch_id", sa.String(80), nullable=True, index=True),
        sa.Column("node_name", sa.String(100), nullable=False),
        sa.Column("status", sa.String(30), default="started"),
        sa.Column("state_snapshot", JSONB(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )

    # ── Add email notification status to batches ─────────────────
    op.add_column(
        "batches",
        sa.Column("email_notification_status", sa.String(30), default="pending"),
    )


def downgrade() -> None:
    op.drop_column("batches", "email_notification_status")
    op.drop_table("pipeline_memory")
    op.drop_index("ix_interview_invitations_batch_id", table_name="interview_invitations")
    op.drop_table("interview_invitations")
