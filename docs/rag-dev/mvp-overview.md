# Memory Manager MVP — Overview

> **Status:** Planning. No code written from this document.
> **Sibling docs:** [mvp-checklist.md](mvp-checklist.md) | [mvp-agent-endpoint.md](mvp-agent-endpoint.md) | [mvp-relationships.md](mvp-relationships.md)
> **Parent spec:** [spec.md](spec.md) — full GraphRAG design (A1-A6). This MVP is a stripped subset.

## What We're Building

A **memory manager** accessible as both a Python library and a LangChain agent tool. It ingests text, stores it in Qdrant (vectors) + a graph store (relationships), links the two bidirectionally, and retrieves context via semantic search + graph traversal.

The orchestrator (or any agent, or the user directly) calls it to inject relevant memory into any stage of the orchestrator cycle.

## What's Stripped from the Full Spec

| Full Spec (A1-A6) | MVP Keeps | MVP Drops |
|--------------------|-----------|-----------|
| 10 node types | 5: Bug, Decision, Goal, Component, Chunk | Agent, Session, Document, CodeEntity, Environment, Configuration |
| 40 edge triples | ~10 core edges | 30 specialized edges |
| Edge contract JSON validation | Trust the code (validate later) | `edge_validator.py` not required at first |
| Memgraph (Bolt) | DictGraphStore (in-memory dict) | Memgraph setup deferred |
| LLM entity extraction | Classifier-driven node creation | Extractor agent (full A3) |
| Session tracking + reingestion | Single-session ingest | Multi-session idempotency |
| 8 Qdrant payload fields | 6: chunk_id, graph_node_id, content, category, tags, source | session_id, version, validated_at, status |

## Stack Map

```
┌──────────────────────────────────────────────────────┐
│  AGENT LAYER                                          │
│  LangChain/Deep Agent wrapping memory manager as     │
│  tools: ingest_memory, search_memory, retrieve_context│
│  Model pivot: ChatLiteLLM → openai/deepseek-flash    │
├──────────────────────────────────────────────────────┤
│  MEMORY MANAGER API  (src/memory/)                    │
│  ingest(path) → IngestResult                          │
│  search(query) → list[ChunkResult]                    │
│  retrieve_context(query) → list[ContextChunk]         │
├──────────────────────┬───────────────────────────────┤
│  VECTOR STORE        │  GRAPH STORE                   │
│  Qdrant (REST)       │  DictGraphStore (in-memory)   │
│  collection: memory_ │  Nodes: Bug, Decision, Goal,  │
│  chunks, 768d Cosine │  Component, Chunk              │
│                      │  Edges: AFFECTS, RESOLVES,     │
│                      │  SATISFIES, PARENT_OF,         │
│                      │  RELATED_TO, EXTRACTED_TO      │
├──────────────────────┴───────────────────────────────┤
│  INFRASTRUCTURE                                       │
│  Ollama: nomic-embed-text (768d)                      │
│  LiteLLM: openai/deepseek-flash (classifier)          │
└──────────────────────────────────────────────────────┘
```

## Core Flow (Simplified)

```
Text file
    │
    ▼
classifier.classify(text)      → category + tags
    │                              (LiteLLM → deepseek-flash)
    ▼
chunker.chunk(text)            → list of text chunks
    │
    ▼
embedder.embed(chunks)         → 768d vectors (Ollama nomic-embed-text)
    │
    ├──────────────────────────┐
    ▼                          ▼
qdrant.upsert(points)     graph.merge_node() + merge_edge()
    │                          │
    └──────────┬───────────────┘
               ▼
         linkage: set graph_node_id in Qdrant payload
         + create :Chunk ref node in graph
               │
               ▼
         ready for retrieval
```

## What This Enables

When complete, you can:

1. **Ingest** — `python -m memory ingest docs/context/stack.md` → stored in Qdrant + graph
2. **Search** — `python -m memory search "what embedding model"` → returns relevant chunks
3. **Retrieve context** — `retrieve_context("what issues affect qdrant")` → vector hits + graph neighbors
4. **Agent tool** — any LangChain agent calls `search_memory` or `retrieve_context` as tools
5. **Inject into orchestrator** — the orchestrator's GATHER or ORIENT phase calls `retrieve_context` for enriched context

## What This Does NOT Do (by design)

- No session tracking across invocations (single-session ingest is fine for MVP)
- No reingestion with SUPERSEDES logic (re-ingest = overwrite for now)
- No edge contract validation (trust the classification pipeline)
- No Memgraph dependency (DictGraphStore is zero-infrastructure)
- No periodic validation loop
- No multi-hop graph traversal (1-hop BFS only)
- No StoreBackend or persistent memory across threads (MemorySaver only)

## Files to Create/Modify

| File | Action | From |
|------|--------|------|
| `src/memory/classifier.py` | Replace mock with LiteLLM call | A2 (existing, modify) |
| `src/memory/graph/__init__.py` | New package init | New |
| `src/memory/graph/dict_store.py` | DictGraphStore implementation | New |
| `src/memory/link.py` | Bidirectional linkage logic | New |
| `src/memory/retrieve.py` | search() + retrieve_context() | New |
| `src/memory/ingest.py` | Wire graph + linkage into pipeline | A2 (existing, modify) |
| `src/agents/memory_agent.py` | LangChain tool definitions | New |
| `src/scripts/ingest_test.py` | Update for graph | A2 (existing, modify) |
| `src/tests/test_memory_mvp.py` | Integration tests | New |
