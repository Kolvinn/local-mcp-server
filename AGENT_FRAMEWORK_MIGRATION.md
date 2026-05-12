# Agent Framework Migration

The agentic bootstrap/controller system has been moved to a separate repository:

- **Repo:** `git@github.com/Kolvinn/agent_framework.git`
- **Location locally:** `~/agent_framework/`

## What Moved

All controller container code, agent runtime entrypoints, Docker/volume/compose orchestration, and bootstrap logic now live in the `agent_framework` repo. This includes:

- Controller CLI (`agentctl`) and MCP server
- Docker operations (volume creation, subpath init, compose generation)
- Agent container entrypoint (`agent_entrypoint.py`)
- Dual-network compose topology
- Token-based project registry
- Configuration schema and validation

## What Stays Here

This repo (`app/`) now contains only:

- **Memory Manager** (`src/memory/`) — GraphRAG ingestion pipeline
- **RAG Pipeline** (`src/rag/`) — Document processing and retrieval
- **Active MCP Servers** — Proxy server (port 8000), Memory service (port 8001)
- **Agent Prompts** (`.opencode/prompts/`) — OpenCode agent configurations
- **Project Infrastructure** — Dockerfile, docker-compose, test suite

## Cross-Reference

- Design history and research relevant to the controller have been migrated to `agent_framework/docs/{context,history,research,specs}/`
- A full content manifest is at `agent_framework/docs/content_manifest.md`
- `src/agent_framework/` has been deleted from this repo — use `~/agent_framework/` instead
