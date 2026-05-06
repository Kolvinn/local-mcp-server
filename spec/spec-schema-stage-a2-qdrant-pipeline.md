---
title: Stage A2 — Qdrant Ingestion Pipeline
version: 1.0
date_created: 2026-05-06
owner: RAG Flow Architect
tags: [infrastructure, schema, process, qdrant, ingestion]
---

# Introduction

Stage A2 of the GraphRAG Memory Manager implementation plan. Builds on A1 core models to deliver the Qdrant vector store ingestion pipeline: chunking, embedding, classification, and upsert. No graph database integration — that is A3.

## 1. Purpose & Scope

**Purpose**: Produce a working ingestion pipeline that accepts a file path, classifies its content, chunks it, embeds the chunks via Ollama (model from `EMBEDDING_MODEL`), and upserts them into Qdrant with correct payload structure.

**Audience**: Implementer subagents building the 6 files defined below.

**In scope**:
- Qdrant collection creation with payload indexes
- Text chunking (paragraph boundaries)
- LLM classification (deepseek-flash → Category + tags)
- Text embedding (model from `EMBEDDING_MODEL` via Ollama)
- CLI ingest script accepting a file path
- Idempotent upsert (UUID chunk_id)

**Out of scope**:
- Graph DB integration
- Entity extraction
- Session tracking
- Reingestion logic
- `graph_node_id` population (leave `null`)

## 2. Definitions

| Term | Definition |
|------|-----------|
| **Qdrant** | Vector database storing chunk vectors + payload, running at `QDRANT_HOST:QDRANT_PORT` |
| **nomic-embed-text** | Embedding model specified by `EMBEDDING_MODEL` env var, served via Ollama. Produces vectors of model-specific dimensionality. |
| **deepseek-flash** | LLM accessed via opencode-go subscription; used for classification |
| **Chunk** | A semantic unit of text (paragraph or section) with a UUID, category, tags, and vector |
| **Category** | Singular, mutually exclusive label from A1's `Category` enum |
| **Tags** | Cross-cutting labels from A1's `TagDimension` taxonomy |
| **Idempotent upsert** | Inserting a point with an existing `chunk_id` replaces it rather than creating a duplicate |

## 3. Requirements, Constraints & Guidelines

### Requirements

- **REQ-001**: Pipeline shall accept a single file path and produce populated Qdrant points
- **REQ-002**: Qdrant collection (name from `QDRANT_COLLECTION_NAME` env var) shall be created with vector dimensions and distance metric appropriate for the model specified by `EMBEDDING_MODEL`
- **REQ-003**: Chunk units shall be paragraphs separated by double newlines (`\n\n`); if a paragraph exceeds ~1000 chars, split on single newlines
- **REQ-004**: Each chunk shall be classified via deepseek-flash using a structured prompt that returns `{category: str, tags: [str]}`
- **REQ-005**: Each chunk shall be embedded via Ollama using the model specified by `EMBEDDING_MODEL` env var
- **REQ-006**: Chunk IDs shall be UUIDv4, generated at ingest time
- **REQ-007**: Upserting a chunk with an existing `chunk_id` shall replace the point (idempotent)
- **REQ-008**: CLI entry point shall accept a positional file path argument and print a result summary

### Constraints

- **CON-001**: `graph_node_id` payload field shall be set to `null` — not populated until A4
- **CON-002**: Collection name is read from `QDRANT_COLLECTION_NAME` env var (default: `memory_chunks`)
- **CON-003**: All configuration values (Qdrant host, Ollama URL) shall come from environment variables — no hardcoded values
- **CON-004**: The classifier must import and use A1's `Category` enum values to constrain its output
- **CON-005**: Payload indexes shall be created after the first upsert to avoid indexing an empty collection

### Guidelines

- **GUD-001**: Chunker should strip excessive whitespace but preserve meaningful line structure (code blocks, lists)
- **GUD-002**: Embedder should batch requests to Ollama where practical (default: single text per call for simplicity)
- **GUD-003**: Ingest should log progress (chunk count, upsert count) to stdout

## 4. Interfaces & Data Contracts

### 4.1 Qdrant Collection Schema

**Collection**: Name from `QDRANT_COLLECTION_NAME` env var (default: `memory_chunks`)
- Vectors: dimensions determined by `EMBEDDING_MODEL` (for nomic-embed-text: 768d), Cosine distance
- Payload indexes (keyword): `category`, `tags`, `status`, `graph_node_id`, `validated_at`, `version`, `source`

**Point payload**:

