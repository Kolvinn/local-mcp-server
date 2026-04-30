# Project Stack

## Runtime
- Language: Python 3.14+
- Package manager: uv (via conda)
- Base image: framework-base:latest (custom, not on Docker Hub)

## Environment
- the `.env` file in the app root directory contains the appropriate env vars that should either be injected into the framework, or readfrom
- BUNX REPLACES NPX
- CONDA MANAGES BUN, PYTHON, UV, ETC.
- THIS CURRENT ENVIRONMENT IS CALLED 'dev1'. This is where everything is installed 

## Frameworks & Libraries
- MCP Server: FastMCP (streamable-http transport)
- Memory: mem0ai (in-process Python library)
- HTTP: httpx (async client)
- Data validation: Pydantic models
- Config: python-dotenv, os.getenv() with defaults

## Infrastructure
- Container: Docker Compose, single service on `internal-net` (external network)
- Reverse proxy: Traefik (Docker labels for routing)
- User: dev:1000:1000
- Container mount: /home/dev/app

  
## External Services (user-managed, not in this repo)
- Qdrant: vector store, port 6333
- Ollama: LLM + embeddings, port 11434
  - Available models: nomic-embed-text (embeddings), llama3.1:8b (LLM)

## Hardware
- GPU: RTX 3080 (10GB VRAM)
- RAM: 32GB
- Keep memory usage within limits

## Do-Not
- No npx — use bunx for JS tooling
- No Node.js — use bun if JS runtime needed
- No auth/multi-tenancy — single user access model
- No hardcoded secrets, API keys, or credentials
- No reliance on src/index.ts — dead code

## Version Locking
- pyproject.toml for Python dependencies
- No other version lock files
