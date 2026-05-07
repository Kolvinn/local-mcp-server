# Plans Directory — Condensed Summary

## 1. `base/` — Mem0 MCP Server Architecture (Dual-Layer Memory)
- **Proposed:** Dual-layer memory server: Mem0 (semantic vector) + local metadata files (hierarchical YAML). 7 MCP tools, hexagonal architecture, staleness validation via git timestamps.
- **Scope/Goals:** Full architecture design across 5 phases (tool surface, data model, validation, config, failure modes). Hexagonal ports/adapters pattern. No code written until planning complete (ADR-008).
- **Status:** **Complete (designed).** All 5 phases done. No implementation started — code deferred to agent-team execution.

## 2. `agent-team/` — 5-Agent Team Architecture
- **Proposed:** Evolve from single generic `coder` to 5 specialized agents: **Coordinator** (why/strategy), **Expert** (domain knowledge, `all`-mode), **Explorer** (codebase scout, read-only), **Implementer** (spec-driven coding, `subagent`), **Reviewer** (priority-based verification, read-only). 3-layer delegation model with user approval gates.
- **Scope/Goals:** Agent config (opencode.jsonc), prompt files (expert.md, implementer.md, reviewer.md, updated coordinator.md), tiered delegation (Task tool → CLI → Server API/plugin). Skills baked into expert prompt for v1.
- **Status:** **Phases 1-3 complete (designed + configured).** Prompts created, opencode.jsonc updated with 5 agents. Expert delegation tested. Phases 4-7 pending: plugin integration (background-agents), custom write plugin, workflow automation, full verification.

## 3. `mcp-mem0-update/` — Goal Tree Migration into Mem0
- **Proposed:** Replace standalone `goal_trees.py` (raw Qdrant/Ollama) with 5 Mem0-native tools in `main.py`. Share single `memory_client`, delete duplicate infrastructure.
- **Scope/Goals:** 5 new MCP tools (`add_goal_node`, `search_goal_nodes`, `get_goal_tree`, `update_goal_node`, `delete_goal_node`), Pydantic models, proxy config + RBAC update, .env fixes, delete legacy file, 52 unit tests + integration script.
- **Status:** **FULLY ACTED ON — Complete.** All 5 phases implemented. SPEC.md defined metadata schema/tool pseudocode. main.py modified, proxy updated, goal_trees.py deleted, .env fixed, 96 unit tests passing.

## 4. `product_owner/` — Product Owner Strategic Agent Design
- **Proposed:** Design a project-agnostic strategic orchestration agent (product_owner) that owns the "why" — sits above the coordinator, delegates all exploration/summarization/code work, serves as single user point of contact.
- **Scope/Goals:** Agent system prompt with personality, delegation rules, write heuristic, communication flow, edge cases. Context from reference files (not baked). Coordinates specialist teams from `agent-team` file.
- **Status:** **Designed (agent design only).** SPEC.md + PO_trim.md (trimmed version) created. Phases 1-5 complete. Phase 6 (review) and Phase 7 (final spec) pending. Not yet instantiated as a live agent.

## Key Architectural Decisions Across Plans
- **Dual-layer memory** (Mem0 vector + local YAML files) with hierarchical discovery (like .gitignore)
- **Hexagonal architecture** — domain core never imports mem0ai/file I/O directly
- **5-agent team** with 3-layer delegation (why/how/what) and user approval gates at every stage
- **Expert owns domain knowledge** (baked in); **coordinator owns project context** (passed per-task)
- **Single Mem0 collection** for all data (general memories + goal nodes), metadata-partitioned via filters
- **In-memory goal-tree reconstruction** (flat Mem0 storage + client-side tree build)
- **Project-agnostic product_owner** — context from reference files, not baked prompts
