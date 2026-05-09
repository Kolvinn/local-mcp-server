# Memory Manager MVP — Build Checklist

> **Sibling docs:** [mvp-overview.md](mvp-overview.md) | [mvp-agent-endpoint.md](mvp-agent-endpoint.md) | [mvp-relationships.md](mvp-relationships.md)
> **For each item:** Purpose, what to look at, acceptance criteria. No code — just what and why.

## Phase 0: Verify What's Already Built

A1 (models) and A2 (Qdrant pipeline) were built in a prior session. Verify they work before adding anything.

### 0.1 — Install qdrant-client

| | |
|---|---|
| **Purpose** | A2's `qdrant_client.py` imports `qdrant_client`. If the venv was rebuilt, it's missing. |
| **Look at** | `/home/dev/app/src/.venv`, `uv pip install qdrant-client` |
| **Acceptance** | `python -c "from qdrant_client import QdrantClient; print('ok')"` runs without error |
| **Stack position** | Infrastructure — vector store SDK dependency |

### 0.2 — Run A1 tests

| | |
|---|---|
| **Purpose** | Confirm 82 model/validator tests still pass. These define `Category`, `NodeType`, `EdgeType` enums your graph code depends on. |
| **Look at** | `src/tests/test_models.py`, `cd /home/dev/app/src && .venv/bin/python -m pytest tests/test_models.py -v` |
| **Acceptance** | 82/82 pass |
| **Stack position** | Models layer — validates enums and edge type registry |

### 0.3 — Run A2 acceptance gate (spec §10)

| | |
|---|---|
| **Purpose** | Verify the Qdrant ingestion pipeline actually works end-to-end. A2 was built but never acceptance-tested. |
| **Look at** | `docs/rag-dev/spec.md` §10 Stage A2 acceptance gate (6 criteria) |
| **Acceptance** | 1. Ingest `docs/context/stack.md` → Qdrant has points. 2. Ingest session summary → correct category. 3. Search "what embedding model" → returns nomic-embed-text chunk. 4. Filtered search `category=bug` works. 5. Re-ingest same file → no duplicates. 6. Payload indexes created. |
| **Stack position** | Validation — crosses ingestion pipeline + Qdrant |

---

## Phase 1: Working Classifier

A2 used a keyword-heuristic mock. Replace with real LLM via LiteLLM.

### 1.1 — Replace mock classifier with LiteLLM → deepseek-flash

| | |
|---|---|
| **Purpose** | Real classification produces accurate `Category` + `Tags` for every chunk. This metadata drives: Qdrant filtered search, graph node type selection, edge creation. |
| **Look at** | `src/tests/test_langchain.py` for working LiteLLM config: `ChatLiteLLM(api_base="http://litellm:4000", api_key="sk-1234", model="openai/deepseek-flash")`. Modify `src/memory/classifier.py`: keep the `classify(text) -> (Category, list[str])` signature, replace mock internals with LiteLLM call. |
| **Acceptance** | Ingest a bug report → `category=bug`. Ingest a session summary → `category=session_memory`. Ingest `docs/context/stack.md` → `tags` includes `scope:qdrant`, `scope:ollama`. |
| **Stack position** | LLM inference layer — sits between ingestion entry and chunker |

### 1.2 — Verify classifier integration in ingest pipeline

| | |
|---|---|
| **Purpose** | Confirm `ingest_file()` in `src/memory/ingest.py` calls the new classifier and passes results through to Qdrant payload. |
| **Look at** | `src/memory/ingest.py` — the `classify()` call should produce real (not mock) output. |
| **Acceptance** | Full `python scripts/ingest_test.py docs/context/stack.md` → Qdrant points have meaningful (not "technical_fact") categories. |
| **Stack position** | Ingestion pipeline integration test |

---

## Phase 2: Graph Layer (DictGraphStore)

No Memgraph. No edge contract validation. Just an in-memory graph that stores nodes and edges.

### 2.1 — Create DictGraphStore

