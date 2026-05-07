# Findings — Agentic Container Overhaul

## Current System State (from explorer research)

### Working
- FastMCP server with 5 memory tools (add/search/delete/sync/list) on port 8000
- Agent team v2 designed — 5 agents with pseudocode handoff, 4-gate approval pipeline
- mcp-mem0-update fully complete (goal tree migration, 96 unit tests passing)
- RAG pipeline A1+A2 complete (Pydantic models, edge contract 40 triples/10 node types, chunker, embedder, Qdrant client — 82 tests pass)

### Diagrams Model (from docs/diagrams/)
- Orchestrator flow: ORIENT → Clarify → Assess → Gather → Synthesize → Gate
- Two-tier RAG: light at ORIENT, deep (GraphRAG+Qdrant) at GATHER
- 4-gate user approval pipeline with rework paths returning to ORIENT
- Memory Manager companion: Goal Graph, Phase Tracker, Context Index, Session State
- Anti-pattern guard nodes: over-delegating, going deep too early, gate-skipping

### Known Issues
- Qdrant collections stale (1536-dim), need recreation at 768-dim
- Mem0 v3 API: `user_id` must be inside `filters` dict
- PORT=8001 still in `.env` causing 3 test failures
- Integration tests: 3/8 pass, 5 fail
- RAG paused at A3 (Graph DB integration — zero code, spec written)
- `infer` parameter not yet implemented

### Previous Design Decisions (ADRs)
- ADR-006: Single user, no auth
- ADR-007: In-process Mem0 import with external Qdrant/Ollama
- ADR-019: v0 is single-file MCP server with 5 tools, forward-compatible metadata
- ADR-023: Agent team v2 uses 5 agents with pseudocode handoff, file-based transparency, 4 approval gates
- Hexagonal architecture pattern (domain core never imports mem0ai/file I/O directly)
- Relative imports within packages, `src/` is NOT a Python package

### User's Overhaul Vision
- LangGraph for per-agent state management (not LangChain chains)
- Flox per container for hermetic, reproducible environments
- Each agent = template that adapts to injected context (e.g., Python vs Java implementer)
- Agents don't communicate directly — they write files or return summaries to orchestrator
- File-based handoffs, orchestrator routes context/files
- User handles global infrastructure, agents access core projects user switches between
- MVP: Implementer + Explorer only

### Installed Skills Available
- LangChain/Graph: `langchain-fundamentals`, `langchain-architecture`, `langgraph-fundamentals`, `langgraph-persistence`, `langgraph-human-in-the-loop`, `langchain-rag`, `langchain-dependencies`, `langchain-middleware`
- Deep Agents: `deep-agents-core`, `deep-agents-orchestration`, `deep-agents-memory`
- Multi-agent: `multi-agent-orchestration`, `planning-with-files`, `project-memory`
- Qdrant: `qdrant-vector-search`, `qdrant-search-quality`
- Python: `python-patterns`, `async-python-patterns`, `python-expert`, `pydantic`

### Validated: Orchestrator as Symlink Bridge (test-docker/)
**Test setup:** Three containers (init, orch, agent) + two Docker volumes (test-vol, agent-vol)
- Orch mounts both volumes, symlinks files from shared → agent volume
- Agent writes follow symlink back to shared volume
- Init confirms changes land in source of truth
- **Proven:** Zero-copy, zero-host-access, dynamic grants via `ln -s`/`rm`, no container restarts

### Open Questions (from session-summary.md)
- Complexity thresholds for deepening
- Memory Manager implementation (agent vs MCP vs service)
- Context buffer limits per agent
- Deepening granularity
- Specialist spawn heuristics
- Light vs deep RAG scope boundaries
- Goal registration context inheritance

### Agent Prompt Design Philosophy (Session Continuation)
- **Mechanics, not domain**: Agent prompts define interaction patterns. Domain expertise comes from skills loaded at runtime and files pointed to.
- **User is Governor**: Universal principle injected into every agent prompt. Permissions bubble up, never assumed.
- **Context Economy**: All agents mandate conciseness, file-pointing, context saving.
- **Learnings Recording**: All agents record to `docs/learnings/` after work.
- **Language-agnostic**: No Python/java assumptions baked into prompts.
- Target: ~60 lines per prompt, stripped of domain examples and skill catalogs.

### Agent Roster (Updated)
- **Removed**: Coordinator (legacy duplicate), Reviewer (replaced by Auditor)
- **Added**: Auditor — 5-check framework (spec compliance, best practices, system integration, adversarial testing, report)
- **Active**: Orchestrator, System Thinker, Implementer, Auditor, Explorer, RAG Architect

### Phase 1 Design (Proposed, Not Yet Approved)
- Flox baked into agent Docker image, `flox install` using project toml manifest
- 3 Docker volumes: `project-vol` (external), `agent-impl-vol`, `agent-expl-vol`
- Explorer gets read-only mount for enforcement
- Context injection via JSON config file written by orchestrator
