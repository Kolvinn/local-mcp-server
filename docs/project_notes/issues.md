# Issues / Work Log

Work completed and planned, with ticket references where available. Keep it simple — just enough to remember what was done.

---

### 2026-04-23 - Session 002: Architecture & Planning Alignment
- **Status**: Completed
- **Description**: Read and absorbed all `.memory/` files. Confirmed architectural decisions with user (ADRs 007-009 accepted). Installed mem0, architecture-patterns, and planning-with-files skills.
- **Notes**: Planning-first approach confirmed (ADR-008). No code written this session.

### 2026-04-23 - Session 002: Memory Migration
- **Status**: Completed
- **Description**: Migrating `.opencode/memory/` to `docs/project_notes/` (project-memory skill format).

---

### 2026-04-23 - Session 003: Architecture Planning Complete
- **Status**: Completed
- **Description**: Full 5-phase architecture plan for dual-layer memory MCP server. Defined 7 v1 tools, 3-dimension scoping, git-first drift detection, on-retrieval staleness checks. ADRs 010-014 recorded. V2 items deferred (cleanup_stale, check_drift, reingest, subagents). Detailed plan in task_plan.md + findings.md.

### 2026-04-23 - Session 004: Agentic Team Architecture Research & Design
- **Status**: Completed (Phase 1 of 6)
- **Description**: Researched OpenCode agent/plugin/SDK ecosystem. Designed 3-agent team (explorer, implementer, reviewer) with tiered delegation (Task → CLI → Server API) and coordinator-side skill injection. Evaluated ecosystem plugins (background-agents, subtask2, conductor). Created task_plan_agents.md + findings_agents.md.
- **Notes**: Skills to install externally: subagent-creator, fastmcp, code-review-quality. Phase 2 (config changes) is next.

### 2026-04-24 - Session 005: Agent Architecture Redesign & Config
- **Status**: Completed
- **Description**: Redesigned 3-agent team to 5-agent team with 3-layer delegation (ADR-017/018). Created prompts/expert.md (domain principles + skill index), prompts/implementer.md (syntax-focused), prompts/reviewer.md (priority-based review). Updated coordinator prompt with user gates and @expert delegation. Updated opencode.jsonc with 5 agents.
- **Notes**: ADR-015/016 superseded by ADR-018/017. Expert bakes domain knowledge only; coordinator passes project context per-task. Delegation flow mapping still needed.

### 2026-04-24 - Session 006: v0 MCP Server Implementation
- **Status**: Completed
- **Description**: Pivoted from hexagonal directory structure to working v0 implementation (ADR-019). Replaced old src/main.py with 5-tool MCP server: add_memory, search_memory, delete_memory, sync_metadata, list_projects. 50 tests passing. Forward-compatible metadata schema (tags, project_id, source_user, related_files, source_path, validated_at). Path validation on sync_metadata.
- **Notes**: Delegation flow worked: explorer→expert→implementer→reviewer→implementer(fixes). User gate at each stage.

### 2026-04-25 - Session 007: Live Ingestion Test Planning
- **Status**: In Progress
- **Description**: Planned live infrastructure smoke test for all 5 MCP tools. Discovered EMBEDDING_MODEL default mismatch (bge-m3 → nomic-embed-text), fixed. Proposed adding `infer` parameter to `add_memory` (ADR-020). Designed 11-test ingestion plan (ADR-021). Key architectural question emerged: should fact extraction happen server-side (infer=True, local LLM) or agent-side (infer=False, agent pre-extracts facts)?
- **Notes**: Test must go through MCP protocol, not direct function calls. Cleanup via Qdrant collection deletion. Ollama has nomic-embed-text + llama3.1:8b pulled. Dependencies must be installed via `uv pip install` in conda dev1 env.

---

## Planned Work (Priority Order)

### Next: Fix docker-compose.yml & config.json
- **Status**: Not Started
- **Description**: Port 8001→8000 in docker-compose, config.json, and Traefik label. Add all 10 env vars to compose.
- **Priority**: 0e

### Next: Create .env.example
- **Status**: Not Started
- **Description**: Document all 10 env vars (9 original + MEMORY_CONTEXT_BASE). Note: .env was deleted; this would be a template only.
- **Priority**: 0f

### Next: Add `infer` Parameter to add_memory
- **Status**: Not Started
- **Description**: Add `infer` as optional boolean param to `add_memory` (default True). Enables testing embedding-only path and agent-side fact extraction. See ADR-020.
- **Priority**: 0h

### Next: Live Ingestion Test Suite
- **Status**: Not Started
- **Description**: Create `tests/integration/test_live_ingestion.py` — 11 tests across 5 tools + both infer paths. Test via MCP streamable-http protocol. Cleanup via Qdrant collection deletion. See ADR-021.
- **Priority**: 0g

### Next: Agent Team — Delegation Flow Mapping
- **Status**: Not Started
- **Description**: Map what project context the coordinator passes to the expert for each priority implementation item (ADRs, key facts, goal scope).
- **Priority**: 0c

### Next: Agent Team — Plugin Integration
- **Status**: Not Started
- **Description**: Install opencode-background-agents plugin, test delegate/delegation_read tools for async read-only delegation.
- **Priority**: 0d

### Next: Validation & Staleness (v0.1)
- **Status**: Not Started
- **Description**: On-retrieval staleness checks (validated_at + STALENESS_WINDOW_DAYS), git drift (git log --since on related_files), validate_memories tool, audit_stale tool.
- **Priority**: 1

### Next: .memory-context.yaml Discovery (v0.2)
- **Status**: Not Started
- **Description**: Auto-discover .memory-context.yaml per directory (like .gitignore cascade). Inject project_id + tags into search filters automatically.
- **Priority**: 2

### Next: compact_session Tool (v0.2)
- **Status**: Not Started
- **Description**: Session summarization → permanent facts via Mem0 + LLM.
- **Priority**: 3

### Next: Hexagonal Refactor (v1.0)
- **Status**: Not Started
- **Description**: Restructure src/ into domain/, use_cases/, adapters/, infrastructure/ per expert design. No functional changes — purely structural.
- **Priority**: 4

---

## Tips

- Keep descriptions brief (1-2 lines max)
- Always include ticket URL for easy reference if applicable
- Update status if work gets blocked or resumed
- Clean out very old entries periodically (3+ months)