"""Qdrant vector store client wrapper.

Provides a thin wrapper around the ``qdrant-client`` Python SDK for
collection management, point upsert, search, scroll, and count operations.
All configuration values come from environment variables per CON-003.

Usage::

    from memory.qdrant_client import QdrantClient

    client = QdrantClient()
    client.create_collection()
    client.upsert(points=[{...}])
    results = client.search(query_vector=[0.1, 0.2, ...], limit=5)
    total = client.count()
"""

from __future__ import annotations

import logging
import os
from typing import Any

from qdrant_client import QdrantClient as _QdrantClient
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchValue,
    PayloadSchemaType,
    PointStruct,
    VectorParams,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Known embedding model → vector dimension mapping
# ---------------------------------------------------------------------------
# Extend this mapping as new models are introduced.  If a model is not listed
# a warning is emitted and a default of 768 is used (nomic-embed-text size).
_EMBEDDING_DIMENSIONS: dict[str, int] = {
    "nomic-embed-text": 768,
    "text-embedding-ada-002": 1536,
    "text-embedding-3-small": 1536,
    "text-embedding-3-large": 3072,
    "all-MiniLM-L6-v2": 384,
    "all-mpnet-base-v2": 768,
}

# Payload fields that require a KEYWORD index per §4.1 / VAL-003.
_PAYLOAD_INDEX_FIELDS: tuple[str, ...] = (
    "category",
    "tags",
    "status",
    "graph_node_id",
    "validated_at",
    "version",
    "source",
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_collection_name() -> str:
    """Read ``QDRANT_COLLECTION_NAME`` from env (default ``memory_chunks``)."""
    return os.getenv("QDRANT_COLLECTION_NAME", "memory_chunks")


def _get_vector_size() -> int:
    """Derive vector dimensions from ``EMBEDDING_MODEL`` env var.

    Falls back to 768 (nomic-embed-text) when the model name is not
    recognised.
    """
    model = os.getenv("EMBEDDING_MODEL", "nomic-embed-text")
    dim = _EMBEDDING_DIMENSIONS.get(model)
    if dim is None:
        logger.warning(
            "Unknown embedding model %r, defaulting to 768 dimensions. "
            "Consider adding it to _EMBEDDING_DIMENSIONS in %s.",
            model,
            __name__,
        )
        return 768
    return dim


def _dict_to_filter(filter_dict: dict[str, Any] | None) -> Filter | None:
    """Convert a simple dict filter to a :class:`Filter` object.

    Supports the following shorthand::

        {"category": "bug"}              → must match value exactly
        {"category": "bug", "status": "active"}  → AND of all conditions

    Returns ``None`` when *filter_dict* is ``None`` or empty, which is
    equivalent to "no filter" in the Qdrant API.
    """
    if not filter_dict:
        return None

    conditions: list[FieldCondition] = []
    for key, value in filter_dict.items():
        conditions.append(
            FieldCondition(key=key, match=MatchValue(value=value))
        )
    return Filter(must=conditions)


def _scored_point_to_dict(
    point: Any,  # qdrant_client.http.models.models.ScoredPoint
) -> dict[str, Any]:
    """Convert a ``ScoredPoint`` to a plain dict for the public API."""
    result: dict[str, Any] = {
        "id": point.id,
        "score": point.score,
        "payload": point.payload or {},
    }
    if point.vector is not None:
        result["vector"] = point.vector
    return result


def _record_to_dict(
    record: Any,  # qdrant_client.http.models.models.Record
) -> dict[str, Any]:
    """Convert a ``Record`` to a plain dict for the public API."""
    result: dict[str, Any] = {
        "id": record.id,
        "payload": record.payload or {},
    }
    if record.vector is not None:
        result["vector"] = record.vector
    return result


# ---------------------------------------------------------------------------
# Public wrapper
# ---------------------------------------------------------------------------


class QdrantClient:
    """Thin wrapper around the ``qdrant-client`` Python SDK.

    All configuration is read from environment variables:

    * ``QDRANT_HOST`` — default ``localhost``
    * ``QDRANT_PORT`` — default ``6333``
    * ``QDRANT_COLLECTION_NAME`` — default ``memory_chunks``
    * ``EMBEDDING_MODEL`` — default ``nomic-embed-text``
    """

    def __init__(self) -> None:
        host = os.getenv("QDRANT_HOST", "qdrant")
        port = int(os.getenv("QDRANT_PORT", "6333"))
        self._collection_name = _get_collection_name()
        self._client = _QdrantClient(host=host, port=port)
        logger.info(
            "QdrantClient initialized — host=%s:%d, collection=%s",
            host,
            port,
            self._collection_name,
        )

    # ------------------------------------------------------------------
    # Collection management
    # ------------------------------------------------------------------

    def create_collection(self) -> None:
        """Create the Qdrant collection if it does not already exist.

        Vector dimensions are derived from ``EMBEDDING_MODEL`` and the
        distance metric is always Cosine.

        .. note::

            Payload indexes are **not** created here — call
            :meth:`create_payload_indexes` after the first upsert to
            comply with CON-005 (avoid indexing an empty collection).
        """
        if self._client.collection_exists(self._collection_name):
            logger.info(
                "Collection %r already exists — skipping creation.",
                self._collection_name,
            )
            return

        vector_size = _get_vector_size()
        self._client.create_collection(
            collection_name=self._collection_name,
            vectors_config=VectorParams(
                size=vector_size,
                distance=Distance.COSINE,
            ),
        )
        logger.info(
            "Created collection %r (size=%d, distance=Cosine).",
            self._collection_name,
            vector_size,
        )

    def create_payload_indexes(self) -> None:
        """Create KEYWORD payload indexes for the fields listed in §4.1.

        Per CON-005 this should be called **after** the first upsert to
        avoid indexing an empty collection.
        """
        for field in _PAYLOAD_INDEX_FIELDS:
            try:
                self._client.create_payload_index(
                    collection_name=self._collection_name,
                    field_name=field,
                    field_schema=PayloadSchemaType.KEYWORD,
                )
                logger.debug("Created payload index on field %r.", field)
            except Exception:
                logger.warning(
                    "Payload index on field %r may already exist — skipping.",
                    field,
                    exc_info=True,
                )

    # ------------------------------------------------------------------
    # Data operations
    # ------------------------------------------------------------------

    def upsert(self, points: list[dict[str, Any]]) -> None:
        """Insert or replace points into the collection (idempotent).

        Args:
            points: List of point dicts.  Each dict must have the keys
                ``id`` (chunk_id), ``vector`` (list[float]), and
                ``payload`` (dict of metadata).

        Raises:
            ValueError: If any point is missing a required key.
        """
        point_structs: list[PointStruct] = []
        for i, p in enumerate(points):
            point_id = p.get("id")
            vector = p.get("vector")
            payload = p.get("payload")
            if point_id is None or vector is None:
                raise ValueError(
                    f"Point at index {i} is missing required key(s). "
                    "Each point must have 'id', 'vector', and 'payload'."
                )
            point_structs.append(
                PointStruct(
                    id=point_id,
                    vector=vector,
                    payload=payload or {},
                )
            )

        self._client.upsert(
            collection_name=self._collection_name,
            points=point_structs,
            wait=True,
        )
        logger.debug("Upserted %d point(s).", len(point_structs))

    def search(
        self,
        query_vector: list[float],
        limit: int = 10,
        filter: dict[str, Any] | None = None,  # noqa: A002
    ) -> list[dict[str, Any]]:
        """Vector similarity search.

        Args:
            query_vector: The query embedding vector.
            limit: Maximum number of results to return (default 10).
            filter: Optional dict of payload field filters.  All
                conditions are combined with AND (``must``).  Example::

                    {"category": "bug", "status": "active"}

        Returns:
            List of result dicts, each containing ``id``, ``score``,
            ``payload``, and optionally ``vector``.
        """
        qfilter = _dict_to_filter(filter)
        response = self._client.query_points(
            collection_name=self._collection_name,
            query=query_vector,
            query_filter=qfilter,
            limit=limit,
            with_payload=True,
            with_vectors=False,
        )
        return [_scored_point_to_dict(p) for p in response.points]

    def scroll(
        self,
        filter: dict[str, Any] | None = None,  # noqa: A002
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Paginated point retrieval.

        Args:
            filter: Optional dict of payload field filters (AND
                semantics).
            limit: Maximum number of points to return (default 100).

        Returns:
            List of point dicts, each containing ``id``, ``payload``,
            and optionally ``vector``.
        """
        sfilter = _dict_to_filter(filter)
        records, _ = self._client.scroll(
            collection_name=self._collection_name,
            scroll_filter=sfilter,
            limit=limit,
            with_payload=True,
            with_vectors=False,
        )
        return [_record_to_dict(r) for r in records]

    def count(self) -> int:
        """Return the total number of points in the collection.

        Returns:
            The exact point count.
        """
        result = self._client.count(
            collection_name=self._collection_name,
            exact=True,
        )
        return result.count