```python
{
    "chunk_id":       str,       # UUIDv4 — immutable identity
    "graph_node_id":  None,      # str in future; null for A2
    "session_id":     str,       # placeholder: "a2-ingest"
    "category":       str,       # one of: technical_fact, bug, decision, goal, code_symbol, documentation, exploration_finding, session_memory
    "tags":           list[str], # from TagDimension taxonomy
    "content":        str,       # chunk text
    "source":         str,       # origin file path
    "version":        int,       # monotonic, starts at 1
    "validated_at":   int,       # unix timestamp of ingest
    "status":         str,       # "active"
}
```

### 4.2 Chunker Interface

```python
def chunk(text: str) -> list[str]:
    """Split text into semantic chunks (paragraph boundaries).
    Returns list of chunk strings, each with consistent whitespace."""
```

### 4.3 Classifier Interface

```python
def classify(text: str) -> tuple[str, list[str]]:
    """Classify a chunk of text.
    Returns (category: str, tags: list[str]).
    Category must be a valid Category enum value.
    Tags must be valid TagDimension strings."""
```

The LLM prompt shall constrain output to valid Category values and TagDimension taxonomy from A1 models.

### 4.4 Embedder Interface

```python
def embed(texts: list[str]) -> list[list[float]]:
    """Embed one or more texts using the model from EMBEDDING_MODEL env var via Ollama.
    Returns list of vectors with dimensions matching the model."""
```

Ollama endpoint: `POST {OLLAMA_URL}/api/embeddings` with `{"model": os.getenv("EMBEDDING_MODEL"), "prompt": text}`.

### 4.5 Qdrant Client Interface

```python
class QdrantClient:
    def create_collection(self) -> None: ...
    def upsert(self, points: list[dict]) -> None: ...
    def search(self, query_vector: list[float], limit: int = 10, filter: dict = None) -> list[dict]: ...
    def scroll(self, filter: dict = None, limit: int = 100) -> list[dict]: ...
    def count(self) -> int: ...
```

### 4.6 Ingest Interface

```python
def ingest_file(path: str) -> IngestResult:
    """Full pipeline for a single file.
    1. Read file
    2. Chunk
    3. Classify each chunk
    4. Embed each chunk content
    5. Upsert to Qdrant
    6. Return result summary"""
```

```python
@dataclass
class IngestResult:
    file_path: str
    chunks: int
    category: str          # majority category across chunks
    chunk_ids: list[str]   # all UUIDs produced
```

### 4.7 CLI Entry Point

```bash
python scripts/ingest_test.py <file_path>
```

Output: prints IngestResult summary, total Qdrant point count.

## 5. Acceptance Criteria

