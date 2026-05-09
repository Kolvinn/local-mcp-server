# Learnings — Memory Manager MVP Planning

**Session date:** 2026-05-09
**Domain:** rag-dev / memory-manager

## What I Was Asked

1. Read the thought-graph design context (v5 diagram, session rules)
2. Pivot from thought-graph to memory manager MVP — a more foundational starting point
3. Read all `docs/rag-dev/` files (spec, edge contract, findings, handoff, exploration)
4. Read `src/tests/test_langchain.py` — working LiteLLM + Deep Agent pattern
5. Load skills: memgraph-graph-rag, qdrant, langchain-architecture, deep-agents-core, create-specification
6. Produce an expanded MVP checklist with relationship entities, purpose, tools/libraries, and stack position per item
7. Add a LangChain agentic endpoint section
8. Write to 4 cross-referenced files, strip scope (fewer nodes, fewer edges, no edge contract validation, no Memgraph)

## Key Decisions

- **5 node types** (down from 10): Bug, Decision, Goal, Component, Chunk. Dropped Agent, Session, Document, CodeEntity, Environment, Configuration.
- **~10 edge types** (down from 40): Kept AFFECTS, RESOLVES, SATISFIES, PARENT_OF, EXTRACTED_TO. Introduced `RELATED_TO` as catch-all for same-type connections, replacing ~15 specialized edges.
- **No edge contract validation** for MVP — trust the classifier-driven pipeline. EdgeValidator exists and works but is optional.
- **DictGraphStore only** — zero-infrastructure in-memory graph. No Memgraph, no Bolt protocol until proven.
- **Classifier-driven node creation** — skip LLM entity extraction. `category=bug` → create Bug node. `scope:X` tag → create Component node + edge.
- **Single-session ingest** — no session tracking, no version field, no reingestion with SUPERSEDES. Same content = same ID = idempotent upsert.
- **1-hop BFS retrieval** — not multi-hop. Expanded context but bounded.

## What I Assumed

- Qdrant is running and `memory_chunks` collection can be created
- Ollama is running with `nomic-embed-text` model available
- LiteLLM is running at `http://litellm:4000` with `openai/deepseek-flash` available
- A1 models (82 tests) are still passing
- A2 Qdrant pipeline files exist but acceptance gate was never run
- The user wants to code this themselves — this is a guide, not a delegation

## Uncertainty

- Whether the existing A2 `ingest.py` wiring works end-to-end (untested)
- Whether `deepseek-flash` is available via the user's LiteLLM/openai gateway
- Whether the DictGraphStore will scale for the user's actual data volume

## What I'd Do Differently

- The `RELATED_TO` catch-all edge is intentionally vague. If the MVP proves useful, the first post-MVP task should be splitting it into specific edges from the full contract.
- The classifier prompt wasn't specified — that's the most impactful lever for graph quality. Should be tuned early.
