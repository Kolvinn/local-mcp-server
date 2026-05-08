# Progress Log — Agentic Container Overhaul

## Session 001 — 2026-05-07

### Started
- Mandatory context read (docs/context/*) — ✅
- Explorer research (6 directories explored in parallel) — ✅
- Skills audit: langchain-architecture, langgraph-*, deep-agents-*, multi-agent-orchestration installed — ✅
- Planning files created (task_plan.md, findings.md, progress.md) — ✅

### Architecture Exploration
- Compared 5 volume/isolation approaches (MCP-gateway, bind-mount, overlayFS, volume-subpath, symlink-bridge) — ✅
- **Validated symlink bridge** in test-docker/ — ✅
  - Shared volume + per-agent volumes, orchestrator bridges via `ln -s`
  - Agent writes flow through symlink to shared volume
  - Zero copies, zero host access, dynamic grants without restart
- Architecture plan revised with validated symlink bridge model — ✅

### Current Phase
- Phase 0: Planning & Context Gathering — complete
- Phase 1: Architecture Design — in_progress (validated, design pending)

### Next Actions
1. Load `langgraph-fundamentals` — understand state model
2. Load `langchain-architecture` — container-per-agent patterns
3. Begin Phase 1 design: volume topology + container model

### Handoff
- `SESSION_HANDOFF.md` updated — session continuation recorded
- `docs/context/LEARNINGS.md` updated — §12 Agent Prompt Design added

### Session Continuation (Same Session)
- Skills loaded: `langgraph-fundamentals`, `langchain-architecture` — ✅
- Phase 1 design proposed (volume topology, container model, Flox, symlink bridge) — ✅
- Agent prompts redesigned (mechanics-not-domain philosophy) — ✅
  - `auditor.md` created (5-check framework, 96 lines)
  - `system_thinker.md` rewritten (127→89 lines)
  - `implementer.md` rewritten (removed domain assumptions, 84→87 lines)
  - `orchestrator.md` updated (consolidated principles, mandatory block)
- `opencode.jsonc` updated (removed coordinator/reviewer, added auditor, tightened permissions) — ✅
- Flox integration confirmed: baked into agent image, uses project toml manifest — ✅
- **Next**: Awaiting user approval on Phase 1 design, then delegate to System Thinker for formal spec

---

## Session 002 — 2026-05-08

### Agent Variation Framework Solidification
- Read SESSION_HANDOFF.md + architecture_chat.md + all context files
- Identified problems: RAG Architect breaks template model, missing architect variation, model mapping needed, interaction flow undefined
- User decisions captured:
  - Core 5 types: Orchestrator, System Thinker, Implementer, Auditor, Explorer
  - RAG Architect absorbed into System Thinker as `rag_thinker` variation
  - Researcher + Tester → backlog
  - Named variations with defined injection profiles (skills + context + model)
  - Model mapping: GLM-5.1 → Orchestrator, Qwen 3.6 Plus → Thinker, DeepSeek V4 Flash → Impl/Expl, DeepSeek V4 Pro → Auditor
  - Architect is System Thinker variation, not separate type
  - Code Auditor + Integration Auditor merged into single variation (context differentiates)
  - File-based handoff protocol: orchestrator reads summaries only, agents read/write specific directories

### Files Modified
- `.opencode/prompts/orchestrator.md` — Updated: Variation Framework section, File-Based Handoff Protocol, Read/Write Summary table
- `.opencode/prompts/system_thinker.md` — Updated: Read/Write Boundaries table, brief consumption clarification, anti-scope expanded
- `.opencode/prompts/implementer.md` — Updated: Read/Write Boundaries table, "Never read briefs" in anti-scope
- `.opencode/prompts/auditor.md` — Updated: Read/Write Boundaries table, "Never read briefs" in anti-scope
- `.opencode/prompts/explorer.md` — Updated: Mandatory Principles block added, Read/Write Boundaries table
- `.opencode/prompts/reviewer.md` — DELETED (absorbed into Auditor)
- `.opencode/prompts/coordinator.md` — DELETED (redundant with Orchestrator)
- `.opencode/prompts/rag_architect.md` — DELETED (absorbed into System Thinker as rag_thinker variation)
- `.opencode/opencode.jsonc` — Updated: model changes (glm-5.1, qwen3.6-plus, deepseek-v4-pro), removed rag_architect, added variation names to descriptions
- `docs/plans/overhaul/agent-variation-matrix.md` — CREATED: full variation table, interaction flow, model rationale, decisions log
- `docs/context/LEARNINGS.md` — Updated: §13 Variation Framework, §14 File-Based Handoff Protocol, §15 Retired Agents
- `docs/plans/overhaul/task_plan.md` — Updated: new phase numbering, variation framework section, agent roster updated
- `docs/plans/overhaul/findings.md` — Updated (next)
- `docs/plans/overhaul/progress.md` — This file

### Current Phase
- Phase 0: Planning & Context Gathering — ✅ complete
- Phase 1: Agent Design — ✅ complete
- Phase 2: Container & Volume Topology Design — pending (next)

### Next Actions
1. Delegate Phase 2 design to architect_thinker (System Thinker variation with architecture-patterns skill)
2. Design volume topology + Docker Compose layout + Flox env manifests per variation
3. Map variation matrix to container specs
4. User approval gate before implementation

---

## Session 003 — 2026-05-08

### Phase 2: Container & Volume Topology Design

#### What Happened
- User instructed: conda phased out, Flox is the way, containers long-lived per project
- Flox research delegated to `explorer` (not `explore`) with context7 skill — ✅
- Flox research written to `docs/exploration/flox-docker-research.md` — 553 lines
- Key findings: Flox in Docker works via apt install + `.flox/run/bin` on PATH, uv IS in Flox catalog, Nix closure adds ~100-200MB
- Phase 2 design spec delegated to architect_thinker (system_thinker variation)

#### Failures Encountered
| Failure | Cause | Resolution |
|---------|-------|------------|
| Explorer didn't load context7 | Used `explore` subagent type (thin search) instead of `explorer` (our defined agent) | Respawned with correct `explorer` subagent_type |
| Orchestrator read Docker/compose files directly | Violated context economy rule — should have delegated | Corrected; lesson recorded in LEARNINGS §16 |
| System thinker looped on context re-reading | Write tool silently failing on large content (1050-line spec) | Switched to bash `echo >>` commands for file writes |
| Multiple resume attempts failed | Same write-size issue persisted across resumes | Fresh approach: bash commands + small edits |

#### What Changed
- **Created**: `docs/exploration/flox-docker-research.md` — Flox research (553 lines)
- **Created**: `docs/specs/container-volume-topology.md` — Phase 2 design spec (1050 lines — needs splitting per §16)
- **Updated**: `docs/context/LEARNINGS.md` — §16 added (spec size limits, write failures, agent type selection, context economy)

#### Key Learnings (Session 003)
1. **Specs > 350 lines = failure.** Break into multiple files. Orchestrator must pre-empt this.
2. **Write tool silently fails on large content.** Fallback: bash `echo >>` / `cat`.
3. **`explore` ≠ `explorer`.** Different subagent types with different capabilities.
4. **Orchestrator reads too much.** Delegate file reading to sub agents.

### Current Phase
- Phase 0: Planning & Context Gathering — ✅ complete
- Phase 1: Agent Design — ✅ complete
- **Phase 2: Container & Volume Topology Design — spec written, awaiting user review**

### Next Actions
1. User reviews `docs/specs/container-volume-topology.md`
2. User approves (or requests changes) to Phase 2 design
3. Phase 3: LangGraph State Management (pending user gate)
