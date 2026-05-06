#!/usr/bin/env python
"""CLI entry point for the ingestion pipeline.

Usage:
    python scripts/ingest_test.py <file_path>

Imports :func:`ingest_file` from the ``memory`` package, invokes it with the
provided file path, and prints a formatted result summary alongside the total
Qdrant point count.

Exit codes:
    0 — success
    1 — missing argument or file not found
"""

from __future__ import annotations

import logging
import os
import sys

# ---------------------------------------------------------------------------
# sys.path hack: make ``memory`` importable from scripts/
#
# Project convention: src/ is NOT a package (no src/__init__.py).
# This hack lets scripts/*.py do ``from memory.ingest import ingest_file``.
# ---------------------------------------------------------------------------
_src_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _src_root)

from memory.ingest import ingest_file  # noqa: E402
from memory.qdrant_client import QdrantClient  # noqa: E402


def main() -> None:
    """Parse CLI args, run ingest, print summary."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s  %(name)s  %(message)s",
        stream=sys.stderr,
    )

    if len(sys.argv) < 2:
        print("Usage: python scripts/ingest_test.py <file_path>", file=sys.stderr)
        sys.exit(1)

    file_path = sys.argv[1]

    if not os.path.isfile(file_path):
        print(f"Error: file not found — {file_path}", file=sys.stderr)
        sys.exit(1)

    result = ingest_file(file_path)

    # Query Qdrant for total point count
    client = QdrantClient()
    total_points = client.count()

    # Print result summary
    sep = "=" * 50
    print(f"\n{sep}")
    print(f"  File:      {result.file_path}")
    print(f"  Chunks:    {result.chunks}")
    print(f"  Category:  {result.category or '(none)'}")
    print(f"  Chunk IDs: {len(result.chunk_ids)} UUID(s) created")
    print(f"  Qdrant total points: {total_points}")
    print(f"{sep}\n")


if __name__ == "__main__":
    main()
