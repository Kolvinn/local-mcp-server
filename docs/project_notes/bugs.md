# Bug Log

Bug entries with solutions and prevention notes. Keep entries brief and chronological.

---

### 2026-04-23 - Broken MCP Proxy Target in root main.py
- **Issue**: `main.py` (root) mounts a proxy to `mcp-memory-service:8000/mcp` — no container provides this endpoint. Server starts but all requests fail.
- **Root Cause**: Proxy scaffold references a downstream service that doesn't exist yet.
- **Solution**: Root main.py no longer exists. v0 uses in-process Mem0 in src/main.py (per ADR-007/019). **Fixed in Session 006.**
- **Prevention**: Don't create proxy routes to non-existent services. Wire real implementations first.

### 2026-04-23 - Port Misalignment (8001 vs 8000)
- **Issue**: Both `main.py` files ran on port 8001, but serving port is 8000. Docker compose also exposes 8001.
- **Root Cause**: Port 8001 was a default during scaffolding. Port 8000 was decided later but never propagated.
- **Solution**: src/main.py now uses PORT env var (default 8000). **Partially fixed** — docker-compose.yml and config.json still reference 8001.
- **Prevention**: Define serving port in a single env var or config, reference everywhere.

### 2026-04-23 - Stale user_id "roo_agent" in src/main.py
- **Issue**: `src/main.py` hardcodes `user_id="roo_agent"` from the Roo Code era.
- **Root Cause**: Scaffolded during Roo Code usage and never updated.
- **Solution**: v0 uses AGENT_ID env var (default: "default_agent"). **Fixed in Session 006.**
- **Prevention**: Don't hardcode agent-specific identifiers. Use generic or configurable values.

### 2026-04-23 - Duplicate Imports and Messy Code in src/main.py
- **Issue**: `src/main.py` had duplicate imports and inconsistent code structure from iterative scaffolding.
- **Root Cause**: Multiple sessions of incremental edits without cleanup.
- **Solution**: Complete rewrite in Session 006 — clean imports, no duplicates, well-structured. **Fixed.**
- **Prevention**: Always review and clean before committing incremental changes.

---

## Tips

- Keep descriptions under 2-3 lines
- Focus on what was learned, not exhaustive details
- Include enough context for future reference
- Date entries so you know how recent the issue is
- Periodically clean out very old entries (6+ months)