| | |
|---|---|
| **Purpose** | A graph you can add nodes/edges to and query. Zero infrastructure — just Python dicts. This stores the relationship side of the dual-store system. |
| **Look at** | Python `dict` with adjacency list pattern. Node storage: `{node_id: {label, properties}}`. Edge storage: adjacency map from source_id → list of (target_id, relationship). Query: simple MATCH-like traversal (find nodes by label, follow edges 1-hop). |
| **Acceptance** | `store.merge_node("Bug", {id: "b1", summary: "test"})` → node exists. `store.merge_edge("b1", "AFFECTS", "c1")` → edge exists. `store.query_nodes("Bug")` → returns `["b1"]`. `store.get_neighbors("b1")` → returns `[("c1", "AFFECTS")]`. |
| **Stack position** | Graph store layer — development implementation, no infrastructure |
| **Files** | `src/memory/graph/__init__.py`, `src/memory/graph/dict_store.py` |

### 2.2 — Classifier-driven node and edge creation

| | |
|---|---|
| **Purpose** | Each ingested chunk produces graph nodes based on its classifier output. This avoids LLM entity extraction (the hardest part of full A3). |
| **How it works** | `category=bug` → `merge_node("Bug", {id, summary: first_sentence_of_chunk})`. `category=decision` → `merge_node("Decision", {id, summary})`. `category=goal` → `merge_node("Goal", {id, summary})`. Then parse tags: `scope:qdrant` → find-or-create `(:Component {name:"qdrant"})`, add edge `(node)-[:AFFECTS]->(component)`. |
| **Look at** | A1 `models.py` for `Category` enum values. `chunker.py` output for chunk text (use first sentence as `summary`). |
| **Acceptance** | Ingest `docs/context/stack.md` → graph has `(:Component {name:"qdrant"})`, `(:Component {name:"ollama"})`, and edges between components mentioned in same chunk. |
| **Stack position** | Ingestion pipeline — between classifier and graph store |

### 2.3 — Wire graph ingestion into ingest.py

| | |
|---|---|
| **Purpose** | `ingest_file("path")` now produces both Qdrant points AND graph nodes/edges in one call. |
| **Look at** | `src/memory/ingest.py` — add graph step after Qdrant upsert. For each chunk: create node from category, create edges from tags, store in DictGraphStore. |
| **Acceptance** | `result = ingest_file("docs/context/stack.md")` → `result.nodes_created > 0` and `result.edges_created > 0`. |
| **Stack position** | Ingestion pipeline orchestrator |

---

## Phase 3: Bidirectional Linkage

Connect Qdrant and the graph so you can traverse from either direction.

### 3.1 — Set graph_node_id in Qdrant payload

| | |
|---|---|
| **Purpose** | After graph node is created, write its ID back into the Qdrant chunk's payload. This is the bridge: vector search hits a chunk → read `graph_node_id` → enter the graph. |
| **Look at** | `qdrant_client.upsert()` already supports payload updates. After `merge_node()` returns a `node_id`, call upsert with the same `chunk_id` and updated `graph_node_id` field. |
| **Acceptance** | Ingest a file. Query Qdrant for a specific `chunk_id` → payload has `graph_node_id` set (not null). |
| **Stack position** | Cross-store linkage — connects vector store to graph store |

### 3.2 — Create :Chunk reference nodes in graph

| | |
|---|---|
| **Purpose** | Enables reverse traversal: graph entity → find its source chunks. A `:Chunk` node is lightweight (just `id` + `graph_node_id`, no content stored). |
| **Look at** | `store.merge_node("Chunk", {id: chunk_id})`, `store.merge_edge(chunk_id, "EXTRACTED_TO", graph_node_id)`. |
| **Acceptance** | Query graph for `:Chunk` nodes → returns one per ingested chunk. Query `(chunk)-[:EXTRACTED_TO]->(node)` → returns the correct entity node. |
| **Stack position** | Graph store — reverse pointer from entity to source |

### 3.3 — Single ingest() call does everything

