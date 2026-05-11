"""Qdrant vector store client for the Memory Manager.

Provides module-level functions for collection management and point upsert.
All configuration is read from environment variables.
"""

from __future__ import annotations

import logging
import os

from qdrant_client import QdrantClient as _QdrantClient
from qdrant_client.models import (
    Distance,
    HnswConfigDiff,
    Modifier,
    MultiVectorComparator,
    MultiVectorConfig,
    PointStruct,
    SparseVectorParams,
    VectorParams,
)

from . import taxonomy_loader

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration (from environment)
# ---------------------------------------------------------------------------

QDRANT_HOST: str = os.getenv("QDRANT_HOST", "qdrant")
QDRANT_PORT: int = int(os.getenv("QDRANT_PORT", "6333"))
COLLECTION_NAME: str = os.getenv("COLLECTION_NAME", "memory_chunks")
DENSE_DIM: int = int(os.getenv("DENSE_DIM", "768"))
LI_DIM: int = int(os.getenv("LI_DIM", "128"))

# ---------------------------------------------------------------------------
# Error classes
# ---------------------------------------------------------------------------


class QdrantError(ConnectionError):
    """Raised when Qdrant is unreachable or an upsert is rejected."""


# ---------------------------------------------------------------------------
# Singleton client
# ---------------------------------------------------------------------------

_client: _QdrantClient | None = None


def get_qdrant_client() -> _QdrantClient:
    """Return the module-level singleton ``QdrantClient``.

    The client is lazily created on first call and reused thereafter.
    Host and port are read from environment variables.
    """
    global _client  # noqa: PLW0603
    if _client is None:
        try:
            _client = _QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)
        except Exception as exc:
            raise QdrantError(
                f"Failed to connect to Qdrant at {QDRANT_HOST}:{QDRANT_PORT}: {exc}"
            ) from exc
    return _client


# ---------------------------------------------------------------------------
# Collection management
# ---------------------------------------------------------------------------


def ensure_collection_exists() -> None:
    """Create the ``memory_chunks`` collection and payload indexes if needed.

    If the collection already exists the function is a no-op (idempotent).
    Payload indexes that already exist are silently skipped.

    Raises:
        QdrantError: If Qdrant is unreachable.
        RuntimeError: If collection creation fails (propagated from Qdrant).
    """
    client = get_qdrant_client()

    try:
        if client.collection_exists(COLLECTION_NAME):
            logger.info("Collection %r already exists — skipping creation.", COLLECTION_NAME)
            return
    except Exception as exc:
        raise QdrantError(
            f"Qdrant unreachable while checking collection existence: {exc}"
        ) from exc

    try:
        client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config={
                "dense": VectorParams(
                    size=DENSE_DIM,
                    distance=Distance.COSINE,
                ),
                "multi": VectorParams(
                    size=LI_DIM,
                    distance=Distance.COSINE,
                    multivector_config=MultiVectorConfig(
                        comparator=MultiVectorComparator.MAX_SIM,
                    ),
                    hnsw_config=HnswConfigDiff(m=0),
                ),
            },
            sparse_vectors_config={
                "sparse": SparseVectorParams(modifier=Modifier.IDF),
            },
        )
        logger.info(
            "Created collection %r (dense=%d, multi=%d, sparse=IDF).",
            COLLECTION_NAME,
            DENSE_DIM,
            LI_DIM,
        )
    except Exception as exc:
        raise RuntimeError(
            f"Failed to create collection {COLLECTION_NAME}: {exc}"
        ) from exc

    # Create payload indexes from taxonomy
    _create_payload_indexes(client)


def _create_payload_indexes(client: _QdrantClient) -> None:
    """Create payload indexes from the taxonomy schema.

    Duplicate index errors are caught and silently ignored.
    """
    try:
        taxonomy = taxonomy_loader.load_taxonomy()
    except Exception as exc:
        logger.warning("Could not load taxonomy for payload indexes: %s", exc)
        return

    indexes = taxonomy_loader.get_payload_indexes(taxonomy)
    for field_name, index_type in indexes:
        try:
            client.create_payload_index(
                collection_name=COLLECTION_NAME,
                field_name=field_name,
                field_schema=index_type,
            )
            logger.debug("Created payload index on field %r (%s).", field_name, index_type)
        except Exception:
            logger.debug(
                "Payload index on field %r may already exist — skipping.", field_name,
            )


# ---------------------------------------------------------------------------
# Data operations
# ---------------------------------------------------------------------------


def upsert_point(point: PointStruct) -> str:
    """Upsert a single ``PointStruct`` into the collection.

    Args:
        point: The point to upsert.  Must have a ``payload`` dict containing
            a ``"chunk_id"`` key.

    Returns:
        The ``chunk_id`` from the point's payload as confirmation.

    Raises:
        QdrantError: If Qdrant is unreachable.
        ValueError: If *point* has no payload or no ``"chunk_id"`` in payload.
        RuntimeError: If the upsert is rejected by Qdrant.
    """
    if point.payload is None or "chunk_id" not in point.payload:
        raise ValueError(
            "Point must have a payload with a 'chunk_id' key."
        )

    client = get_qdrant_client()
    try:
        client.upsert(
            collection_name=COLLECTION_NAME,
            points=[point],
            wait=True,
        )
    except Exception as exc:
        raise QdrantError(
            f"Failed to upsert point {point.id} into {COLLECTION_NAME}: {exc}"
        ) from exc

    return str(point.payload["chunk_id"])
