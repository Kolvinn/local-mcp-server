"""Text classifier for ingested chunks.

Translates raw text into a (category, tags) pair using keyword heuristics.
This is a **mock implementation** — it will be replaced with deepseek-flash
LLM inference via opencode-go subscription once that invocation interface is
specified.

Usage::

    from memory.classifier import classify

    category, tags = classify(
        "Qdrant is a vector database that supports HNSW indexing..."
    )
    # → ("technical_fact", ["qdrant", "infra"])
"""

from __future__ import annotations

import re
from typing import ClassVar

from .models import Category


# ---------------------------------------------------------------------------
# Heuristic rules
# ---------------------------------------------------------------------------

# Priority-ordered list of (keyword_pattern, category) rules.
# First match wins. Patterns are compiled once at module load.
_CATEGORY_RULES: ClassVar[list[tuple[re.Pattern[str], Category]]] = [
    # Bug / error keywords (check before generic technical)
    (re.compile(r"\b(50[0-9]|4[0-9][0-9]|crash|exception|traceback|fail(ed|ure)?|bug)\b", re.IGNORECASE), Category.BUG),
    # Session memory — retrospective / recap language (before decision: "Yesterday we decided..." is session memory)
    (re.compile(r"\b(yesterday|earlier|last (week|session|time)|we (decided|talked|discussed))\b", re.IGNORECASE), Category.SESSION_MEMORY),
    # Decision keywords
    (re.compile(r"\b(decid(e|ed)|chose|selected|opted|concluded|agreed|elect(ed)?)\b", re.IGNORECASE), Category.DECISION),
    # Goal / objective keywords
    (re.compile(r"\b(goal|objective|aim|target|milestone|plan to|intend to)\b", re.IGNORECASE), Category.GOAL),
    # Code symbols — backtick blocks, function/method/class definitions, imports
    (re.compile(r"(```\w*\n|def \w+|class \w+|import |from \w+ import)"), Category.CODE_SYMBOL),
    # Exploration / research
    (re.compile(r"\b(explor(e|ed|ation)|investigat(e|ed|ion)|research(ed)?|findings?)\b", re.IGNORECASE), Category.EXPLORATION_FINDING),
    # Technical facts (default for infra / tech content)
    (re.compile(r"\b(vector database|index|embedding|ollama|qdrant|memgraph|HNSW|API|endpoint|server|database|query|model|inference)\b", re.IGNORECASE), Category.TECHNICAL_FACT),
]

# Keyword-to-tag mappings for domain and scope detection.
_SCOPE_KEYWORDS: ClassVar[list[tuple[re.Pattern[str], str]]] = [
    (re.compile(r"\b(ollama|nomic)\b", re.IGNORECASE), "ollama"),
    (re.compile(r"\bqdrant\b", re.IGNORECASE), "qdrant"),
    (re.compile(r"\b(memgraph|cypher)\b", re.IGNORECASE), "memgraph"),
    (re.compile(r"\btraefik\b", re.IGNORECASE), "traefik"),
    (re.compile(r"\bopencode\b", re.IGNORECASE), "opencode"),
]

_DOMAIN_KEYWORDS: ClassVar[list[tuple[re.Pattern[str], str]]] = [
    # Infra — check before data so "vector database" → infra, not data
    (re.compile(r"\b(infra|infrastructure|deploy|host|container|docker|vector database|HNSW|indexing)\b", re.IGNORECASE), "infra"),
    # Architecture — before devops so "ingestion pipeline" → architecture, not devops
    (re.compile(r"\b(architecture|design|pattern|component|system|pipeline)\b", re.IGNORECASE), "architecture"),
    (re.compile(r"\b(code|function|class|method|variable|import|module)\b", re.IGNORECASE), "code"),
    (re.compile(r"\btest(s|ing|ed)?\b", re.IGNORECASE), "testing"),
    (re.compile(r"\b(data|dataset|database|schema)\b", re.IGNORECASE), "data"),
    (re.compile(r"\b(security|auth|permission|encrypt|token)\b", re.IGNORECASE), "security"),
    (re.compile(r"\b(ux|user interface|frontend|ui)\b", re.IGNORECASE), "ux"),
    (re.compile(r"\bdevops|ci|cd\b", re.IGNORECASE), "devops"),
]

