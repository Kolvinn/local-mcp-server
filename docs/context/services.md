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

## Agent Services
- System Thinker: spawnable template for domain design
- Implementer: code translator
- Reviewer: read-only verification
- Explorer: read-only codebase scout
