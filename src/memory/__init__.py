"""Memory models and edge validation for the GraphRAG Memory Manager."""

from .models import (
    Category,
    NodeType,
    EdgeType,
    TagDimension,
    TagRegistry,
    register_edge_type,
    is_edge_type,
)

__all__ = [
    "Category",
    "NodeType",
    "EdgeType",
    "TagDimension",
    "TagRegistry",
    "register_edge_type",
    "is_edge_type",
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
