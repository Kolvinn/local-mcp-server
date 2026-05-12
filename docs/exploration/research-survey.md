# Research & Exploration Survey

**Generated:** 2026-05-12
**Source:** `/home/dev/app/docs/exploration/` (15 files)
**Cross-reference:** `/home/dev/agent_framework/docs/research/`

---

## Summary Table

| File | Category | Already in agent_framework? | Action |
|------|----------|---------------------------|--------|
| `flox-per-project-research.md` | CONTAINER_RELEVANT | YES (`flox-in-containers.md`) | KEEP (or DELETE if no longer referenced from current app) |
| `docker-compose-portability-research.md` | CONTAINER_RELEVANT | YES (`compose-portability.md`) | KEEP |
| `docker-subpath-research.md` | CONTAINER_RELEVANT | YES (`docker-subpaths.md`) | KEEP |
| `langsmith-trace-granularity.md` | APP_INFRA | NO | KEEP |
| `litellm-config-reference.md` | APP_INFRA | NO | KEEP |
| `litellm-docker-compose.md` | APP_INFRA | NO | KEEP |
| `litellm-ollama.md` | APP_INFRA | NO | KEEP |
| `litellm-proxy.md` | APP_INFRA | NO | KEEP |
| `langchain-dependencies.md` | ACTIVE_RESEARCH | YES (`langchain-dependencies.md`) | KEEP |
| `langgraph-fundamentals.md` | ACTIVE_RESEARCH | YES (`langgraph-fundamentals.md`) | KEEP |
| `deep-agents-core.md` | ACTIVE_RESEARCH | YES (`deep-agents-core.md`) | KEEP |
| `deep-agents-orchestration.md` | ACTIVE_RESEARCH | YES (`deep-agents-orchestration.md`) | KEEP |
| `flox-docker-research.md` | CONTAINER_RELEVANT | YES (`flox-docker.md`) | KEEP |
| `plans-summary.md` | SCRATCH | NO | KEEP (short reference doc) |
| `diagrams-summary.md` | SCRATCH | YES (`diagrams-exploration.md`) | KEEP |

---

## Detailed Findings

### flox-per-project-research.md
- **Content:** Deep research into Flox per-project environment patterns — how `flox activate --dir` works with mounted volumes, symlink forests, three viable patterns for Docker + Flox, and per-project environment configs.
- **Accuracy:** Still accurate. Dated 2026-05-12, sources from flox.dev docs and GitHub.
- **Already in agent_framework?** YES — as `flox-in-containers.md` (22,749 bytes, same content).
- **Recommendation:** KEEP in place. Both copies exist. If the current app no longer references this directory, consider marking for cleanup. Content is still valid.

### docker-compose-portability-research.md
- **Content:** Comprehensive research on Docker Compose portable multi-instance patterns — project name isolation (`--project-name`), external volume naming, environment file patterns, network isolation, and compose file templating.
- **Accuracy:** Still accurate. Dated 2026-05-12, sourced from official Docker Compose docs.
- **Already in agent_framework?** YES — as `compose-portability.md` (21,601 bytes, same content).
- **Recommendation:** KEEP. Both copies valid. Content is foundational for Docker orchestration patterns.

### docker-subpath-research.md
- **Content:** Research on Docker named volume subpath support — compatibility with `external: true` volumes, long-syntax vs short-syntax, driver-specific behavior, and workarounds for legacy Docker versions.
- **Accuracy:** Still accurate. Dated 2026-05-12, sourced from official Docker docs.
- **Already in agent_framework?** YES — as `docker-subpaths.md` (11,323 bytes, same content).
- **Recommendation:** KEEP. Both copies valid.

### langsmith-trace-granularity.md
- **Content:** Deep dive into LangSmith trace data model — all captured fields (IDs, timing, payloads, metadata, token usage), agent decision tree reconstruction, feedback/annotation API, run filtering/querying, and assessment of LangSmith as a decision log.
- **Accuracy:** Still accurate. Dated 2026-05-09. LangSmith schema is stable and unlikely to have changed.
- **Already in agent_framework?** NO.
- **Recommendation:** KEEP. Valuable reference for tracing/debugging. Consider copying to agent_framework if the framework uses LangSmith.

