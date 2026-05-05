# GraphRAG Memory Manager — Specification v0.2

> Status: implementation plan approved (Option A). See §10 for staged build.
> Re-read the Deferred Decisions table (§9) before each stage — items may shift here.

## 1. Architecture

```
Ingestion Source (session log, doc, code, goal, memory)
        │
        ▼
┌───────────────────────┐
│  Classifier            │  deepseek-flash: assign category + tags
└───────┬───────────────┘
        │
        ▼
┌───────────────────────┐
│  Chunker               │  semantic-boundary chunking
└───────┬───────────────┘
        │
        ▼
┌───────────────────────┐
│  Entity Extractor      │  deepseek-flash: extract graph nodes + edges
└───────┬───────────────┘
        │
   ┌────┴────┐
   ▼         ▼
┌──────┐  ┌──────────┐
│Qdrant│  │ Graph DB │   parallel upsert
│(REST)│  │ (Cypher) │
└──────┘  └──────────┘
   │         │
   │  chunk_id ◄──► graph_node_id  (bidirectional)
   │         │
   └────┬────┘
        ▼
   Session Tracking
```

Two-tier retrieval (deferred):
- **Light RAG** (ORIENT phase): query Memory Manager for current phase, goal hierarchy, recent decisions
- **Deep RAG** (GATHER phase): vector search Qdrant → collect graph_node_id → graph traversal → enriched context

## 2. Node Taxonomy (Nouns Only)

| Label | Kind | Example Properties |
|-------|------|-------------------|
| `:Agent` | role/persona | `{name, type}` |
| `:Component` | system thing | `{name, kind}` |
| `:Document` | persisted artifact | `{path, kind, source}` |
| `:Session` | time-bounded event | `{id, started_at, ended_at}` |
| `:Goal` | desired outcome | `{summary, status}` |
| `:Decision` | choice made | `{summary, rationale}` |
| `:Bug` | known defect | `{summary, severity}` |
| `:CodeEntity` | code construct | `{name, kind, location}` |
| `:Environment` | runtime context | `{name, type}` |
| `:Configuration` | config value | `{key, value}` |
| `:Chunk` | **reference only** (no content) | `{id, graph_node_id}` — bridges Qdrant to graph |

Facts emerge from triples: `(:Bug)-[:AFFECTS]->(:Component)` — the triple is the truth.

## 3. Edge Contract (Subset — Core Edges)

```
Bug → Component        AFFECTS
Bug → CodeEntity       LOCATED_IN
Bug → Configuration    TRIGGERED_BY
Bug → Environment      REPRODUCED_IN
Bug → Session          DISCOVERED_IN
Bug → Bug              DUPLICATE_OF, CAUSED_BY

Decision → Bug         RESOLVES
Decision → Component   SELECTS
Decision → Goal        SATISFIES
Decision → Decision    SUPERSEDES, CONFLICTS_WITH
Decision → CodeEntity  IMPLEMENTED_BY

Goal → Goal            PARENT_OF, BLOCKS, SUPERSEDES
Goal → Bug             BLOCKED_BY
Goal → Decision        MOTIVATED

Agent → Bug            REPORTED
Agent → Decision       PROPOSED
Agent → CodeEntity     OWNS
Agent → Session        PARTICIPATED_IN

CodeEntity → CodeEntity  CALLS, EXTENDS, IMPLEMENTS, OVERRIDES, DEPENDS_ON
CodeEntity → Component   BELONGS_TO
CodeEntity → Configuration READS

Component → Component     DEPENDS_ON, HOSTS
Component → Environment   DEPLOYED_IN

Configuration → Environment DEFINED_IN
Configuration → Component   SETS

Session → Session          FOLLOWS
Session → Document         PRODUCED
Session → Goal             WORKED_ON

Document → Decision        RECORDS
Document → CodeEntity      DOCUMENTS

Chunk → *                  EXTRACTED_TO   (links chunk ref to its graph node)
```

Full contract stored as `docs/rag-dev/edge-contract.json` — machine-readable adjacency matrix.
Agents validate edge creation against this contract.

## 4. Qdrant Collection Schema

Collection: `memory_chunks`
- Vectors: 768d, Cosine distance
- Payload indexes: `category` (keyword), `tags` (keyword), `status` (keyword), `graph_node_id` (keyword), `validated_at` (integer), `version` (integer), `source` (keyword)

**Point payload**:

