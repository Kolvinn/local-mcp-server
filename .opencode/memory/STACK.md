# Tech Stack & Constraints

---

## Runtime Stack

| Layer | Technology | Version | Notes |
|-------|-----------|---------|-------|
| Language | Python | 3.14+ | Primary runtime |
| Language | TypeScript/Bun | latest | Placeholder only — `src/index.ts` is dead code |
| MCP Framework | FastMCP | 3.2.4+ | Composite orchestrator with proxy mounting via `create_proxy()` |
| Web Framework | FastAPI | 0.136+ | Dependency present, not yet used |
| ASGI Server | Uvicorn | 0.44+ | Serves the MCP app |
| HTTP Client | httpx | 0.28+ | For downstream service calls |
| Memory SDK | mem0ai | latest | In pyproject.toml, no code integration yet |
| Env Vars | python-dotenv | 1.2+ | Dependency present, no `.env` file yet |
| Package Mgr | uv | latest | Python dependency management (installed via conda) |
| JS Runtime | Bun | latest | Available via conda, unused for core logic |
| Container | Docker | — | `FROM framework-base:latest` (custom conda-based image) |
| Orchestration | Docker Compose | — | Single compose file at project root |
| Reverse Proxy | Traefik | — | Labels-based routing, `internal-net` |

## Infrastructure

| Component | Detail |
|-----------|--------|
| Base image | `framework-base:latest` — custom, conda-based. Not on Docker Hub. |
| Container mount | `/home/dev/app` → volume `mcp-server` |
| Network | `internal-net` (external Docker network, shared by all containers) |
| Serving port | **8000** — the container's purpose is to serve MCP on port 8000 |
| Traefik label port | 6274 — vestigial, was for MCP Inspector UI on host. No longer used. |
| Docker expose | 8001 — in compose, misaligned with serving port 8000 |
| User | `dev:1000:1000` |
| Access model | Single user only. No auth, no public exposure. User connects directly. |
| Agent context | **OpenCode** (previously Roo Code — user_id "roo_agent" in src/main.py is stale) |

## External Infrastructure (User-Managed)

| Component | Detail |
|-----------|--------|
| Qdrant | Vector store. User ensures it's running and accessible at `QDRANT_HOST`:`QDRANT_PORT`. Not in this repo's compose. |
| Ollama | LLM + embeddings. User ensures it's running at `OLLAMA_URL`. Embedding model: `bge-m3` (configurable via `EMBEDDING_MODEL`). Not in this repo's compose. |

## Do-Nots

- **Do NOT** use Node.js/npx — this environment uses conda + bun. Use `bunx` instead of `npx`.
- **Do NOT** rely on `src/index.ts` — it's `console.log("Hello via Bun!")` dead code.
- **Do NOT** hardcode secrets — use `.env` files (gitignored).
- **Do NOT** exceed 10GB VRAM / 32GB RAM — this runs on RTX 3080.
- **Do NOT** add auth/multi-tenancy — single user access model only.
- **Do NOT** worry about healthchecks — not a priority right now.
- **Do NOT** worry about Traefik port 6274 label — vestigial, was for inspector, no longer used.
- **Do NOT** use "roo_agent" as user_id — stale, from Roo Code era.

## Port Reference

| Service | Internal Port | Traefik Route | Notes |
|---------|---------------|---------------|-------|
| mcp-server | **8000** (target serving port) | `mcp-server.local.net` (via port 6274 label, vestigial) | User connects directly to 8000 |
| mcp-memory-service | 8000 | N/A | Referenced in root main.py but no container provides it yet — broken reference |
| Inspector (defunct) | 6274 | Was connecting to host | No longer used, label is vestigial |
| Qdrant | 6333 | N/A | User-managed, external to this repo |
| Ollama | 11434 | N/A | User-managed, external to this repo |

## Locked Versions

(None yet — no pins beyond what pyproject.toml specifies.)

---

Last updated: 2026-04-23