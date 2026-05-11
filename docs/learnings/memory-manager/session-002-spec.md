# Learnings — Memory Manager Spec Writing (Session 001)

## Task
Write pseudocode spec for the LangGraph memory manager, covering 5 modules, data structures, error handling, and test plan.

## Key Decisions
- **Pydantic models for all data structures** (MemoryManagerInput, MemoryManagerOutput, TaxonomyClassification, QdrantPayload) — aligns with conventions.md requirement. The StateGraph TypedDict is separate (LangGraph's state schema, not a Pydantic model).
- **Error-return pattern over exceptions in nodes** — nodes return `{"error": str}` rather than raising. Graph always reaches END. Caller checks `result["error"]` after invoke(). Keeps the graph simple (no conditional error routing, no try/except in edges).
- **Embedder refactored as module-level singletons** — lazy-init pattern for FastEmbed models (they're expensive to load). LiteLLM calls are stateless so no singleton needed there.
- **Collection setup is idempotent** — `ensure_collection_exists()` is called in the embed_ingest node, not at import time. First ingestion triggers setup. Safe for repeated calls.
- **LLM retry limited to parse failures** — one retry with error context injected. Validation failures (unknown taxonomy values) are NOT retried — those indicate caller error, not LLM flakiness.

## Assumptions
- deepseek-flash is accessible via the same opencode-go API pattern used elsewhere in the project
- The taxonomy-schema.json `payload_indexes` dict values map cleanly to Qdrant's `PayloadSchemaType` enum (keyword → KEYWORD, keyword_list → KEYWORD)
- The existing `hybrid_embed_test.py` ColBERT dimension (96 → 128) will be corrected when the model is finalized
- Single-point upsert is acceptable for MVP (agent calls are event-driven, not batched)

## Uncertainties
- Exact LLM client to use for deepseek-flash — didn't specify in spec (implementer discovers or user provides)
- Whether `litellm.embedding()` accepts the same parameters as the `LiteLLMEmbeddings` LangChain wrapper consistently — spec used the direct litellm path since that's what hybrid_embed_test.py uses
- UID/GID for the memory manager container files — not relevant yet (container topology is Phase 2+)

## What I'd Do Differently
- The stateDiagram-v2 format was the right call from the start — flowchart edge labels with `:` break the parser. Should have known this from Mermaid's documented syntax quirks.