```python
{
    "chunk_id":       str,       # UUID — immutable identity
    "graph_node_id":  str,       # e.g., "bug-42" — bidirectional link
    "session_id":     str,       # which session produced this
    "category":       Category,  # singular enum
    "tags":           list[str], # cross-cutting labels
    "content":        str,       # chunk text
    "source":         str,       # origin file/path
    "version":        int,       # monotonic, incremented on reingest
    "validated_at":   int,       # unix timestamp of last validation pass
    "status":         str,       # active | superseded | stale | merged
}
```

**Category enum** (singular, mutually exclusive):
```
technical_fact, bug, decision, goal, code_symbol, documentation,
exploration_finding, session_memory
```

**Tags** (cross-cutting, many per chunk):
```
scope: [ollama, qdrant, memgraph, traefik, ...]
domain: [infra, code, architecture, testing, ...]
quality: [bug, workaround, verified, deprecated, ...]
phase: [orient, gather, spec, code, review]
```

## 5. Graph Schema (Cypher)

```cypher
// Nodes
(:Agent {id, name, type})
(:Component {id, name, kind})
(:Document {id, path, kind, source})
(:Session {id, started_at, ended_at})
(:Goal {id, summary, status})
(:Decision {id, summary, rationale})
(:Bug {id, summary, severity})
(:CodeEntity {id, name, kind, location})
(:Environment {id, name, type})
(:Configuration {id, key, value})
(:Chunk {id, graph_node_id})   -- lightweight bridge; no content/vector

// Edge directions follow contract
(agent)-[:REPORTED]->(bug)
(bug)-[:AFFECTS]->(component)
...
```

All nodes have a unique `id` property. Edge existence is validated against the contract before creation.

## 6. Ingestion Pipeline

```
def ingest(source: Source) -> IngestResult:
    # 1. Classify
    category, tags = classifier.classify(source.content)    # LLM call (~50 tokens out)

    # 2. Chunk
    chunks = chunker.chunk(source.content)                  # semantic boundaries
    for chunk in chunks:
        assign chunk_id, attach category, tags, session_id, source

    # 3. Embed + upsert Qdrant
    vectors = embedder.embed([c.content for c in chunks])   # nomic-embed-text, batch
    qdrant.upsert(points_for(chunks, vectors))

    # 4. Extract entities + upsert graph
    graph_nodes, graph_edges = extractor.extract(source.content)  # LLM call (~150 tokens out)
    for node in graph_nodes:
        graph.merge_node(node)
        # link chunk reference node
        graph.merge_edge(Chunk(id=chunk_id) -[:EXTRACTED_TO]-> node)
    for edge in graph_edges:
        validate_against_contract(edge)                    # edge-contract.json
        graph.merge_edge(edge)

    # 5. Session tracking
    session.add_produced_chunk(chunk_id)
    session.add_produced_graph_node(node.id)

    return IngestResult(chunks=N, nodes=M, edges=K)
```

**Idempotency**: if `chunk_id` already exists in Qdrant, upsert (version+1). If `graph_node.id` already exists, MERGE (update properties if changed).

## 7. Reingestion & Updates

```
Source updated → check session's tracked_chunk_ids for this source
    ├── new chunk → INSERT
    ├── existing chunk → UPSERT (version++, status stays "active")
    └── content no longer relevant → status="superseded", add [:SUPERSEDES] edge in graph

Validation loop (periodic, not real-time):
    SELECT chunks WHERE validated_at < now() - TTL
    LLM re-evaluates → bump validated_at or mark stale/superseded
```

## 8. Abstract Graph Interface

```python
class GraphStore(ABC):
    """Cypher-oriented graph operations."""
    def merge_node(self, label: str, props: dict) -> str: ...
    def merge_edge(self, source_id: str, rel: str, target_id: str, props: dict = None): ...
    def query(self, cypher: str, params: dict = None) -> list[dict]: ...
    def get_schema(self) -> dict: ...
```

Initial implementation targets Memgraph via Bolt protocol. Interface allows swap without touching Qdrant or ingestion logic.

## 9. Deferred Decisions

| Item | Why deferred |
|------|-------------|
| Retrieval strategy (single-hop vs multi-hop GraphRAG) | User preference; design in separate phase |
| MCP tool exposure | Build first, wrap later |
| Specific Memgraph config (docker, connection, indexes) | Graph interface is abstract; concrete impl later |
| Validation TTL / schedule | Premature — get ingestion working first |
| Chunking algorithm specifics | Semantic boundary chunking assumed; exact implementation TBD |
| Light RAG (ORIENT phase) retrieval | Separate scope from deep RAG design |

