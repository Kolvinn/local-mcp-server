"""Core data models for the GraphRAG Memory Manager.

Provides the canonical enums (Category, NodeType, EdgeType, TagDimension),
a singleton TagRegistry for dynamic tag values, and module-level functions
for registering and querying edge types at runtime.
"""

from __future__ import annotations

import re
from enum import StrEnum
from typing import ClassVar

# ---------------------------------------------------------------------------
# 4.1  Category
# ---------------------------------------------------------------------------


class Category(StrEnum):
    """Mutually exclusive classification assigned to each ingested chunk.

    Exactly 8 values, matching the parent spec §4 (Qdrant Collection Schema).
    """

    TECHNICAL_FACT = "technical_fact"
    BUG = "bug"
    DECISION = "decision"
    GOAL = "goal"
    CODE_SYMBOL = "code_symbol"
    DOCUMENTATION = "documentation"
    EXPLORATION_FINDING = "exploration_finding"
    SESSION_MEMORY = "session_memory"


# ---------------------------------------------------------------------------
# 4.2  Tag Taxonomy & Registry
# ---------------------------------------------------------------------------


class TagDimension(StrEnum):
    """The four tag dimensions.

    Each dimension has a bootstrap set of allowed values managed by TagRegistry.
    """

    SCOPE = "scope"
    DOMAIN = "domain"
    QUALITY = "quality"
    PHASE = "phase"


class TagRegistry:
    """Singleton registry for tag values across 4 dimensions.

    Bootstrap values are loaded from the canonical taxonomy (parent spec §4).
    New values can be registered at runtime via :meth:`register`.

    Usage::

        registry = TagRegistry()
        registry.register("scope", "kubernetes")   # True
        registry.is_valid("scope", "kubernetes")   # True
    """

    _instance: ClassVar[TagRegistry | None] = None

    # Canonical bootstrap values per dimension (from parent spec §4 Tags table)
    _BOOTSTRAP: ClassVar[dict[str, set[str]]] = {
        "scope": {"ollama", "qdrant", "memgraph", "traefik", "opencode"},
        "domain": {
            "infra",
            "code",
            "architecture",
            "testing",
            "data",
            "security",
            "ux",
            "devops",
        },
        "quality": {
            "bug",
            "workaround",
            "verified",
            "deprecated",
            "unstable",
            "critical",
        },
        "phase": {"orient", "gather", "spec", "code", "review", "deploy"},
    }

    def __new__(cls) -> TagRegistry:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._tags: dict[str, set[str]] = {
                dim: values.copy() for dim, values in cls._BOOTSTRAP.items()
            }
        return cls._instance

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def register(self, dimension: str, value: str) -> bool:
        """Register a new tag value for a dimension.

        Args:
            dimension: Must be a member of :class:`TagDimension`.
            value: The tag string (lowercase, non-empty).

        Returns:
            True if the value was newly added, False if already present.

        Raises:
            ValueError: If *dimension* is not a valid TagDimension or
                *value* is empty.
        """
        try:
            TagDimension(dimension)
        except ValueError:
            raise ValueError(
                f"Invalid dimension: {dimension!r}. "
                f"Must be one of {sorted(m.value for m in TagDimension)}"
            ) from None
        if not value:
            raise ValueError("Tag value must be non-empty")

        if value in self._tags[dimension]:
            return False
        self._tags[dimension].add(value)
        return True

    def is_valid(self, dimension: str, value: str) -> bool:
        """Check if a tag value is known for the given dimension.

        Returns:
            True if the value exists in the registry for *dimension*.
        """
        if dimension not in self._tags:
            return False
        return value in self._tags[dimension]

    def list_dimension(self, dimension: str) -> list[str]:
        """Return all tag values for a dimension, sorted alphabetically."""
        return sorted(self._tags[dimension])

    def list_all(self) -> dict[str, list[str]]:
        """Return ``{dimension: [values]}`` for all dimensions, sorted."""
        return {dim: sorted(values) for dim, values in self._tags.items()}

    def reset(self) -> None:
        """Reset to bootstrap values.  Intended for testing only."""
        self._tags = {
            dim: values.copy() for dim, values in self._BOOTSTRAP.items()
        }


# ---------------------------------------------------------------------------
# 4.3  NodeType
# ---------------------------------------------------------------------------


