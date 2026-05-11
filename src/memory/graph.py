"""LangGraph state graph for the Memory Manager ingestion pipeline.

Defines a 3-node linear graph::

    START -> validate_classify -> build_payload -> embed_ingest -> END

All configuration is read from environment variables (see ``embedder.py``
for shared constants).
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime
from typing import Any, Literal, TypedDict

from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from litellm import completion
from pydantic import BaseModel, Field
from qdrant_client.models import PointStruct

from . import embedder, qdrant_client, taxonomy_loader

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Data Structures  (§1)
# ---------------------------------------------------------------------------


class MemoryManagerInput(BaseModel):
    """Input model for the memory ingestion pipeline."""

    content: str = Field(..., min_length=1)
    category_type: Literal["knowledge", "objective", "learning", "thought"] | None = None
    category: str | None = None
    tags: list[str] = Field(default_factory=list)
    source: str = Field(..., min_length=1)


class MemoryManagerOutput(BaseModel):
    """Output model returned by the ``ingest()`` shortcut."""

    chunk_id: str | None = None
    ingested_at: str | None = None
    error: str | None = None


class TaxonomyClassification(BaseModel):
    """Classification result returned by the LLM."""

    category_type: Literal["knowledge", "objective", "learning", "thought"]
    category: str
    tags: list[str]
    key_words: list[str]


class QdrantPayload(BaseModel):
    """Payload stored in the Qdrant point for each memory chunk."""

    chunk_id: str
    graph_node_id: str | None = None  # always None for MVP
    category_type: str
    category: str
    tags: list[str]
    key_words: list[str]
    content: str
    summary: str | None = None  # always None for MVP
    source: str
    status: str = "active"
    version: int = 1
    created_at: str  # ISO8601
    updated_at: str  # ISO8601


class MemoryManagerState(TypedDict):
    """LangGraph state schema for the ingestion pipeline."""

    content: str
    category_type: str | None
    category: str | None
    tags: list[str]
    source: str
    key_words: list[str]
    chunk_id: str | None
    payload: dict | None
    point_struct: PointStruct | None
    ingested_at: str | None
    error: str | None


# ---------------------------------------------------------------------------
# Error classes  (§7)
# ---------------------------------------------------------------------------


class LLMError(RuntimeError):
    """Raised when a LiteLLM completion call fails or returns unparseable JSON."""


# ---------------------------------------------------------------------------
# Node 1: validate_classify
# ---------------------------------------------------------------------------


def validate_classify_node(state: MemoryManagerState) -> dict[str, Any]:
    """Ensure ``category_type``, ``category``, ``tags``, and ``key_words``
    are present and valid.

    If the caller provided ``category_type`` and ``category`` they are
    validated directly against the taxonomy.  Otherwise the LLM is called
    to classify the content.
    """
    try:
        taxonomy = taxonomy_loader.load_taxonomy()
    except Exception as exc:
        return {"error": f"Failed to load taxonomy: {exc}"}

    # ── Case 1: caller provided full classification ──
    if state.get("category_type") is not None and state.get("category") is not None:
        try:
            taxonomy_loader.validate_classification(
                taxonomy,
                state["category_type"],
                state["category"],
                state.get("tags", []),
            )
        except ValueError as exc:
            return {"error": str(exc)}

        return {
            "category_type": state["category_type"],
            "category": state["category"],
            "tags": state.get("tags", []),
            "key_words": state.get("key_words", []),
        }

    # ── Case 2: classify via LLM ──
    return _classify_via_llm(taxonomy, state)


def _classify_via_llm(
    taxonomy: dict[str, Any],
    state: MemoryManagerState,
) -> dict[str, Any]:
    """Call the LLM to classify ``state["content"]`` against the taxonomy.

    Retries **once** on parse failure (unparseable JSON).  Validation
    failures (unknown category_type / category / tag) are **not** retried
    — they bubble up as errors.
    """
    system_prompt = (
        "You are a text classifier. Classify this text using the taxonomy below.\n"
        "Return JSON with keys: category_type, category, tags, key_words.\n"
        f"Taxonomy: {json.dumps(taxonomy['categories'])}\n"
        f"Text: {state['content']}"
    )

    # Attempt 1
    result_dict = _llm_classify(system_prompt)
    if result_dict is None:
        # Retry once with error injected into prompt
        result_dict = _llm_classify(
            system_prompt
            + "\n\nNote: The previous attempt failed to return valid JSON. "
            "Please ensure the response is valid JSON."
        )

    if result_dict is None:
        return {"error": "LLM classification failed after retry"}

    # Parse into TaxonomyClassification
    try:
        classification = TaxonomyClassification.model_validate(result_dict)
    except Exception as exc:
        return {"error": f"LLM classification returned invalid fields: {exc}"}

    # Validate against taxonomy
    try:
        taxonomy_loader.validate_classification(
            taxonomy,
            classification.category_type,
            classification.category,
            classification.tags,
        )
    except ValueError as exc:
        return {"error": str(exc)}

    return {
        "category_type": classification.category_type,
        "category": classification.category,
        "tags": classification.tags,
        "key_words": classification.key_words,
    }


def _llm_classify(system_prompt: str) -> dict[str, Any] | None:
    """Make a single LLM completion call and parse the JSON response.

    Returns ``None`` if the call fails or the response is unparseable.
    """
    try:
        response = completion(
            model=embedder.LLM_MODEL,
            api_base=embedder.LITE_LLM_URL,
            api_key=embedder.LITE_LLM_API_KEY,
            messages=[{"role": "system", "content": system_prompt}],
            response_format={"type": "json_object"},
        )
    except Exception as exc:
        logger.warning("LLM completion call failed: %s", exc)
        return None

    try:
        raw = response.choices[0].message.content  # type: ignore[union-attr]
        return json.loads(raw)
    except (IndexError, AttributeError, json.JSONDecodeError, TypeError) as exc:
        logger.warning("Failed to parse LLM response as JSON: %s", exc)
        return None


# ---------------------------------------------------------------------------
# Node 2: build_payload
# ---------------------------------------------------------------------------


def build_payload_node(state: MemoryManagerState) -> dict[str, Any]:
    """Assemble the ``QdrantPayload`` and wrap into a ``PointStruct``
    (vectors are added in node 3).
    """
    chunk_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat() + "Z"

    payload = QdrantPayload(
        chunk_id=chunk_id,
        graph_node_id=None,
        category_type=state["category_type"],
        category=state["category"],
        tags=state.get("tags", []),
        key_words=state.get("key_words", []),
        content=state["content"],
        summary=None,
        source=state["source"],
        status="active",
        version=1,
        created_at=now,
        updated_at=now,
    )

    point = PointStruct(
        id=chunk_id,
        vector={},
        payload=payload.model_dump(),
    )

    return {
        "chunk_id": chunk_id,
        "payload": payload.model_dump(),
        "point_struct": point,
    }


# ---------------------------------------------------------------------------
# Node 3: embed_ingest
# ---------------------------------------------------------------------------


def embed_ingest_node(state: MemoryManagerState) -> dict[str, Any]:
    """Generate all three vectors, attach to the ``PointStruct``,
    and upsert into Qdrant.
    """
    # Ensure collection exists (idempotent)
    try:
        qdrant_client.ensure_collection_exists()
    except Exception as exc:
        return {"error": f"Qdrant collection setup failed: {exc}"}

    # Get embedder
    try:
        emb = embedder.get_embedder()
    except Exception as exc:
        return {"error": f"Failed to initialise embedder: {exc}"}

    point = state["point_struct"]
    if point is None:
        return {"error": "No point_struct in state — cannot embed and ingest"}

    content = state["content"]

    # ── Generate vectors ──
    try:
        point.vector["dense"] = emb.embed(content, embedder.EmbedType.DENSE)
    except Exception as exc:
        return {"error": f"Embedding failed (dense): {exc}"}

    try:
        point.vector["sparse"] = emb.embed(content, embedder.EmbedType.SPARSE)
    except Exception as exc:
        return {"error": f"Embedding failed (sparse): {exc}"}

    try:
        point.vector["multi"] = emb.embed(content, embedder.EmbedType.LATE_INTERACTION)
    except Exception as exc:
        return {"error": f"Embedding failed (late-interaction): {exc}"}

    # ── Upsert into Qdrant ──
    try:
        qdrant_client.upsert_point(point)
    except Exception as exc:
        return {"error": f"Upsert failed: {exc}"}

    ingested_at = datetime.utcnow().isoformat() + "Z"
    return {"ingested_at": ingested_at}


# ---------------------------------------------------------------------------
# Graph assembly
# ---------------------------------------------------------------------------


def build_graph() -> CompiledStateGraph:
    """Construct, wire, and compile the 3-node ``StateGraph``.

    The compiled graph is cached at module level so subsequent calls are
    O(1) — use :func:`get_graph` for the cached version.

    Graph structure::

        START -> validate_classify -> build_payload -> embed_ingest -> END

    All nodes return ``{"error": ...}`` on failure.  The graph always
    reaches ``END`` regardless of errors.
    """
    builder = (
        StateGraph(MemoryManagerState)
        .add_node("validate_classify", validate_classify_node)
        .add_node("build_payload", build_payload_node)
        .add_node("embed_ingest", embed_ingest_node)
        .add_edge(START, "validate_classify")
        .add_edge("validate_classify", "build_payload")
        .add_edge("build_payload", "embed_ingest")
        .add_edge("embed_ingest", END)
    )
    return builder.compile()


# ---------------------------------------------------------------------------
# Module-level cached graph
# ---------------------------------------------------------------------------

_graph: CompiledStateGraph | None = None


def get_graph() -> CompiledStateGraph:
    """Return the module-level cached compiled graph, building on first call.

    Idempotent — subsequent calls return the same compiled instance.
    """
    global _graph  # noqa: PLW0603
    if _graph is None:
        _graph = build_graph()
    return _graph


# ---------------------------------------------------------------------------
# Shortcut invoke
# ---------------------------------------------------------------------------


def ingest(
    content: str,
    source: str,
    category_type: str | None = None,
    category: str | None = None,
    tags: list[str] | None = None,
) -> MemoryManagerOutput:
    """Convenience wrapper — build input, invoke the graph, return output.

    Args:
        content: The text content to ingest (required, non-empty).
        source: Origin identifier for the content (required, non-empty).
        category_type: Optional pre-classified type
            (one of ``"knowledge"``, ``"objective"``, ``"learning"``,
            ``"thought"``).
        category: Optional pre-classified subcategory.
        tags: Optional list of tag keys.

    Returns:
        A ``MemoryManagerOutput`` with ``chunk_id`` and ``ingested_at``
        on success, or ``error`` populated on failure.
    """
    input_state = MemoryManagerInput(
        content=content,
        source=source,
        category_type=category_type,
        category=category,
        tags=tags or [],
    )

    graph = get_graph()
    result = graph.invoke(input_state.model_dump())

    return MemoryManagerOutput(
        chunk_id=result.get("chunk_id"),
        ingested_at=result.get("ingested_at"),
        error=result.get("error"),
    )
