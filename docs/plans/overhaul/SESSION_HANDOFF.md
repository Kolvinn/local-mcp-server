# Session Handoff — Session 005

**Date:** 2026-05-12
**Handoff to:** Next agent or human continuation
**Primary context files:** `docs/plans/overhaul/MASTER_STATUS.md` + this file

---

## 1. What Happened This Session

### Bootstrap system fully specified (6 files)
Converted the bash `bootstrap_project.sh` into a Python bootstrap system. No code written — comprehensive pseudocode spec only.

- **`docs/specs/bootstrap-system-01-overview.md`** — Architecture, lifecycle, data flow
- **`docs/specs/bootstrap-system-02-schema.md`** — `agent-project.yaml` schema, validation rules, type registry, manifest generation
- **`docs/specs/bootstrap-system-03-bootstrap.md`** — `bootstrap.py` CLI (validate/bootstrap/teardown), Docker SDK usage, volume/subdir/seed/compose logic
- **`docs/specs/bootstrap-system-04-entrypoint.md`** — Container entrypoint: manifest→graph→MCP tools→`create_deep_agent()`→ACP
- **`docs/specs/bootstrap-system-05-skills.md`** — Symlink model, SKILL.md validation, MCP proxy vs router two-phase model
- **`docs/specs/bootstrap-system-00-pre-read.md`** — Implementer guide: which skills/context to load per spec part

### Framework injection chain confirmed
Loaded 7 skills and 4 LangChain doc pages to confirm exactly how tools, MCP, skills, permissions, and persistence are wired:

| Concern | Mechanism | API |
|---------|-----------|-----|
| **Tools** | `create_deep_agent(tools=[...])` | `@tool` functions + MCP-loaded tools merged |
| **MCP** | `MultiServerMCPClient(server_config).get_tools()` | `langchain-mcp-adapters`, supports http+stdio transports |
| **Skills** | `create_deep_agent(skills=[...])` + `FilesystemBackend` | Deep Agents `SkillsMiddleware`, SKILL.md progressive disclosure |
| **Permissions** | `create_deep_agent(interrupt_on={...})` | `HumanInTheLoopMiddleware`, requires `checkpointer`+`thread_id` |
| **Persistence** | `checkpointer=MemorySaver()`, `store=InMemoryStore()` | MVP; PostgresSaver/PostgresStore for production |
| **ACP** | `AgentServerACP(agent)` + `run_agent(server)` | `deepagents-acp` package, stdio mode (container transport TBD) |

### Key design decisions for the bootstrap system
- **manifest.json as intermediate artifact** — bootstrap writes JSON, entrypoint reads JSON. Decouples host (Docker SDK, YAML) from container (minimal deps).
- **Skills symlinked at bootstrap time** — relative symlinks resolve correctly when both volumes mounted in container.
- **MCP MVP: direct URLs; governance proxy later** — manifest URLs change from `http://qdrant:6333` to `http://governance:8000/mcp/proxy/qdrant` when governance is built. No entrypoint code change.
- **Flat agent map config** (not type registry + instances) — simpler for MVP. No variations built yet.
- **`interrupt_on` included from start** — simple dict passthrough, avoids config migration.

---

## 2. Key Decisions

| Decision | Rationale |
|----------|-----------|
| `docker-py` SDK (not CLI subprocess) | Python-native, no shell parsing. User directed. |
| `agent-project.yaml` config-driven | Single source of truth. No hardcoded agent lists. |
| `manifest.json` decouples bootstrap from runtime | Bootstrap writes JSON (host, YAML, Docker SDK); entrypoint reads JSON (container, `json.loads` only). |
| Graph module contract: `get_graph() -> CompiledStateGraph` | Consistent interface. Optional `get_tools() -> list` for custom tools. |
| MCP endpoints as URLs in manifest | Transport-agnostic. Same manifest field works for direct and proxied connections. |
| ACP container transport deferred | `deepagents-acp` only shows stdio. Need to investigate HTTP/SSE or Docker exec bridging. |

---

## 3. Files Created/Modified This Session

