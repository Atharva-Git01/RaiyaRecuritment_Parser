"""
Configuration for the Resume Extraction System.

Centralizes directory paths, supported file extensions,
and processing settings.
"""

from pathlib import Path


# Base directory is the parent of /modules (i.e. the project root)
_BASE_DIR = Path(__file__).resolve().parent.parent


class Config:
    """Application-wide settings."""

    # ── Directories ──────────────────────────────────────────────────
    INPUT_DIR: Path = _BASE_DIR / "resumes"
    OUTPUT_DIR: Path = _BASE_DIR / "resume_extraction_outputs"
    HASHED_OUTPUT_DIR: Path = _BASE_DIR / "hashed_resume_extraction_results"

    # ── Supported formats ────────────────────────────────────────────
    SUPPORTED_EXTENSIONS: set = {
        ".pdf", ".docx", ".doc", ".txt", ".rtf",
        ".html", ".htm", ".xlsx", ".xls", ".csv",
        ".pptx", ".ppt",
        ".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".webp", ".gif",
    }

    # ── Processing knobs ─────────────────────────────────────────────
    PROCESSING: dict = {
        "max_workers": 4,
    }

    @classmethod
    def ensure_directories(cls) -> None:
        """Create all required directories if they don't already exist."""
        cls.INPUT_DIR.mkdir(parents=True, exist_ok=True)
        cls.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        cls.HASHED_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
