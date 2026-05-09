# Taxonomy Rebuild — Instructions for Downstream Agent

## Context

This is a **GraphRAG Memory Manager** project. Ingestion pipeline: file → chunk → classify → embed → upsert to Qdrant. A graph DB (Memgraph) layer is planned for later stages.

### Current architecture (`src/memory/`)

| File | Role |
|------|------|
| `models.py` | Hardcoded `StrEnum` classes: `Category` (8), `NodeType` (11), `EdgeType` (38), plus `TagRegistry` singleton with hardcoded bootstrap tag values |
| `classifier.py` | Keyword-heuristic classifier that references `Category.BUG`, `Category.SESSION_MEMORY`, etc. by enum member |
| `edge_validator.py` | Validates edge triples against `docs/rag-dev/edge-contract.json` (loaded at import time) |
| `chunker.py` | Paragraph-boundary text chunker |
| `embedder.py` | Ollama embeddings client (`nomic-embed-text`, 768d) |
| `ingest.py` | Full ingestion pipeline: read → chunk → classify → embed → upsert Qdrant |
| `qdrant_client.py` | Qdrant SDK wrapper: create collection, upsert, search, scroll, count |

### Current Qdrant point payload layout (from `spec.md` §4)

```python
{
    "chunk_id":       str,       # UUID — immutable identity
    "graph_node_id":  str,       # e.g. "bug-42" — bidirectional link (currently null)
    "session_id":     str,       # which session produced this
    "category":       str,       # singular category enum value
    "tags":           list[str], # cross-cutting labels
    "content":        str,       # chunk text
    "source":         str,       # origin file/path
    "version":        int,       # monotonic, incremented on reingest
    "validated_at":   int,       # unix timestamp of last validation pass
    "status":         str,       # active | superseded | stale | merged
}
```

Payload indexes (keyword): `category`, `tags`, `status`, `graph_node_id`, `validated_at`, `version`, `source`.

### Current categories (mutually exclusive)

`technical_fact`, `bug`, `decision`, `goal`, `code_symbol`, `documentation`, `exploration_finding`, `session_memory`

### Current node types (11, PascalCase for Cypher)

`Agent`, `Component`, `Document`, `Session`, `Goal`, `Decision`, `Bug`, `CodeEntity`, `Environment`, `Configuration`, `Chunk`

### Current edge types (38, SCREAMING_CASE)

Full list in `models.py:EdgeType` — includes `AFFECTS`, `LOCATED_IN`, `TRIGGERED_BY`, ... `EXTRACTED_TO`.

### Current tag dimensions (4) with bootstrap sets

- **scope**: `ollama`, `qdrant`, `memgraph`, `traefik`, `opencode`
- **domain**: `infra`, `code`, `architecture`, `testing`, `data`, `security`, `ux`, `devops`
- **quality**: `bug`, `workaround`, `verified`, `deprecated`, `unstable`, `critical`
- **phase**: `orient`, `gather`, `spec`, `code`, `review`, `deploy`

### Edge contract storage pattern (already exists)

`docs/rag-dev/edge-contract.json` is a machine-readable adjacency matrix loaded at import time by `edge_validator.py`. Format:

```json
{
  "Bug": {
    "Component": ["AFFECTS"],
    "CodeEntity": ["LOCATED_IN"]
  },
  "Chunk": {
    "*": ["EXTRACTED_TO"]
  }
}
```

---

## Task: Make Taxonomy Dynamic

Move all hardcoded taxonomy out of Python enums into a JSON config file, then build `StrEnum` classes dynamically from that JSON at import time.

### Assets that must become data-driven

1. **`Category` enum** — currently 8 hardcoded members
2. **`NodeType` enum** — currently 11 hardcoded members
3. **`EdgeType` enum** — currently 38 hardcoded members
4. **`TagRegistry._BOOTSTRAP`** — currently hardcoded `dict[str, set[str]]`
5. **Qdrant payload field definitions** — currently listed in `spec.md` §4 and `qdrant_client.py:_PAYLOAD_INDEX_FIELDS`

### What to produce

A new JSON file (or files) in `docs/rag-dev/` that defines:

- **Node types** — labels and optional metadata (example properties, description)
- **Edge types** — labels and optional metadata
- **Categories** — allowed category values
- **Tag dimensions** — bootstrap values per dimension
- **Qdrant payload schema** — field names, types, which get payload indexes, default values
- **Default collection config** — vector size, distance metric, collection name

