# Memory Manager — LangGraph Brief

**Purpose:** A compiled LangGraph graph that agents call to ingest text into the dual-store GraphRAG system (Qdrant now; Memgraph deferred). Agents provide content + classification hints; the graph validates, classifies gaps via LLM fallback, and embeds into Qdrant using the hybrid pipeline.

**Deferred:** Redis taxonomy store, Memgraph graph layer, chunking (caller provides pre-chunked content), endpoint exposure.

---

## 1. Graph Structure — Linear 3-Node Pipeline

```
START → validate_classify → build_payload → embed_ingest → END
```

No branching, no Send fan-out, no loops. Linear state flow. Each node returns a partial state dict.

### Node 1: `validate_classify`
- **Inputs from state:** `content`, `category_type` (optional), `category` (optional), `tags` (optional), `source`
- **Logic:**
  1. Load `docs/rag-dev/taxonomy-schema.json` (cached at startup or first call)
  2. If `category_type` + `category` are both provided → validate against schema (raise on invalid)
  3. If `category_type` or `category` are missing/partial → call deepseek-flash LLM to infer from `content`
  4. LLM gets the full taxonomy as a system prompt (~500 tokens) and returns structured classification: `{category_type, category, tags, key_words}`
  5. Validate LLM output against schema, return filled classification fields
- **Outputs to state:** `category_type`, `category`, `tags`, `key_words` (all now guaranteed valid)
- **Error conditions:** Invalid category_type (not in schema) → `ValueError`; LLM returns unparseable output → retry once, then `ValueError`

### Node 2: `build_payload`
- **Inputs from state:** all classification fields, `content`, `source`
- **Logic:**
  1. Generate `chunk_id` (UUID4)
  2. Assemble payload dict per the taxonomy-redis brief §3.1:
     ```
     {chunk_id, graph_node_id: None, category_type, category, tags,
      key_words, content, summary: None, source, status: "active",
      version: 1, created_at: ISO8601, updated_at: ISO8601}
     ```
  3. Wrap into `PointStruct` with placeholder vector names (vectors filled by next node)
- **Outputs to state:** `payload` (dict), `point_struct` (PointStruct without vectors yet)
- **Error conditions:** None (pure data assembly)

### Node 3: `embed_ingest`
- **Inputs from state:** `point_struct` (with payload), `content` (for embedding)
- **Logic:**
  1. Call the shared embedder (refactored from `hybrid_embed_test.py`) to produce three vectors:
     - `dense` (nomic-embed, 768-dim, via LiteLLM → Ollama)
     - `sparse` (SPLADE, via FastEmbed)
     - `multi` (ColBERT-small, via FastEmbed, 128-dim multivector)
  2. Attach vectors to `point_struct`
  3. Upsert single point into Qdrant collection `memory_chunks`
- **Outputs to state:** `chunk_id` (confirmation), `ingested_at` (timestamp)
- **Error conditions:** Qdrant unreachable → `ConnectionError`; embedding model fails → `RuntimeError`; upsert rejected → propagate Qdrant error

---

## 2. State Schema (TypedDict)

```python
from typing import TypedDict, Optional

class MemoryManagerState(TypedDict):
    # --- Input fields (caller provides) ---
    content: str                        # The text chunk to ingest
    category_type: Optional[str]        # "knowledge" | "objective" | "learning" | "thought"
    category: Optional[str]             # e.g. "definition", "goal", "error_trace"
    tags: Optional[list[str]]           # e.g. ["p0", "foundational"]
    source: str                         # Origin identifier (file path, agent name, etc.)

    # --- Intermediate fields (populated by nodes) ---
    key_words: list[str]               # Extracted keywords (LLM-filled or caller-provided)
    payload: dict                       # Assembled Qdrant payload (PointStruct payload)
    point_struct: object                # PointStruct ready for vector attachment

    # --- Output fields ---
    chunk_id: str                       # UUID4, returned to caller
    ingested_at: str                    # ISO8601 timestamp
    error: Optional[str]                # Error message if any node fails
```

No reducers needed — all fields are scalar overwrites or single-assignment.

---

## 3. Integration with Existing Code

