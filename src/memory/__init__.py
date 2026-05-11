"""Memory models, graph pipeline, and edge validation for the GraphRAG Memory Manager."""

from .embedder import EmbedType, Embedder, get_embedder
from .graph import build_graph, get_graph, ingest
from .models import (
    Category,
    NodeType,
    EdgeType,
    TagDimension,
    TagRegistry,
    register_edge_type,
    is_edge_type,
)
from .qdrant_client import ensure_collection_exists, get_qdrant_client, upsert_point
from .taxonomy_loader import get_payload_indexes, load_taxonomy, validate_classification

__all__ = [
    # Models
    "Category",
    "NodeType",
    "EdgeType",
    "TagDimension",
    "TagRegistry",
    "register_edge_type",
    "is_edge_type",
    # Memory ingestion pipeline
    "build_graph",
    "get_graph",
    "ingest",
    "Embedder",
    "EmbedType",
    "get_embedder",
    "get_qdrant_client",
    "ensure_collection_exists",
    "upsert_point",
    "load_taxonomy",
    "validate_classification",
    "get_payload_indexes",
    # Edge validation (forward-imported below)
    "validate",
    "register_edge",
    "get_registered_edges",
]

# edge_validator.py is built in a later task — forward-import with fallback
# so downstream code can import everything from src.memory regardless of build order.
try:
    from .edge_validator import (  # type: ignore[import-unused]
        validate,
        register_edge,
        get_registered_edges,
    )
except ImportError:
    # Placeholder stubs so the package is importable before edge_validator exists.
    def validate(source_label: str, relation: str, target_label: str) -> bool:  # type: ignore[misc]
        """Placeholder — installed when edge_validator.py is created."""
        raise NotImplementedError(
            "validate() is not available until edge_validator.py is built."
        )

    def register_edge(source: str, relation: str, target: str) -> bool:  # type: ignore[misc]
        """Placeholder — installed when edge_validator.py is created."""
        raise NotImplementedError(
            "register_edge() is not available until edge_validator.py is built."
        )

    def get_registered_edges() -> list[tuple[str, str, str]]:  # type: ignore[misc]
        """Placeholder — installed when edge_validator.py is created."""
        raise NotImplementedError(
            "get_registered_edges() is not available until edge_validator.py is built."
        )
