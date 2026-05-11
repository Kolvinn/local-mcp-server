"""Taxonomy loader and classification validator for the Memory Manager.

Provides functions to load the taxonomy schema from disk, validate
classifications against it, and extract payload index definitions.
"""

from __future__ import annotations

import json
import os
from typing import Any

_TAXONOMY_PATH: str = "docs/rag-dev/taxonomy-schema.json"
_taxonomy_cache: dict[str, Any] | None = None


class ClassificationError(ValueError):
    """Raised when a classification value is not valid per the taxonomy."""


def load_taxonomy() -> dict[str, Any]:
    """Load the taxonomy schema from disk and return the parsed dict.

    The taxonomy file is read from ``docs/rag-dev/taxonomy-schema.json``
    relative to the project root (current working directory).  Results are
    cached in a module-level singleton so subsequent calls are O(1).

    Returns:
        The parsed taxonomy as a ``dict``.

    Raises:
        FileNotFoundError: If ``taxonomy-schema.json`` does not exist.
        json.JSONDecodeError: If the file contains malformed JSON.
    """
    global _taxonomy_cache

    if _taxonomy_cache is not None:
        return _taxonomy_cache

    path = os.getenv("TAXONOMY_PATH", _TAXONOMY_PATH)
    with open(path, encoding="utf-8") as f:
        _taxonomy_cache = json.load(f)

    return _taxonomy_cache


def validate_classification(
    taxonomy: dict[str, Any],
    category_type: str,
    category: str,
    tags: list[str],
) -> bool:
    """Check that *category_type*, *category*, and each *tag* exist in the taxonomy.

    Args:
        taxonomy: The parsed taxonomy dict from :func:`load_taxonomy`.
        category_type: One of the known category types (e.g. ``"knowledge"``).
        category: A subcategory key under the given *category_type*.
        tags: A list of tag keys.  May be empty.

    Returns:
        ``True`` if all values are valid.

    Raises:
        ClassificationError: With a descriptive message when any value is
            unknown according to the taxonomy schema.
    """
    # Validate category_type
    if category_type not in taxonomy["category_types"]:
        raise ClassificationError(
            f"Unknown category_type: {category_type}"
        )

    # Validate category (subcategory)
    subcats = taxonomy["categories"][category_type]["subcats"]
    if category not in subcats:
        raise ClassificationError(
            f"Unknown category: {category} for type {category_type}"
        )

    # Validate each tag
    valid_tags = taxonomy["categories"][category_type]["tags"]
    for tag in tags:
        if tag not in valid_tags:
            raise ClassificationError(
                f"Unknown tag: {tag} for type {category_type}"
            )

    return True


def get_payload_indexes(
    taxonomy: dict[str, Any],
) -> list[tuple[str, str]]:
    """Extract ``(field_name, index_type)`` pairs from the taxonomy's payload indexes.

    Args:
        taxonomy: The parsed taxonomy dict from :func:`load_taxonomy`.

    Returns:
        A list of ``(field_name, index_type)`` tuples, e.g.::

            [("category_type", "keyword"),
             ("category", "keyword"),
             ("tags", "keyword_list"),
             ...]
    """
    return [
        (field_name, field_schema)
        for field_name, field_schema in taxonomy["payload_indexes"].items()
    ]
