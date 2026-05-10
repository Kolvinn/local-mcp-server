# Session Summary — Taxonomy Redis Schema

**Date:** 2026-05-10
**Domain:** RAG / Memory Manager — Taxonomy Store
**Status:** Redis seeded, JSON backup created, plan verified against redis-development skill

## What We Did

1. Designed a dynamic taxonomy store in Redis to replace hardcoded Python enums (`Category`, `NodeType`, `EdgeType`, `TagRegistry`)
2. Rebased the 5 category types from `taxonomy-ex.md` into 4: **knowledge**, **objective**, **learning**, **thought**
   - `concept` + `execution` → `knowledge` (static facts + specs)
   - `planning` → `objective` (goals, tasks, constraints — user disliked "planning" as a gerund)
   - `learning` + `experience` → `learning` (merged — experience is only worth recording if it teaches)
   - `question` → `thought` (broadened to include vague ideas, connection hints, hypotheses — not just questions)
3. Verified the plan against `redis-development` skill rules — all structures comply
4. Seeded all taxonomy data into Redis via the MCP proxy server
5. Created JSON backup at `docs/rag-dev/taxonomy-schema.json`

## Key Decisions

- **Redis Hashes** for subcats/tags/keywords per category type — O(1) `hexists` validation, field-level updates, no parsing
- **Redis Sets** for flat enumerations (category_types, edge_types) — `sadd`/`sismember`
- **Edge types as flat set** not adjacency matrix — MVP simplicity. Pair validation added later when A3 extractor needs it
- **Status values** (`active` vs `deprecated`) on hash entries — enables soft deprecation
- **No TTLs** — taxonomy is persistent schema, not cache
- **Pipelining** for seed — `redis.pipeline()` for all initial writes (single round trip)
- **SCAN not KEYS** for startup enumeration — non-blocking iteration

## Assumptions

- Redis container is running and accessible via MCP proxy
- The memory manager will cache taxonomy in local memory after init (one `hgetall` per hash at startup)
- Classifier is responsible for assigning category_type + subcategory + tags + keywords
- Unknown values discovered by classifier are added to Redis automatically (schema evolves)

## Uncertainties

- Whether 4 category types is final or will evolve further with usage
- Whether `thought` subtypes (vague_idea, connection_hint) will actually be used by the classifier or remain theoretical
- Whether the current A1 `models.py` enums should be migrated to read from Redis, or if the new memory manager replaces them entirely

## What We'd Do Differently Next Time

- Seed script should be Python code delegated to implementer, not manual MCP calls (86 individual tool invocations is brittle)
- Should have built a `seed_from_json.py` script first that reads `taxonomy-schema.json` and pipelines all writes