- **AC-001**: Given `docs/context/stack.md`, When ingested, Then the Qdrant collection (from `QDRANT_COLLECTION_NAME`) contains >0 points
- **AC-002**: Given a session summary file, When ingested, Then at least one chunk has a coherent category (manual spot-check)
- **AC-003**: Given `docs/context/stack.md` ingested, When vector search for "what embedding model is used?", Then at least one result's content contains "nomic-embed-text"
- **AC-004**: Given any file ingested, When filtered search for `category=bug`, Then all returned points have category `bug` (may return 0 results — that's valid)
- **AC-005**: Given a file ingested twice, When checking Qdrant point count, Then count equals chunks from the file (no duplicates — idempotent upsert)
- **AC-006**: CLI entry point exits 0 on success and prints a result summary with chunk count and category

## 6. Test Automation Strategy

- **Test Levels**: Unit tests for chunker, classifier (mocked LLM), embedder (mocked Ollama). Integration tests require live Qdrant + Ollama.
- **Frameworks**: pytest (>=8.3.4) already installed in venv
- **Test directory**: `src/tests/test_a2_*.py` or within `src/memory/tests/` — implementer's choice
- **Test isolation**: Use a test-specific Qdrant collection (or the same collection with `scroll` + `delete` cleanup)
- **Coverage**: Focus on pipeline integration — can a file go from path → Qdrant points end-to-end
- **Mock strategy**: Classifier and embedder can be mocked with deterministic responses for unit tests; Qdrant client can be mocked for chunker/classifier/embedder logic tests

## 7. Rationale & Context

**Why paragraph chunking first**: Simple, predictable, no LLM dependency. Semantic boundary chunking via LLM can be added later if paragraph-chunking proves insufficient.

**Why idempotent upsert**: Enables re-running ingestion without creating duplicates. UUID chunk_id is stable per chunk — if same UUID is upserted, Qdrant replaces the point. This is foundational for A5 reingestion.

**Why collection name from env var**: Collection name may change between development and production. Env var avoids re-deployment to change it.

**Why graph_node_id = null now**: Graph nodes don't exist until A3. Populating `graph_node_id` requires bidirectional linkage in A4.

## 8. Dependencies & External Integrations

### External Systems
- **EXT-001**: Qdrant vector database — host:port from `QDRANT_HOST` and `QDRANT_PORT` env vars. HTTP REST API.
- **EXT-002**: Ollama embedding service — URL from `OLLAMA_URL` env var. Model: specified by `EMBEDDING_MODEL` env var (currently nomic-embed-text, 768d, ~274MB).

### Third-Party Services
- **SVC-001**: deepseek-flash LLM via opencode-go subscription — used for content classification.

### Data Dependencies
- **DAT-001**: A1 core models — `Category` enum, `TagDimension` taxonomy, `EdgeType` enums. Import from `src.memory.models` via relative import.
- **DAT-002**: A1 edge contract (`docs/rag-dev/edge-contract.json`) — not directly used in A2 but referenced for tag consistency.

### Infrastructure Dependencies
- **INF-001**: Python 3.14.4 venv at `src/.venv/` — managed by uv.
- **INF-002**: Qdrant client library — may need `pip install qdrant-client` via `uv pip install qdrant-client` if not present.
- **INF-003**: httpx (async HTTP client) — already in pyproject.toml or available via uv.

### Technology Platform Dependencies
- **PLT-001**: Python 3.14+ — required for type hint features used in A1 models.
- **PLT-002**: Pydantic >=2.10.6 — already installed, used by A1 models.

## 9. Examples & Edge Cases

### Chunker behavior with various inputs

```python
# Standard paragraph split
text = "First paragraph.\n\nSecond paragraph.\n\nThird paragraph."
chunk(text) → ["First paragraph.", "Second paragraph.", "Third paragraph."]

# Single newline (within paragraph boundary — keep as one)
text = "Line one\nLine two\n\nNext paragraph."
chunk(text) → ["Line one\nLine two", "Next paragraph."]

# Long paragraph (exceeds ~1000 chars) — split on single newlines
text = "A" * 500 + "\n" + "B" * 500 + "\n\n" + "C" * 100
chunk(text) → ["A" * 500 + "\n" + "B" * 500, "C" * 100]

# Code block with backticks — preserve as one chunk if no double newline inside
text = "```python\nprint('hello')\nprint('world')\n```"
chunk(text) → ["```python\nprint('hello')\nprint('world')\n```"]

# Empty file
chunk("") → []
```

### Classifier behavior

```python
# Technical documentation → technical_fact
classify("Qdrant is a vector database that supports HNSW indexing...")
→ ("technical_fact", ["qdrant", "infra"])

# Bug report → bug
classify("Nomic embed returns 502 when batch size exceeds 100")
→ ("bug", ["ollama", "bug"])

# Session memory → session_memory
classify("Yesterday we decided to use Option A for the ingestion pipeline")
→ ("session_memory", ["architecture"])
```

### Idempotent upsert

```python
# First ingest
ingest_file("stack.md") → IngestResult(chunks=5, ...)
qdrant.count() → 5

# Same file again (same chunk UUIDs if deterministic; otherwise new UUIDs = new points)
ingest_file("stack.md") → IngestResult(chunks=5, ...)
qdrant.count() → 5  # still 5 — upsert, not append
```

**Note on UUID determinism**: If chunk_id is derived from content hash, re-ingest produces same UUIDs → upsert replaces. If UUIDs are random, re-ingest produces new points. Implementer shall choose content-hash-based UUIDs for true idempotency. Use `uuid.uuid5(uuid.NAMESPACE_DNS, f"{source}:{chunk_index}:{content_hash}")` or similar.

## 10. Validation Criteria

- **VAL-001**: `ingest_test.py` prints chunk count ≥ 0 and does not crash on any valid text file
- **VAL-002**: Qdrant collection (from `QDRANT_COLLECTION_NAME`) exists with vector dimensions matching `EMBEDDING_MODEL` and Cosine distance after first ingest
- **VAL-003**: Payload indexes exist on `category`, `tags`, `status`, `graph_node_id`, `validated_at`, `version`, `source` on the collection after first ingest
- **VAL-004**: All upserted points have non-null `chunk_id`, `category`, `content`, `source` fields
- **VAL-005**: All upserted points have `graph_node_id: null`
- **VAL-006**: Category values are valid `Category` enum members (no typos, no free-form strings)
- **VAL-007**: Vector search returns results sorted by Cosine similarity (lower score = more similar)

## 11. Related Specifications / Further Reading

- [Parent spec: GraphRAG Memory Manager](../docs/rag-dev/spec.md) — full architecture, node taxonomy, edge contract
- [Stage A1 spec — Core Models](../spec/spec-schema-stage-a1-core-models.md) — Category, TagDimension, EdgeType enums
- [Edge contract](../docs/rag-dev/edge-contract.json) — adjacency matrix for edge validation (A3+)
- [Session handoff](../docs/rag-dev/session-handoff.md) — A1 completion status, environment details
- [Stack context](../docs/context/stack.md) — Qdrant/Ollama host/port details
- [Conventions](../docs/context/conventions.md) — import style, testing patterns
