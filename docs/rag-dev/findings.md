# Findings & Decisions

## Requirements

- GraphRAG system within Memory Manager layer (orchestrator's GATHER phase — deep retrieval)
- Dual-store: Qdrant (vectors + chunk content) + graph DB (relationships), abstract interface
- Cypher-oriented graph interface, swappable backend (Memgraph being tested)
- Heterogeneous ingestion: memories, agent learnings, user goals, docs, code relationships, files
- Coherent metadata: Qdrant chunks must semantically link to graph entities (bidirectional `graph_node_id`)
- Category (singular, mutually exclusive) vs Tags (multiple, cross-cutting) — distinct metadata dimensions
- Nodes as nouns only — facts emerge from `(Node)-[edge]->(Node)` triples
- Edge types dependent on node pair — machine-readable contract
- Reingestable: session-tracked chunk IDs enable idempotent upserts
- Supersedes update model: stale content flagged, not deleted; temporal queries possible
- LLM classifier: deepseek-flash (via opencode-go subscription)
- Embedding: nomic-embed-text (768d, ~274MB) — performance first

## Research Findings

- Qdrant supports: complex payload filtering (must/should/must_not), keyword/text/int payload indexing, match.any/match.except for array fields, scroll iteration, range queries
- Qdrant payload indexing is required for performant filtered search on category/tags/status/validated_at
- Memgraph GraphRAG standard pattern co-locates chunks+vectors+entities in one database; we diverge intentionally
  - Pro: each store specialized (Qdrant for vector search, graph for relationships)
  - Con: retrieval requires two queries (Qdrant → IDs → graph traversal)
- Memgraph supports Bolt protocol, native Cypher, vector indexes on node properties
- Orchestrator architecture (from session-summary.md): Light RAG at ORIENT, Deep GraphRAG+Qdrant at GATHER
- Memory Manager subcomponents: Goal Graph, Phase Tracker, Context Index, Session State
- Mem0ai no longer in use — greenfield design
- Hardware: RTX 3080 (10GB VRAM), 32GB RAM — models must fit within constraints

## Technical Decisions

| Decision | Rationale |
|----------|-----------|
| Qdrant for content/vectors, graph DB for entities/relationships | Separation of concerns; each store optimized for its workload |
| Noun-only node taxonomy (10 types) | RDF-triple model: facts emerge from edges, not Fact nodes |
| Category/Tag distinction with Qdrant payload indexes | Enables filtered vector search without polluting graph schema |
| Edge contract as JSON file | Machine-readable validation for agents at ingestion + query time |
| Two-query retrieval pattern | Divergence from standard Memgraph pattern; trade-off accepted for store specialization |
| Lightweight `:Chunk` reference nodes in graph | Enables BFS expansion without storing content in graph |
| Session-tracked chunk IDs via `(:Session)-[:PRODUCED]->()` | Idempotent reingestion; session can update its own chunks |
| Abstract graph interface (Cypher-oriented) | Swappable backend; not committed to Memgraph yet |
| deepseek-flash for classification + extraction | Cheap, sufficient accuracy, accessible via opencode-go |
| nomic-embed-text (768d) | Already deployed; focus on performance before model upgrade |
| Implementation plan: Option A (Qdrant-First, Graph-Later) | Fastest path to usable search (A2 delivers vector search in 1-2 sessions). Graph layers on incrementally. A2+A3 can parallel after A1 |

## Resources

- Orchestrator diagrams: `docs/diagrams/orchestrator-thinking-loop-v2.mmd`, `docs/diagrams/orchestrator-overview-v2.mmd`
- Session summary: `docs/diagrams/session-summary.md`
- Stack context: `docs/context/stack.md`, `docs/context/services.md`, `docs/context/constraints.md`
- Memgraph GraphRAG skill: `.opencode/skills/memgraph-graph-rag/`
- Qdrant skills: `.opencode/skills/qdrant/`, `.opencode/skills/qdrant-vector-search/`
