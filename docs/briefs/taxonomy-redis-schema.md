# Taxonomy Store in Redis — Condensed Plan

**Purpose:** Redis holds the evolving metadata schema for Qdrant collections and graph nodes. The memory manager queries Redis at startup and during ingestion to validate/learn category types, subcategories, tags, and edge types. Schema evolves as new data patterns are discovered — no code changes needed.

---

## 1. Redis Key Layout

All keys under the `taxonomy:` namespace so the memory manager can scan them at init time.

| Redis Key | Type | Content | Purpose |
|-----------|------|---------|---------|
| `taxonomy:category_types` | Set | `{knowledge, objective, learning, thought}` | Top-level router — what category types exist |
| `taxonomy:cat:{type}:subcats` | Hash | `{technical: active, behavior: active, ...}` | Valid subcategory values per category type |
| `taxonomy:cat:{type}:tags` | Hash | `{direct_input: active, high_stability: active, ...}` | Valid tag values per category type |
| `taxonomy:cat:{type}:keywords` | Hash | `{workflow_style: active, syntax_preference: active, ...}` | Keyword focus areas per category type |
| `taxonomy:node_types` | Hash | `{Bug: active, Decision: active, Goal: active, Component: active, Chunk: active}` | Valid graph node labels |
| `taxonomy:edge_types` | Set | `{AFFECTS, RESOLVES, SATISFIES, PARENT_OF, ...}` | Flat list of legal edge type names |
| `taxonomy:payload_indexes` | Hash | `{category_type: keyword, category: keyword, tags: keyword_list, ...}` | Which Qdrant payload fields get indexes |
| `taxonomy:meta` | Hash | `{version: 1, updated_at: ..., source: docs/rag-dev/taxonomy-ex.md}` | Version tracking |

**Why hashes for subcats/tags/keywords:** O(1) single-field lookup — `hexists("taxonomy:cat:learning:tags", "volatile")`. Easy to add (`hset`) or deprecate (`hset ... deprecated`).

**Why sets for category_types and edge_types:** These are flat enumerations with no metadata per item. `sadd` to extend, `smembers` to list all.

---

## 2. Category Types & Their Sub-Data Options

Four category types. Each defines its own valid subcategories, tags, and keyword focuses. The memory manager queries these at ingestion time to validate against and to extend the schema when new patterns emerge.

### 2.1 KNOWLEDGE — Static facts, references, specifications

```
taxonomy:cat:knowledge:subcats
  definition       → active
  domain_rule      → active
  entity_property  → active
  api_spec         → active
  parameter_map    → active
  env_config       → active
  access_protocol  → active

taxonomy:cat:knowledge:tags
  foundational   → active
  deprecated     → active
  expert_level   → active
  cross_domain   → active
  production     → active
  sandbox        → active
  read_only      → active
  destructive    → active

taxonomy:cat:knowledge:keywords
  subject_uri       → active
  parent_concept    → active
  endpoint_url      → active
  auth_type         → active
  rate_limit        → active
  schema_version    → active
```

**Use:** The "world model" and "how-to" layer merged. Absorbs what were formerly `concept` and `execution`. Everything from ontology definitions to API specs to environment configs. "Qdrant uses HNSW for ANN" → `knowledge, definition`. "Qdrant on port 6333, no auth" → `knowledge, env_config`.

### 2.2 OBJECTIVE — Goals, tasks, constraints on outcomes

```
taxonomy:cat:objective:subcats
  goal        → active
  sub_task    → active
  milestone   → active
  condition   → active
  blocker     → active

taxonomy:cat:objective:tags
  p0               → active
  p1               → active
  sequential       → active
  parallel         → active
  high_uncertainty → active

taxonomy:cat:objective:keywords
  prerequisite_id   → active
  outcome_target    → active
  estimated_effort  → active
```

**Use:** Maps the Task Dependency Graph and desired outcomes. "Phase 3 depends on Phase 2 completing" → `objective, condition`. "Ship the memory manager MVP by Friday" → `objective, goal, p0`.

### 2.3 LEARNING — Lessons, experiences, behavioral patterns

