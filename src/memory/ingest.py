"""Ingestion pipeline for the Qdrant vector store.

Provides the :func:`ingest_file` entry point that reads a file, chunks it,
classifies each chunk, embeds all chunks, and upserts them into Qdrant with
idempotent chunk IDs (content-hash-based UUIDv5).

Usage::

    from memory.ingest import ingest_file

    result = ingest_file("/path/to/file.md")
    print(result.chunks, "chunks ingested")
"""

from __future__ import annotations

import hashlib
import logging
import time
import uuid
from collections import Counter
from dataclasses import dataclass, field
from typing import Any

from .chunker import chunk
from .classifier import classify
from .embedder import embed
from .qdrant_client import QdrantClient

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# IngestResult
# ---------------------------------------------------------------------------


@dataclass
class IngestResult:
    """Summary of a single file ingestion.

    Attributes:
        file_path: Absolute or relative path to the ingested file.
        chunks: Number of chunks produced.
        category: Majority category across all chunks (empty string if
            zero chunks were produced).
        chunk_ids: List of UUID strings assigned to each chunk, in
            document order.
    """

    file_path: str
    chunks: int = 0
    category: str = ""
    chunk_ids: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _compute_chunk_id(source: str, chunk_index: int, content: str) -> uuid.UUID:
    """Deterministic UUIDv5 derived from content hash.

    Uses ``uuid.NAMESPACE_DNS`` and a composite name
    ``{source}:{chunk_index}:{sha256_of_content}`` so that re-ingesting
    the same file produces identical chunk IDs → idempotent upsert.

    Args:
        source: Origin file path (used in the name for namespacing).
        chunk_index: Zero-based index of this chunk in the file.
        content: The raw chunk text (hashed for the name).

    Returns:
        A :class:`uuid.UUID` (version 5, SHA-1 based).
    """
    content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
    name = f"{source}:{chunk_index}:{content_hash}"
    return uuid.uuid5(uuid.NAMESPACE_DNS, name)


def _majority_category(categories: list[str]) -> str:
    """Return the most frequent category.

    Args:
        categories: List of category strings, may be empty.

    Returns:
        The most common category, or ``""`` if the list is empty.
    """
    if not categories:
        return ""
    return Counter(categories).most_common(1)[0][0]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def ingest_file(path: str) -> IngestResult:
    """Full ingestion pipeline for a single file.

    Steps:
        1. Read the file (UTF-8).
        2. Chunk the text (paragraph boundaries via :func:`chunk`).
        3. Classify each chunk via :func:`classify`.
        4. Embed all chunk contents in a single call to :func:`embed`.
        5. Build Qdrant points with deterministic UUIDv5 chunk IDs.
        6. Ensure the Qdrant collection exists.
        7. Upsert all points to Qdrant (idempotent — same UUID replaces).
        8. Create payload indexes (safe no-op after first call).
        9. Return an :class:`IngestResult` summary.

    Args:
        path: File path to ingest.  Must exist and be readable.

    Returns:
        An :class:`IngestResult` summarising the ingestion.

    Raises:
        FileNotFoundError: If *path* does not exist.
        IOError: If the file cannot be read.
        ValueError: If ``EMBEDDING_MODEL`` is not set (propagated from
            :func:`embed`).
        httpx.HTTPStatusError: If the Ollama API returns an error
            (propagated from :func:`embed`).
    """
    # Step 1 — Read file
    logger.info("Ingesting file: %s", path)
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()

    # Step 2 — Chunk
    chunks = chunk(text)
    logger.info("Chunked into %d part(s)", len(chunks))

    if not chunks:
        logger.warning("No chunks produced from %s — skipping upsert.", path)
        return IngestResult(file_path=path, chunks=0, category="", chunk_ids=[])

    # Step 3 — Classify each chunk
    categories: list[str] = []
    tags_list: list[list[str]] = []
    for i, c in enumerate(chunks):
        cat, tags = classify(c)
        categories.append(cat)
        tags_list.append(tags)
        logger.debug("Chunk %d: category=%s tags=%s", i, cat, tags)

    # Step 4 — Embed all chunk contents at once
    logger.info("Embedding %d chunk(s) ...", len(chunks))
    vectors = embed(chunks)
    logger.info("Embedding complete — got %d vector(s)", len(vectors))

    # Step 5 — Build points
    now = int(time.time())
    points: list[dict[str, Any]] = []

    for i, (content, vector) in enumerate(zip(chunks, vectors, strict=True)):
        chunk_id = _compute_chunk_id(path, i, content)
        points.append(
            {
                "id": str(chunk_id),
                "vector": vector,
                "payload": {
                    "chunk_id": str(chunk_id),
                    "graph_node_id": None,
                    "session_id": "a2-ingest",
                    "category": categories[i],
                    "tags": tags_list[i],
                    "content": content,
                    "source": path,
                    "version": 1,
                    "validated_at": now,
                    "status": "active",
                },
            }
        )

    # Step 6 — Ensure collection exists
    client = QdrantClient()
    client.create_collection()

    # Step 7 — Upsert to Qdrant
    client.upsert(points)
    logger.info("Upserted %d point(s) to Qdrant", len(points))

    # Step 8 — Create payload indexes (idempotent — safe no-op after first)
    client.create_payload_indexes()

    # Step 9 — Return result
    chunk_ids: list[str] = [str(p["id"]) for p in points]
    return IngestResult(
        file_path=path,
        chunks=len(chunks),
        category=_majority_category(categories),
        chunk_ids=chunk_ids,
    )