_QUALITY_KEYWORDS: ClassVar[list[tuple[re.Pattern[str], str]]] = [
    # HTTP error codes and error keywords imply bug quality
    (re.compile(r"\b(50[0-9]|4[0-9][0-9]|error|exception|traceback)\b", re.IGNORECASE), "bug"),
    (re.compile(r"\bworkaround\b", re.IGNORECASE), "workaround"),
    (re.compile(r"\b(verified|confirmed|resolved)\b", re.IGNORECASE), "verified"),
    (re.compile(r"\bdeprecated\b", re.IGNORECASE), "deprecated"),
    (re.compile(r"\b(unstable|flaky|intermittent)\b", re.IGNORECASE), "unstable"),
    (re.compile(r"\b(critical|severe|blocker)\b", re.IGNORECASE), "critical"),
]

_PHASE_KEYWORDS: ClassVar[list[tuple[re.Pattern[str], str]]] = [
    (re.compile(r"\borient(ation|ed)?\b", re.IGNORECASE), "orient"),
    (re.compile(r"\bgather(ing|ed)?\b", re.IGNORECASE), "gather"),
    (re.compile(r"\bspec(ification)?\b", re.IGNORECASE), "spec"),
    (re.compile(r"\b(implement|code|write|build)\b", re.IGNORECASE), "code"),
    (re.compile(r"\breview(ed|ing)?\b", re.IGNORECASE), "review"),
    (re.compile(r"\b(deploy|release|ship)\b", re.IGNORECASE), "deploy"),
]


def _match_first(text: str, rules: list[tuple[re.Pattern[str], str]]) -> str | None:
    """Return the value from the first matching rule, or *None*."""
    for pattern, value in rules:
        if pattern.search(text):
            return value
    return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def classify(text: str) -> tuple[str, list[str]]:
    """Classify a chunk of text using keyword heuristics.

    Args:
        text: The chunk text to classify.

    Returns:
        A ``(category, tags)`` tuple where *category* is a valid
        :class:`Category` enum value and *tags* is a list of
        :class:`TagDimension` taxonomy strings drawn from the bootstrap
        registry values.

    Example:
        >>> classify("Qdrant is a vector database that supports HNSW indexing...")
        ('technical_fact', ['qdrant', 'infra'])

        >>> classify("Nomic embed returns 502 when batch size exceeds 100")
        ('bug', ['ollama', 'bug'])

        >>> classify("Yesterday we decided to use Option A for the ingestion pipeline")
        ('session_memory', ['architecture'])
    """
    if not text or not text.strip():
        return (Category.DOCUMENTATION, ["code"])

    text_stripped = text.strip()

    # --- Category ---
    category: Category = Category.DOCUMENTATION  # default fallback
    for pattern, cat in _CATEGORY_RULES:
        if pattern.search(text_stripped):
            category = cat
            break

    # --- Tags ---
    tags: list[str] = []

    scope_tag = _match_first(text_stripped, _SCOPE_KEYWORDS)
    domain_tag = _match_first(text_stripped, _DOMAIN_KEYWORDS)
    quality_tag = _match_first(text_stripped, _QUALITY_KEYWORDS)
    phase_tag = _match_first(text_stripped, _PHASE_KEYWORDS)

    if scope_tag is not None:
        tags.append(scope_tag)
    if domain_tag is not None:
        tags.append(domain_tag)
    if quality_tag is not None:
        tags.append(quality_tag)
    if phase_tag is not None:
        tags.append(phase_tag)

    # Ensure at least one tag exists
    if not tags:
        tags.append("code")

    return (category.value, tags)
