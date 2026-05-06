# Project Conventions

## Code Style
- Type hints on ALL function signatures
- Pydantic models for data validation and MCP tool inputs
- Single entry point at root main.py
- Async where appropriate (httpx, FastMCP)

## Naming
- Functions: snake_case
- Classes: PascalCase
- Constants: UPPER_SNAKE_CASE
- Modules: lowercase, underscores

## Configuration
- ALL configuration from environment variables
- Use os.getenv("VAR", "default") — never hardcode values
- .env.example documents available variables
- No hardcoded hostnames, ports, or model names

## Testing
- pytest for test execution (run from `src/` directory with `.venv/bin/python -m pytest`)
- Tests in `src/tests/`, `src/test_*.py`, or a package-local `tests/` directory
- Direct function calls for unit tests; MCP protocol (httpx POST) for integration tests where applicable
- AGENT_ID=test_ingest for test isolation

## Imports
- Relative imports within packages (e.g., `from .models import ...`)
- Do NOT use `from src.*` — `src/` is not a Python package (no `src/__init__.py`)
- Do not add `__init__.py` to `src/` without explicit architectural reason

## User/Auth
- AGENT_ID env var (default: "default_agent")
- NEVER hardcode user IDs
- Single user access — no auth middleware

## Communication
- Agents write full output to files, pass summaries
- docs/context/ is single source of truth for project specifics
- docs/project_notes/ for institutional memory (ADRs, bugs, issues)
