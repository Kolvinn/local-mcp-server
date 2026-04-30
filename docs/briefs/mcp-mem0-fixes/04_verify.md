# Brief 4: Verify — run tests + integration

## Context
All fixes applied (Brief 0–3). Verify everything passes.

## Steps

### 1. Unit tests
```bash
pytest src/test_main.py -v
```
**Requirement**: zero failures. All 94+ tests pass.

### 2. Integration tests
```bash
python scripts/test_goal_tools_live.py
```
**Requirement**: all goal-tree integration tests pass against live Qdrant + Ollama.

### 3. Qdrant collection check
```bash
curl -s http://qdrant:6333/collections | python3 -c "import sys,json; [print(c['name'], c.get('config',{}).get('params',{}).get('vectors',{}).get('size')) for c in json.load(sys.stdin)['result']['collections']]"
```
**Requirement**: both `memories` and `goal_trees` exist with 768-dim vectors.

### 4. Cleanup
Delete the orphaned `mem0` collection (1536-dim):
```bash
curl -X DELETE http://qdrant:6333/collections/mem0
```

## Expected output
- Unit tests: `94 passed` (or more, no failures)
- Integration tests: all tests pass
- Qdrant: two collections, both 768-dim
- No orphaned `mem0` collection

## If anything fails
Report which test failed and the error message. Do NOT attempt to fix — return to Coordinator.
