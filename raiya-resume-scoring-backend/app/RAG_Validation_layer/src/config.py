"""
RAG Validation Layer — Configuration.
Uses pgvector (PostgreSQL 16) instead of Pinecone for all vector operations.
"""

import os
from pathlib import Path
from dotenv import load_dotenv
from pydantic_settings import BaseSettings

# Load environment variables
load_dotenv()


class Settings(BaseSettings):
    # API Keys (pgvector uses the main PostgreSQL connection — no separate API key)
    AZURE_OPENAI_API_KEY: str = os.getenv("AZURE_OPENAI_API_KEY", "")
    AZURE_OPENAI_ENDPOINT: str = os.getenv("AZURE_OPENAI_ENDPOINT", "")
    AZURE_OPENAI_DEPLOYMENT: str = os.getenv("AZURE_OPENAI_DEPLOYMENT", "mmresumeparser")

    # Database — pgvector (PostgreSQL 16)
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql+asyncpg://raiya:raiya_dev@localhost:5432/raiya",
    )
    SYNC_DATABASE_URL: str = os.getenv(
        "SYNC_DATABASE_URL",
        "postgresql://raiya:raiya_dev@localhost:5432/raiya",
    )

    # Paths
    BASE_DIR: Path = Path(__file__).parent.parent
    DATA_DIR: Path = BASE_DIR / "data"
    INPUT_DIR: Path = DATA_DIR / "inputs"
    OUTPUT_DIR: Path = DATA_DIR / "outputs"
    HISTORICAL_DIR: Path = DATA_DIR / "historical"

    # Default Input Files
    DEFAULT_JD_INPUT: Path = INPUT_DIR / "job_description.json"
    DEFAULT_AI_INPUT: Path = INPUT_DIR / "score_my_resume_20260211_151434.json"

    # Processed / Output Files
    VALIDATED_JD_PATH: Path = OUTPUT_DIR / "validated_jd.json"
    DET_OUT_PATH: Path = OUTPUT_DIR / "deterministic_validator_output.json"
    MATH_OUT_PATH: Path = OUTPUT_DIR / "mathematical_validator_report.json"
    RULE_EVD_OUT_PATH: Path = OUTPUT_DIR / "rule_based_evidence.json"
    FINAL_OUT_PATH: Path = OUTPUT_DIR / "final_validation_report.json"

    # pgvector Configuration
    PGVECTOR_EVIDENCE_TABLE: str = "rag_evidence_embeddings"
    PGVECTOR_HISTORICAL_TABLE: str = "rag_historical_embeddings"
    # Unified: same model as primary pipeline (BGE-large-en-v1.5)
    EMBEDDING_MODEL: str = "BAAI/bge-large-en-v1.5"
    EMBEDDING_DIMS: int = 768
    PGVECTOR_TOP_K: int = 10

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
