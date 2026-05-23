"""001 Initial Schema — All RAIYA tables.

Revision ID: 001
Create Date: 2026-05-14
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Enable extensions
    op.execute("CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\"")
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # Organizations
    op.create_table("organizations",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("org_code", sa.String(50), unique=True, nullable=False),
        sa.Column("plan", sa.String(50), server_default="free"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
    )

    # Users
    op.create_table("users",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("org_id", UUID(as_uuid=True), sa.ForeignKey("organizations.id", ondelete="CASCADE")),
        sa.Column("full_name", sa.String(255), nullable=False),
        sa.Column("email", sa.String(255), unique=True, nullable=False),
        sa.Column("phone", sa.String(20)), sa.Column("address", sa.Text),
        sa.Column("role", sa.String(20), server_default="recruiter"),
        sa.Column("hashed_password", sa.String(255)),
        sa.Column("oauth_provider", sa.String(50)), sa.Column("oauth_sub", sa.String(255)),
        sa.Column("phone_verified", sa.Boolean, server_default="false"),
        sa.Column("email_verified", sa.Boolean, server_default="false"),
        sa.Column("is_active", sa.Boolean, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
    )
    op.create_index("idx_users_org", "users", ["org_id"])

    # OTP tokens
    op.create_table("otp_tokens",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE")),
        sa.Column("channel", sa.String(10), nullable=False),
        sa.Column("otp_hash", sa.String(255), nullable=False),
        sa.Column("purpose", sa.String(50), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used", sa.Boolean, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
    )

    # Job Descriptions
    op.create_table("job_descriptions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("org_id", UUID(as_uuid=True), sa.ForeignKey("organizations.id")),
        sa.Column("uploaded_by", UUID(as_uuid=True), sa.ForeignKey("users.id")),
        sa.Column("file_name", sa.String(500)),
        sa.Column("file_hash", sa.String(80), nullable=False),
        sa.Column("content_hash", sa.String(80), nullable=False),
        sa.Column("extracted_json", JSONB), sa.Column("extraction_hash", sa.String(80)),
        sa.Column("ocr_confidence", sa.Float),
        sa.Column("normalized_json", JSONB), sa.Column("normalized_hash", sa.String(80)),
        sa.Column("weights_json", JSONB),
        sa.Column("weights_hash_pre_hitl", sa.String(80)),
        sa.Column("weights_hash", sa.String(80)),
        sa.Column("hitl_verified", sa.Boolean, server_default="false"),
        sa.Column("hitl_verified_at", sa.DateTime(timezone=True)),
        sa.Column("hitl_verified_by", UUID(as_uuid=True), sa.ForeignKey("users.id")),
        sa.Column("version", sa.Integer, server_default="1"),
        sa.Column("status", sa.String(30), server_default="uploaded"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
    )
    op.create_index("idx_jd_org", "job_descriptions", ["org_id"])
    op.create_index("idx_jd_file_hash", "job_descriptions", ["file_hash"])

    # Resumes
    op.create_table("resumes",
        sa.Column("file_id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("batch_id", UUID(as_uuid=True)),
        sa.Column("file_name", sa.String(500)),
        sa.Column("file_hash", sa.String(80), nullable=False),
        sa.Column("content_hash", sa.String(80), nullable=False),
        sa.Column("parsed_json", JSONB), sa.Column("extraction_hash", sa.String(80)),
        sa.Column("ocr_confidence", sa.Float),
        sa.Column("status", sa.String(30), server_default="uploaded"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
    )
    op.create_index("idx_resume_file_hash", "resumes", ["file_hash"])
    op.create_index("idx_resume_batch", "resumes", ["batch_id"])

    # Batches
    op.create_table("batches",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("org_id", UUID(as_uuid=True), sa.ForeignKey("organizations.id")),
        sa.Column("jd_id", UUID(as_uuid=True), sa.ForeignKey("job_descriptions.id")),
        sa.Column("created_by", UUID(as_uuid=True), sa.ForeignKey("users.id")),
        sa.Column("name", sa.String(255)),
        sa.Column("total_resumes", sa.Integer, server_default="0"),
        sa.Column("completed", sa.Integer, server_default="0"),
        sa.Column("failed", sa.Integer, server_default="0"),
        sa.Column("status", sa.String(30), server_default="queued"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
    )

    # Match Results
    op.create_table("match_results",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("batch_id", UUID(as_uuid=True), sa.ForeignKey("batches.id")),
        sa.Column("resume_file_id", UUID(as_uuid=True), sa.ForeignKey("resumes.file_id")),
        sa.Column("jd_id", UUID(as_uuid=True), sa.ForeignKey("job_descriptions.id")),
        sa.Column("output_hash", sa.String(80)),
        sa.Column("final_result_json", JSONB), sa.Column("final_score", sa.Float),
        sa.Column("deterministic_report", JSONB), sa.Column("mathematical_report", JSONB),
        sa.Column("rule_based_evidence", JSONB), sa.Column("rag_final_verdict", JSONB),
        sa.Column("reasoning_labels", JSONB), sa.Column("reasoning_context", sa.Text),
        sa.Column("reasoning_hash", sa.String(80)),
        sa.Column("llm_explanation", sa.Text), sa.Column("explanation_hash", sa.String(80)),
        sa.Column("guardrails_applied", JSONB),
        sa.Column("recommendation", sa.String(30)),
        sa.Column("is_valid", sa.Boolean, server_default="false"),
        sa.Column("hallucinations_detected", sa.Boolean, server_default="false"),
        sa.Column("is_confident", sa.Boolean, server_default="false"),
        sa.Column("math_accuracy", sa.Float), sa.Column("mae", sa.Float),
        sa.Column("rank", sa.Integer), sa.Column("percentile", sa.Float),
        sa.Column("cache_hit", sa.Boolean, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
    )
    op.create_index("idx_result_batch", "match_results", ["batch_id"])
    op.create_index("idx_result_score", "match_results", ["batch_id", "final_score"])

    # Reasoning Log
    op.create_table("reasoning_log",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("batch_id", UUID(as_uuid=True), sa.ForeignKey("batches.id")),
        sa.Column("resume_file_id", UUID(as_uuid=True), sa.ForeignKey("resumes.file_id")),
        sa.Column("jd_id", UUID(as_uuid=True), sa.ForeignKey("job_descriptions.id")),
        sa.Column("structural_facts", JSONB), sa.Column("evidence_map", JSONB),
        sa.Column("reasoning_labels", JSONB), sa.Column("verification_report", JSONB),
        sa.Column("reasoning_context", sa.Text),
        sa.Column("phases_completed", sa.Integer, server_default="5"),
        sa.Column("corrections_applied", sa.Integer, server_default="0"),
        sa.Column("cache_hit", sa.Boolean, server_default="false"),
        sa.Column("reasoning_hash", sa.String(80)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
    )

    # Hash Chain Log
    op.create_table("hash_chain_log",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("session_id", sa.String(80)), sa.Column("stage", sa.String(80)),
        sa.Column("artifact_type", sa.String(80)), sa.Column("artifact_id", sa.String(255)),
        sa.Column("content_hash", sa.String(80)),
        sa.Column("chain_hash", sa.String(80), nullable=False),
        sa.Column("previous_chain_hash", sa.String(80)),
        sa.Column("actor", sa.String(20), server_default="system"),
        sa.Column("metadata", JSONB),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
    )
    op.create_index("idx_chain_session", "hash_chain_log", ["session_id"])

    # Token Usage Log
    op.create_table("token_usage_log",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("batch_id", UUID(as_uuid=True)), sa.Column("resume_file_id", UUID(as_uuid=True)),
        sa.Column("model", sa.String(100)),
        sa.Column("prompt_tokens", sa.Integer), sa.Column("completion_tokens", sa.Integer),
        sa.Column("total_tokens", sa.Integer),
        sa.Column("est_cost_usd", sa.Numeric(10, 6)),
        sa.Column("pipeline_stage", sa.String(80)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
    )

    # pgvector embedding tables
    op.execute("""
        CREATE TABLE resume_embeddings (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            resume_file_id UUID REFERENCES resumes(file_id) ON DELETE CASCADE,
            chunk_index INTEGER NOT NULL, dimension VARCHAR(50) NOT NULL,
            chunk_text TEXT NOT NULL, embedding vector(768) NOT NULL,
            chunk_hash VARCHAR(80) NOT NULL, metadata JSONB,
            created_at TIMESTAMPTZ DEFAULT NOW()
        )
    """)
    op.execute("CREATE INDEX ON resume_embeddings USING ivfflat (embedding vector_cosine_ops) WITH (lists=100)")
    op.execute("CREATE INDEX idx_re_file_dim ON resume_embeddings(resume_file_id, dimension)")

    op.execute("""
        CREATE TABLE jd_embeddings (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            jd_id UUID REFERENCES job_descriptions(id) ON DELETE CASCADE,
            chunk_index INTEGER NOT NULL, dimension VARCHAR(50) NOT NULL,
            chunk_text TEXT NOT NULL, embedding vector(768) NOT NULL,
            chunk_hash VARCHAR(80) NOT NULL, metadata JSONB,
            created_at TIMESTAMPTZ DEFAULT NOW()
        )
    """)
    op.execute("CREATE INDEX ON jd_embeddings USING ivfflat (embedding vector_cosine_ops) WITH (lists=100)")

    op.execute("""
        CREATE TABLE rag_evidence_embeddings (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            evidence_id VARCHAR(120) NOT NULL,
            source_type VARCHAR(50) NOT NULL,
            section_name VARCHAR(80) NOT NULL,
            chunk_text TEXT NOT NULL, embedding vector(768) NOT NULL,
            chunk_hash VARCHAR(80) NOT NULL, metadata JSONB,
            created_at TIMESTAMPTZ DEFAULT NOW()
        )
    """)
    op.execute("CREATE INDEX ON rag_evidence_embeddings USING ivfflat (embedding vector_cosine_ops) WITH (lists=100)")


def downgrade() -> None:
    op.drop_table("rag_evidence_embeddings")
    op.drop_table("jd_embeddings")
    op.drop_table("resume_embeddings")
    op.drop_table("token_usage_log")
    op.drop_table("hash_chain_log")
    op.drop_table("reasoning_log")
    op.drop_table("match_results")
    op.drop_table("batches")
    op.drop_table("resumes")
    op.drop_table("job_descriptions")
    op.drop_table("otp_tokens")
    op.drop_table("users")
    op.drop_table("organizations")