### litellm-config-reference.md
- **Content:** Complete `config.yaml` reference for LiteLLM Proxy — all top-level sections (`model_list`, `router_settings`, `litellm_settings`, `general_settings`, `environment_variables`), provider prefixes, load balancing, retry policies, caching, secrets management, and complete working examples.
- **Accuracy:** Still accurate. Dated 2026-05-08. LiteLLM config format is stable.
- **Already in agent_framework?** NO.
- **Recommendation:** KEEP. Comprehensive reference. Consider copying to agent_framework.

### litellm-docker-compose.md
- **Content:** Complete Docker Compose setup for LiteLLM Proxy — Docker Compose YAML with PostgreSQL, Prometheus, Ollama host networking via `host.docker.internal`, health checks, `.env` file template, startup sequence diagram, and quick-start commands.
- **Accuracy:** Still accurate. Dated 2026-05-08. Uses standard Docker Compose patterns.
- **Already in agent_framework?** NO.
- **Recommendation:** KEEP. Both APP_INFRA and CONTAINER_RELEVANT. Consider copying to agent_framework.

### litellm-ollama.md
- **Content:** LiteLLM + Ollama integration details — model name formats (`ollama/` vs `ollama_chat/`), `api_base` configuration (host vs Docker), `keep_alive` parameter, function/tool calling support, streaming options, multi-model config, and common error fixes.
- **Accuracy:** Still accurate. Dated 2026-05-08. Integration patterns are stable.
- **Already in agent_framework?** NO.
- **Recommendation:** KEEP. Practical troubleshooting content. Consider copying to agent_framework.

### litellm-proxy.md
- **Content:** Overview of LiteLLM Proxy capabilities — OpenAI-compatible unified API, retry/fallback/circuit-breaker logic, multi-model routing strategies, streaming normalization, embeddings support, and an assessment of LiteLLM as a routing layer.
- **Accuracy:** Still accurate. Dated 2026-05-08.
- **Already in agent_framework?** NO.
- **Recommendation:** KEEP. Strategic overview of why LiteLLM was chosen. Consider copying to agent_framework.

### langchain-dependencies.md
- **Content:** LangChain ecosystem dependency research — required packages with minimum versions, `ChatOpenAI` vs `ChatOllama` comparison, compatibility issues, and minimal `requirements.txt` for LangChain + Ollama.
- **Accuracy:** **Mostly accurate. Minor caveat:** Mentions `create_react_agent` being deprecated in favor of `create_agent` (LangGraph v1 change) — this is noted correctly. Version ranges (`langchain>=1.0,<2.0`, `langgraph>=1.0,<2.0`) are current as of 2026-05. Recommends `deepagents` (latest) — accurate.
- **Already in agent_framework?** YES — as `langchain-dependencies.md` (5,804 bytes).
- **Recommendation:** KEEP. Still valid. No action needed.

### langgraph-fundamentals.md
- **Content:** LangGraph fundamentals — StateGraph basics with `MessagesState`, ReAct agent construction (manual StateGraph API vs Functional API), streaming modes with v2 format, `MemorySaver` checkpointing, and interrupt/HITL patterns.
- **Accuracy:** **Mostly accurate.** Mentions `create_react_agent` as deprecated in favor of `create_agent` — this is correct per LangGraph v1 migration. All code examples (interrupt(), Command(resume=...), MemorySaver, v2 streaming envelope) are current.
- **Already in agent_framework?** YES — as `langgraph-fundamentals.md` (9,280 bytes).
- **Recommendation:** KEEP. Still valid. No action needed.

### deep-agents-core.md
- **Content:** Deep Agents core research — minimal setup with `create_deep_agent()`, harness architecture (middleware stack, LangGraph compilation), key configuration options for local Ollama models, source files discovered, and dependency requirements.
- **Accuracy:** Still accurate. Dated 2026-05-08. Recommends `deepagents >= 0.3.5` — current. All patterns (model strings, custom tools, system prompt composition) are current.
- **Already in agent_framework?** YES — as `deep-agents-core.md` (4,609 bytes).
- **Recommendation:** KEEP. Still valid. No action needed.