```
taxonomy:cat:learning:subcats
  technical_lesson  → active
  behavior          → active
  preference        → active
  constraint        → active
  error_trace       → active
  observation       → active
  user_feedback     → active
  action_result     → active

taxonomy:cat:learning:tags
  direct_input     → active
  inferred         → active
  high_stability   → active
  volatile         → active
  success          → active
  failure          → active
  halting_error    → active
  optimized_path   → active

taxonomy:cat:learning:keywords
  workflow_style     → active
  syntax_preference  → active
  user_limit         → active
  tool_id            → active
  latency_ms         → active
  token_usage        → active
  correction_id      → active
```

**Use:** Merges what were formerly `learning` (agent behavior evolution) and `experience` (episodic execution logs). If an experience teaches nothing actionable, it's not worth recording — so they're the same thing. "implementer failed on import error because qdrant-client was missing" → `learning, error_trace, failure`. "agent should prefer async patterns for I/O" → `learning, technical_lesson`.

### 2.4 THOUGHT — Unresolved inquiries, investigations, embryonic ideas

```
taxonomy:cat:thought:subcats
  open_question    → active
  investigation    → active
  hypothesis       → active
  clarification    → active
  vague_idea       → active
  connection_hint  → active

taxonomy:cat:thought:tags
  nascent       → active
  formulating   → active
  researching    → active
  stalled        → active
  resolved       → active
  actionable     → active
  speculative    → active
  confirmed      → active

taxonomy:cat:thought:keywords
  question_text      → active
  related_concept    → active
  confidence_level   → active
  blocker_for        → active
  evidence_for       → active
  evidence_against   → active
```

**Use:** Broader than just questions. Captures ephemeral thinking: a sensed connection not yet validated, a half-formed idea, an active investigation, a hypothesis awaiting testing. Mirrors the `:Question` node in the thought graph but extends to pre-question states. "Is the classifier bottlenecking ingestion?" → `thought, open_question`. "Qdrant's HNSW might be related to how Memgraph indexes..." → `thought, connection_hint, nascent`.

---

## 3. Qdrant Payload Schema

### 3.1 The Payload (per point)

```python
{
    "chunk_id":       str,       # UUID — immutable identity
    "graph_node_id":  str | null,# bidirectional link to graph (nullable until A4)
    "category_type":  str,       # knowledge | objective | learning | thought
    "category":       str,       # subtype (e.g., "technical", "goal", "error_trace")
    "tags":           list[str], # cross-cutting labels (e.g., ["p0", "sequential"])
    "key_words":      list[str], # extracted keywords for enhanced retrieval
    "content":        str,       # chunk text (the actual data)
    "summary":        str | null,# LLM-generated summary (future, nullable)
    "source":         str,       # origin file/path
    "status":         str,       # active | superseded | stale
    "version":        int,       # monotonic, bumped on reingest
    "created_at":     str,       # ISO8601
    "updated_at":     str,       # ISO8601
}
```

### 3.2 Indexed Fields (Qdrant payload indexes)

These fields get `CreatePayloadIndex` calls because they're used in Qdrant filter expressions:

| Field | Index Type | Reason |
|-------|-----------|--------|
| `category_type` | keyword | Primary router — "give me all learning chunks" |
| `category` | keyword | Sub-router — "give me all bug reports" |
| `tags` | keyword (array) | Cross-filter — "give me all p0 items about qdrant" |
| `status` | keyword | Lifecycle filter — "show only active chunks" |
| `graph_node_id` | keyword | Bridge to graph — "find chunk for node bug-42" |
| `source` | keyword | Source filter — "what did we learn from stack.md?" |

### 3.3 NOT Indexed (data carriers only)

| Field | Why Not Indexed |
|-------|----------------|
| `chunk_id` | Unique per point — accessed by point ID, not filtered |
| `content` | Full text — searched via vector similarity, not keyword match |
| `summary` | Same as content — vector search covers it |
| `key_words` | Used for retrieval augmentation, not Qdrant filtering (can index later if needed) |
| `version` | Monotonic — used client-side for reingestion logic, not queried |
| `created_at` / `updated_at` | Metadata — no query use case yet (can add integer index later for range queries) |

---

## 4. Edge Types — Flat, Evolvable

