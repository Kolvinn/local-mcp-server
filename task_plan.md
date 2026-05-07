# Task Plan — Agentic Container Overhaul

## Goal
Overhaul local Docker setup from a single OpenCode MCP server into a **LangGraph-based multi-container agent system** powered by **Flox environments**. Each agent type is a modifiable template with its own stateflow, learnings, and file access via MCP protocol. Orchestrator routes work; agents don't talk to each other.

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

---

## Phases

### Phase 1: Architecture Design — Container & Environment
**Status:** pending

- Design Flox environment per agent type (implementer, explorer)
- Define container-per-agent model: one Dockerfile template, parameterized by agent type + injected context
- Plan Docker Compose layout (orchestrator + N agents on `internal-net`)
- Define context injection mechanism (env vars, mounted files, startup args)
- Define file access boundaries per agent (which projects, which directories)
- **Gate:** User approves architecture diagram + container model

### Phase 2: LangGraph State Management
**Status:** pending

- Design per-agent StateGraph (state schema, nodes, edges, conditional routing)
- Design LangGraph persistence (checkpointer) per agent for "learnings" retention
- Design approval gate integration (human-in-the-loop interrupts)
- Design orchestrator state: tracks agent assignments, phase transitions, session context
- **Skills needed:** langgraph-fundamentals, langgraph-persistence, langgraph-human-in-the-loop
- **Gate:** User approves state management model

### Phase 3: MCP File Access Protocol
**Status:** pending

- Define MCP file access server contract (tools: read_file, write_file, list_directory, search_files)
- Define per-agent permission boundaries
- Design how orchestrator grants/revokes file access per task
- Integrate with existing FastMCP patterns in codebase
- **Gate:** User approves MCP contract

### Phase 4: Orchestrator Agent Design
**Status:** pending

- Design orchestrator stateflow (ORIENT → Clarify → Assess → Gather → Synthesize → Gate)
- Design delegation logic (which agent, with what scope, with what files)
- Design context injection per spawn (environment, import rules, workdir, output format)
- Integrate existing two-tier RAG (light at ORIENT, deep at GATHER)
- **Skills needed:** multi-agent-orchestration
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

### Phase 6: Implementation — Phase 1+2 (Container + State)
**Status:** pending

- Write Flox env manifests per agent
- Write Dockerfile template
- Write docker-compose.yml with orchestrator + agent containers
- Implement LangGraph state graphs per agent
- Wire LangGraph persistence
- **Skills needed:** langgraph-fundamentals, langgraph-persistence
- **Gate:** User approves Phase 6 before Phase 7

### Phase 7: Implementation — Phase 3+4 (MCP + Orchestrator)
**Status:** pending

- Implement MCP file access server
- Implement orchestrator LangGraph
- Wire file access per agent task
- End-to-end test: user request → orchestrator → agent → file output → orchestrator summary
- **Gate:** User approves working end-to-end

### Phase 8: Polish & Docs
**Status:** pending

- Run existing test suite (96 unit tests, 3/8 integration)
- Fix known issues (collections, PORT, infer parameter)
- Update docs/context/ with new stack
- Handoff documentation

---

## Errors Encountered
| Error | Attempt | Resolution |
|-------|---------|------------|
| — | — | — |