### deep-agents-orchestration.md
- **Content:** Deep Agents orchestration layers — SubAgentMiddleware (multi-agent coordination), CLI connection patterns (deepagents dev, --skill, stdin piping), TUI integration (streaming with subgraph namespaces), and HITL interrupt patterns (approve/edit/reject).
- **Accuracy:** Still accurate. Dated 2026-05-08. CLI commands and HITL patterns are current.
- **Already in agent_framework?** YES — as `deep-agents-orchestration.md` (5,313 bytes).
- **Recommendation:** KEEP. Still valid. No action needed.

### flox-docker-research.md
- **Content:** Flox for Docker container integration research — Flox overview (manifest.toml, `flox containerize`, OCI output), installation methods in Docker, patterns for using Flox environments inside containers, and the three-architecture recommendation.
- **Accuracy:** Still accurate. Dated 2026-05-08. Sources from flox.dev docs and GitHub.
- **Already in agent_framework?** YES — as `flox-docker.md` (19,995 bytes).
- **Recommendation:** KEEP. Foundation for the container+CAPS architecture. Content valid.

### plans-summary.md
- **Content:** Condensed summary of the `docs/plans/` directory — base/ (Mem0 MCP Server), agent-team/ (5-agent architecture), mcp-mem0-update/ (goal tree migration), and product_owner/ (strategic agent). Lists architectural decisions and status of each plan.
- **Accuracy:** Snapshot of planning documents at time of writing (2026-05-12). Content is a summary, not research.
- **Already in agent_framework?** NO.
- **Recommendation:** KEEP. Useful reference index into the plans directory. Not research per se but helpful navigation.

### diagrams-summary.md
- **Content:** Summary of 7 `.mmd` files and 1 session-summary.md — models a multi-agent orchestrator architecture with phases (ORIENT, Clarify, Assess, Gather, Synthesize, Gate), two-tier RAG, Memory Manager companion subgraph, 4-gate approval pipeline, and anti-pattern guard nodes.
- **Accuracy:** Snapshot of diagram content at time of writing. Not research — it's a summary.
- **Already in agent_framework?** YES — as `diagrams-exploration.md` (2,241 bytes).
- **Recommendation:** KEEP. Useful reference for architecture diagrams.

---

## Notes

- **All ACTIVE_RESEARCH files are still current.** No file contains references to deprecated APIs or outdated version constraints that would need action.
- **8 of 15 files** have been copied to `/home/dev/agent_framework/docs/research/`.
- **7 files are NOT in agent_framework:** `langsmith-trace-granularity.md`, `litellm-config-reference.md`, `litellm-docker-compose.md`, `litellm-ollama.md`, `litellm-proxy.md`, `plans-summary.md`.
- The 4 LiteLLM files and 1 LangSmith file form a natural **APP_INFRA** group that may be worth copying to agent_framework if that framework also needs LLM infrastructure research.
- No files reference container/Flox research that hasn't already been copied to agent_framework.
- **No files are candidates for deletion** — all contain either active research or useful summaries of other documents.

## Cross-Reference: agent_framework Matches

| agent_framework file | Source exploration file |
|---|---|
| `compose-portability.md` | `docker-compose-portability-research.md` |
| `deep-agents-core.md` | `deep-agents-core.md` |
| `deep-agents-orchestration.md` | `deep-agents-orchestration.md` |
| `diagrams-exploration.md` | `diagrams-summary.md` |
| `docker-subpaths.md` | `docker-subpath-research.md` |
| `flox-docker.md` | `flox-docker-research.md` |
| `flox-in-containers.md` | `flox-per-project-research.md` |
| `langchain-dependencies.md` | `langchain-dependencies.md` |
| `langgraph-fundamentals.md` | `langgraph-fundamentals.md` |

All agent_framework copies appear to be exact or near-exact duplicates (same content, same dates).