Just a Redis set. No adjacency matrix, no node-pair validation for MVP. The graph layer validates: "is this edge name in the set?"

```
taxonomy:edge_types (Redis Set):
  AFFECTS, RESOLVES, SATISFIES, PARENT_OF, DEPENDS_ON,
  BELONGS_TO, RELATED_TO, EXTRACTED_TO, PRODUCED, MOTIVATED,
  FOLLOWS, BLOCKS, TRIGGERED_BY, LOCATED_IN, IMPLEMENTS,
  DOCUMENTS, REPORTS, OWNS, HOSTS, CONFIGURES
```

**Adding a new edge:** `sadd taxonomy:edge_types "NEW_EDGE_NAME"` — no code change. The graph layer starts using it immediately.

**The edge contract JSON** (`docs/rag-dev/edge-contract.json`) can be loaded into the graph layer separately for A3's extractor if node-pair validation is needed later. Not needed for MVP.

---

## 5. Qdrant Collection Config (stored in Redis, queried at init)

```
taxonomy:collection_config  (Hash):
  collection_name   → memory_chunks
  vector_size       → 768
  distance_metric   → COSINE
  embedding_model   → nomic-embed-text
```

Why in Redis instead of hardcoded: changing the embedding model (e.g., to 1536-dim) updates the taxonomy store. The memory manager picks it up on next init. No code change.

---

## 6. Node Types → Graph Labels

```
taxonomy:node_types (Hash):
  Bug         → active
  Decision    → active
  Goal        → active
  Component   → active
  Chunk       → active
  Knowledge   → active
  Objective   → active
  Learning    → active
  Thought     → active
  Agent       → active (staged — not used in MVP)
  Session     → active (staged)
  Document    → active (staged)
  CodeEntity  → active (staged)
  Environment → active (staged)
```

The 5 original Bug/Decision/Goal/Component/Chunk remain for MVP. The four category types (Knowledge, Objective, Learning, Thought) map 1:1 to graph node labels — available if the graph layer evolves to use typed entity nodes. Staged types (Agent, Session, etc.) are present but not wired to the classifier yet.

---

## 7. How the Memory Manager Uses This

### At Init (startup)
1. `SCAN 0 MATCH taxonomy:* COUNT 100` → enumerate all taxonomy keys (non-blocking; do NOT use `KEYS`)
2. `hgetall taxonomy:payload_indexes` → know which fields to create Qdrant indexes for
3. `hgetall taxonomy:collection_config` → know vector size, distance, collection name
4. `smembers taxonomy:category_types` → know the 4 valid category types
5. Cache results in local dict — no repeated Redis calls during ingestion loop

### During Ingestion (per chunk)
1. Classifier returns `category_type` + `category` + `tags` + `key_words`
2. Validate against Redis:
   - `sismember taxonomy:category_types {category_type}` → valid?
   - `hexists taxonomy:cat:{type}:subcats {category}` → valid subcategory?
   - For each tag: `hexists taxonomy:cat:{type}:tags {tag}` → valid?
3. If any are unknown → add to Redis: `hset taxonomy:cat:{type}:tags {new_tag} active` (schema learns)
4. Build Qdrant point with validated payload

### At Query Time
1. `hgetall taxonomy:payload_indexes` → build filter expressions using indexed fields only
2. `smembers taxonomy:edge_types` → know what edge types are available for graph traversal

---

## 8. Evolution Mechanics

### Adding a new category type
```
sadd taxonomy:category_types "new_type"
hset taxonomy:cat:new_type:subcats subtype_a active subtype_b active
hset taxonomy:cat:new_type:tags tag_a active tag_b active
hset taxonomy:cat:new_type:keywords kw_a active kw_b active
```

### Adding a new tag to an existing category
```
hset taxonomy:cat:learning:tags "experimental" "active"
```
Classifier can now return `tags=["experimental"]` for learning chunks. No code change.

### Deprecating an entry
```
hset taxonomy:cat:knowledge:tags "deprecated_old_tag" "deprecated"
```
Memory manager reads value as status. Can decide: accept with warning, reject, or auto-migrate.

