# Brief 3: Update tests to match corrected API

## Context
Tests mock the old `memory_client` singleton and assert old API signatures (user_id top-level, limit param). Must match Brief 0–2 changes.

## Changes

### A. Module-level mock replacement

In `src/test_main.py`, the module-level mock setup (near line 14–28):

1. **Replace `mock_memory_client = MagicMock()`** with two mocks:
   `mock_mem_client = MagicMock()` and `mock_goal_client = MagicMock()`
2. **Override module globals** after import:
   `main.mem_client = mock_mem_client`
   `main.goal_client = mock_goal_client`
3. **Remove** `main.memory_client = mock_memory_client`

### B. Client name changes per test class

| Test class | Old reference | New reference |
|-----------|--------------|---------------|
| `TestAddMemory` | `main.memory_client.add` | `main.mem_client.add` |
| `TestSearchMemory` | `main.memory_client.search` | `main.mem_client.search` |
| `TestDeleteMemory` | `main.memory_client.delete` | `main.mem_client.delete` |
| `TestListProjects` | `main.memory_client.get_all/search` | `main.mem_client.get_all / mem_client.search` |
| `TestSyncMetadata` | (no memory client) | unchanged |
| `TestAddGoalNode` | `main.memory_client.add` | `main.goal_client.add` |
| `TestSearchGoalNodes` | `main.memory_client.search` | `main.goal_client.search` |
| `TestGetGoalTree` | `main.memory_client.get_all/search` | `main.goal_client.get_all / goal_client.search` |
| `TestUpdateGoalNode` | `main.memory_client.update` | `main.goal_client.update` |
| `TestDeleteGoalNode` | `main.memory_client.delete` | `main.goal_client.delete` |
| `TestFilterConstruction` | (no client, but add `user_id` param) | unchanged except Brief 1 changes |
| `TestBuildGoalFilters` | (no client, but add `user_id` param) | unchanged except Brief 1 changes |
| `TestReconstructTree` | (no client) | unchanged |
| `TestConfigLoading` | (no client) | unchanged |
| `TestServerStartup` | (no client) | unchanged |
| `TestNoHardcodedValues` | (no client) | unchanged |

### C. Assertion changes — `user_id` location

Every test that asserts `user_id=AGENT_ID` as a top-level kwarg:

4. **Remove** `assert call_args[1]["user_id"] == main.AGENT_ID`.
5. **Replace with** `assert "user_id" in call_args[1]["filters"]` or equivalent assertion that `user_id` is inside the filters dict.

Key locations (approximate line numbers — search for pattern):
- `TestSearchMemory` tests
- `TestListProjects` tests
- `TestSearchGoalNodes` tests  
- `TestGetGoalTree` tests

6. **`TestSearchGoalNodes` line ~647–648**: The assertion `assert "user_id" not in call_kwargs.get("filters", {})` **flips** to `assert "user_id" in call_kwargs["filters"]`.

### D. Assertion changes — `top_k` vs `limit`

7. For `search()` mock assertions: verify `call_args[1]["top_k"]` instead of `call_args[1]["limit"]`.
   Affected: `TestSearchMemory`, `TestSearchGoalNodes`, `TestGetGoalTree` (search fallback path).
8. For `get_all()` mock assertions: keep `call_args[1]["limit"]` for now (see Brief 2 note about unconfirmed param name).

### E. `TestFilterConstruction` and `TestBuildGoalFilters`

9. Add `user_id=main.AGENT_ID` to all helper calls (per Brief 1).
10. Add new test cases verifying `user_id` appears in returned filters dict.

### F. `TestNoHardcodedValues`

11. If this class checks for `memory_client` string, update to `mem_client` or `goal_client`.

## Contract
- Every test that hit the old `memory_client` mock now hits `mem_client` or `goal_client`.
- All assertions match v3 API signatures.
- No `memory_client` references in test file.

## Verify
- `pytest src/test_main.py` — all tests pass.
