"""
Interactive Menu for the Resume Extraction CLI.

Provides a numbered file menu and selection parsing for the CLI entry point.
"""

from pathlib import Path
from typing import List, Optional

from .file_utils import format_file_size


def display_files_menu(resume_files: List[Path]) -> Optional[List[Path]]:
    """
    Display a numbered list of resume files and prompt for selection.

    Args:
        resume_files: List of discovered resume file paths.

    Returns:
        List of selected Path objects, or None if user quits.
    """
    if not resume_files:
        print("\n⚠️  No supported files found in the input directory.")
        return None

    print(f"\n📄 Found {len(resume_files)} resume(s):\n")
    for idx, fp in enumerate(resume_files, start=1):
        try:
            size = format_file_size(fp.stat().st_size)
        except OSError:
            size = "unknown"
        print(f"  [{idx:>3}]  {fp.name}  ({size})")

    print(
        "\nOptions:  'all' → process all  |  '1,3,5' → select specific  "
        "|  '1-5' → range  |  'q' → quit"
    )

    try:
        selection = input("\n▶ Enter selection: ").strip()
    except (EOFError, KeyboardInterrupt):
        print("\n\n👋 Session cancelled.")
        return None

    indices = parse_selection(selection, len(resume_files))
    if indices is None:
        return None

    return [resume_files[i] for i in indices]


def parse_selection(selection: str, max_index: int) -> Optional[List[int]]:
    """
    Parse user input into a list of 0-based indices.

    Supported formats:
        - ``all``  → all indices
        - ``1,3,5`` → comma-separated
        - ``2-7``   → range (inclusive)
        - ``q``     → quit (returns None)

    Args:
        selection: Raw user input string.
        max_index: Number of available items.

    Returns:
        List of 0-based indices, or None if user chose to quit.
    """
    sel = selection.strip().lower()

    if sel in ("q", "quit", "exit"):
        print("\n👋 Session cancelled.")
        return None

    if sel == "all":
        return list(range(max_index))

    # Comma-separated
    if "," in sel:
        indices = []
        for part in sel.split(","):
            part = part.strip()
            if part.isdigit():
                idx = int(part) - 1
                if 0 <= idx < max_index:
                    indices.append(idx)
        return sorted(set(indices)) if indices else None

    # Range (e.g. "2-7")
    if "-" in sel:
        parts = sel.split("-", 1)
        if len(parts) == 2 and parts[0].strip().isdigit() and parts[1].strip().isdigit():
            start = int(parts[0].strip()) - 1
            end = int(parts[1].strip()) - 1
            if 0 <= start <= end < max_index:
                return list(range(start, end + 1))
        return None

    # Single number
    if sel.isdigit():
        idx = int(sel) - 1
        if 0 <= idx < max_index:
            return [idx]

    print(f"⚠️  Invalid selection: '{selection}'")
    return None