### Adding a new payload field with backfill
1. Update Redis: `hset taxonomy:payload_indexes "new_field" "keyword"`
2. Memory manager creates Qdrant payload index for `new_field`
3. `refresh_payloads()` scans existing points — any with `created_at < field_introduced_at` get the new field populated with default

---

## 9. Default Seed Data

A one-shot script or startup hook populates all of §1-§6 with the default values shown above. The source of truth for defaults is `docs/rag-dev/taxonomy-ex.md` (category type concepts adapted to 4-type taxonomy: knowledge, objective, learning, thought) and `docs/rag-dev/spec.md` (node types, collection config). After initial seed, the memory manager owns the Redis store and evolves it independently.

**Seed command (conceptual):**
```
python scripts/seed_taxonomy.py
```
Reads the defaults from the taxonomy docs, populates Redis using `redis.pipeline()` (single round trip for all `hset`/`sadd` calls). Idempotent — skips keys that already exist. Only run once, or after intentional schema changes.

---

## 10. Redis Best Practice Verification

Verified against the `redis-development` skill rules:

| Rule | Requirement | Plan Compliance |
|------|-------------|-----------------|
| `data-choose-structure` | Hash for flat objects with atomic fields; Set for unique membership | ✅ Hashes for subcats/tags/keywords/payload_indexes; Sets for category_types and edge_types |
| `data-key-naming` | Colons as separators, consistent hierarchy, keep keys short | ✅ `taxonomy:cat:{type}:subcats` — colons, hierarchy, readable |
| `json-vs-hash` | JSON only for nested structures needing atomic partial updates | ✅ No nested structures in taxonomy — hashes are correct. Dropped JSON edge contract per MVP simplification. |
| `conn-blocking` | Avoid `KEYS *`, use `SCAN`; avoid `HGETALL`/`SMEMBERS` on large collections | ⚠️ Seed script must `SCAN taxonomy:*` not `KEYS`. For now hashes/sets are small (<50 entries each) so `hgetall`/`smembers` is safe, but should use `HSCAN`/`SSCAN` if any grow large. |
| `conn-pipelining` | Batch bulk operations with `redis.pipeline()` — 5-10x faster | ⚠️ Seed script must pipeline all `hset`/`sadd` calls into a single round trip. Not yet stated — added below. |
| `ram-ttl` | Set TTL on cache keys to prevent unbounded growth | ✅ Taxonomy is persistent schema, NOT cache. No TTL needed (correct omission). |

### Adjustments Made

1. **Seed script uses pipelining**: All initial `hset`/`sadd` calls batched via `redis.pipeline()` → single round trip. Idempotent (skip if key exists).

2. **Startup enumeration uses SCAN**: `SCAN 0 MATCH taxonomy:* COUNT 100` instead of `KEYS taxonomy:*` to avoid blocking the server.

3. **Fallback pattern for large hashes**: If a category type's subcats/tags grow beyond ~100 entries, switch from `hgetall` to `hscan` iteration. Not expected for MVP but noted for future.

---

## 11. Key Design Decisions

| Decision | Why |
|----------|-----|
| Hashes over JSON for subcats/tags/keywords | O(1) single-field lookup for validation. Easy add/remove without parsing. |
| Sets for flat enumerations (category_types, edge_types) | No metadata per item. `sadd`/`sismember` are the simplest possible API. |
| Edge types as flat set, not adjacency matrix | The full edge contract is overengineered for MVP. Validate edge name existence, not node-pair legality. Add pair validation later when extractor needs it. |
| Taxonomy learns at ingestion time | New tags/categories discovered by the classifier get added to Redis automatically. Schema evolves with data. |
| Status values on hash entries (`active` vs `deprecated`) | Enables soft deprecation without data loss. Queries can filter by status. |
| Separate category_type from category | Two-level routing. Coarse filter (`category_type=objective`) then fine filter (`category=blocker`). More efficient and extensible than flat enum. |
| `key_words` in payload but not indexed | Keywords assist retrieval augmentation (can be injected into LLM prompts), not Qdrant filtering. Can index later. |
| Collection config in Redis | One place to change. Switching embeddings model? Update `vector_size` in Redis. Collection rebuilt on next init. |
