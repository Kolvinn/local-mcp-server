# Phase 1 Implementation Brief

## Task
Add 5 goal-tree MCP tools + 2 helpers to `src/main.py`

## Files
- **Modify**: `src/main.py`
- **Reference**: `docs/plans/mcp-mem0-update/SPEC.md` (sections 4.1, 4.2, 4.3, 4.4)

## What to Add

### 1. Pydantic Input Models (section 4.4)
Add these BEFORE the existing tool functions in `main.py`:
- `AddGoalNodeInput`
- `SearchGoalNodesInput`
- `GetGoalTreeInput`
- `UpdateGoalNodeInput`
- `DeleteGoalNodeInput`

Follow the exact schema in SPEC.md section 4.4.

### 2. Helper Functions
Add before the `@mcp.tool()` decorators:

**`build_goal_filters()`** - Mem0-compatible filter constructor
- Signature: `build_goal_filters(node_type, root_id, parent_id, session_id, status, project_id, tags) -> Dict[str, Any]`
- Tags use OR logic within list; all other fields use AND
- Reference: SPEC.md section 4.3 / existing `build_search_filters` pattern in main.py

**`reconstruct_tree()`** - Build nested JSON from flat Mem0 results
- Signature: `reconstruct_tree(all_nodes: List[Dict], root_id: str) -> Dict`
- Reference: SPEC.md section 4.3 `BuildTreeNode` subroutine

### 3. MCP Tools (section 4.2)
Add these `@mcp.tool()` decorated functions:
- `add_goal_node(input: AddGoalNodeInput) -> str`
- `search_goal_nodes(input: SearchGoalNodesInput) -> str`
- `get_goal_tree(input: GetGoalTreeInput) -> str`
- `update_goal_node(input: UpdateGoalNodeInput) -> str`
- `delete_goal_node(input: DeleteGoalNodeInput) -> str`

All return `str` (JSON or formatted text). Error returns start with `"Error:"`.

### 4. Dependencies
- `List`, `Dict`, `Any` from `typing`
- `Optional` from `typing`
- `List` from `typing` (already imported)
- `uuid.uuid4()` for node ID generation
- `json` for tree output
- `datetime.datetime.utcnow()` for `validated_at` timestamp

### 5. AGENT_ID
Use the existing `AGENT_ID` global that `main.py` already has (loaded from env). Do NOT hardcode.

## Key Constraints
- `infer=False` always for goal nodes
- Use `memory_client` global (already initialized)
- No new imports of `qdrant_client` or `ollama`
- All tools use `from fastmcp import FastMCP` (already imported)
- Match existing error handling pattern in main.py

## Existing Patterns to Follow
- Look at existing tool functions for input model usage
- `build_search_filters` in main.py for filter building pattern
- Error handling: try/except with `"Error: ..."` return strings
- Tool docstrings with descriptions

## Output
Return the modified `src/main.py` with all additions clearly marked.
