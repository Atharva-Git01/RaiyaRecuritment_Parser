"""
SHA-256 Hashing & Cache System.

Provides deterministic, content-based fingerprinting for extracted resumes.
Only raw extracted plain text (UTF-8) is ever hashed — never markdown,
JSON, PDF binary, filenames, or metadata.

Cache files:
    <hash>.txt        → processed plain-text output
    <hash>.meta.json  → metadata (source, timestamp, lengths)
"""

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Optional, Tuple


def canonicalize(text: str) -> str:
    """
    Normalize text before hashing.

    Lowercase → collapse all whitespace to single space → strip.
    Ensures spacing/casing differences don't produce different hashes.

    Args:
        text: Raw extracted text.

    Returns:
        Canonical form of the text.
    """
    text = text.lower()
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def sha256_text(text: str) -> str:
    """
    Compute SHA-256 of canonicalized text.

    This is the primary hashing function.  Input **must** be raw
    extracted text (UTF-8).

    Args:
        text: Raw extracted text.

    Returns:
        64-char hex digest.
    """
    canonical = canonicalize(text)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def sha256_bytes(data: bytes) -> str:
    """
    Compute SHA-256 of raw bytes (file-level identity).

    Args:
        data: Raw file bytes.

    Returns:
        64-char hex digest.
    """
    return hashlib.sha256(data).hexdigest()


def section_hashes(sections: Dict[str, str]) -> Dict[str, str]:
    """
    Compute per-section SHA-256 digests for tailoring detection.

    Args:
        sections: Mapping of section name → section text.

    Returns:
        Mapping of section name → hex digest.
    """
    return {name: sha256_text(text) for name, text in sections.items() if text}


def hash_and_check(
    text: str,
    source_file: str,
    cache_dir: Path,
) -> Tuple[str, bool, Optional[str]]:
    """
    Primary entry-point for the cache system.

    1. Compute SHA-256 of raw text.
    2. Look up the hash in ``cache_dir``.
    3. Return ``(hash, hit?, cached_content)``.

    Args:
        text: Raw extracted text (must come from
              ``ExtractionResult.get_raw_extracted_text()``).
        source_file: Original filename (for metadata only).
        cache_dir: Path to ``hashed_resume_extraction_results/``.

    Returns:
        Tuple of (hex_digest, cache_hit_bool, cached_output_or_None).
    """
    digest = sha256_text(text)
    cached = lookup_hash(digest, cache_dir)
    if cached is not None:
        return (digest, True, cached)
    return (digest, False, None)


def lookup_hash(digest: str, cache_dir: Path) -> Optional[str]:
    """
    Read ``<hash>.txt`` from cache if it exists.

    Args:
        digest: SHA-256 hex digest.
        cache_dir: Cache directory path.

    Returns:
        Cached plain-text content, or None.
    """
    txt_path = cache_dir / f"{digest}.txt"
    if txt_path.exists():
        return txt_path.read_text(encoding="utf-8")
    return None


def store_hash(
    digest: str,
    output: str,
    source_file: str,
    cache_dir: Path,
    extracted_text: str = "",
) -> None:
    """
    Write ``<hash>.txt`` and ``<hash>.meta.json`` to cache.

    Args:
        digest: SHA-256 hex digest.
        output: Processed plain-text output to cache.
        source_file: Original filename.
        cache_dir: Cache directory path.
        extracted_text: Raw extracted text (for length metadata).
    """
    cache_dir.mkdir(parents=True, exist_ok=True)

    # Write plain-text output
    txt_path = cache_dir / f"{digest}.txt"
    txt_path.write_text(output, encoding="utf-8")

    # Write metadata
    meta_path = cache_dir / f"{digest}.meta.json"
    meta = {
        "sha256": digest,
        "source_file": source_file,
        "source_type": "extracted_text",
        "encoding": "utf-8",
        "stored_at": datetime.now(timezone.utc).isoformat(),
        "content_length": len(output),
        "extracted_text_length": len(extracted_text) if extracted_text else len(output),
    }
    meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")
