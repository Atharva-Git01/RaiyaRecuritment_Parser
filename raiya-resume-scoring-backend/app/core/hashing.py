"""
RAIYA Hashing Utilities — All hashes use SHA-256 prefixed "sha256:".
"""

import hashlib
import json
from typing import Union


def hash_content(content: Union[str, bytes]) -> str:
    """
    Compute SHA-256 hash of content, prefixed with "sha256:".
    
    Args:
        content: String or bytes to hash.
    
    Returns:
        Hash string prefixed with "sha256:".
    """
    if isinstance(content, str):
        content = content.encode("utf-8")
    digest = hashlib.sha256(content).hexdigest()
    return f"sha256:{digest}"


def hash_file(file_bytes: bytes) -> str:
    """
    Compute SHA-256 hash of file bytes, prefixed with "sha256:".
    """
    digest = hashlib.sha256(file_bytes).hexdigest()
    return f"sha256:{digest}"


def hash_json(data: dict) -> str:
    """
    Compute SHA-256 hash of a JSON-serializable dict.
    Keys are sorted for deterministic output.
    """
    json_str = json.dumps(data, separators=(",", ":"), sort_keys=True, default=str)
    return hash_content(json_str)


def hash_chain(previous_hash: str, content_hash: str) -> str:
    """
    Compute chain hash: SHA-256(previous_hash + content_hash).
    Used for append-only hash chain integrity.
    """
    combined = f"{previous_hash}{content_hash}"
    return hash_content(combined)


def verify_hash(content: Union[str, bytes], expected_hash: str) -> bool:
    """Verify that content matches an expected hash."""
    computed = hash_content(content)
    return computed == expected_hash
