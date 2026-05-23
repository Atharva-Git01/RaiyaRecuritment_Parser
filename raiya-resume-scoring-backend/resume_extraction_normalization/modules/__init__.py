"""
Modules package for the Universal Resume Extraction System.
"""

import sys
from pathlib import Path

# Add docstrange-main to sys.path so we can import `docstrange` directly
_docstrange_root = str(Path(__file__).resolve().parent / "docstrange-main")
if _docstrange_root not in sys.path:
    sys.path.insert(0, _docstrange_root)

from .config import Config
from .file_utils import get_resume_files, format_file_size, sanitize_filename
from .menu import display_files_menu, parse_selection
from .hashing import hash_and_check, store_hash, sha256_text, sha256_bytes, section_hashes

# Re-export docstrange classes (available after sys.path adjustment above)
from docstrange import DocumentExtractor, ConversionResult

# Re-export schema validation public API
from .resume_schema_validation import (
    validate_resume,
    validate_resume_file,
    validate_and_save,
    ValidatedResumeSchema,
    ValidationReport,
)

__all__ = [
    "Config",
    "get_resume_files",
    "format_file_size",
    "sanitize_filename",
    "display_files_menu",
    "parse_selection",
    "hash_and_check",
    "store_hash",
    "sha256_text",
    "sha256_bytes",
    "section_hashes",
    "DocumentExtractor",
    "ConversionResult",
    # Schema Validation
    "validate_resume",
    "validate_resume_file",
    "validate_and_save",
    "ValidatedResumeSchema",
    "ValidationReport",
]
