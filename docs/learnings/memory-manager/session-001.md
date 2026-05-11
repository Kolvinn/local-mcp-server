# Learnings — Memory Manager LangGraph Design (Session 001)

## Task
Design a LangGraph-based memory manager for agentic memory ingestion into Qdrant using the hybrid embed pipeline.

## Key Decisions
- **Linear 3-node pipeline** (validate_classify → build_payload → embed_ingest) chosen over branching/fan-out. Caller brings classification intent, so routing complexity is unnecessary for MVP.
- **LLM as fallback classifier, not primary path.** Agents that call the MM typically know what they're storing (category_type + category). LLM (deepseek-flash) only fires when classification fields are missing. Saves tokens on the common path.
- **Schema-as-JSON-file, not Redis.** The taxonomy-redis brief had a full Redis design with auto-learning tags. Deferred to reduce infrastructure dependency. taxonomy-schema.json is version-controlled and loaded at runtime. Redis can wrap it later with zero graph changes.
- **HNSW disabled for multivectors is correct and intentional.** The max-similarity metric is non-symmetric; HNSW produces incorrect results. Exact search over prefetched candidates is the documented Qdrant pattern.
- **Separate embedder module** refactored from hybrid_embed_test.py so both the graph and the test script share the same embedding pipeline.

## Assumptions
- Caller provides pre-chunked content (200-300 words). Chunking is out of scope for MM.
- Single-point ingestion (not batch) — agent calls are event-driven.
- Qdrant collection `memory_chunks` created once at setup, not in graph.
- deepseek-flash is accessible via opencode go API for LLM classification fallback.
- No content deduplication or summary generation in MVP.

## Uncertainties
- Exact dimension of `answerai-colbert-small-v1` — user acknowledged this will change if model changes.
- Whether the graph should be compiled with a checkpointer (not needed for stateless pipeline, but may be relevant when Memgraph is added).
- How the caller's classification intent maps to the 4-type taxonomy in practice — may need refinement after real agent calls.

## What I'd Do Differently
- Nothing significant. The user was clear about scope boundaries and the brief reflects those directly.
