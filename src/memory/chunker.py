"""Text chunker for the ingestion pipeline.

Splits text into semantic chunks at paragraph boundaries (double newlines).
Long paragraphs are split on single newlines to keep chunk sizes manageable.

Usage::

    from memory.chunker import chunk

    paragraphs = chunk("First paragraph.\\n\\nSecond paragraph.")
    # -> ["First paragraph.", "Second paragraph."]
"""

from __future__ import annotations

import re

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Paragraphs longer than this threshold (in characters) and containing single
# newlines are split further on those single newlines.
_LONG_PARAGRAPH_THRESHOLD: int = 2000


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def chunk(text: str) -> list[str]:
    """Split *text* into semantic chunks at paragraph boundaries.

    The algorithm:

    1. Strip leading/trailing whitespace.
    2. Split on two or more consecutive newlines (``\\n\\n+``) — these mark
       paragraph boundaries.
    3. For each resulting paragraph:
       - Strip leading/trailing whitespace.
       - Skip empty paragraphs.
       - If the paragraph exceeds ``_LONG_PARAGRAPH_THRESHOLD`` *and*
         contains single newlines, split further on those newlines.
       - Otherwise keep the paragraph as a single chunk.

    Code blocks (triple-backtick fences) and list structures are preserved
    because they typically lack double-newline separators and fall under the
    threshold.

    Args:
        text: The raw text to chunk.

    Returns:
        A list of chunk strings, each with consistent whitespace.

    Example:
        >>> chunk("First paragraph.\\n\\nSecond paragraph.\\n\\nThird paragraph.")
        ['First paragraph.', 'Second paragraph.', 'Third paragraph.']

        >>> chunk("Line one\\nLine two\\n\\nNext paragraph.")
        ['Line one\\nLine two', 'Next paragraph.']

        >>> chunk("")
        []
    """
    if not text:
        return []

    # Normalize Windows-style line endings to Unix.
    normalized = text.replace("\r\n", "\n")
    stripped = normalized.strip()
    if not stripped:
        return []

    # Split on paragraph boundaries (two or more newlines).
    raw_paragraphs = re.split(r"\n\n+", stripped)

    result: list[str] = []
    for para in raw_paragraphs:
        para = para.strip()
        if not para:
            continue

        # Long paragraph with internal single newlines -> split further.
        if len(para) > _LONG_PARAGRAPH_THRESHOLD and "\n" in para:
            for line in para.split("\n"):
                line = line.strip()
                if line:
                    result.append(line)
        else:
            result.append(para)

    return result
