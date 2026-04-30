# Brief 1: Fix filter helpers — inject `user_id`

## Context
Mem0 v3 requires `user_id` inside `filters` dict for `search()` and `get_all()`. Move it into the helpers so tool callers don't manage it inline.

## Changes

### `src/main.py` — `build_search_filters()` (lines 176–201)

1. **Add `user_id: str` parameter.** Signature becomes:
   `build_search_filters(tags, project_id, source_user, user_id)`
2. **After building the conditions list, merge `user_id`:**
   - If conditions empty → return `{"user_id": user_id}`
   - If conditions exist → return `{"AND": [{"user_id": user_id}, conditions_result]}`
3. Existing tag/project/source logic **unchanged.**

### `src/main.py` — `build_goal_filters()` (lines 204–250)

4. **Add `user_id: str` parameter.** Signature becomes:
   `build_goal_filters(node_type, root_id, parent_id, session_id, status, project_id, tags, user_id)`
5. **Same merge logic** as `build_search_filters` — insert `{"user_id": user_id}` as first condition in AND.

### `src/test_main.py` — `TestFilterConstruction` test class

6. **Add `user_id=main.AGENT_ID` to all `build_search_filters()` calls** in test functions.
7. **Add new test cases:**
   - `user_id` alone → returns `{"user_id": "..."}`
   - `user_id` + tags → AND wraps both
   - `user_id` + project → AND wraps both
   - `user_id` + tags + project → AND wraps all three

### `src/test_main.py` — `TestBuildGoalFilters` test class

8. **Add `user_id=main.AGENT_ID` to all `build_goal_filters()` calls.**
9. **Add new test cases** mirroring the `build_search_filters` additions.

## Contract
- Both helpers always return a filters dict containing `user_id`.
- Callers (Brief 2) no longer pass `user_id=AGENT_ID` as a separate kwarg.
- `user_id` always first condition in AND (ordering irrelevant, but consistent).

## Verify
- `pytest src/test_main.py -k "TestFilterConstruction or TestBuildGoalFilters"` passes.
