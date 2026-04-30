# Phase 3 Implementation Brief

## Task
Fix `.env` environment variables

## Files
- **Modify**: `.env`
- **Reference**: `docs/plans/mcp-mem0-update/task_plan.md` (Phase 3), `docs/plans/mcp-mem0-update/findings.md` (lines 86-87)

## What to Fix

### 1. OLLAMA_URL (CRITICAL BUG)
- **Current**: Uses shell interpolation `${}` which python-dotenv doesn't resolve
- **Fix**: Change to literal `http://ollama:11434`

### 2. AGENT_ID
- **Current**: Empty string `AGENT_ID=`
- **Fix**: Set to `AGENT_ID=default_agent`

### 3. PORT
- **Current**: May not exist or be wrong
- **Fix**: Set/add `PORT=8000`

### 4. Obsolete Variables (OPTIONAL - check if used)
- `OLLAMA_MODEL` - check if used anywhere; may be obsolete since Mem0 handles model internally
- `OLLAMA_HOST` / `OLLAMA_PORT` - check if used anywhere; may be obsolete
- If unused after Mem0 migration, remove or comment out

## Key Notes
- Do NOT use `${}` syntax — python-dotenv doesn't interpolate
- `http://ollama:11434` is the correct Docker service URL for Ollama
- `PORT=8000` matches the FastMCP server port in main.py

## Verification
After fix, verify:
- `OLLAMA_URL` is a valid HTTP URL (not shell syntax)
- `AGENT_ID` is non-empty
- `PORT` matches what main.py expects

## Output
Return the modified `.env` file content with all fixes applied.
