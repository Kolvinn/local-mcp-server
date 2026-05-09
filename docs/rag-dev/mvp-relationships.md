# Memory Manager MVP — Entity Relationships & Data Flow

> **Sibling docs:** [mvp-overview.md](mvp-overview.md) | [mvp-checklist.md](mvp-checklist.md) | [mvp-agent-endpoint.md](mvp-agent-endpoint.md)
> **Parent contract (full):** [edge-contract.json](edge-contract.json) — 10 node types, 40 triples. This MVP uses a strict subset.

## Simplified Node Taxonomy (5 types)

From the full spec's 10 types, we keep the 5 most impactful for an MVP:

| Label | Kind | Example | Created By |
|-------|------|---------|------------|
| `:Bug` | known defect | `{id, summary}` | `category=bug` from classifier |
| `:Decision` | choice made | `{id, summary}` | `category=decision` from classifier |
| `:Goal` | desired outcome | `{id, summary}` | `category=goal` from classifier |
| `:Component` | system component | `{id, name}` | Tag `scope:X` → find-or-create Component |
| `:Chunk` | reference only (no content) | `{id, graph_node_id}` | linkage step — bridges Qdrant ↔ graph |

**Dropped for MVP:** `:Agent`, `:Session`, `:Document`, `:CodeEntity`, `:Environment`, `:Configuration`. These can be added later from the full spec when needed.

## Simplified Edge Types (~10 relationships)

From 40 legal triples, we keep the ones that matter for project memory:

```
Source       Edge            Target          Meaning
─────────────────────────────────────────────────────────────
Bug     →    AFFECTS     →   Component       Bug impacts this component
Bug     →    RELATED_TO  →   Bug             Bugs are related
Decision →   RESOLVES    →   Bug             Decision fixes this bug
Decision →   SATISFIES   →   Goal            Decision fulfills this goal
Goal    →   PARENT_OF   →   Goal             Goal hierarchy
Goal    →   RELATED_TO  →   Goal             Goals are related
Decision →  RELATED_TO  →   Decision         Decisions are related
Component → RELATED_TO  →   Component        Components are related
Chunk   →   EXTRACTED_TO →  *               Chunk produced this node (any type)
```

**`RELATED_TO`** is a catch-all edge for same-type connections. It replaces 15+ specialized edges (`SUPERSEDES`, `CONFLICTS_WITH`, `BLOCKS`, `MOTIVATED`, `DEPENDS_ON`, `HOSTS`, etc.) for the MVP. Specific semantics come later.

## How Data Flows

### Flow 1: Ingestion

```
File "stack.md"
    │
    ▼
classifier.classify(text)
    │  returns: category="technical_fact", tags=["scope:qdrant", "scope:ollama", "domain:infra"]
    ▼
chunker.chunk(text)
    │  returns: ["Qdrant runs on port 6333...", "Ollama serves nomic-embed-text...", ...]
    ▼
embedder.embed(chunks)
    │  returns: [[0.12, -0.34, ...], [0.56, 0.78, ...], ...]  (768d each)
    ▼
┌─────────────────────────────────────────────────────────────┐
│ QDRANT UPSERT                                                │
│   Point 1: {chunk_id: "uuid-aaa", content: "Qdrant runs...",│
│             category: "technical_fact", tags: [...],         │
│             source: "docs/context/stack.md",                 │
│             graph_node_id: None}   ← filled in linkage step  │
│   Point 2: {chunk_id: "uuid-bbb", content: "Ollama serves...│
│             ...}                                             │
└─────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────┐
│ GRAPH UPSERT (classifier-driven, no LLM extraction)          │
│                                                              │
│   For each chunk:                                            │
│     category → node type:                                    │
│       "technical_fact" → no entity node (just tag edges)    │
│       "bug" → (:Bug {id: "bug-001", summary: "Port 8001..."})│
│       "decision" → (:Decision {id: "dec-001", summary: ...})│
│                                                              │
│   For each tag "scope:X":                                    │
│     merge_node("Component", {id: "comp-X", name: "X"})      │
│                                                              │
│   For each unique pair of nodes in same chunk:               │
│     merge_edge(node_a, "RELATED_TO", node_b)                 │
│                                                              │
│   Category-specific edges:                                   │
│     bug + scope:X → (bug)-[:AFFECTS]->(component:X)         │
│     decision + scope:X → (decision)-[:RELATED_TO]->(comp:X) │
└─────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────┐
│ LINKAGE                                                      │
│                                                              │
│   For each chunk → graph_node pair:                          │
│     1. Update Qdrant: set graph_node_id in payload           │
│     2. Create graph: (:Chunk {id: chunk_id})                 │
│     3. Create edge: (chunk)-[:EXTRACTED_TO]->(graph_node)   │
└─────────────────────────────────────────────────────────────┘
```