## 10. Implementation Plan — Option A (Qdrant-First, Graph-Later)

Each stage is self-contained and produces a testable artifact. Stage descriptions below include exactly what to build, what not to build, and the acceptance gate. A new session should read this section first, then the relevant architecture sections above.

### Stage A1: Core Models + Edge Contract

**Build**: Pydantic models for Category enum, Tag taxonomy, node type labels, edge type enums. Generate `docs/rag-dev/edge-contract.json` from the edge table in §3. Validation function that accepts `(source_label, relation, target_label)` and returns True if legal.

**Do NOT build**: Qdrant client, graph client, embeddings, LLM calls, ingestion pipeline.

**Files to produce**:
- `docs/rag-dev/edge-contract.json` — adjacency matrix, machine-readable
- `src/memory/models.py` — Category, Tag, NodeType, EdgeType enums
- `src/memory/edge_validator.py` — validate(s_label, rel, t_label) → bool

**Acceptance gate**: `pytest` passes on: (a) imports work, (b) edge validator rejects illegal edges from contract, (c) edge validator accepts all legal edges.

**Notes for implementer**:
- Category enum values: `technical_fact, bug, decision, goal, code_symbol, documentation, exploration_finding, session_memory`
- Node type labels derive from §2 table
- Edge contract format: `{"Bug": {"Component": ["AFFECTS"], ...}, ...}` — list `source → [edge] → target`

---

### Stage A2: Qdrant Ingestion Pipeline

**Build**: Qdrant client wrapper, collection creation with payload indexes, nomic-embed-text integration (via Ollama), chunker (semantic boundaries — paragraph/newline based initially), classifier (deepseek-flash → category + tags), ingest script that takes a file path and produces populated Qdrant points.

**Do NOT build**: Graph DB integration, entity extraction, session tracking, reingestion logic, `graph_node_id` field (leave null for now).

**Files to produce**:
- `src/memory/qdrant_client.py` — create_collection, upsert, search, scroll
- `src/memory/embedder.py` — embed(texts) via Ollama nomic-embed-text (768d)
- `src/memory/chunker.py` — chunk(text) → list[str] (paragraph-split initially)
- `src/memory/classifier.py` — classify(text) → (Category, list[str]) via deepseek-flash
- `src/memory/ingest.py` — ingest_file(path) → IngestResult (wrap above components)
- `scripts/ingest_test.py` — CLI entry: `python scripts/ingest_test.py <path>`

