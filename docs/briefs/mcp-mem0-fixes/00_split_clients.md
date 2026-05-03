# Brief 0: Split into two Memory clients with named collections

## Context
Bug 1: existing Qdrant `mem0` collection has 1536-dim schema but `nomic-embed-text` outputs 768. Fix by naming collections explicitly — Mem0 auto-creates fresh ones with correct dims.

## Changes

### `src/main.py` — `init_memory_client()` (lines 47–89)

1. **Replace single `memory_client` global** with two: `mem_client` and `goal_client`.
2. **Add `collection_name` to each config dict** inside `vector_store.config`:
   - `"collection_name": "memories"` for general memory
   - `"collection_name": "goal_trees"` for goal nodes
3. **Share the config template.** Same host/port/llm/embedder for both. Only `collection_name` differs.
4. **Module-level globals** (line 44): replace `memory_client = None` with `mem_client = None` and `goal_client = None`.
5. **`init_memory_client()` returns both** or sets both globals. Legacy `init_memory_client()` call on line 89 must init both.
6. **No `memory_client` references remain** in the file.

### Tool function client assignments

| Client | Tools |
|--------|-------|
| `mem_client` | `add_memory`, `search_memory`, `delete_memory`, `list_projects`, `sync_metadata` |
| `goal_client` | `add_goal_node`, `search_goal_nodes`, `get_goal_tree`, `update_goal_node`, `delete_goal_node` |

### `mcp_proxy_server.py`
- No changes. Proxy mounts `main.py` as subprocess — internal changes invisible.

## Contract
- Both `Memory` instances share one Qdrant server, one Ollama server, one process.
- Zero additional VRAM/connection overhead.
- Old `mem0` collection becomes orphaned (delete manually: `curl -X DELETE http://qdrant:6333/collections/mem0`).

## Verify
- `pytest src/test_main.py` — expected to fail (tests still mock `main.memory_client`). Brief 3 fixes this.
- After Brief 4: `curl http://qdrant:6333/collections` shows `memories` and `goal_trees`, both 768-dim.
