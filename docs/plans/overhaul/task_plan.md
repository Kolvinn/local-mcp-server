# Task Plan — Agentic Container Overhaul

## Goal
Overhaul local Docker setup from a single OpenCode MCP server into a **LangGraph-based multi-container agent system** powered by **Flox environments**. Each agent type is a generic template with config-driven variations (model + skills + context), its own stateflow, learnings, and filesystem isolation via the orchestrator acting as a symlink bridge between shared and agent-specific Docker volumes.

## Core Architecture (Validated)
```
project-vol (shared, source of truth)     agent-vol(s) (isolated per agent)
┌──────────────────┐                     ┌──────────────────┐
│ src/             │                     │ /ws/             │
│ tests/           │     orchestrator    │  src/ ───symlink │
│ docs/            │◄────mounts both────►│  tests/──symlink │
│ config/ (hidden) │     creates symlinks│                  │
└──────────────────┘                     └──────────────────┘
```
- **Orchestrator** mounts `project-vol` + all `agent-vol`s, bridges via `ln -s`
- **Agents** mount only their own `agent-vol`, see only what orch symlinked
- **Writes** follow symlinks → land in `project-vol` directly
- **Dynamic grants**: orch adds/removes symlinks (no container restart)
- **Zero copies, zero host access, zero Docker socket**

## Agent Variation Framework (Solidified)
See `docs/plans/overhaul/agent-variation-matrix.md` for full detail.

**5 core types, config-driven variations:**
| Type | Variations | Model |
|------|-----------|-------|
| Orchestrator | (none — primary) | glm-5.1 |
| System Thinker | strategic_thinker, rag_thinker, architect_thinker | qwen-3.6-plus |
| Implementer | python_implementer, infra_implementer | deepseek-v4-flash |
| Auditor | code_auditor | deepseek-v4-pro |
| Explorer | codebase_explorer, dependency_explorer | deepseek-v4-flash |

**Principle:** Prompts stay generic. Variations = model + skills + context injection. New variations = new config row, zero prompt changes.

**File-Based Handoff:** Orchestrator never reads full content — only summaries + file paths. Thinkers write briefs/specs, implementers read specs, auditors read specs+code, explorers write to docs/exploration/. Each agent only sees what it needs.

**Retired types:** Reviewer (→ Auditor 5-check), Coordinator (→ redundant), RAG Architect (→ rag_thinker variation)

**Backlog types:** Researcher, Tester

## Constraints (from docs/context/constraints.md)
- RTX 3080 (10GB VRAM), 32GB RAM
- Python 3.14+, uv package manager, conda
- Ollama (llama3.1:8b, nomic-embed-text 768d)
- Qdrant vector store
- Single user, no auth
- No npx (bunx only)
- **Agents never access host** — only Docker volumes

---

## Phases

### Phase 0: Planning & Context Gathering — ✅ Complete

### Phase 1: Agent Design — ✅ Complete
- Agent types solidified: Orchestrator, System Thinker, Implementer, Auditor, Explorer
- Variation framework designed: config-driven, prompts stay generic
- Model assignments: GLM-5.1 (orch), Qwen 3.6 Plus (thinker), DeepSeek V4 Flash (impl/expl), DeepSeek V4 Pro (auditor)
- File-based handoff protocol: orchestrator reads summaries only, agents read/write to specific directories
- Read/write boundaries defined per agent type
- Prompts updated with variation awareness and boundary tables
- Legacy agents deleted (reviewer, coordinator, rag_architect)
- Config updated (opencode.jsonc)
- Variation matrix documented: `docs/plans/overhaul/agent-variation-matrix.md`

### Phase 2: Container & Volume Topology Design
**Status:** pending

- Design volume topology: `project-vol` (shared) + per-agent `agent-vol`s
- Design orchestrator symlink management (grant/revoke file access per task)
- Define Docker Compose layout (orchestrator + N agents on `internal-net`)
- Define Flox environment per agent variation (each variation = different Flox manifest)
- Define container-per-agent model: one Dockerfile template, parameterized by variation
- Define context injection mechanism (env vars, startup args, variation config)
- Map variation matrix to container specs (each row → Dockerfile + Flox + skill preload)
- **Gate:** User approves volume topology + container model

### Phase 3: LangGraph State Management
**Status:** pending

- Design per-agent StateGraph (state schema, nodes, edges, conditional routing)
- Design LangGraph persistence (checkpointer) per agent for "learnings" retention
- Design approval gate integration (human-in-the-loop interrupts)
- Design orchestrator state: tracks agent assignments, phase transitions, session context
- **Skills needed:** langgraph-fundamentals, langgraph-persistence, langgraph-human-in-the-loop
- **Gate:** User approves state management model

### Phase 4: Orchestrator Agent Design
**Status:** pending

- Design orchestrator LangGraph stateflow (ORIENT → Clarify → Assess → Gather → Synthesize → Gate)
- Design delegation logic (which variation, with what scope, with what files)
- Design symlink management (grant/revoke file access per task — orchestrator runs `ln -s`/`rm`)
- Design context injection per spawn (skills, context files, env rules)
- Design agent communication protocol (task dispatch, result collection)
- Integrate existing two-tier RAG (light at ORIENT, deep at GATHER)
- **Skills needed:** langgraph-fundamentals, multi-agent-orchestration
- **Gate:** User approves orchestrator design

### Phase 5: RAG Integration (Complete paused A3-A6)
**Status:** pending

- A3: Graph DB integration (Memgraph or DictGraphStore mock)
- A4: Bidirectional Qdrant↔Graph linkage
- A5: Session tracking / reingestion
- A6: Deep retrieval queries
- Fix known issues: 768-dim collections, Mem0 v3 filter API, PORT=8001
- **Skills needed:** langchain-rag, qdrant-vector-search
- **Gate:** User approves RAG completion plan

### Phase 6: Implementation — Container + State
**Status:** pending

- Write Flox env manifests per agent variation
- Write Dockerfile template (based on validated test-docker/ pattern)
- Write docker-compose.yml (project-vol + agent-vols + symlink bridge)
- Implement LangGraph state graphs per agent
- Wire LangGraph persistence
- **Skills needed:** langgraph-fundamentals, langgraph-persistence
- **Gate:** User approves Phase 6 before Phase 7

### Phase 7: Implementation — Orchestrator + RAG
**Status:** pending

- Implement orchestrator LangGraph stateflow
- Wire symlink management into orchestrator
- Integrate RAG into GATHER phase
- End-to-end test: user request → orchestrator → agent → file output
- **Gate:** User approves working end-to-end

### Phase 8: Polish & Docs
**Status:** pending

- Run existing test suite (96 unit tests, 3/8 integration)
- Fix known issues (collections, PORT, infer parameter)
- Update docs/context/ with new stack
- Handoff documentation

### Backlog
- Filesystem MCP (symlink bridge makes it unnecessary for bulk I/O)
- Researcher agent type
- Tester agent type

---

## Errors Encountered
| Error | Attempt | Resolution |
|-------|---------|------------|
| — | — | — |
