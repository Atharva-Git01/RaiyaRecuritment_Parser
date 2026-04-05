"""
File Handling Utilities for the Resume Extraction System.

Provides file discovery, size formatting, and filename sanitization functions.
"""

import os
import re
from pathlib import Path
from typing import List, Dict, Any, Optional, Set

from .config import Config


def get_resume_files(
    input_dir: Optional[Path] = None,
    exclude_subdirs: bool = True,
) -> List[Path]:
    """
    Scan input directory for supported resume files.

    Args:
        input_dir: Directory to scan. Defaults to Config.INPUT_DIR.
        exclude_subdirs: If True, only list files at the top level.

    Returns:
        Sorted list of Path objects for supported files.
    """
    input_dir = input_dir or Config.INPUT_DIR

    try:
        if not input_dir.exists():
            return []

        files: List[Path] = []
        if exclude_subdirs:
            for entry in input_dir.iterdir():
                if entry.is_file() and entry.suffix.lower() in Config.SUPPORTED_EXTENSIONS:
                    files.append(entry)
        else:
            for ext in Config.SUPPORTED_EXTENSIONS:
                files.extend(input_dir.rglob(f"*{ext}"))

        return sorted(files, key=lambda p: p.name.lower())
    except OSError:
        return []


def get_files_by_type(
    input_dir: Optional[Path] = None,
) -> Dict[str, List[Path]]:
    """
    Group discovered files by extension.

    Returns:
        Dict mapping extension → list of paths.
    """
    files = get_resume_files(input_dir, exclude_subdirs=False)
    grouped: Dict[str, List[Path]] = {}
    for f in files:
        ext = f.suffix.lower()
        grouped.setdefault(ext, []).append(f)
    return grouped


def get_file_info(file_path: Path) -> Dict[str, Any]:
    """
    Return metadata about a file (name, size, extension).

    Args:
        file_path: Path to the file.

    Returns:
        Dictionary with file metadata.
    """
    try:
        stat = file_path.stat()
        size = stat.st_size
    except OSError:
        size = 0

    return {
        "name": file_path.name,
        "stem": file_path.stem,
        "extension": file_path.suffix.lower(),
        "size_bytes": size,
        "size_formatted": format_file_size(size),
        "path": str(file_path),
    }


def format_file_size(size_bytes: int) -> str:
    """
    Format file size in human-readable form.

    Args:
        size_bytes: Size in bytes.

    Returns:
        Formatted string (e.g. "1.23 MB").
    """
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 ** 2:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 ** 3:
        return f"{size_bytes / (1024 ** 2):.2f} MB"
    else:
        return f"{size_bytes / (1024 ** 3):.2f} GB"


def sanitize_filename(filename: str) -> str:
    """
    Clean a filename for safe filesystem use.

    Args:
        filename: Original filename string.

    Returns:
        Sanitized filename.
    """
    # Remove or replace unsafe characters
    sanitized = re.sub(r'[<>:"/\\|?*]', "_", filename)
    # Collapse multiple underscores / spaces
    sanitized = re.sub(r"[_\s]+", "_", sanitized)
    # Strip leading/trailing underscores and dots
    sanitized = sanitized.strip("_.")
    return sanitized or "unnamed"


def list_directory_contents(directory: Path) -> List[Dict[str, Any]]:
    """
    List all files within a directory with metadata.

    Args:
        directory: Directory to scan.

    Returns:
        List of file metadata dicts.
    """
    try:
        if not directory.exists():
            return []
        return [get_file_info(p) for p in sorted(directory.iterdir()) if p.is_file()]
    except OSError:
        return []