### What gets refactored from `hybrid_embed_test.py`
- `Embedder` class → extracted into `src/memory/embedder.py`
- `EmbedType` enum → same module
- Collection creation logic → `src/memory/qdrant_setup.py` (create `memory_chunks` collection with named vectors + payload indexes on first run)
- Qdrant client instantiation → `src/memory/qdrant_client.py` (host/port from env)

### What stays in the graph only
- `validate_classify` — net new, reads taxonomy-schema.json
- `build_payload` — net new, assembles the structured payload
- `embed_ingest` — thin wrapper calling the refactored embedder + Qdrant client

### Collection setup (one-time, not in graph)
On first run or when collection doesn't exist: create `memory_chunks` with:
- Named vectors: `dense` (768, COSINE), `sparse` (SPLADE, IDF modifier), `multi` (128, COSINE, multivector, HNSW disabled)
- Payload indexes on: `category_type`, `category`, `tags`, `status`, `graph_node_id`, `source`
  (from taxonomy-schema.json `payload_indexes`)

---

## 4. LLM Classification Fallback

- **Model:** deepseek-flash (via opencode go API)
- **When triggered:** `category_type` or `category` is `None` or missing from state
- **System prompt structure:**
  ```
  You are a text classifier. Given a chunk of text, classify it using this taxonomy:
  <taxonomy-schema.json contents injected here>
  Return JSON: {"category_type": "...", "category": "...", "tags": [...], "key_words": [...]}
  ```
- **Validation:** After LLM returns, check every value against the schema. Unknown values → rejected, not auto-added to schema (unlike the Redis design, which auto-learned).
- **Retry:** If validation fails, retry once with the validation error included in the prompt.

---

## 5. Caller Contract

Agents invoke the compiled graph:

```python
result = memory_manager_graph.invoke({
    "content": "Qdrant uses HNSW for approximate nearest neighbor search",
    "category_type": "knowledge",   # Agent knows what it's storing
    "category": "definition",        # Fully specified → no LLM call
    "source": "agent:explorer"
})
# Returns: {"chunk_id": "uuid-...", "ingested_at": "2026-05-11T...", ...}
```

Minimal invocation (LLM fills gaps):
```python
result = memory_manager_graph.invoke({
    "content": "implementer failed on import because qdrant-client was missing",
    "source": "agent:implementer"
})
# LLM classifies as: category_type="learning", category="error_trace", tags=["failure"]
```

---

## 6. File Layout (target)

```
src/memory/
    graph.py            # StateGraph definition, all three nodes, compile()
    embedder.py         # Refactored Embedder class from hybrid_embed_test.py
    qdrant_client.py    # Qdrant client singleton, collection setup, upsert helper
    taxonomy_loader.py  # Load + cache taxonomy-schema.json, validation helpers
    __init__.py         # Expose compiled graph + invoke shortcut
```

---

## 7. Key Design Decisions

| Decision | Why |
|----------|-----|
| Linear pipeline, no branching | Caller brings intent — no need for routing. Simpler to test, debug, and later extend. |
| LLM as fallback, not primary classifier | Most calls come from agents that know category_type at dispatch time. LLM tokens are expensive; skip when unnecessary. |
| Schema-as-JSON-file, not Redis | Zero infrastructure dependency. taxonomy-schema.json is version-controlled. Redis can wrap it later without graph changes. |
| Single-point ingestion (not batch) | Agent calls are event-driven, not batched. Batch support can layer on later with Send fan-out. |
| No auto-learning of new tags | With Redis, unknown tags get auto-added. With JSON file, they're rejected. Safer for MVP — schema changes are intentional. |
| Separate embedder module | `hybrid_embed_test.py` is a working prototype. Refactoring into a module lets the graph and test script share the same embedder without copy-paste. |
| HNSW disabled for multivectors | Max-similarity metric is non-symmetric; HNSW produces incorrect results. Exact search over prefetched candidates is correct and the documented pattern. |

---

## 8. Out of Scope (explicitly)

- Chunking — caller provides pre-chunked content
- Memgraph ingestion — deferred until Qdrant path is stable
- Redis taxonomy store — deferred; JSON file is source of truth
- Collection lifecycle management (reindexes, schema migrations)
- Endpoint exposure (MCP, HTTP, proxy routing)
- Batch ingestion or parallel chunk processing
- Content deduplication
- Summary generation (LLM-generated `summary` field)