### Flow 2: Retrieval (search)

```
User query: "what embedding model"
    │
    ▼
embedder.embed(["what embedding model"])
    │  returns: [[0.42, -0.11, ...]]  (768d)
    ▼
Qdrant.search(vector, limit=5)
    │  returns: [
    │    {chunk_id: "uuid-bbb", score: 0.92, content: "Ollama serves nomic-embed-text...",
    │     category: "technical_fact", tags: ["scope:ollama"], graph_node_id: "comp-ollama"},
    │    ...
    │  ]
    ▼
return formatted results
```

### Flow 3: Retrieval (context — with graph expansion)

```
User query: "what issues affect qdrant"
    │
    ▼
embedder.embed(query) → vector
    │
    ▼
Qdrant.search(vector, limit=5)
    │  returns chunks with graph_node_ids
    ▼
Collect graph_node_ids: ["bug-001", "comp-qdrant", ...]
    │
    ▼
For each node_id: graph.get_neighbors(node_id)  (1-hop BFS)
    │
    │  bug-001 → [(comp-qdrant, AFFECTS), (bug-003, RELATED_TO)]
    │  comp-qdrant → [(bug-001, AFFECTS), (comp-ollama, RELATED_TO)]
    ▼
Collect neighbor node IDs → find their :Chunk refs → Qdrant lookup
    │
    ▼
Deduplicate by chunk_id → merge metadata
    │
    ▼
Return enriched results:
    Direct match: "Qdrant timeout on port 6333..."  (score: 0.91)
    Graph neighbor: "Bug: Ollama model loading fails..."  (via comp-qdrant → comp-ollama)
    Graph neighbor: "Bug: Memory leak in vector search..."  (via bug-001 RELATED_TO bug-003)
```

## Node ID Strategy

Use deterministic IDs to avoid duplicates from repeated ingestion:

| Node Type | ID Pattern | Example |
|-----------|-----------|---------|
| Bug | `bug-{first-8-of-content-hash}` | `bug-a3f2c109` |
| Decision | `dec-{first-8-of-content-hash}` | `dec-7b41e882` |
| Goal | `goal-{first-8-of-content-hash}` | `goal-2d55f941` |
| Component | `comp-{lowercase-name}` | `comp-qdrant` |
| Chunk | UUIDv5(chunk content) | (already generated by A2 chunker) |

This ensures: re-ingesting the same file = same IDs = upsert (update) not duplicate.

## What Happens When You Ingest Twice

For MVP: no session tracking, no SUPERSEDES, no version field.

- Same chunk content → same UUIDv5 → Qdrant upsert (overwrite payload)
- Same graph node ID → merge (overwrite properties)
- Same edges → merge (no duplicates if using deterministic IDs)
- **Net effect:** re-ingestion is idempotent. Old data is overwritten, not versioned.

This is acceptable for MVP. Full reingestion with version history and SUPERSEDES chains comes later.

## Edge Cases

| Scenario | Expected Behavior |
|----------|-------------------|
| Chunk with no `scope:` tags | Node created, no Component edges |
| Chunk classified as `technical_fact` | No entity node created (just stored in Qdrant) |
| Two chunks produce same Component | `merge_node` is idempotent — one Component node |
| Query returns 0 results | `retrieve_context` returns empty list with message |
| Graph has node but Qdrant linkage broken | Graph traversal returns node without chunk content |
| Empty file ingested | 0 chunks, 0 nodes, 0 edges — no crash |
| Very long file (100+ chunks) | Batch embed, batch Qdrant upsert — no OOM |
