# Phase 5 Implementation Brief

## Task
Add unit tests (mocked) + integration tests (live) for 5 new goal-tree tools

## Files
- **Modify**: `src/test_main.py` (unit tests)
- **Create**: `scripts/test_goal_tools_live.py` (integration tests)
- **Reference**: `docs/plans/mcp-mem0-update/SPEC.md` (sections 5, 6), `scripts/test_mcp_proxy.py`, `scripts/mcp-test.sh`

## Test Strategy: Dual Approach

### 1. Unit Tests (Mocked) — src/test_main.py
Follow existing mock pattern. Fast feedback, verify code paths.

**Add 5 test classes:**

1. **TestAddGoalNode**
   - test_invalid_node_type_returns_error
   - test_parent_id_without_root_id_returns_error
   - test_valid_call_builds_correct_metadata
   - test_error_handling

2. **TestSearchGoalNodes**
   - test_filter_building
   - test_result_formatting
   - test_empty_results

3. **TestGetGoalTree**
   - test_tree_reconstruction
   - test_missing_root_returns_error_json
   - test_flat_results

4. **TestUpdateGoalNode**
   - test_invalid_status_returns_error
   - test_partial_metadata_update
   - test_error_handling

5. **TestDeleteGoalNode**
   - test_deletes_correct_node_id
   - test_error_handling

### 2. Integration Tests (Live) — scripts/test_goal_tools_live.py
Hit actual running server via MCP protocol. Verify real Mem0 + Qdrant + Ollama behavior.

**Use MCPTester class from `scripts/test_mcp_proxy.py`** as reference. Create similar script that:

1. Connects to `http://localhost:8000/mcp` (main.py directly) or `http://localhost:8001/mcp` (via proxy)
2. Calls `init` handshake
3. Tests each goal-tree tool with real data:
   - `add_goal_node` — create a real goal node
   - `search_goal_nodes` — search for it
   - `get_goal_tree` — fetch the tree
   - `update_goal_node` — update it
   - `delete_goal_node` — delete it
4. Uses unique IDs/tags to avoid collisions
5. Cleans up test data after each test (teardown)

**Test data approach:**
- Use unique prefixes like `test_goal_<uuid>[:8]` for content
- Use unique tags like `test-goal-<timestamp>`
- Clean up via `delete_goal_node` in teardown

**Infrastructure assumed:**
- Qdrant at `QDRANT_HOST:QDRANT_PORT`
- Ollama at `OLLAMA_URL`
- main.py running on port 8000

## Verification
- Run `pytest src/test_main.py` — unit tests must pass
- Run `python scripts/test_goal_tools_live.py` — integration tests must pass
- Both test suites must pass

## Key Notes
- Unit tests mock `memory_client`; integration tests use real Mem0
- Integration tests assume server is running (can be skipped if not)
- Use `requests` library for HTTP (already in environment)

## Output
1. Write unit tests to `src/test_main.py`
2. Create `scripts/test_goal_tools_live.py`
3. Return brief summary: tests added, integration test result