**Acceptance gate**:
1. Ingest `docs/context/stack.md` → verify Qdrant has points
2. Ingest a session summary → verify correct category assignment (manual spot-check)
3. Run vector search: "what embedding model is used?" → returns chunk containing "nomic-embed-text"
4. Run filtered search: `category=bug` → returns only bugs (may be empty if none ingested — that's fine)
5. Ingest same file twice → verify no duplicates (idempotent upsert by chunk_id)

**Notes for implementer**:
- Qdrant host/port from env: `QDRANT_HOST`, `QDRANT_PORT` (see stack.md)
- Ollama URL from env: `OLLAMA_URL` (see stack.md)
- deepseek-flash: available via opencode-go subscription — ask user for invocation details
- Chunk IDs: UUIDs, generated at ingest time
- Collection name: `memory_chunks` (hardcoded for now, configurable later)
- Payload indexes: create AFTER first ingestion to avoid empty-index overhead (or create inline — your call)
- The `graph_node_id` field in payload: set to `None`/`null` — will be populated in A4

---

### Stage A3: Graph DB Integration

**Build**: Abstract `GraphStore` interface (see §8). Concrete implementation for Memgraph via Bolt protocol (or placeholder if Memgraph not available yet). Entity extractor (deepseek-flash → list of nodes + edges from text). Graph ingestion that MERGEs nodes and edges, validates against edge contract from A1.

**Do NOT build**: Bidirectional linkage to Qdrant (A4), `:Chunk` reference nodes, session tracking (A5), retrieval queries.

**Files to produce**:
- `src/memory/graph/interface.py` — GraphStore ABC
- `src/memory/graph/memgraph.py` — MemgraphGraphStore (or mock if unavailable)
- `src/memory/extractor.py` — extract_entities(text) → (nodes, edges)
- `scripts/ingest_graph.py` — ingest file → classify → extract → upsert graph

**Acceptance gate**:
1. Ingest `docs/context/stack.md` → verify `(:Component {name: "qdrant"})` node exists
2. Ingest same → verify `(:Component)-[:DEPENDS_ON]->(:Component)` edge exists (qdrant depends on ollama)
3. Run Cypher: `MATCH (n) RETURN labels(n), count(*)` → returns node type distribution
4. Edge validation: attempt illegal edge via extractor → verify rejection
5. If Memgraph unavailable: interface + mock passes same tests with in-memory dict store

**Notes for implementer**:
- Memgraph connection: check with user for host/port/credentials
- If Memgraph not running: implement a `DictGraphStore` (in-memory) that satisfies the ABC — makes A4/A5 testable without infrastructure dependency
- Extractor prompt must include the full edge contract so LLM knows what relationships are legal
- Node IDs: generate deterministically where possible (e.g., `component::qdrant`) to support MERGE

---

### Stage A4: Bidirectional Linkage

**Build**: `graph_node_id` field population in Qdrant payload. `:Chunk` reference nodes in graph with `EXTRACTED_TO` edges. Ingest flow: after Qdrant upsert and graph upsert, link each chunk_id to its graph node_id in both stores.

**Do NOT build**: Session tracking (A5), retrieval queries, validation loop.

**Files to modify**:
- `src/memory/ingest.py` — add linkage step after parallel Qdrant+graph upsert
- `src/memory/qdrant_client.py` — add `set_graph_node_id(chunk_id, node_id)` or rely on upsert with full payload

**Acceptance gate**:
1. Ingest a source → note a chunk_id from Qdrant
2. Query Qdrant for that chunk → verify `graph_node_id` is populated (not null)
3. Query graph: `MATCH (c:Chunk {id: $chunk_id})-[:EXTRACTED_TO]->(n) RETURN n` → returns correct node
4. Migration: run a script that backfills `graph_node_id` on all previously ingested A2 points (scroll Qdrant, find oldest `:Chunk` node by matching content hash or timestamp — implementer's discretion)

**Notes for implementer**:
- This stage assumes A2 data exists (Qdrant has points without graph_node_id) and A3 data exists (graph has nodes without Chunk refs)
- The linkage key: Qdrant `chunk_id` → `:Chunk {id: chunk_id}` → `[:EXTRACTED_TO]` → target node
- Migration strategy: if content is deterministic, match by source+offset; otherwise manual script

---

### Stage A5: Session Tracking + Reingestion

**Build**: Session model (immutable session_id, timestamps). Track which chunks and graph nodes a session produced. Reingestion: if source re-ingested, upsert existing chunks (version++), add `[:SUPERSEDES]` edges for replaced nodes, set stale status on superseded chunks.

**Do NOT build**: Validation loop (periodic re-evaluation — deferred), retrieval queries.

**Files to produce**:
- `src/memory/session.py` — Session dataclass, `track(chunk_id, node_id)`, `get_produced_ids()`
- `src/memory/reingest.py` — reingest logic: compare new chunks to session's tracked chunks, decide INSERT vs UPSERT vs SUPERSEDE

**Acceptance gate**:
1. Session A ingests a file → track produced IDs
2. Modify file, Session B reingests → verify existing chunk version incremented, new content has new chunk_id
3. Verify `status="superseded"` on old chunk, `graph_node_id` updated in Qdrant
4. Verify `[:SUPERSEDES]` edge in graph: `(new_node)-[:SUPERSEDES]->(old_node)`

---

### Stage A6: Deep Retrieval (Full GraphRAG)

**Build**: `retrieve_context(query)` — vector search Qdrant → collect graph_node_ids → graph traversal (1-2 hop BFS) → ranked, deduped context chunks. Optionally merge with Light RAG output from Memory Manager.

**Do NOT build**: Real-time indexing, streaming retrieval, MCP exposure (wrap later).

**Acceptance gate**:
1. Query "what issues affect qdrant?" → returns bug chunks + related component nodes
2. Measure: all chunk_ids resolved to correct graph nodes (no broken links)
3. Measure: BFS expansion adds related chunks not in initial vector results
4. P95 latency target: define with user before building

---

### Dependency Graph

```
A1 (models) ──────┬──────────────┐
                  ▼              ▼
               A2 (Qdrant)   A3 (Graph)
                  │              │
                  └──────┬───────┘
                         ▼
                      A4 (linkage)
                         │
                         ▼
                      A5 (sessions + reingest)
                         │
                         ▼
                      A6 (retrieval)
```

A2 and A3 can run in parallel after A1. All stages after A4 are sequential.
