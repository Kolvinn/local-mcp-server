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

---

## Planned Work (Priority Order)

### Next: Agent Team — Configuration Changes
- **Status**: Not Started
- **Description**: Rename coder→implementer, add reviewer agent, update coordinator prompt/permissions, create focused agent prompts.
- **Priority**: 0 (prerequisite for all implementation work)

### Next: Agent Team — Plugin Integration
- **Status**: Not Started
- **Description**: Install opencode-background-agents plugin, test delegate/delegation_read tools for async read-only delegation.
- **Priority**: 0b

### Next: Implementation — Directory Structure
- **Status**: Not Started
- **Description**: Set up hexagonal src/ layout per architecture-patterns skill. Domain, use cases, adapters, infrastructure.
- **Priority**: 1

### Next: Fix Server Entry Point
- **Status**: Not Started
- **Description**: Single main.py at root, port 8000, remove broken proxy reference, wire Mem0 config from env vars.
- **Priority**: 2

### Next: Wire Mem0 Integration
- **Status**: Not Started
- **Description**: Implement add_memory, search_memory, delete_memory against Mem0 adapter.
- **Priority**: 3

### Next: Local Metadata Layer
- **Status**: Not Started
- **Description**: File discovery adapter, .memory-context.yaml parser, sync_metadata tool.
- **Priority**: 4

### Next: Validation & Staleness
- **Status**: Not Started
- **Description**: On-retrieval checks (validated_at + git log), validate_memories, audit_stale.
- **Priority**: 5

### Next: compact_session Tool
- **Status**: Not Started
- **Description**: Session summarization → permanent facts via Mem0 + LLM.
- **Priority**: 6

### Next: Add .env.example
- **Status**: Not Started
- **Description**: Document all 9 env vars.
- **Priority**: 7

---

## Tips

- Keep descriptions brief (1-2 lines max)
- Always include ticket URL for easy reference if applicable
- Update status if work gets blocked or resumed
- Clean out very old entries periodically (3+ months)