The downstream agent should then read these doc files to **suggest** the actual content of the JSON — i.e., propose what node types, edge types, payload fields, and defaults should exist, given that the system should be adaptable to evolving ingested data rather than frozen at code time.

### Qdrant is schemaless — implications for this design

Qdrant does not enforce a payload schema. Any point can carry any JSON payload fields. This means we can dynamically add, remove, or reshape payload fields without migration — **but** data integrity requires consistency across points.

**Strategy:**

1. **Index important fields** — declare which payload fields get keyword/integer indexes (for filtered search). These indexes must exist at the collection level. Adding a new indexed field is a runtime API call (idempotent).
2. **Backfill new metadata fields** — when a new payload field is introduced (e.g. a new tag dimension or a new metadata key), points created *before* that field existed will lack it. Use the `refresh_payloads` method to detect and fix this.
3. **`refresh_payloads` method** — periodically scans points by comparing their `created_at` timestamp against the timestamp of when a metadata field was introduced. Any point with `created_at < field_introduced_at` is candidate for refresh: re-classify/re-embed or simply populate the new field with a default value.
4. **Cursor-based scan** — uses Qdrant's `scroll` API (page through all points) rather than a single large query, so it works on collections of any size.
5. **Idempotent** — running `refresh_payloads` multiple times is safe; it skips points already up-to-date.

This means a **metadata field registry** must exist — a record mapping each payload field name to the timestamp when it was introduced (e.g. `{"summary": "2026-05-09T12:00:00Z", "source_user": "2026-05-09T12:00:00Z"}`). When `refresh_payloads` runs, it reads this registry and for each point checks: if `point.created_at < field.introduced_at`, the point predates that field and needs a backfill. The registry itself lives in the taxonomy JSON, and gets updated whenever a new field is added to the schema.

### Example payload (inspired by prior mem0-based metadata patterns)

```python
{
    "chunk_id":       str,       # UUID — immutable identity
    "graph_node_id":  str,       # e.g. "bug-42" — bidirectional link
    "session_id":     str,       # which session produced this
    "created_at":     str,       # ISO8601 timestamp of first ingestion
    "updated_at":     str,       # ISO8601 timestamp of last modification
    "validated_at":   str,       # ISO8601 timestamp of last validation pass
    "category":       str,       # singular category value
    "tags":           list[str], # cross-cutting labels for filtering
    "source":         str,       # origin file/path
    "project_id":     str,       # project grouping key
    "source_user":    str,       # who this memory is about
    "source_path":    str,       # directory context at creation
    "related_files":  list[dict],# [{path, entered}, ...]
    "summary":        str,       # optional LLM-generated summary
    "version":        int,       # monotonic, incremented on reingest
    "status":         str,       # active | superseded | stale | merged
}
```

Not all of these fields are mandatory — `summary`, `related_files`, `source_user`, `source_path`, `project_id` may be null for many points. The taxonomy JSON should declare which fields are **indexed** (keyword, integer, etc.) and which are optional vs required.

### Design constraints

- The JSON must be loadable at import time (same pattern as `edge_validator.py` loading `edge-contract.json`)
- `StrEnum` classes should be built dynamically (e.g. `Category = StrEnum('Category', values_from_json)`)
- `TagRegistry` should read its bootstrap from the same JSON
- The classifier's keyword rules currently reference Python enum members (e.g. `Category.BUG`) — those will need to become string literals matching the JSON values
- The `__init__.py` currently re-exports enum members — update if names change
- **Do NOT modify tests** — they will be updated in a separate pass
- The Qdrant payload layout must remain compatible with `ingest.py` which builds points with specific field names

### Downstream agent's job

1. Read `spec.md` (especially §2 Node Taxonomy, §3 Edge Contract, §4 Qdrant Schema)
2. Read `models.py` (current Category, NodeType, EdgeType, TagRegistry)
3. Read `edge-contract.json` (existing adjacency matrix)
4. Read `qdrant_client.py` (current payload indexes, vector config)
5. Read `classifier.py` (how it references current enum values)
6. **Propose** the new JSON taxonomy file contents — which node types, edge types, categories, tag dimensions, payload fields, and defaults should the system use, optimized for dynamic adaptation as data evolves?
7. Note any fields in the current payload that seem vestigial or should be reconsidered for dynamic generation
8. Flag any enums that might shrink vs grow vs stay static
9. **Research Qdrant payload indexing** via the context7 skill — understand best practices for which field types need indexes, the performance trade-offs of indexing too many vs too few fields, and how to dynamically manage indexes at runtime (create, drop, modify). Use this research to inform which payload fields in the proposal should be indexed and why.
