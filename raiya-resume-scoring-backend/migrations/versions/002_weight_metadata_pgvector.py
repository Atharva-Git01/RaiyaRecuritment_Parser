"""002 Add weight metadata and pgvector evidence tables.

Revision ID: 002
Revises: 001
Create Date: 2026-05-14

Adds:
  - weight_generation_metadata column to job_descriptions
  - weight_strategy column for audit traceability
  - RAG evidence embeddings index for pgvector
  - Scoring trace columns to match_results
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── job_descriptions — weight metadata columns ───────────────
    op.add_column("job_descriptions",
        sa.Column("weight_strategy", sa.String(80), server_default="criteria_average_normalized"))
    op.add_column("job_descriptions",
        sa.Column("weight_generation_metadata", JSONB, nullable=True))
    op.add_column("job_descriptions",
        sa.Column("normalization_factor", sa.Float, nullable=True))
    op.add_column("job_descriptions",
        sa.Column("total_raw_weight", sa.Float, nullable=True))

    # ── match_results — scoring trace columns ────────────────────
    op.add_column("match_results",
        sa.Column("scoring_trace", JSONB, nullable=True))
    op.add_column("match_results",
        sa.Column("weight_strategy_used", sa.String(80), nullable=True))

    # ── rag_evidence_embeddings — add section-level index ────────
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_rag_evidence_section
        ON rag_evidence_embeddings (evidence_id, section_name)
    """)

    # ── Ensure pgvector cosine index exists (idempotent) ─────────
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_rag_evidence_cosine
        ON rag_evidence_embeddings
        USING ivfflat (embedding vector_cosine_ops)
        WITH (lists = 100)
    """)

    # ── Add weight_generation_log table ──────────────────────────
    op.create_table("weight_generation_log",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("jd_id", UUID(as_uuid=True), sa.ForeignKey("job_descriptions.id", ondelete="CASCADE")),
        sa.Column("strategy", sa.String(80), nullable=False),
        sa.Column("raw_weights", JSONB),
        sa.Column("normalized_weights", JSONB),
        sa.Column("normalization_factor", sa.Float),
        sa.Column("section_criteria", JSONB),
        sa.Column("validation_passed", sa.Boolean, server_default="false"),
        sa.Column("validation_errors", JSONB),
        sa.Column("llm_model", sa.String(100)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
    )
    op.create_index("idx_wgl_jd", "weight_generation_log", ["jd_id"])


def downgrade() -> None:
    op.drop_table("weight_generation_log")
    op.execute("DROP INDEX IF EXISTS idx_rag_evidence_cosine")
    op.execute("DROP INDEX IF EXISTS idx_rag_evidence_section")
    op.drop_column("match_results", "weight_strategy_used")
    op.drop_column("match_results", "scoring_trace")
    op.drop_column("job_descriptions", "total_raw_weight")
    op.drop_column("job_descriptions", "normalization_factor")
    op.drop_column("job_descriptions", "weight_generation_metadata")
    op.drop_column("job_descriptions", "weight_strategy")
