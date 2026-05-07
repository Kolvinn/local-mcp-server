# Task Plan — Agentic Container Overhaul

## Goal
Overhaul local Docker setup from a single OpenCode MCP server into a **LangGraph-based multi-container agent system** powered by **Flox environments**. Each agent type is a modifiable template with its own stateflow, learnings, and filesystem isolation via the orchestrator acting as a symlink bridge between shared and agent-specific Docker volumes.

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

## MVP Agent Roster
- **Implementer** — spec-driven code translator
- **Explorer** — read-only codebase scout
- **Backlog**: Expert, Architect, Researcher, Reviewer, System Thinker

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

### Phase 1: Architecture Design — Volume Model & Containers
**Status:** pending

**Validated foundation** (see test-docker/): orchestrator as symlink bridge
- Design volume topology: `project-vol` (shared) + per-agent `agent-vol`s
- Design orchestrator symlink management (grant/revoke file access per task)
- Define Docker Compose layout (orchestrator + N agents on `internal-net`)
- Define Flox environment per agent type (implementer, explorer)
- Define container-per-agent model: one Dockerfile template, parameterized by agent type
- Define context injection mechanism (env vars, startup args, agent config)
- **Gate:** User approves volume topology + container model

### Phase 2: LangGraph State Management
**Status:** pending

- Design per-agent StateGraph (state schema, nodes, edges, conditional routing)
- Design LangGraph persistence (checkpointer) per agent for "learnings" retention
- Design approval gate integration (human-in-the-loop interrupts)
- Design orchestrator state: tracks agent assignments, phase transitions, session context
- **Skills needed:** langgraph-fundamentals, langgraph-persistence, langgraph-human-in-the-loop
- **Gate:** User approves state management model

### Phase 3: Orchestrator Agent Design
**Status:** pending

- Design orchestrator LangGraph stateflow (ORIENT → Clarify → Assess → Gather → Synthesize → Gate)
- Design delegation logic (which agent, with what scope, with what files)
- Design symlink management (grant/revoke file access per task — orchestrator runs `ln -s`/`rm`)
- Design context injection per spawn (environment, import rules, workdir, output format)
- Design agent communication protocol (task dispatch, result collection, heartbeat)
- Integrate existing two-tier RAG (light at ORIENT, deep at GATHER)
- **Skills needed:** langgraph-fundamentals, multi-agent-orchestration
- **Gate:** User approves orchestrator design

### Phase 4: RAG Integration (Complete paused A3-A6)
**Status:** pending

- A3: Graph DB integration (Memgraph or DictGraphStore mock)
- A4: Bidirectional Qdrant↔Graph linkage
- A5: Session tracking / reingestion
- A6: Deep retrieval queries
- Fix known issues: 768-dim collections, Mem0 v3 filter API, PORT=8001
- **Skills needed:** langchain-rag, qdrant-vector-search
- **Gate:** User approves RAG completion plan

### Phase 5: Implementation — Container + State
**Status:** pending

- Write Flox env manifests per agent
- Write Dockerfile template (based on validated test-docker/ pattern)
- Write docker-compose.yml (project-vol + agent-vols + symlink bridge)
- Implement LangGraph state graphs per agent
- Wire LangGraph persistence
- **Skills needed:** langgraph-fundamentals, langgraph-persistence
- **Gate:** User approves Phase 5 before Phase 6

### Phase 6: Implementation — Orchestrator + RAG
**Status:** pending

- Implement orchestrator LangGraph stateflow
- Wire symlink management into orchestrator
- Integrate RAG into GATHER phase
- End-to-end test: user request → orchestrator → agent → file output
- **Gate:** User approves working end-to-end

### Phase 7: Polish & Docs
**Status:** pending

- Run existing test suite (96 unit tests, 3/8 integration)
- Fix known issues (collections, PORT, infer parameter)
- Update docs/context/ with new stack
- Handoff documentation

### Backlog
- Filesystem MCP (symlink bridge makes it unnecessary)
- Expert, Architect, Researcher agents
- Reviewer agent

---

## Errors Encountered
| Error | Attempt | Resolution |
|-------|---------|------------|
| — | — | — |
