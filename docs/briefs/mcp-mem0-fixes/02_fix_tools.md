# Brief 2: Fix tool implementations — user_id in filters + `limit`→`top_k`

## Context
Two Mem0 v3 API changes:
1. `user_id` must be in `filters` dict for `search()`/`get_all()`, not top-level kwarg.
2. `search()` parameter renamed from `limit=` to `top_k=` in v3 Python OSS.

Brief 1 already injected `user_id` into the helpers. This brief removes the now-redundant `user_id=AGENT_ID` kwargs and fixes the param rename.

## Changes

### A. Change `memory_client` references to correct client (per Brief 0)

Use `mem_client` for general memory tools, `goal_client` for goal-tree tools.

### B. `search_memory()` (lines 391–396)

1. Replace `memory_client.search(...)` with `mem_client.search(...)`.
2. Remove `user_id=AGENT_ID` kwarg. Filters from helper already carry it.
3. Replace `limit=top_k` with `top_k=top_k`.
4. Pass `AGENT_ID` to helper: `build_search_filters(tags..., user_id=AGENT_ID)`.

### C. `list_projects()` (lines 509–518)

5. Replace `memory_client.get_all(...)` with `mem_client.get_all(...)`.
6. Remove `user_id=AGENT_ID` top-level. Build filter inline: `filters={"user_id": AGENT_ID}`.
   **Keep `limit=limit`** — `get_all` param name in Python OSS v3 is unconfirmed. Verify with `inspect.signature(mem_client.get_all)` before changing.
7. Fallback `search()`: remove `user_id=AGENT_ID`, set `filters={"user_id": AGENT_ID}`, replace `limit=limit` with `top_k=limit`.

### D. `search_goal_nodes()` (lines 618–623)

8. Replace `memory_client.search(...)` with `goal_client.search(...)`.
9. Remove `user_id=AGENT_ID` kwarg.
10. Replace `limit=input.top_k` with `top_k=input.top_k`.
11. Pass `AGENT_ID` to helper: `build_goal_filters(..., user_id=AGENT_ID)`.

### E. `get_goal_tree()` (lines 683–694)

12. Replace `memory_client.get_all(...)` with `goal_client.get_all(...)`.
13. **Inline merge `user_id` into filters.** Current inline filters:
    `{"root_id": {"eq": root_id}, "node_type": {"in": ["goal","task","subtask"]}}`
    Wrap in AND with user_id:
    `{"AND": [{"user_id": AGENT_ID}, {"root_id": {"eq": root_id}, "node_type": {"in": ["goal","task","subtask"]}}]}`
14. Remove top-level `user_id=AGENT_ID` kwarg.
15. Same for fallback `search()`: merge user_id into filters, use `top_k=1000`.

### F. All other tools (add, delete, update, sync_metadata)

16. Change `memory_client.add(...)` → respective client. **No API signature change needed** — `add()` still accepts top-level `user_id` in v3.
17. Same for `delete()` and `update()`. Only client name changes.

## Contract
- Zero calls to `memory_client` remain (it no longer exists).
- All `search()` calls use `top_k=`, never `limit=`.
- All `get_all()` calls use `filters` dict carrying `user_id`, never top-level.

## Verify
- `pytest src/test_main.py` — expected to fail until Brief 3.
- Manual: no `memory_client` string in `src/main.py` except in tests.
