# Constraints & Boundaries

## Hard Limits
- VRAM: 10GB total (RTX 3080)
- RAM: 32GB total
- Keep agent context windows lean — use file-based handoffs
- No background jobs or scheduled tasks

## Do NOT
- No npx (use bunx)
- No Node.js runtime (bun available if needed)
- No auth, no multi-tenancy — single user only
- No hardcoded secrets or credentials
- No hardcoded user_id — use AGENT_ID env var
- No hardcoded port 8001 — target is 8000
- No reliance on src/index.ts — dead code
- No exceeding 10GB VRAM — monitor model loading
- No embedding model heavier than nomic-embed-text (~274MB)

## Security
- All inputs validated before processing
- Environment variables for all configuration
- No command injection vectors
- No eval() or exec() on user/agent input
- Read-only agents: explorer (always), auditor (code review only, no edits to source)

## Compatibility
- Python 3.14+
- Docker on internal-net
- Qdrant available at QDRANT_HOST:QDRANT_PORT
- Ollama available at OLLAMA_URL
- Framework base image must be available