| File | Action |
|------|--------|
| `docs/specs/bootstrap-system-00-pre-read.md` | Created — implementer guide |
| `docs/specs/bootstrap-system-01-overview.md` | Created — architecture overview |
| `docs/specs/bootstrap-system-02-schema.md` | Created — agent-project.yaml schema |
| `docs/specs/bootstrap-system-03-bootstrap.md` | Created — bootstrap CLI spec |
| `docs/specs/bootstrap-system-04-entrypoint.md` | Created — container entrypoint spec |
| `docs/specs/bootstrap-system-05-skills.md` | Created — skills & MCP spec |
| `docs/learnings/bootstrap/2026-05-12-spec.md` | Created — session learnings |
| `docs/plans/overhaul/MASTER_STATUS.md` | Updated — component status, reference map, unknowns |
| `docs/plans/overhaul/SESSION_HANDOFF.md` | This file — rewrites Session 004 handoff |

Skills loaded this session (7): `langchain-fundamentals`, `langgraph-fundamentals`, `deep-agents-core`, `deep-agents-orchestration`, `deep-agents-memory`, `langchain-middleware`, `langgraph-persistence`, `agent-pseudocode`, `create-specification`

LangChain docs fetched (via Explorer): MCP (`langchain-mcp-adapters`), ACP (`deepagents-acp`), Deep Agents customization page (full `create_deep_agent` parameter list)

---

## 4. Component Status Summary

| Component | Status |
|-----------|--------|
| Bootstrap System | Spec-only. 6-file pseudocode spec ready for implementation. |
| Memory Manager (`src/memory/`) | Built, not tested, no endpoint (needs ACP wrapper) |
| RAG Pipeline A1+A2 | Built, functional, 82 tests pass |
| Governance MCP Container | Spec only |
| Agent Container Template | Spec only |
| Orchestrator Container | Spec only |
| ACP Protocol | Confirmed: `deepagents-acp` + `acp` package. Container transport TBD. |

---

## 5. Current Phase

- Phase 0: Planning — ✅
- Phase 1: Agent Design — ✅
- Phase 2: Container & Volume Topology — ✅
- **Phase 2.5: Bootstrap System Spec — ✅ (this session)**
- **Phase 3: LangGraph State Management — pending**
- Phase 4-8: pending

---

## 6. Exact Next Steps (in order)

1. **Implement bootstrap system** — `bootstrap.py` CLI + config validation (specs 02+03). Load `docker-py`, `pydantic`, `PyYAML`. Test with real Docker.
2. **Design agent Dockerfile template** — single image for all agent types. Flox for system tools, uv for Python packages. PATH bypass.
3. **Implement container entrypoint** — `entrypoint.py` (spec 04). Load deep-agents, langgraph, langchain-mcp-adapters skills. Wire manifest→agent→ACP.
4. **Design governance MCP server spec** — FastMCP + Docker SDK. Tools: `provision_agent`, `destroy_agent`, `list_agents`, `modify_agent_capability`.
5. **Test end-to-end** — bootstrap → compose up → agent starts → ACP server running.
6. **Backlog**: symlink bridge, multi-project templates, agent variations, GraphRAG, ACP container transport.

---

## 7. Rules the Next Agent Must Follow

1. **No autonomous decisions** — pause and ask user before acting
2. **User is most efficient data source** — ask before delegating to Explorer, loading skills, writing files
3. **Wide and tentative** — surface options/trade-offs, don't commit without user gate
4. **Don't assume intent** — ambiguity → query user directly
5. **Don't over-summarize** what user tells you — waste of tokens
6. **Goal refinement only** unless ordered to design/build
7. **No host access** — agents never access host filesystem, only Docker volumes
8. **User is Governor** — permissions bubble up, never assumed downward
9. **Context Economy** — be concise, point to files
10. **Learnings Recording** — after completing work, record to `docs/learnings/{domain}/{session}.md`

---

## 8. What to Read First

1. **`docs/plans/overhaul/MASTER_STATUS.md`** — definitive context
2. **This file** — what happened, what's next
3. **`docs/specs/bootstrap-system-00-pre-read.md`** — which skills/context to load per task
4. **`docs/specs/bootstrap-system-01-overview.md`** — architecture
5. **`docs/specs/bootstrap-system-02-schema.md`** — config schema (if writing validation)
6. **`docs/specs/bootstrap-system-03-bootstrap.md`** — CLI spec (if writing bootstrap.py)
7. **`docs/specs/bootstrap-system-04-entrypoint.md`** — entrypoint spec (if writing entrypoint.py)
8. **`docs/specs/bootstrap-system-05-skills.md`** — skills & MCP model
9. **`docs/learnings/bootstrap/2026-05-12-spec.md`** — session learnings (assumptions, uncertainties)