class NodeType(StrEnum):
    """Graph node label applied to a node in the graph database.

    11 values, matching the Node Taxonomy table in parent spec §2.
    PascalCase to match Cypher node label conventions.
    """

    AGENT = "Agent"
    COMPONENT = "Component"
    DOCUMENT = "Document"
    SESSION = "Session"
    GOAL = "Goal"
    DECISION = "Decision"
    BUG = "Bug"
    CODE_ENTITY = "CodeEntity"
    ENVIRONMENT = "Environment"
    CONFIGURATION = "Configuration"
    CHUNK = "Chunk"


# ---------------------------------------------------------------------------
# 4.4  EdgeType  +  Runtime extensibility
# ---------------------------------------------------------------------------


class EdgeType(StrEnum):
    """Bootstrap set of legal relationship labels between graph node types.

    38 members, matching every unique relationship label from the Edge
    Contract table in parent spec §3.

    New edge types can be registered at runtime via :func:`register_edge_type`.
    """

    AFFECTS = "AFFECTS"
    LOCATED_IN = "LOCATED_IN"
    TRIGGERED_BY = "TRIGGERED_BY"
    REPRODUCED_IN = "REPRODUCED_IN"
    DISCOVERED_IN = "DISCOVERED_IN"
    DUPLICATE_OF = "DUPLICATE_OF"
    CAUSED_BY = "CAUSED_BY"
    RESOLVES = "RESOLVES"
    SELECTS = "SELECTS"
    SATISFIES = "SATISFIES"
    SUPERSEDES = "SUPERSEDES"
    CONFLICTS_WITH = "CONFLICTS_WITH"
    IMPLEMENTED_BY = "IMPLEMENTED_BY"
    PARENT_OF = "PARENT_OF"
    BLOCKS = "BLOCKS"
    MOTIVATED = "MOTIVATED"
    BLOCKED_BY = "BLOCKED_BY"
    REPORTED = "REPORTED"
    PROPOSED = "PROPOSED"
    OWNS = "OWNS"
    PARTICIPATED_IN = "PARTICIPATED_IN"
    CALLS = "CALLS"
    EXTENDS = "EXTENDS"
    IMPLEMENTS = "IMPLEMENTS"
    OVERRIDES = "OVERRIDES"
    DEPENDS_ON = "DEPENDS_ON"
    BELONGS_TO = "BELONGS_TO"
    READS = "READS"
    HOSTS = "HOSTS"
    DEFINED_IN = "DEFINED_IN"
    SETS = "SETS"
    DEPLOYED_IN = "DEPLOYED_IN"
    FOLLOWS = "FOLLOWS"
    PRODUCED = "PRODUCED"
    WORKED_ON = "WORKED_ON"
    RECORDS = "RECORDS"
    DOCUMENTS = "DOCUMENTS"
    EXTRACTED_TO = "EXTRACTED_TO"


# Module-level set of runtime-registered edge type labels.
# Grows when callers invoke register_edge_type().
_runtime_edge_types: set[str] = set()

_EDGE_TYPE_PATTERN = re.compile(r"^[A-Z][A-Z_]*$")


def register_edge_type(label: str) -> bool:
    """Register a new edge type at runtime.

    The label must be uppercase and match the pattern ``^[A-Z][A-Z_]*$``.
    It must not collide with an existing :class:`EdgeType` member or a
    previously runtime-registered label.

    Args:
        label: The edge type string (e.g. ``"CONFIGURES"``).

    Returns:
        True if the label was newly registered, False if it was already
        present in the runtime set.

    Raises:
        ValueError: If *label* does not match ``^[A-Z][A-Z_]*$``, or if it
            collides with an existing :class:`EdgeType` member.
    """
    if not _EDGE_TYPE_PATTERN.fullmatch(label):
        raise ValueError(
            f"Invalid edge type label: {label!r}. "
            "Must match pattern ^[A-Z][A-Z_]*$"
        )
    if label in EdgeType.__members__:
        raise ValueError(
            f"Edge type {label!r} is already a member of the EdgeType enum "
            "and cannot be re-registered."
        )
    if label in _runtime_edge_types:
        return False
    _runtime_edge_types.add(label)
    return True


def is_edge_type(label: str) -> bool:
    """Check if *label* is a known edge type (bootstrap or runtime).

    Returns:
        True if *label* is a member of :class:`EdgeType` or has been
        registered via :func:`register_edge_type`.
    """
    return label in EdgeType.__members__ or label in _runtime_edge_types
