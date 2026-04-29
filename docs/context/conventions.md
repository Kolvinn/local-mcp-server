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
- pytest for test execution
- Tests in src/test_main.py or tests/ directory
- Test via MCP protocol (httpx POST) for integration tests
- Direct function calls acceptable for unit tests
- AGENT_ID=test_ingest for test isolation

## User/Auth
- AGENT_ID env var (default: "default_agent")
- NEVER hardcode user IDs
- Single user access — no auth middleware

## Communication
- Agents write full output to files, pass summaries
- docs/context/ is single source of truth for project specifics
- docs/project_notes/ for institutional memory (ADRs, bugs, issues)