| | |
|---|---|
| **Purpose** | `ingest_file(path)` produces: Qdrant points + graph nodes + graph edges + `:Chunk` refs + `graph_node_id` in Qdrant. Atomic from the caller's perspective. |
| **Look at** | `src/memory/ingest.py` — ensure all steps run in sequence: classify → chunk → embed → Qdrant upsert → graph node → graph edges → link. |
| **Acceptance** | `python scripts/ingest_test.py docs/context/stack.md` → verify all 5 artifacts exist. |
| **Stack position** | Complete ingestion pipeline |

---

## Phase 4: Retrieval

Search and context retrieval that spans both stores.

### 4.1 — Vector-only search

| | |
|---|---|
| **Purpose** | Basic semantic search against Qdrant. Returns chunks with their metadata. |
| **Look at** | `src/memory/qdrant_client.py` — `search()` method already exists from A2. Wrap it in a clean `search(query, limit=5) -> list[dict]` function. |
| **Acceptance** | `search("what embedding model")` returns chunk containing "nomic-embed-text". Returns `chunk_id`, `content`, `category`, `tags`, `graph_node_id` per result. |
| **Stack position** | Retrieval layer — vector store only |
| **Files** | `src/memory/retrieve.py` |

### 4.2 — Graph-expanded context retrieval

| | |
|---|---|
| **Purpose** | `retrieve_context(query)` does vector search → collects graph_node_ids → 1-hop BFS from each → returns enriched results. This is the "memory injection" capability — returns related knowledge the vector search missed. |
| **Look at** | After vector search: collect all non-null `graph_node_id`s. For each, call `store.get_neighbors(node_id)` to get 1-hop connected nodes. Return chunks for those neighbor nodes too (find their `:Chunk` refs, then Qdrant lookup by chunk_id). |
| **Acceptance** | Query "what issues affect qdrant" → returns not just the Qdrant chunk, but also related bug chunks found via graph traversal. Verify 1-hop expansion adds chunks not in initial vector results. |
| **Stack position** | Retrieval layer — vector search + graph traversal |

### 4.3 — Deduplicate results

| | |
|---|---|
| **Purpose** | Same chunk may appear from vector hit AND as a graph neighbor. Dedup by `chunk_id` to avoid returning duplicate context. |
| **Look at** | Python `dict` keyed by `chunk_id`, merge metadata. |
| **Acceptance** | `retrieve_context(query)` returns no duplicate `chunk_id` values. |
| **Stack position** | Retrieval post-processing |

---

## Phase 5: Agent Endpoint

Wrap the memory manager as LangChain tools. Detailed in [mvp-agent-endpoint.md](mvp-agent-endpoint.md).

### 5.1 — Define LangChain tools

### 5.2 — Create Deep Agent with memory tools

### 5.3 — Test agent invokes memory tools

---

## Dependency Order

```
Phase 0 ──► Phase 1 ──► Phase 2 ──► Phase 3 ──► Phase 4 ──► Phase 5
(verify)    (classifier)  (graph)     (linkage)    (retrieval)  (agent)
```

Each phase gates on the previous. No skipping.

## Test at Every Phase

After each phase, run:
```bash
cd /home/dev/app/src && .venv/bin/python -m pytest tests/test_memory_mvp.py -v
```

Add tests to `test_memory_mvp.py` as you build. Don't wait until the end.

## What to Skip for MVP

- ❌ Edge contract validation (`edge_validator.py`) — trust the pipeline
- ❌ Memgraph or Bolt protocol — DictGraphStore is sufficient
- ❌ Session tracking / session_id in payload
- ❌ Reingestion with SUPERSEDES logic — just overwrite
- ❌ `version`, `validated_at`, `status` fields in Qdrant payload
- ❌ LLM entity extraction — classifier output drives node creation
- ❌ Multi-hop graph traversal — 1-hop BFS only
- ❌ `StructuredTool` or Pydantic tool schemas (Phase 5) — plain `@tool` decorator
