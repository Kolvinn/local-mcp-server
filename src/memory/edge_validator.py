"""Edge validation for the GraphRAG Memory Manager.

Provides functions to validate legal edge triples (source-relation-target)
against the bootstrap edge contract loaded from ``edge-contract.json`` and
any runtime-registered edges.  All validation is pure-Python with zero
external dependencies beyond the standard library.
"""

from __future__ import annotations

import json
from pathlib import Path

# ---------------------------------------------------------------------------
# Module-level: load the bootstrap edge contract at import time
# (fail-fast — if the JSON is missing or malformed the error surfaces
#  immediately rather than silently later in the pipeline.)
# ---------------------------------------------------------------------------

CONTRACT_PATH = (
    Path(__file__).resolve().parent.parent.parent
    / "docs"
    / "rag-dev"
    / "edge-contract.json"
)

_BOOTSTRAP_MATRIX: dict[str, dict[str, list[str]]] = {}
with open(CONTRACT_PATH) as f:
    _BOOTSTRAP_MATRIX = json.load(f)

# Runtime adjacency matrix: {source_label: {target_label: {relation, ...}, ...}}
# Grows when callers invoke register_edge().
_runtime_matrix: dict[str, dict[str, set[str]]] = {}


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _parse_runtime_for_validation() -> dict[str, dict[str, list[str]]]:
    """Convert ``_runtime_matrix`` sets to lists for unified lookup.

    Returns a structure that mirrors the bootstrap matrix format so the
    same lookup code path works for both.
    """
    out: dict[str, dict[str, list[str]]] = {}
    for src, targets in _runtime_matrix.items():
        out[src] = {tgt: list(rels) for tgt, rels in targets.items()}
    return out


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def validate(source_label: str, relation: str, target_label: str) -> bool:
    """Check if a proposed edge triple is legal per the edge contract.

    Validates that *source_label* is a known :class:`NodeType`,
    *relation* is a known edge type (bootstrap or runtime), and the
    triple ``(source_label, relation, target_label)`` exists in the
    bootstrap or runtime adjacency matrix.

    **Wildcard handling:**  If a source's target mapping contains the
    special key ``"*"``, *any* target label is accepted for the listed
    relations (e.g. ``Chunk -- EXTRACTED_TO --> (anything)``).

    Args:
        source_label: The label of the source node (e.g. ``"Bug"``).
        relation: The edge type (e.g. ``"AFFECTS"``).
        target_label: The label of the target node (e.g. ``"Component"``).

    Returns:
        ``True`` if the triple is legal per the merged (bootstrap +
        runtime) contract, ``False`` otherwise.

    Raises:
        ValueError: If *source_label* is not a valid :class:`NodeType`,
            or *relation* is not a known edge type (bootstrap
            :class:`EdgeType` or runtime-registered via
            :func:`register_edge_type`).
    """
    from .models import NodeType, is_edge_type

    # --- validate source_label is a known NodeType (by value) ---------------
    try:
        NodeType(source_label)
    except ValueError:
        raise ValueError(
            f"'{source_label}' is not a valid NodeType. "
            f"Must be one of {sorted(m.value for m in NodeType)}"
        ) from None

    # --- validate relation is a known edge type -----------------------------
    if not is_edge_type(relation):
        raise ValueError(
            f"'{relation}' is not a valid EdgeType. "
            f"Must be a member of EdgeType or registered via register_edge_type()."
        )

    # --- check the merged adjacency matrix ----------------------------------
    # Iterate over both the bootstrap matrix and a runtime snapshot so that
    # the same lookup logic applies to both.
    for matrix in (_BOOTSTRAP_MATRIX, _parse_runtime_for_validation()):
        if source_label not in matrix:
            continue

        targets = matrix[source_label]

        # Wildcard target: "*" matches ANY target_label for the relation.
        if "*" in targets and relation in targets["*"]:
            return True

        # Exact target match
        if target_label in targets and relation in targets[target_label]:
            return True

    return False


def register_edge(source: str, relation: str, target: str) -> bool:
    """Register a new legal triple in the in-memory adjacency matrix.

    The *source* and *target* labels must be valid :class:`NodeType`
    values, or the wildcard ``"*"``.  The *relation* must be a known
    edge type (bootstrap :class:`EdgeType` or previously registered
    via :func:`register_edge_type`).

    Runtime-registered edges **do not** persist to ``edge-contract.json``
    in Stage A1 — they live in memory only.

    Args:
        source: The source :class:`NodeType` label or ``"*"``.
        relation: A known edge type string.
        target: The target :class:`NodeType` label or ``"*"``.

    Returns:
        ``True`` if the triple was newly added, ``False`` if it was
        already registered.

    Raises:
        ValueError: If *source* is not a valid :class:`NodeType` and
            not ``"*"``; *relation* is not a known edge type; or
            *target* is not a valid :class:`NodeType` and not ``"*"``.
    """
    from .models import NodeType, is_edge_type

    # --- validate source ----------------------------------------------------
    if source != "*":
        try:
            NodeType(source)
        except ValueError:
            raise ValueError(
                f"'{source}' is not a valid NodeType. "
                f"Must be one of {sorted(m.value for m in NodeType)} or '*'."
            ) from None

    # --- validate relation --------------------------------------------------
    if not is_edge_type(relation):
        raise ValueError(
            f"'{relation}' is not a known edge type. "
            f"Must be a member of EdgeType or registered via register_edge_type()."
        )

    # --- validate target ----------------------------------------------------
    if target != "*":
        try:
            NodeType(target)
        except ValueError:
            raise ValueError(
                f"'{target}' is not a valid NodeType. "
                f"Must be one of {sorted(m.value for m in NodeType)} or '*'."
            ) from None

    # --- register the triple ------------------------------------------------
    if source not in _runtime_matrix:
        _runtime_matrix[source] = {}
    if target not in _runtime_matrix[source]:
        _runtime_matrix[source][target] = set()

    if relation in _runtime_matrix[source][target]:
        return False  # already present

    _runtime_matrix[source][target].add(relation)
    return True


def get_registered_edges() -> list[tuple[str, str, str]]:
    """Return all runtime-registered triples.

    Returns:
        A list of ``(source, relation, target)`` tuples in insertion
        order (grouped by source, then target, then relation).
    """
    result: list[tuple[str, str, str]] = []
    for src, targets in _runtime_matrix.items():
        for tgt, rels in targets.items():
            for rel in rels:
                result.append((src, rel, tgt))
    return result
