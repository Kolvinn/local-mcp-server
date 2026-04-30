# Phase 2 Implementation Brief

## Task
Update `mcp-proxy-server.py` proxy config and RBAC permissions

## Files
- **Modify**: `mcp-proxy-server.py`
- **Reference**: `docs/plans/mcp-mem0-update/task_plan.md` (Phase 2), `docs/plans/mcp-mem0-update/findings.md` (lines 60-64)

## What to Change

### 1. Proxy Config (proxy_config dict)
- **REMOVE**: The `goals` stdio proxy block (lines with `python ./src/goal_trees.py`)
- **UNCOMMENT/ACTIVATE**: The `memory` HTTP proxy block pointing to `http://localhost:8000/mcp` with `streamable-http` transport
- Verify the URL format: `"url": "http://localhost:8000/mcp"`

### 2. Port Fix (line ~7)
- Change hardcoded `8001` to read from env var `MCP_PROXY_SERVER_PORT` with default `8000`
- Current: `PORT = int(environ.get("MCP_PROXY_SERVER_PORT", 8001))`
- Should be: `PORT = int(environ.get("MCP_PROXY_SERVER_PORT", 8000))`

### 3. RBAC - PERMISSION_TO_TOOLS
Add these 5 goal-tree tool names (NAMES ONLY, not full paths):
- `add_goal_node`
- `search_goal_nodes`
- `get_goal_tree`
- `update_goal_node`
- `delete_goal_node`

Where to add:
- `memory_read` role: add `get_goal_tree`, `search_goal_nodes` (read operations)
- `memory_write` role: add `add_goal_node`, `update_goal_node`, `delete_goal_node` (write operations)
- `memory_admin` role: add all 5 (full access)

Note: In PERMISSION_TO_TOOLS, tools are stored as simple names (e.g., `"search_goal_nodes"`), and the proxy prepends the service namespace when building full tool names.

### 4. Check AGENT_PERMISSIONS
- Verify no new agent roles needed (per task_plan.md)
- Confirm existing roles cover the new tool access patterns

## Key Notes
- The `memory` key in proxy_config must match the namespace tools use in main.py
- Port env var: `MCP_PROXY_SERVER_PORT` (not `PORT`)
- The `goals` entry should be removed entirely, not just commented

## Output
Return the complete modified `mcp-proxy-server.py` file with all Phase 2 changes clearly marked.
