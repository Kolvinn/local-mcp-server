# Task Plan: Migrate goal_trees.py into Mem0-backend

## Goal
Replace the standalone `goal_trees.py` (raw Qdrant/Ollama) with Mem0-backed goal-tree tools inside `src/main.py`, sharing the existing `memory_client`. Expose all tools through the MCP proxy as a single, unified memory service.

## Current Phase
Phase 1

## Phases

### Phase 1: Add goal-tree tools to main.py
- [ ] Define goal-node metadata schema (field names, types, filter compatibility)
- [ ] Implement `add_goal_node` tool — Mem0-backed node creation
- [ ] Implement `search_goal_nodes` tool — Mem0-backed semantic + filtered search
- [ ] Implement `get_goal_tree` tool — fetch all nodes by root_id, reconstruct tree
- [ ] Implement `update_goal_node` tool — update content, status, parent_id, tags
- [ ] Implement `delete_goal_node` tool — delete single node (agent handles cascade)
- [ ] Add Pydantic input models for each new tool
- [ ] Add helper: `build_goal_filters()` for constructing goal-specific Mem0 search filters
- [ ] Add helper: `reconstruct_tree()` for building nested JSON from flat node list
- **Status:** pending

### Phase 2: Update proxy config & RBAC permissions
- [ ] Remove `goals` stdio proxy block from `proxy_config` in `mcp_proxy_server.py`
- [ ] Uncomment/activate `memory` proxy block (HTTP -> main.py on port 8000)
- [ ] Verify transport config: `streamable-http` to `http://localhost:8000/mcp`
- [ ] Add goal-tree tool names to `PERMISSION_TO_TOOLS` under `memory_read` and `memory_write`
- [ ] Add any new agent roles (if needed) to `AGENT_PERMISSIONS`
- [ ] Fix hardcoded port 8001 -> read from `MCP_PROXY_SERVER_PORT` env var (default 8000)
- **Status:** pending

### Phase 3: Fix .env environment variables
- [ ] Fix `OLLAMA_URL` — remove shell interpolation, change to `http://ollama:11434`
- [ ] Set `AGENT_ID=default_agent` (fill empty value)
- [ ] Add/verify `PORT=8000`
- [ ] Remove obsolete `OLLAMA_MODEL` and `OLLAMA_HOST`/`OLLAMA_PORT` if unused after migration
- **Status:** pending

### Phase 4: Remove legacy goal_trees.py
- [ ] Delete `src/goal_trees.py`
- [ ] Remove its compiled cache (`src/__pycache__/goal_trees*.pyc`)
- [ ] Verify no other files import `goal_trees`
- [ ] Verify `pyproject.toml` doesn't need `qdrant-client` or `ollama` added (Mem0 handles them)
- **Status:** pending

### Phase 5: Tests & verification
- [ ] Add `TestAddGoalNode`, `TestSearchGoalNodes`, `TestGetGoalTree`, `TestUpdateGoalNode`, `TestDeleteGoalNode` classes to `test_main.py`
- [ ] Follow existing mock pattern (mock memory_client, verify calls, verify formatting)
- [ ] Verify all existing tests still pass
- [ ] Verify proxy starts and lists all tools correctly
- [ ] Verify RBAC gatekeeper returns correct allowed_tools for each agent role
- **Status:** pending

## Key Questions
1. Mem0 filter operator syntax for metadata equality: `{"node_type": "goal"}` or `{"node_type": {"eq": "goal"}}`? (Answer: use simple dict equality, both work in Mem0 OSS v3)
2. Should `get_goal_tree` include node status in the tree output? (Yes — needed for goal-keeper agent)
3. Should `add_goal_node` auto-generate `root_id` when no parent given? (Yes — creates root goal)

## Decisions Made
| Decision | Rationale |
|----------|-----------|
| Single Mem0 collection, no session collections | Mem0 manages its own Qdrant collection; metadata fields provide partitioning |
| `node_type` stored as metadata field | Mem0 supports `eq`/`in` filter operators on metadata keys — enables filtering by goal/task/subtask |
| Tree reconstruction in-memory via `get_goal_tree` | Mem0 stores flat memories; no graph traversal API. Fetch by root_id, build tree client-side |
| Agent handles cascade delete | Keeps tool simple; goal-keeper agent has full context to decide cascade policy |
| Goal tools use `memory__` namespace in proxy | All tools live in `main.py` -> same proxy server key `"memory"` |
| No new dependencies | Mem0 is already in `pyproject.toml`; handles Qdrant and Ollama internally |
| `FastMCP` from `fastmcp` package | Consistent with `mcp_proxy_server.py` and `pyproject.toml` (`fastmcp>=3.2.4`) |
| Agent IDs not hardcoded | `AGENT_ID` persists from `main.py` into Mem0 calls; per constraint doc |

## Notes
- Goal-keeper agent (future, not in this plan) will handle merge/update/delete heuristics using the `update_goal_node` and `delete_goal_node` tools
- Tools return strings (JSON or formatted text) for MCP compatibility, matching existing pattern
- No changes to `requirements.txt` — dependencies managed in `pyproject.toml`
- `create_session_collection` is deliberately dropped — no Qdrant collection management needed with Mem0
