# Findings & Decisions

## Requirements
- Merge goal_trees.py functionality into main.py's Mem0 client
- Keep goal-tree tools as distinct MCP tool endpoints
- Share the existing `memory_client` (Mem0 OSS) — no raw Qdrant/Ollama
- Expose through the same proxy namespace
- Normalize FastMCP imports
- No creating/deleting Qdrant collections — single collection, metadata-partitioned

## Research Findings

### Current Architecture
- `mcp-proxy-server.py`: Orchestrator on port 8001 (hardcoded), proxies child MCP services
  - `sequential_thinking`: stdio via bunx
  - `goals`: stdio via `python ./src/goal_trees.py`
  - `memory`: HTTP (commented out)
- `src/main.py`: Mem0 OSS server on port 8000 (HTTP)
  - 5 tools: add_memory, search_memory, delete_memory, sync_metadata, list_projects
  - `from mem0 import Memory` — OSS self-hosted class
  - Config: Qdrant + Ollama (nomic-embed-text, llama3.1:8b)
- `src/goal_trees.py`: Standalone stdio server
  - 3 tools: create_session_collection, ingest_node, search_similar_nodes
  - Direct QdrantClient + ollama client (bypasses Mem0)
  - `from mcp.server.fastmcp import FastMCP` — mismatched import

### Mem0 OSS API (v3) — Key Methods for This Task

**`memory_client.add(content, user_id, metadata={}, infer=True)`**
- `content`: string or list of message dicts
- `metadata`: dict with custom key-value pairs (stored in vector DB payload)
- `infer`: True -> LLM extracts categories/summaries; False -> raw storage
- Returns: `{"results": [...], "relations": [...]}`
- For goal nodes: `infer=False` to store raw text without LLM transformation

**`memory_client.search(query, filters={}, user_id, limit=10, threshold=0.1)`**
- `filters`: dict with entity IDs + metadata conditions
- Filter operators: `eq`, `ne`, `in`, `nin`, `gt`, `gte`, `lt`, `lte`, `contains`, `not_contains`
- Entity filtering requires `user_id` in `filters` dict (v3 behavior)
- Returns: list of `{id, memory, score, metadata, ...}`
- For goal nodes: `filters={"node_type": {"eq": "goal"}}` or `filters={"node_type": "goal"}`

**`memory_client.get_all(filters={}, user_id, limit)`**
- Retrieves all memories matching filters
- For tree reconstruction: `filters={"root_id": root_id}` needs metadata filter — verify if OSS supports metadata-only `get_all` filters or if search with high `top_k` is needed

**`memory_client.update(memory_id, text=None, metadata=None)`**
- Updates content and/or metadata of existing memory
- For goal nodes: update status, content, parent_id, tags

**`memory_client.delete(memory_id)`**
- Permanently deletes single memory

### Metadata Filtering Syntax
- Simple equality: `{"field": "value"}` or `{"field": {"eq": "value"}}` — both supported
- OR within field: `{"field": {"in": ["val1", "val2"]}}`
- Compound: `{"AND": [{"field1": "a"}, {"field2": "b"}]}`, `{"OR": [...]}`
- `main.py:build_search_filters` already demonstrates the pattern with `tags` and compound AND/OR

### Port & Transport
- `main.py` runs streamable HTTP on port 8000, endpoint path is `/mcp`
- `mcp-proxy-server.py` hardcodes port 8001 — should read from env `MCP_PROXY_SERVER_PORT`
- Constraint doc says target port is 8000, not 8001
- Proxy config for HTTP service: `{"url": "http://localhost:8000/mcp", "transport": "streamable-http"}`

### Import Paths
- Correct import: `from fastmcp import FastMCP` (matches `pyproject.toml` dep `fastmcp>=3.2.4`)
- Legacy import in goal_trees.py: `from mcp.server.fastmcp import FastMCP` (different package path)
- Goal: normalize all to `from fastmcp import FastMCP`

## Technical Decisions
| Decision | Rationale |
|----------|-----------|
| Metadata field `node_type` instead of separate Qdrant collections | Mem0 manages one collection; metadata key filtering is the standard partitioning method |
| `root_id` stored in every node's metadata | Enables fetching all nodes in a tree with a single filter query |
| `session_id` as optional metadata field | Groups related goals across agent sessions without creating collections |
| `status` field for lifecycle tracking | Needed for goal-keeper agent to mark complete/blocked/abandoned |
| Tree reconstruction in application code, not database | Mem0 has no graph/relationship traversal; simplest approach is fetch-all + client-side tree build |
| `infer=False` for goal nodes | Goal/task text is already structured by the agent; LLM inference would add noise |
| `update_goal_node` accepts partial updates | Only provided fields change; omitted fields left unchanged — standard PATCH semantics |
| Node types limited to `goal`, `task`, `subtask` | Validated on tool input; maps directly to the original `goal_trees.py` convention |

## Issues Encountered
| Issue | Resolution |
|-------|------------|
| `.env` OLLAMA_URL uses shell interpolation (`${}`) — python-dotenv doesn't resolve | Code defaults handle it, but env var is silently wrong. Fix to literal `http://ollama:11434` |
| `.env` AGENT_ID is empty string | Code defaults to `"default_agent"`. Set explicitly |
| `goal_trees.py` imports from `mcp.server.fastmcp` vs `fastmcp` | Irrelevant after deletion; `main.py` already uses correct `from fastmcp import FastMCP` |
| `goal_trees.py` has unused raw Ollama embedding function | Dropped; Mem0 handles embeddings internally |
| Proxy port hardcoded 8001 | Read from env var with default 8000 |
| Mem0 OSS `get_all` may not support metadata-only filters (no entity scope) | Use `search()` with high limit as workaround; verify during implementation |

## Resources
- Mem0 OSS Python client ref: `.agents/skills/mem0/client/python.md` (lines 323-455)
- Mem0 API filter reference: `.agents/skills/mem0/references/api-reference.md` (lines 57-105)
- Current main.py: `src/main.py` (395 lines) — patterns to follow
- Current test file: `src/test_main.py` (714 lines) — mock patterns to follow
- Proxy server: `mcp-proxy-server.py` (127 lines)
- Project constraints: `docs/context/constraints.md`
- Project stack: `docs/context/stack.md`
- Project conventions: `docs/context/conventions.md`
- Services doc: `docs/context/services.md`
