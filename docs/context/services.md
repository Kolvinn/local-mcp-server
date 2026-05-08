# Available Services

## MCP Memory Service
- Endpoint: http://localhost:8000/mcp (streamable-http)
- Tools available:
  - `add_memory(text, tags, infer)` — store a memory
  - `search_memory(query, limit)` — semantic search
  - `delete_memory(memory_id)` — remove a memory
  - `sync_metadata(project_id)` — sync local metadata
  - `list_projects()` — list known projects
- `infer` parameter: True = server-side LLM extraction (uses llama3.1:8b, ~6-8GB VRAM), False = embedding only

## External Infrastructure
- Qdrant: QDRANT_HOST:6333 (vector database)
- Ollama: OLLAMA_URL:11434 (embeddings + LLM)

## Agent Framework
- **Core 5 types** (config-driven variations — see `docs/plans/overhaul/agent-variation-matrix.md`)
- Orchestrator (primary, glm-5.1) — sole user contact, delegation, approval gates
- System Thinker (subagent, qwen-3.6-plus) — domain design, briefs, specs. Variations: strategic_thinker, rag_thinker, architect_thinker
- Implementer (subagent, deepseek-v4-flash) — code translation from specs. Variations: python_implementer, infra_implementer
- Auditor (subagent, deepseek-v4-pro) — 5-check verification. Variation: code_auditor
- Explorer (subagent, deepseek-v4-flash) — read-only codebase scout. Variations: codebase_explorer, dependency_explorer
- **Retired types**: Reviewer (→ Auditor), Coordinator (→ redundant), RAG Architect (→ rag_thinker variation)
- **Backlog types**: Researcher, Tester
