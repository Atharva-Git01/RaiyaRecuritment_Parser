"""
RAIYA Configuration — Pydantic Settings with all environment variables.
Loads from .env file in the backend root directory.
"""

from pydantic_settings import BaseSettings
from pydantic import Field
from typing import List
import json


class Settings(BaseSettings):
    """Centralized configuration loaded from environment variables."""

    # ── Application ──────────────────────────────────────────────
    APP_ENV: str = "development"
    CORS_ORIGINS: str = '["http://localhost:3000","https://app.raiya.ai"]'
    MAX_BATCH_SIZE: int = 200

    # ── Database (PostgreSQL 16 + pgvector) ──────────────────────
    DATABASE_URL: str = "postgresql+asyncpg://raiya:raiya_dev@localhost:5433/raiya"
    SYNC_DATABASE_URL: str = "postgresql://raiya:raiya_dev@localhost:5433/raiya"

    # ── Redis ────────────────────────────────────────────────────
    REDIS_URL: str = "redis://localhost:6379/0"

    # ── Azure OpenAI (Phi-4) ─────────────────────────────────────
    AZURE_OPENAI_ENDPOINT: str = ""
    AZURE_OPENAI_API_KEY: str = ""
    AZURE_OPENAI_DEPLOYMENT: str = "mmresumeparser"
    AZURE_OPENAI_API_VERSION: str = "2024-12-01-preview"
    AZURE_OPENAI_MODEL_NAME: str = "phi4"

    # ── Nanonets DocStrange OCR ──────────────────────────────────
    NANONETS_DOCSTRANGE_API_KEY: str = ""

    # ── JWT Auth ─────────────────────────────────────────────────
    JWT_SECRET_KEY: str = "your_32_char_secret"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 1440
    JWT_REFRESH_EXPIRE_DAYS: int = 30

    # ── LangChain / LangSmith ────────────────────────────────────
    LANGCHAIN_TRACING_V2: bool = True
    LANGCHAIN_API_KEY: str = ""
    LANGCHAIN_PROJECT: str = "raiya-pipeline-v7"
    LANGCHAIN_ENDPOINT: str = "https://api.smith.langchain.com"

    # ── Embeddings (unified: BGE-large-en-v1.5 for all) ────────
    EMBEDDING_MODEL_PRIMARY: str = "BAAI/bge-large-en-v1.5"
    EMBEDDING_DIMS_PRIMARY: int = 768

    # ── RecursiveJsonSplitter ────────────────────────────────────
    JSON_SPLITTER_RESUME_MAX_CHUNK: int = 300
    JSON_SPLITTER_JD_MAX_CHUNK: int = 400
    JSON_SPLITTER_EVD_MAX_CHUNK: int = 500

    # ── Hybrid Search (Deterministic Validator) ──────────────────
    DENSE_WEIGHT_IN_DETERMINISTIC: float = 0.65
    BM25_WEIGHT_IN_DETERMINISTIC: float = 0.35
    DETERMINISTIC_DENSE_THRESHOLD: float = 0.65
    DETERMINISTIC_RRF_K: int = 60

    # ── Guardrails ───────────────────────────────────────────────
    GUARDRAILS_SCORE_STD_DEVS: float = 2.0
    GUARDRAILS_FINAL_SCORE_STD_DEVS: float = 2.5

    # ── Cache TTLs (seconds) ─────────────────────────────────────
    CACHE_TTL_OCR: int = 2592000         # 30 days
    CACHE_TTL_EMBEDDING: int = 604800    # 7 days
    CACHE_TTL_WEIGHTS: int = 172800      # 48 hours
    CACHE_TTL_SEARCH: int = 3600         # 1 hour
    CACHE_TTL_PHI4: int = 86400          # 24 hours
    CACHE_TTL_RAG: int = 7200            # 2 hours
    CACHE_TTL_REASON: int = 7200         # 2 hours
    CACHE_TTL_EXPLANATION: int = 86400   # 24 hours
    CACHE_TTL_SCORE_HISTORY: int = 86400 # 24 hours

    # ── Token Pricing ────────────────────────────────────────────
    PROMPT_COST_PER_1K: float = 0.00030
    COMPLETION_COST_PER_1K: float = 0.00060

    # ── RAG Thresholds ───────────────────────────────────────────
    RAG_MATH_ACCURACY_MIN: float = 80.0

    # ── Reasoning Engine Temps ───────────────────────────────────
    REASONING_PHASE1_TEMP: float = 0.0
    REASONING_PHASE3_TEMP: float = 0.1
    REASONING_PHASE5_TEMP: float = 0.0

    # ── SMTP Email (Pipeline 4) ──────────────────────────────────
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USERNAME: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM_EMAIL: str = "noreply@raiya.ai"
    SMTP_FROM_NAME: str = "RAIYA Recruitment"
    SMTP_USE_TLS: bool = True

    # ── Interview Email Settings ─────────────────────────────────
    INTERVIEW_SCORE_THRESHOLD: float = 70.0
    INTERVIEW_MAX_CANDIDATES: int = 5
    AUTO_SEND_INTERVIEW_EMAILS: bool = False

    @property
    def cors_origins_list(self) -> List[str]:
        """Parse CORS_ORIGINS JSON string into a list."""
        try:
            return json.loads(self.CORS_ORIGINS)
        except (json.JSONDecodeError, TypeError):
            return ["http://localhost:3000"]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"
        case_sensitive = True


# Singleton instance
settings = Settings()
