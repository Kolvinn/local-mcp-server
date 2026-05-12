# Context & Config Survey

**Date:** 2026-05-12
**Scope:** docs/context/*, root config files, src/ structure
**Agent:** Explorer

---

## Context Files Accuracy

| File | Accurate? | Issues |
|------|-----------|--------|
| `constraints.md` | PARTIAL | ① References `src/index.ts` — a file that no longer exists (glob confirms). ② "No hardcoded port 8001" contradicts `memory_service.py` defaulting to 8001 (line 32: `os.getenv("MCP_MEM0_PORT", "8001")`). The constraint implies port 8000 is the only target, but mem0 service defaults to 8001. |
| `conventions.md` | PARTIAL | ① Line 6: "Single entry point at root main.py" — **no `main.py` exists anywhere** in the project. The actual entry points are `src/mcp_proxy_server.py` (port 8000) and `src/memory_service.py` (port 8001). ② Line 18: ".env.example documents available variables" — **no `.env.example` exists**. ③ Line 22-23: pytest run from `src/` directory with `.venv/bin/python -m pytest` — the `.venv` is at `src/.venv/`, which is correct. |
| `stack.md` | NO | **Multiple conda references that should reference Flox** (per ongoing overhaul — see MASTER_STATUS.md, flox-docker-research.md, SESSION_HANDOFF_006.md): ① Line 5: "Package manager: uv (via conda)" — should be Flox. ② Lines 11-12: "CONDA MANAGES BUN, PYTHON, UV, ETC." and "Conda provides the system-level environment..." — all outdated. ③ Line 45: "No reliance on src/index.ts — dead code" — file doesn't exist. ④ Line 47: "pyproject.toml for Python dependencies" — correct, but the file is at `src/pyproject.toml`, not root. ⑤ **Missing Flox stack description entirely.** |
| `services.md` | PARTIAL | ① Line 4: "MCP Memory Service at http://localhost:8000/mcp" — the **memory service defaults to port 8001** (`MCP_MEM0_PORT`), not 8000. The proxy is at 8000. These are different services. ② Lines 19-23: Agent model names differ from `.opencode/opencode.jsonc`: Orchestrator listed as "glm-5.1" but config says "deepseek-v4-pro"; System Thinker listed as "qwen-3.6-plus" but config says "deepseek-v4-pro". Only Implementer/Explorer match (both deepseek-v4-flash). ③ Does not mention the `agent_framework` controller package at all, despite it being the core of the ongoing overhaul. |
| `LEARNINGS.md` | PARTIAL | ① 219 lines of mostly project-agnostic interaction protocol rules — highly useful for agent coordination. ② Contains specific session references (Session 003, Session 001) that are app-specific (line 76, 204). ③ Lists retired agent types (Reviewer, Coordinator, RAG Architect) — still accurate but stale additions expected. ④ Line 159 says orchestrator uses "glm-5.1" but actual config uses "deepseek-v4-pro" — same model discrepancy as services.md. ⑤ Useful as-is but should be trimmed if context economy is a priority. |

---

## Root Configuration

| File | Purpose | Issues |
|------|---------|--------|
| `.env` | Environment variables for all services | No critical issues. Uses `MCP_PROXY_SERVER_PORT=8000` and `MCP_MEM0_PROXY_PORT=8001`. The `MCP_MEM0_PROXY_PORT` name differs from the actual env var consumed by `memory_service.py` (`MCP_MEM0_PORT`). |
| `docker-compose.yml` | Single service: `mcp-server` | Line 23: loadbalancer port set to **6274** — not 8000 or 8001. Line 5: uses image `mcp-server:uv-latest` (build section commented out). Uses `internal-net` external network. Healthcheck commented out. |
| `Dockerfile` | Active Docker build file | **Still uses conda** — `conda install --name base -c conda-forge uv` and `conda run uv sync`. No Flox integration despite Flox being the new standard per overhaul plans. Base image: `framework-opencode:latest`. |
| `Dockerfile.backup` | Backup Dockerfile (uv-based) | Uses `ghcr.io/astral-sh/uv:python3.14-bookworm-slim`, no conda. Contains `PYTHONPATH=/home/dev/src/` typo (line 61: should be `/home/dev/app/src`). |
| `Dockerfile.uvpython` | Another uv-based alternative | Same as `.backup` with same `PYTHONPATH` typo. |
| `README.md` | Brief project description | Only 9 lines, mentions conda (outdated), very minimal. No mention of Flox. |
| `.opencode/opencode.jsonc` | OpenCode agent configuration | Well-structured with 5 agent types. **Discrepancy from services.md** in model assignments (see above). Models used: deepseek-v4-pro (Orchestrator, System Thinker, Auditor) and deepseek-v4-flash (Implementer, Explorer). |
| `src/pyproject.toml` | Python dependencies | At `src/pyproject.toml` (not root). 34 dependencies listed. Includes `deepagents>=0.5.7`, `mem0ai`, `qdrant-client`, `docker`, `typer` for agent_framework. Requires Python >=3.13 (`.python-version` says 3.14). |
| `src/.python-version` | Python version pin | **3.14** — matches `constraints.md`. |
| `src/.venv/` | Project virtual environment | Present at `src/.venv/`. |
| `src/collection-config.jsonc` | Qdrant collection config | **Empty file** — 0 bytes of content. |
| `src/config.json` | MCP client config | Points to `http://0.0.0.0:8001/mcp` (port 8001 — the mem0 service, not the proxy). |
| `.memory-context.yaml` | Memory context metadata | Minimal test config with `project_id: test-verify-project`. |
| `spec/` | Specification files | Contains 2 spec files for schema Stage A1 and A2. |
| `test-docker/` | Docker test artifacts | Contains `Dockerfile.basetest` and `test1.yml`. |
| `.agents/skills/` | Installed skills | 45 skill directories. Comprehensive library. |
| `skills-lock.json` | Skill version lock | Present at root (and a copy at `src/skills-lock.json`). |

---

## Discrepancies

### 1. Conda → Flox Migration Not Reflected in Docs
- `docs/context/stack.md` describes conda as the package manager/system env provider (lines 5, 11, 12)
- `Dockerfile` still uses `conda install` and `conda run uv sync`
- `docs/project_notes/key_facts.md` references `conda env dev1` extensively
- `docs/project_notes/handoff.md` uses `conda run -n dev1` for all test commands
- **BUT** overhaul plans (MASTER_STATUS.md, SESSION_HANDOFF_006.md) and the `agent_framework/controller/` code already use Flox volumes and FLOX_ENV variables
- **Impact:** An agent reading `stack.md` would incorrectly use conda commands instead of Flox

### 2. No `main.py` Exists Despite Convention Claim
- `docs/context/conventions.md` line 6: "Single entry point at root main.py"
- **No `main.py` file exists anywhere in the project** (glob confirmed)
- Actual entry points are `src/mcp_proxy_server.py` and `src/memory_service.py`
- `test_main.py` imports `memory_service as main` at line 27

### 3. Port 8000 vs 8001 Confusion
- `docs/context/constraints.md` line 15: "No hardcoded port 8001 — target is 8000"
- `docs/context/services.md` line 4: "MCP Memory Service at http://localhost:8000/mcp"
- **Reality:** Two services exist — proxy on 8000, mem0 service on 8001
- `src/memory_service.py` defaults to `PORT = os.getenv("MCP_MEM0_PORT", "8001")`
- `.env` sets `MCP_MEM0_PROXY_PORT=8001` (note: different env var name than what code reads)
- `src/config.json` points to `http://0.0.0.0:8001/mcp`
- The test `test_port_is_8000_not_8001` (test_main.py:1640) asserts `main.PORT == 8000` but the module default is 8001 — **test will fail** unless MCP_MEM0_PORT env var is set

### 4. Model Name Discrepancies
- `docs/context/services.md` lists:
  - Orchestrator: `glm-5.1`
  - System Thinker: `qwen-3.6-plus`
  - Implementer: `deepseek-v4-flash`
  - Auditor: `deepseek-v4-pro`
  - Explorer: `deepseek-v4-flash`
- `.opencode/opencode.jsonc` uses:
  - Orchestrator: `opencode-go/deepseek-v4-pro`
  - System Thinker: `opencode-go/deepseek-v4-pro`
  - Implementer: `opencode-go/deepseek-v4-flash`
  - Auditor: `opencode-go/deepseek-v4-pro`
  - Explorer: `opencode-go/deepseek-v4-flash`
- **Implementer and Explorer match** (both deepseek-v4-flash), **Auditor matches** (deepseek-v4-pro)
- **Orchestrator and System Thinker differ** — services.md lists different models than the actual config

### 5. No `.env.example` Despite Convention
- `docs/context/conventions.md` line 18: ".env.example documents available variables"
- **No `.env.example` file exists** — would be useful for onboarding and documentation

### 6. `src/index.ts` Referenced as Dead Code — File No Longer Exists
- `docs/context/constraints.md` line 16: "No reliance on src/index.ts — dead code"
- `docs/context/stack.md` line 45: "No reliance on src/index.ts — dead code"
- **File `src/index.ts` does not exist** — the constraints are accurate but reference a non-existent file. Could be cleaned up.

### 7. `agent_framework` Package Missing from Context Docs
- `docs/context/` files don't mention `src/agent_framework/` at all, despite it being a core package with 10+ files spanning schema/validation/controller/CLI/MCP
- `services.md` lists agent types but doesn't mention the framework package
- The package is actively developed and referenced extensively in overhaul plans

### 8. `docker-compose.yml` Port Mismatch
- Service `mcp-server` has Traefik loadbalancer port set to **6274** (line 23)
- All other configs reference ports 8000 or 8001
- No healthcheck configured (commented out)
- Build section is commented out — uses pre-built image `mcp-server:uv-latest`

### 9. `PYTHONPATH` Typo in Backup Dockerfiles
- `Dockerfile.backup` line 61 and `Dockerfile.uvpython` line 61: `PYTHONPATH=/home/dev/src/`
- Should be `/home/dev/app/src/`

### 10. Test Port Assertion Contradicts Code Default
- `src/test_main.py:1640-1642` asserts `main.PORT == 8000`
- `src/memory_service.py:32` defaults to `os.getenv("MCP_MEM0_PORT", "8001")`
- Unless `MCP_MEM0_PORT=8000` is set in the test environment, this test will **fail**

---

## Recommendations

1. **Update `stack.md`** to reflect Flox as the system package manager instead of conda. Remove all conda references. Add Flox activation/PATH info.

2. **Update `constraints.md`** to remove `src/index.ts` dead code reference (file doesn't exist). Clarify the port 8000/8001 duality — proxy on 8000, mem0 on 8001.

3. **Fix `conventions.md`** — either create a `main.py` or update the convention to reflect the actual entry points (`mcp_proxy_server.py`, `memory_service.py`). Create `.env.example`.

4. **Update `services.md`** with correct model names matching `.opencode/opencode.jsonc`. Clarify port 8000 vs 8001 for proxy vs memory services. Add `agent_framework` package to the service description.

5. **Fix `test_main.py:1640-1642`** — the test asserts PORT is 8000 but the code defaults to 8001. Either fix the assertion or the default, and add a conftest.py to set `MCP_MEM0_PORT=8000` for consistent test results.

6. **Update `Dockerfile`** to use Flox instead of conda (per overhaul plan), or update plan docs if conda is being kept.

7. **Fix `PYTHONPATH`** in `Dockerfile.backup` and `Dockerfile.uvpython` from `/home/dev/src/` to `/home/dev/app/src/`.

8. **Investigate `docker-compose.yml` port 6274** — clarify whether this is intentional (Traefik internal routing) or a stale value.

9. **Either populate or remove `src/collection-config.jsonc`** — currently an empty file.

10. **Trim or relocate app-specific content from `LEARNINGS.md`** — consider moving session-specific learnings to `docs/learnings/` and keeping only protocol rules in `LEARNINGS.md`.

---

## Files Checked

- `docs/context/constraints.md`
- `docs/context/conventions.md`
- `docs/context/LEARNINGS.md`
- `docs/context/services.md`
- `docs/context/stack.md`
- `.env`
- `docker-compose.yml`
- `Dockerfile`, `Dockerfile.backup`, `Dockerfile.uvpython`
- `README.md`
- `.opencode/opencode.jsonc`, `.opencode/prompts/*`
- `src/pyproject.toml`, `src/.python-version`
- `src/mcp_proxy_server.py`, `src/memory_service.py`
- `src/test_main.py`
- `src/agent_framework/` (package structure)
- `src/memory/` (package structure)
- `src/collection-config.jsonc`, `src/config.json`
- `.memory-context.yaml`
- `spec/`, `test-docker/`
