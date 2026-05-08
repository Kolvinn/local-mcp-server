# Container & Volume Topology — Design Spec

**Date:** 2026-05-08
**Phase:** 2 — Container & Volume Topology Design
**Status:** Draft, awaiting user approval (Gate 1)

## 1. Overview

This spec defines the container, volume, and interaction topology for a multi-container agent system. The architecture uses a **symlink bridge** pattern: an orchestrator container mounts a shared `project-vol` plus per-agent `agent-{variation}-vol` volumes, and creates symlinks to dynamically grant agents file access without copying data or exposing the host filesystem. Each agent container runs headless (`sleep infinity`), uses **Flox** for system-level dependencies and **uv** for Python, and receives tasks via a JSON config file written to its volume. LangGraph provides orchestrator state management; the OpenCode agent framework runs headless on each agent container.

Nine agent variations run across a single Docker Compose network (`internal-net`), all backed by one shared Dockerfile template parameterized by variation. Zero host filesystem access, zero copies, zero container restarts for file grants.


## 2. Volume Topology

### 2.1 Named Volumes

| Volume | Type | Purpose | Creates It |
|--------|------|---------|------------|
| `project-vol` | Named, external | Source of truth for all project files (src/, docs/, .opencode/, etc.) | Created by user outside docker-compose |
| `agent-orchestrator-vol` | Auto-created | Orchestrator's workspace for task configs and state | docker-compose |
| `agent-strategic_thinker-vol` | Auto-created | Workspace for strategic_thinker variation | docker-compose |
| `agent-rag_thinker-vol` | Auto-created | Workspace for rag_thinker variation | docker-compose |
| `agent-architect_thinker-vol` | Auto-created | Workspace for architect_thinker variation | docker-compose |
| `agent-python_implementer-vol` | Auto-created | Workspace for python_implementer variation | docker-compose |
| `agent-infra_implementer-vol` | Auto-created | Workspace for infra_implementer variation | docker-compose |
| `agent-code_auditor-vol` | Auto-created | Workspace for code_auditor variation | docker-compose |
| `agent-codebase_explorer-vol` | Auto-created | Workspace for codebase_explorer variation | docker-compose |
| `agent-dependency_explorer-vol` | Auto-created | Workspace for dependency_explorer variation | docker-compose |

### 2.2 Mount Matrix

| Container | Mounts `project-vol` | Mounts Own `agent-*-vol` | Mounts Other Agent Volumes |
|-----------|---------------------|--------------------------|---------------------------|
| **Orchestrator** | rw | rw (its own workspace) | rw (ALL agent volumes — for symlink bridge) |
| **Agent (any variation)** | No | rw (only its own) | No (filesystem isolation) |

### 2.3 Symlink Bridge Mechanics

The orchestrator dynamically creates symlinks from `project-vol` into agent volumes:

```bash
# Grant access: agent will see /workspace/src/ as symlinks to project-vol
ln -s /project-vol/src /agent-vols/python_implementer/workspace/src
ln -s /project-vol/docs/specs/foo.md /agent-vols/python_implementer/workspace/foo.md

# Revoke access (after task completion)
rm /agent-vols/python_implementer/workspace/src
rm /agent-vols/python_implementer/workspace/foo.md
```

**Key properties:**
- Agent writes follow symlinks → land in `project-vol` (source of truth)
- Agent creates new files at symlink target → appear in `project-vol` automatically
- Zero copies — symlink is a pointer, not a copy
- Zero host access — agents never touch the host filesystem
- Dynamic grants — orchestrator adds/removes symlinks without container restarts
- Agent only sees what the orchestrator grants — filesystem isolation per task

### 2.4 Volume Paths Inside Containers

| Volume | Mount Path in Orchestrator | Mount Path in Agent |
|--------|---------------------------|---------------------|
| `project-vol` | `/project-vol` | N/A (agent never mounts it) |
| `agent-orchestrator-vol` | `/workspace` | N/A |
| `agent-{variation}-vol` | `/agent-vols/{variation}` | `/workspace` |

**Critical invariant:** The orchestrator sees agent volumes at `/agent-vols/{variation}/`, but the agent sees its own volume at `/workspace/`. The orchestrator creates symlinks at `/agent-vols/{variation}/workspace/` → `/project-vol/...`. The agent container, seeing `/workspace/`, follows the symlinks transparently.


## 3. Docker Compose Layout

### 3.1 Network

Single external network: `internal-net` (preexisting, shared with Qdrant, Ollama, Traefik).

### 3.2 Compose Pattern (Parameterized)

```yaml
# docker-compose.yml — generated or maintained as canonical
services:
  orchestrator:
    container_name: agent-orchestrator
    image: agent-core:latest
    user: "1000:1000"
    depends_on: []  # no dependencies — agents wait for orchestrator
    volumes:
      - project-vol:/project-vol:rw
      - agent-orchestrator-vol:/workspace:rw
      - agent-strategic_thinker-vol:/agent-vols/strategic_thinker:rw
      - agent-rag_thinker-vol:/agent-vols/rag_thinker:rw
      - agent-architect_thinker-vol:/agent-vols/architect_thinker:rw
      - agent-python_implementer-vol:/agent-vols/python_implementer:rw
      - agent-infra_implementer-vol:/agent-vols/infra_implementer:rw
      - agent-code_auditor-vol:/agent-vols/code_auditor:rw
      - agent-codebase_explorer-vol:/agent-vols/codebase_explorer:rw
      - agent-dependency_explorer-vol:/agent-vols/dependency_explorer:rw
    environment:
      - VARIATION=orchestrator
      - AGENT_ID=orchestrator
      - OLLAMA_URL=${OLLAMA_URL:-http://host.docker.internal:11434}
      - QDRANT_HOST=${QDRANT_HOST:-qdrant}
      - QDRANT_PORT=${QDRANT_PORT:-6333}
    networks:
      - internal-net
    restart: unless-stopped
    command: ["sleep", "infinity"]

  # ─── Agent services (one per active variation) ───
  # Pattern repeats for each variation. Only parameter: VARIATION name.
  agent-strategic_thinker:
    container_name: agent-strategic_thinker
    image: agent-core:latest
    user: "1000:1000"
    depends_on:
      - orchestrator
    volumes:
      - agent-strategic_thinker-vol:/workspace:rw
    environment:
      - VARIATION=strategic_thinker
      - AGENT_ID=strategic_thinker
      - OLLAMA_URL=${OLLAMA_URL:-http://host.docker.internal:11434}
      - QDRANT_HOST=${QDRANT_HOST:-qdrant}
      - QDRANT_PORT=${QDRANT_PORT:-6333}
    networks:
      - internal-net
    restart: unless-stopped
    command: ["sleep", "infinity"]

  # ... repeat for: rag_thinker, architect_thinker, python_implementer,
  #     infra_implementer, code_auditor, codebase_explorer, dependency_explorer

volumes:
  project-vol:
    name: project-vol
    external: true
  agent-orchestrator-vol:
  agent-strategic_thinker-vol:
  agent-rag_thinker-vol:
  agent-architect_thinker-vol:
  agent-python_implementer-vol:
  agent-infra_implementer-vol:
  agent-code_auditor-vol:
  agent-codebase_explorer-vol:
  agent-dependency_explorer-vol:

networks:
  internal-net:
    name: internal-net
    external: true
```

### 3.3 What Differs Between Agent Services

Only the `VARIATION` env var and volume name differ between agent services. Everything else (image, user, command, network, restart policy) is identical. This means the compose file can be generated from a template with a list of variation names.

### 3.4 MVP Optimization

For MVP (fewer active agents), only define services for variations actually in use. The orchestrator can still reference all volumes even if the corresponding containers don't exist yet — volumes are independent of running containers.


## 4. Dockerfile Template

### 4.1 Design Principles

- **One Dockerfile, all variations.** The image is `agent-core:latest`. Variation is selected at runtime via the `VARIATION` env var.
- **Flox first.** All system tools (ripgrep, fd, jq, git, etc.) come from Flox. apt is fallback only.
- **uv for Python.** Python 3.14+ and all Python packages come via uv. Flox provides the system-level Python interpreter.
- **Headless.** No daemon, no entrypoint orchestration. Container runs `sleep infinity` and waits for task dispatch via file.
- **Small image.** Based on `ghcr.io/astral-sh/uv:python3.14-bookworm-slim`. Multistage build optional. Target: under 500MB.
- **`.flox/run/bin` on PATH.** Tools are available without `flox activate` overhead.

### 4.2 Concrete Dockerfile

```dockerfile
# ──────────────────────────────────────────────
# agent-core:latest — Single image for all 9 variations
# Variation selected at runtime via VARIATION env var.
# ──────────────────────────────────────────────

FROM ghcr.io/astral-sh/uv:python3.14-bookworm-slim

# ── Install Flox ─────────────────────────────
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl ca-certificates gnupg xz-utils \
    && curl -fsSL https://downloads.flox.dev/by-env/stable/archive.key \
    | gpg --dearmor -o /usr/share/keyrings/flox-archive-keyring.gpg \
    && echo "deb [signed-by=/usr/share/keyrings/flox-archive-keyring.gpg] \
    https://downloads.flox.dev/by-env/stable/deb/ stable/" \
    > /etc/apt/sources.list.d/flox.list \
    && apt-get update && apt-get install -y flox \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# ── Initialize Flox environment with ALL system tools ──
# One manifest covers all variations. Subset selection at runtime.
WORKDIR /flox-env
COPY flox-manifests/all-variations.toml manifest.toml
RUN flox init && flox edit -f manifest.toml && flox list \
    && rm manifest.toml

# ── Python venv via uv ────────────────────────
WORKDIR /app
RUN uv venv /app/.venv
ENV VIRTUAL_ENV=/app/.venv
ENV PATH="/app/.venv/bin:/flox-env/.flox/run/bin:$PATH"

# ── Install Python deps ───────────────────────
# pyproject.toml includes ALL Python deps for ALL variations
COPY pyproject.toml uv.lock /app/
RUN uv sync --frozen --no-dev

# ── Install bun (for bunx, OpenCode requires it) ──
# bun is already in the Flox manifest (see §5)
# Verify: bunx --version

# ── Set up workspace ──────────────────────────
RUN mkdir -p /workspace && chown -R dev:dev /workspace /app /flox-env
USER dev

# ── Headless run ──────────────────────────────
# Container stays alive, waits for task config file to appear
CMD ["sleep", "infinity"]
```

### 4.3 Key Details

- **`uv:python3.14-bookworm-slim`** base: tiny (~150MB), Python 3.14 and uv pre-installed
- **Flox from apt repo:** adds ~100-200MB for Nix closure, provides all system tools
- **`.flox/run/bin` on PATH:** symlinks to Nix store — no `flox activate` overhead
- **Single `flox edit -f`:** installs all packages for all variations in one Nix closure; agents select tools at runtime
- **bun from Flox:** satisfies `bunx` requirement (no npx/nodejs)
- **`dev` user (1000:1000):** matches host UID/GID for volume permissions

### 4.4 Image Size Target

| Component | Approx Size |
|-----------|-------------|
| uv:python3.14-bookworm-slim | ~150 MB |
| Flox + Nix closure + system tools | ~200 MB |
| Python venv + deps | ~100 MB |
| Application code | <10 MB |
| **Total target** | **~460 MB** |


## 5. Flox Manifest Per Variation

### 5.1 Strategy

Two options, both viable:

**Option A (recommended): Single manifest.** One `all-variations.toml` installs the union of all system tools. Each agent container uses a subset. Slightly larger image (~200MB for Nix closure) but vastly simpler build — one Dockerfile, one image, one build. Runtime selection via env var.

**Option B: Per-variation manifests.** Nine separate manifests, nine images. Smaller per-image but 9x build complexity, 9x CI time, harder caching. Only worth it if per-image size is critical.

This spec uses **Option A** as the default, with Option B as a future optimization.

### 5.2 Unified Manifest: `all-variations.toml`

```toml
version = 1

[install]
# ── Universal tools (every agent needs these) ──
git.pkg-path = "git"
curl.pkg-path = "curl"
bash.pkg-path = "bash"
coreutils.pkg-path = "coreutils"
gnugrep.pkg-path = "gnugrep"
gnused.pkg-path = "gnused"

# ── Explorer tools (ripgrep, fd, jq, tree, bat) ──
ripgrep.pkg-path = "ripgrep"
fd.pkg-path = "fd"
jq.pkg-path = "jq"
tree.pkg-path = "tree"
bat.pkg-path = "bat"
yq.pkg-path = "yq"

# ── Implementer tools ──
python3.pkg-path = "python3"
python3.version = "3.14"
bun.pkg-path = "bun"
nodejs.pkg-path = "nodejs_22"
gcc.pkg-path = "gcc"

# ── Auditor tools ──
sqlite.pkg-path = "sqlite"

# ── System thinker tools ──
# (No additional system tools — uses Python + git + curl already covered)

[options]
systems = ["x86_64-linux"]

[hook]
on-activate = """
    echo "Flox environment activated — all variation tools available"
"""
```

### 5.3 What Each Variation Uses

| Variation | System Tools Used (from manifest) | Notes |
|-----------|----------------------------------|-------|
| **orchestrator** | git, curl, bash, coreutils, grep, sed | Needs git for file ops, curl for health checks |
| **strategic_thinker** | git, curl, coreutils, grep, python3 | Reads/writes spec files, delegates to explorers |
| **rag_thinker** | git, curl, coreutils, grep, python3 | Same as strategic, loads qdrant/langchain skills |
| **architect_thinker** | git, curl, coreutils, grep, python3, yq | Same tools + yq for config inspection |
| **python_implementer** | git, curl, python3, gcc | Needs gcc for compiled extensions, python3 for uv |
| **infra_implementer** | git, curl, python3 | Primarily uses context7 skill for doc lookups |
| **code_auditor** | git, python3, sqlite, bash, grep | Needs sqlite for test DB inspection, grep for code search |
| **codebase_explorer** | ripgrep, fd, jq, tree, bat, git, grep | Heavy CLI tool user — fd for file search, rg for content, bat for preview |
| **dependency_explorer** | ripgrep, fd, jq, grep, git | Same as codebase_explorer minus bat/tree |

### 5.4 What is NOT in Flox

| Dependency | Why Not in Flox | Where Installed |
|-----------|-----------------|----------------|
| uv | In base image (`ghcr.io/astral-sh/uv`) already | Base image |
| Python packages (pytest, pydantic, etc.) | Managed by uv, not Flox | `uv sync` from pyproject.toml |
| OpenCode CLI (opencode) | Not in nixpkgs/Flox catalog | Installed via bun/npm in Dockerfile: `bun install -g @anthropic-ai/claude-code` or equivalent |

### 5.5 Per-Variation Manifests (Option B — for reference only)

If per-variation images are needed later, each manifest is a subset of the unified one:

**codebase_explorer** (heaviest CLI user):
```toml
[install]
ripgrep.pkg-path = "ripgrep"
fd.pkg-path = "fd"
jq.pkg-path = "jq"
tree.pkg-path = "tree"
bat.pkg-path = "bat"
git.pkg-path = "git"
curl.pkg-path = "curl"
coreutils.pkg-path = "coreutils"
gnugrep.pkg-path = "gnugrep"
```

**python_implementer** (Python-heavy):
```toml
[install]
python3.pkg-path = "python3"
python3.version = "3.14"
gcc.pkg-path = "gcc"
git.pkg-path = "git"
curl.pkg-path = "curl"
coreutils.pkg-path = "coreutils"
gnugrep.pkg-path = "gnugrep"
```

**orchestrator** (lightest):
```toml
[install]
git.pkg-path = "git"
curl.pkg-path = "curl"
coreutils.pkg-path = "coreutils"
gnugrep.pkg-path = "gnugrep"
```

### 5.6 OpenCode CLI Installation

OpenCode (the agent execution framework) must be installed in each agent container. It's NOT in Flox. Options:

| Approach | Pros | Cons |
|----------|------|------|
| **bun install -g** in Dockerfile | Simple, in the image | Larger image (~50MB for node_modules) |
| **Volume mount** from host | No image bloat | Violates "no host access" constraint |
| **Shared volume** with pre-installed opencode | Works, CD image | Extra volume, versioning complexity |

**Recommended**: `bun install -g @anthropic-ai/claude-code` (or equivalent opencode package) in the Dockerfile, with version pinned in `package.json`.


## 6. Context Injection

### 6.1 Mechanism

The orchestrator writes a JSON config file to the agent's volume before dispatching a task. The agent container reads this config on startup or when polling for tasks. No API calls, no network communication — pure file-based handoff.

### 6.2 Config File Location

```
/agent-vols/{variation}/workspace/task-config.json
```

Written by: orchestrator container
Read by: agent container (at `/workspace/task-config.json`)

### 6.3 Config Schema

```json
{
  "$schema": "task-config-v1",
  "task_id": "uuid-v4",
  "variation": "python_implementer",
  "base_type": "implementer",
  "model": "deepseek-v4-flash",
  "skills": [
    "python-expert",
    "python-best-practices",
    "pydantic",
    "python-type-safety"
  ],
  "context_files": [
    "docs/context/constraints.md",
    "docs/context/conventions.md",
    "docs/context/stack.md",
    "docs/specs/feature-x.md"
  ],
  "task": {
    "description": "Implement the UserRepository class per spec §3.1-3.3",
    "read_boundaries": {
      "allow": ["docs/specs/feature-x.md", "docs/context/*", "src/models/*.py"],
      "deny": ["docs/briefs/*", "docs/exploration/*", "*.env"]
    },
    "write_boundaries": {
      "allow": ["src/repositories/user_repository.py", "src/tests/test_user_repository.py"],
      "deny": ["src/services/*", "src/models/*"]
    }
  },
  "environment": {
    "python_binary": "/app/.venv/bin/python",
    "test_runner": "/app/.venv/bin/python -m pytest",
    "workdir": "/workspace",
    "import_style": "relative within packages",
    "package_manager": "uv"
  },
  "symlinks": {
    "src/": "/project-vol/src",
    "docs/": "/project-vol/docs",
    ".opencode/": "/project-vol/.opencode"
  },
  "output": {
    "format": "summary",
    "max_bullets": 3,
    "return_to": "orchestrator"
  },
  "timing": {
    "created_at": "2026-05-08T14:30:00Z",
    "expires_at": "2026-05-08T15:30:00Z",
    "priority": "normal"
  }
}
```

### 6.4 Field Descriptions

| Field | Required | Description |
|-------|----------|-------------|
| `task_id` | Yes | UUID v4, unique per task. Used for result correlation. |
| `variation` | Yes | One of the 9 variation names. |
| `base_type` | Yes | Core agent type (system_thinker, implementer, auditor, explorer). |
| `model` | Yes | Model to use for LLM calls (e.g., `deepseek-v4-flash`). |
| `skills` | Yes | List of skill names to load at spawn. |
| `context_files` | Yes | List of file paths (relative to project-vol) the agent should read. |
| `task.description` | Yes | 1-3 sentence human-readable task summary. |
| `task.read_boundaries` | Yes | Glob patterns for files the agent MAY read. |
| `task.write_boundaries` | Yes | Glob patterns for files the agent MAY write. |
| `environment` | Yes | Runtime context: Python binary path, test runner, workdir, import style. |
| `symlinks` | No | Map of workspace paths → project-vol targets. For agent awareness only — symlinks are already created by orchestrator. |
| `output` | Yes | Output format specification (summary, max bullets, return target). |
| `timing` | No | Task metadata: creation time, expiry, priority. |

### 6.5 How the Agent Reads Config

Two patterns, depending on task dispatch model:

**Pattern A: Polling loop (agent polls for new tasks)**
```
while true; do
  if [ -f /workspace/task-config.json ]; then
    # Read config, execute task, write results, delete config
    execute_task /workspace/task-config.json
    rm /workspace/task-config.json
  fi
  sleep 5
done
```

**Pattern B: Signal file (orchestrator writes a trigger)**
```
# Orchestrator writes config, then creates signal file:
echo "ready" > /agent-vols/{variation}/workspace/task-ready.signal

# Agent watches for signal:
inotifywait -e create /workspace/task-ready.signal
execute_task /workspace/task-config.json
```

**Recommended:** Pattern B (signal files) for lower latency. The orchestrator writes the full config, then creates a small signal file. The agent uses `inotifywait` or a polling loop.

### 6.6 Result Collection

Agent writes results to its workspace, then the orchestrator reads from the agent volume:

```
Agent writes:   /workspace/result.json → /agent-vols/{variation}/workspace/result.json
Agent signals:  echo "done" > /workspace/task-done.signal
Orchestrator reads: /agent-vols/{variation}/workspace/result.json
```

Files generated by the agent at symlinked paths (e.g., `src/repositories/user_repository.py`) flow through the symlink into `project-vol` automatically — no result collection needed for those.


## 7. Container Lifecycle

### 7.1 Startup Sequence

```
1. docker compose up -d
2. All containers start (orchestrator + all active agent variations)
3. Each container runs CMD ["sleep", "infinity"] — stays alive
4. Agent containers write a readiness file:
   echo "$(date -Iseconds)" > /workspace/agent-ready.signal
5. Orchestrator polls for readiness files before dispatching tasks:
   ls /agent-vols/*/workspace/agent-ready.signal
6. System is ready for user input
```

### 7.2 Readiness Check

| Method | Pros | Cons |
|--------|------|------|
| **Signal file** (recommended) | Simple, no HTTP needed, file-based | Requires polling by orchestrator |
| **Docker healthcheck** | Docker-native, `docker ps` shows health | Adds `curl` dependency, HTTP overhead |
| **TCP port** | Docker-native | Agents don't run servers |

**Recommended pattern:** Signal file + polling. The orchestrator checks for `/agent-vols/{variation}/workspace/agent-ready.signal` before dispatching. Agent writes this file at the end of its startup script (after Flox env is activated, venv is ready).

### 7.3 Task Dispatch Flow

```
Orchestrator decides to spawn agent (e.g., python_implementer)
    │
    ├─► 1. Creates symlinks for task-specific files
    │     ln -s /project-vol/docs/specs/foo.md /agent-vols/python_implementer/workspace/foo.md
    │     ln -s /project-vol/src /agent-vols/python_implementer/workspace/src
    │
    ├─► 2. Writes task-config.json to agent volume
    │     echo '{"task_id":"...","variation":"..."}' > /agent-vols/python_implementer/workspace/task-config.json
    │
    ├─► 3. Creates signal file
    │     echo "ready" > /agent-vols/python_implementer/workspace/task-ready.signal
    │
    ├─► 4. Agent detects signal → reads config → loads skills → executes task
    │     (Agent writes code/analysis to workspace, following symlinks to project-vol)
    │
    ├─► 5. Agent writes result.json + task-done.signal
    │     echo '{"status":"complete","summary":"..."}' > /workspace/result.json
    │     echo "done" > /workspace/task-done.signal
    │
    ├─► 6. Orchestrator detects task-done.signal → reads result.json
    │     cat /agent-vols/python_implementer/workspace/result.json
    │
    └─► 7. Orchestrator removes task-specific symlinks (revoke access)
        rm /agent-vols/python_implementer/workspace/foo.md
        rm /agent-vols/python_implementer/workspace/src
        rm /agent-vols/python_implementer/workspace/task-config.json
```

### 7.4 Shutdown

- `docker compose down` stops all containers
- Volumes persist across restarts (data survives)
- `docker compose down -v` removes volumes (clean slate)

### 7.5 Idle State

Between tasks, agent containers run `sleep infinity` with no CPU consumption. The orchestrator is the only container actively running (LangGraph state machine + polling loop). Memory usage at idle: ~50-100MB per agent container (python process + sleep), well within 32GB constraint even with 10 containers.

### 7.6 Concurrency

**One task per agent at a time.** The orchestrator checks `task-done.signal` before dispatching a new task. If an agent is busy, the orchestrator queues the task or spawns a thinker first (since thinkers have no practical concurrency limit — they just read and write files).

For variations of the same base type (e.g., python_implementer + infra_implementer), they share the base type but run in separate containers — true parallel work is possible.

### 7.7 Failure Recovery

| Failure | Recovery |
|---------|----------|
| Agent container crashes | Docker `restart: unless-stopped` brings it back. Orchestrator detects missing `agent-ready.signal` and waits. |
| Task times out | Orchestrator checks `timing.expires_at`. If expired and no `task-done.signal`, writes `task-cancel.signal`. Agent checks for this between steps. |
| Orchestrator crashes | User restarts compose. LangGraph state persisted to project-vol, resumes from checkpoint. |
| Volume corruption | Volume is Docker-managed. `docker volume rm` + `docker compose up -d` recreates it. `project-vol` is external — user manages independently. |


## 8. OpenCode + LangGraph Coexistence

**This is the most consequential architectural decision of the overhaul.** Two frameworks must coexist: OpenCode (the current agent execution framework) and LangGraph (the planned orchestrator state machine). This section defines what each framework owns and presents two viable coexistence architectures.

### 8.1 What Each Framework Provides

| Capability | OpenCode | LangGraph |
|-----------|----------|-----------|
| LLM call routing (model selection, API calls) | ✓ (opencode.jsonc models) | Via LangChain models |
| Tool execution (bash, read, write, glob, grep) | ✓ (permission system) | Via LangChain tools |
| Skill loading (SKILL.md injection) | ✓ (SkillsMiddleware) | Not natively |
| Prompt system (agent prompt files) | ✓ (.opencode/prompts/) | Via system messages |
| Subagent spawning | ✓ (task tool) | Via LangGraph subgraphs |
| Permission system (allow/deny/ask) | ✓ (opencode.jsonc) | Manual in nodes |
| State machine (nodes, edges, routing) | Not natively | ✓ (StateGraph) |
| Human-in-the-loop (interrupt/resume) | Not natively | ✓ (interrupt()) |
| Persistence (checkpointing) | Not natively | ✓ (checkpointer) |
| Streaming | Via subprocess | ✓ |
| File-based handoff protocol | Manual | Manual |
| MCP server integration | ✓ (opencode.jsonc mcp) | Via LangChain MCP tools |

### 8.2 The Core Question

**Does LangGraph replace OpenCode for the orchestrator, or do they coexist as layers?**

Currently:
- The orchestrator IS an OpenCode agent (mode: "primary")
- It spawns subagents via OpenCode's `task` tool
- Skills, prompts, permissions all flow through OpenCode
- The user interacts directly with the OpenCode orchestrator

The desired state:
- LangGraph manages orchestrator state and decision flow
- Agents run in Docker containers, not OpenCode subprocesses
- File-based handoff replaces in-process delegation

### 8.3 Approach A: LangGraph Orchestrator + OpenCode Headless Agents ("Clean Separation")

```
┌──────────────────────────────────────────────────────────────┐
│ USER                                                         │
│  │  (interacts via CLI / API)                                │
│  ▼                                                           │
│ ┌──────────────────────────────────────┐                     │
│ │ LangGraph Orchestrator (Python proc) │                     │
│ │  - StateGraph: ORIENT→Clarify→...    │                     │
│ │  - Human-in-the-loop gates           │                     │
│ │  - Checkpointer for session state    │                     │
│ │  - Symlink bridge management         │                     │
│ │  - Task config generation            │                     │
│ │  - Reads: summaries, result.json     │                     │
│ └──────────┬───────────────────────────┘                     │
│            │ writes task-config.json + signal files           │
│            ▼                                                 │
│ ┌──────────────────────────────────────┐                     │
│ │ Agent Container (e.g., python_impl)  │                     │
│ │  ┌────────────────────────────────┐  │                     │
│ │  │ OpenCode (headless)            │  │                     │
│ │  │  - Reads task-config.json      │  │                     │
│ │  │  - Loads skills from .opencode │  │                     │
│ │  │  - Uses prompts, tools, models │  │                     │
│ │  │  - Writes result.json          │  │                     │
│ │  │  - Writes code via symlinks    │  │                     │
│ │  └────────────────────────────────┘  │                     │
│ └──────────────────────────────────────┘                     │
└──────────────────────────────────────────────────────────────┘
```

**What runs where:**

| Component | Runs In | Framework |
|-----------|---------|-----------|
| Orchestrator decision flow | orchestrator container | LangGraph (Python) |
| User interaction | orchestrator container | LangGraph + CLI |
| Agent task execution | agent container | OpenCode (headless) |
| Skill loading | agent container | OpenCode SkillsMiddleware |
| Prompt system | agent container | OpenCode (.opencode/prompts/) |
| State persistence | orchestrator container | LangGraph checkpointer |
| File-based handoff | Between containers | Files on volumes |

**Pros:**
- Clean separation of concerns: LangGraph = orchestration, OpenCode = execution
- Each framework does what it's best at
- LangGraph is a standard Python application (easy to develop, test, debug)
- OpenCode's prompt/skill/tool system is fully preserved and leveraged
- The orchestrator is NOT an OpenCode agent — no conflict of identity
- LangGraph's human-in-the-loop integrates naturally with approval gates

**Cons:**
- The orchestrator is completely rewritten (from OpenCode agent → LangGraph Python app)
- Two codebases to maintain (LangGraph orchestrator + OpenCode agent config)
- The current OpenCode orchestrator prompt and config become dead code
- Must implement user interaction in LangGraph (CLI, input handling)
- LangGraph orchestrator needs its own model calls for decision-making
- OpenCode headless mode may not be officially supported or documented
- Integration risk: can OpenCode run truly headless with file-based I/O?

**Open questions for this approach:**
1. Can OpenCode run in a fully headless, non-interactive mode? (CLI flag needed)
2. Does OpenCode support reading task context from a file rather than stdin?
3. How does the orchestrator (LangGraph) call LLMs for its own reasoning? Via LangChain models? Which model?
4. What does user interaction look like? A CLI readline loop? A web UI? Stdin/stdout?

### 8.4 Approach B: LangGraph as OpenCode Tool ("Minimal Disruption")

```
┌──────────────────────────────────────────────────────────────┐
│ USER                                                         │
│  │  (interacts exactly as today — through OpenCode)          │
│  ▼                                                           │
│ ┌──────────────────────────────────────┐                     │
│ │ OpenCode Orchestrator (mode:primary) │                     │
│ │  - Same prompt, same skills          │                     │
│ │  - User interacts as before          │                     │
│ │  ┌────────────────────────────────┐  │                     │
│ │  │ LangGraph (embedded library)   │  │                     │
│ │  │  - Called as a tool:           │  │                     │
│ │  │    dispatch_task(variation,..)  │  │                     │
│ │  │  - State tracking in background │  │                     │
│ │  │  - Approval gate integration    │  │                     │
│ │  └────────────────────────────────┘  │                     │
│ │  - Writes task-config.json           │                     │
│ │  - Manages symlinks                  │                     │
│ └──────────┬───────────────────────────┘                     │
│            │ writes files to agent volumes                    │
│            ▼                                                 │
│ ┌──────────────────────────────────────┐                     │
│ │ Agent Container (e.g., python_impl)  │                     │
│ │  ┌────────────────────────────────┐  │                     │
│ │  │ OpenCode (headless)            │  │                     │
│ │  │  (same as Approach A)          │  │                     │
│ │  └────────────────────────────────┘  │                     │
│ └──────────────────────────────────────┘                     │
└──────────────────────────────────────────────────────────────┘
```

**What runs where:**

| Component | Runs In | Framework |
|-----------|---------|-----------|
| Orchestrator (user-facing) | orchestrator container | OpenCode (mode: primary) |
| State management | orchestrator container | LangGraph (embedded Python lib) |
| Agent task execution | agent container | OpenCode (headless) |
| Everything else | same as Approach A | same as Approach A |

**Pros:**
- Minimal disruption — the orchestrator remains an OpenCode agent
- User experience unchanged (same OpenCode CLI interaction)
- Existing orchestrator prompt and config are preserved and extended
- OpenCode handles all LLM calls for the orchestrator (model routing already configured)
- Human-in-the-loop flows through OpenCode's approval system, not a new UI
- Lower integration risk — LangGraph is "just a Python library" called from within OpenCode

**Cons:**
- Architectural layering is muddy — OpenCode wraps LangGraph, which wraps OpenCode agents
- The orchestrator has TWO state systems: OpenCode's context window + LangGraph's checkpointer
- Harder to reason about: "who is in charge?" when both frameworks are active at the orchestrator level
- OpenCode's permission system may interfere with LangGraph's file operations
- LangGraph is embedded, not standalone — harder to test independently
- The orchestrator's context window gets used for both user interaction AND state management
- Violates the "prompts stay generic" principle — orchestrator prompt must know about LangGraph

**Open questions for this approach:**
1. How does OpenCode call into a Python LangGraph library? Via bash tool (`python -c "..."`)? Or a proper Python tool?
2. Does the LangGraph checkpointer survive across OpenCode sessions?
3. If OpenCode is the orchestrator, does it still run in a container? Or remain on the host?

### 8.5 Trade-off Summary

| Dimension | Approach A (LangGraph Orch) | Approach B (OpenCode Orch + LG lib) |
|-----------|----------------------------|-------------------------------------|
| **Clean separation** | ✓ Clear layers | ✗ Intertwined |
| **Preserves existing work** | ✗ Orch prompt/config replaced | ✓ Orch prompt/config preserved |
| **User experience** | Requires new UI/work | Unchanged (OpenCode CLI) |
| **Development complexity** | Higher (new LangGraph app) | Medium (LangGraph as library) |
| **Testing** | Easy (standard Python app) | Harder (embedded in OpenCode) |
| **Integration risk** | Medium (headless OpenCode) | Low (OpenCode stays primary) |
| **State management clarity** | ✓ Single source of truth (LG) | ✗ Dual state (OC context + LG) |
| **Skill/prompt reuse** | ✓ Full (agent containers) | ✓ Full (agent containers) |
| **Approval gates** | LangGraph interrupt() | OpenCode permission system |
| **Model usage** | LangChain models for orch | OpenCode model for orch |
| **Long-term viability** | Better — independent layers | Fragile — tight coupling |

### 8.6 Hybrid Option: Approach C — Deep Agents as Orchestrator

A third approach uses **Deep Agents** (the framework built on LangGraph) as the orchestrator. Deep Agents provides planning (TodoListMiddleware), file management (FilesystemMiddleware), subagent delegation (SubAgentMiddleware), and skill loading (SkillsMiddleware) out of the box — capabilities that map directly to the orchestrator's needs.

```
Deep Agents Orchestrator (runs in orchestrator container)
  ├── TodoListMiddleware: break user goal into phases
  ├── SubAgentMiddleware: delegate to agent containers
  │     └── Custom subagents that write/read task-config.json
  ├── FilesystemMiddleware: manage symlink bridge
  ├── SkillsMiddleware: load orchestrator skills
  └── HumanInTheLoopMiddleware: approval gates
```

Agent containers still run OpenCode headless. The orchestrator uses Deep Agents because it provides the middleware layer between the user and agent containers — planning, file ops, and subagent dispatch are built-in. Less code to write than Approach A, cleaner separation than Approach B.

### 8.7 Recommendation

**Approach A (LangGraph Orchestrator + OpenCode Headless Agents)** is recommended for its clean separation of concerns. However, it requires answering the open questions in §8.3 before proceeding:

- **Can OpenCode run headless?** This is a binary gate. If no, Approach A is not viable.
- **How does the orchestrator interact with the user?** A simple CLI loop? A web interface? This affects the entire UX design.
- **Which model drives the orchestrator's reasoning?** GLM-5.1 is assigned to the orchestrator; does it run via LangChain or remain in OpenCode?

**If headless OpenCode is not feasible**, fall back to Approach B (LangGraph embedded in the OpenCode orchestrator) or Approach C (Deep Agents as orchestrator, which may handle agent dispatch differently).

### 8.8 What Does NOT Change Regardless of Approach

- Agent containers always run OpenCode headless (or equivalent agent runner)
- File-based handoff protocol (config JSON + signal files) remains the same
- Symlink bridge mechanics remain the same
- Docker volume topology remains the same
- Flox + uv environment management remains the same
- Per-variation skills and prompts are preserved in `.opencode/`

Only the **orchestrator's runtime** changes between approaches.


## 9. Diagrams

### 9.1 Volume Topology

```mermaid
flowchart TB
    subgraph Host["Docker Host"]
        PV["project-vol<br/>(external, named)<br/>src/ docs/ .opencode/"]
    end

    subgraph Orch["Orchestrator Container"]
        OW["/workspace/<br/>(orch's own volume)"]
        OM["/project-vol/<br/>(mount: rw)"]
        OAV["/agent-vols/<br/>(ALL agent volumes, rw)"]
    end

    subgraph Agent1["Agent: python_implementer"]
        A1W["/workspace/<br/>(mount: agent-python_implementer-vol, rw)"]
    end

    subgraph Agent2["Agent: codebase_explorer"]
        A2W["/workspace/<br/>(mount: agent-codebase_explorer-vol, rw)"]
    end

    subgraph AgentN["Agent: ... (any variation)"]
        ANW["/workspace/<br/>(mount: own volume, rw)"]
    end

    PV -->|"docker volume mount"| OM
    OM -->|"ln -s /project-vol/src → A1W/src"| A1W
    OM -->|"ln -s /project-vol/docs → A2W/docs"| A2W
    OAV -->|"orchestrator creates symlinks here"| A1W
    OAV -->|"orchestrator creates symlinks here"| A2W
    OAV -->|"orchestrator creates symlinks here"| ANW

    A1W -->|"agent writes follow symlink →"| PV
    A2W -->|"agent writes follow symlink →"| PV
    ANW -->|"agent writes follow symlink →"| PV
```

### 9.2 Task Dispatch Flow

```mermaid
sequenceDiagram
    participant U as User
    participant O as Orchestrator<br/>(LangGraph)
    participant AV as Agent Volume<br/>(agent-{var}-vol)
    participant A as Agent Container<br/>(OpenCode headless)
    participant PV as project-vol<br/>(source of truth)

    U->>O: "Implement UserRepository per spec §3"
    O->>O: LangGraph decides: spawn python_implementer
    O->>AV: Create symlinks: src/ → /project-vol/src
    O->>AV: Write task-config.json
    O->>AV: Write task-ready.signal
    A->>AV: Poll: detect task-ready.signal
    A->>AV: Read task-config.json
    A->>A: Load skills (python-expert, pydantic, etc.)
    A->>A: Execute task — write code
    A->>PV: Write src/repositories/user_repository.py<br/>(via symlink, lands in project-vol)
    A->>AV: Write result.json
    A->>AV: Write task-done.signal
    O->>AV: Detect task-done.signal
    O->>AV: Read result.json (summary only)
    O->>AV: Remove task symlinks (revoke access)
    O->>U: "Complete — 3 files modified. See src/repositories/"
```

### 9.3 OpenCode + LangGraph Relationship (Approach A)

```mermaid
flowchart TB
    subgraph UserSpace["User Interaction"]
        U["User<br/>(CLI / stdin)"]
    end

    subgraph OrchContainer["Orchestrator Container"]
        LG["LangGraph StateGraph<br/>ORIENT → Clarify → Assess → Gather → Synthesize → Gate"]
        CP["Checkpointer<br/>(persisted to project-vol)"]
        SM["Symlink Manager<br/>(ln -s / rm)"]
        TC["Task Config Generator<br/>(JSON schema)"]
        LG --> CP
        LG --> SM
        LG --> TC
    end

    subgraph AgentContainers["Agent Containers (1 per variation)"]
        subgraph AC1["agent-python_implementer"]
            OC1["OpenCode (headless)"]
            S1["Skills: python-expert, pydantic, ..."]
            P1["Prompt: implementer.md"]
            T1["Tools: bash, read, write, ..."]
            OC1 --> S1
            OC1 --> P1
            OC1 --> T1
        end
        subgraph AC2["agent-codebase_explorer"]
            OC2["OpenCode (headless)"]
            S2["Skills: none (built-in tools)"]
            P2["Prompt: explorer.md"]
            T2["Tools: glob, grep, read, ..."]
            OC2 --> S2
            OC2 --> P2
            OC2 --> T2
        end
        subgraph ACn["agent-architect_thinker"]
            OCn["OpenCode (headless)"]
            Sn["Skills: architecture-patterns, ..."]
            Pn["Prompt: system_thinker.md"]
            Tn["Tools: read, write, bash, ..."]
            OCn --> Sn
            OCn --> Pn
            OCn --> Tn
        end
    end

    subgraph Volumes["Docker Volumes"]
        PV["project-vol<br/>(source of truth)"]
        V1["agent-python_implementer-vol"]
        V2["agent-codebase_explorer-vol"]
        Vn["agent-architect_thinker-vol"]
    end

    U <-->|"input/output"| LG
    TC -->|"writes task-config.json"| V1
    TC -->|"writes task-config.json"| V2
    TC -->|"writes task-config.json"| Vn
    SM -->|"creates symlinks"| V1
    SM -->|"creates symlinks"| V2
    SM -->|"creates symlinks"| Vn
    V1 <-->|"symlink bridge"| PV
    V2 <-->|"symlink bridge"| PV
    Vn <-->|"symlink bridge"| PV
    AC1 -->|"reads config from"| V1
    AC2 -->|"reads config from"| V2
    ACn -->|"reads config from"| Vn
```


## 10. Decisions Required

These decisions must be made by the user before proceeding to Phase 3 (LangGraph State Management) and Phase 6 (Implementation).

### 10.1 OpenCode + LangGraph Architecture (CRITICAL — Binary Gate)

**D-001: Which coexistence approach?**

| Option | Implication |
|--------|------------|
| **Approach A:** LangGraph as standalone orchestrator | Rewrite orchestrator. OpenCode runs headless on agents. Clean separation. |
| **Approach B:** LangGraph embedded in OpenCode orchestrator | Preserve current orchestrator. LangGraph as a library. Muddy layering. |
| **Approach C:** Deep Agents as orchestrator | Middleware handles planning/files/delegation. Agent containers run OpenCode. |

**Requirement before choosing:** Must verify OpenCode can run headless (non-interactive, file-based I/O). If not, Approach A is not viable.

### 10.2 Headless OpenCode Feasibility (Gating Question)

**D-002: Can OpenCode run in a fully headless mode?**

This is the single most important technical question for the entire container architecture. Must verify:

- Can OpenCode be invoked without an interactive TTY?
- Can it read task input from a file (not stdin)?
- Can it write output to a file (not stdout)?
- Can it run within `sleep infinity` containers where it's invoked on-demand or polls for tasks?
- What is the CLI command for headless execution? (e.g., `opencode run --input task.json --output result.json`)

If headless OpenCode is NOT feasible, the architecture must pivot to a custom agent runner that replicates OpenCode's prompt/skill/tool system, or adopt a different agent framework entirely (e.g., LangChain agents in each container).

### 10.3 MVP Agent Set

**D-003: Which variations are active in MVP?**

The compose file defines 10 services (1 orchestrator + 9 agents). For MVP, the user may want fewer:

| MVP Option | Active Containers | RAM (idle) |
|-----------|-------------------|------------|
| **Full** | 10 | ~1 GB |
| **Core** | Orchestrator + python_implementer + codebase_explorer | ~300 MB |
| **Minimal** | Orchestrator + python_implementer | ~200 MB |

### 10.4 Orchestrator Model

**D-004: Which model drives the orchestrator's reasoning?**

| Model | Where It Runs | RAM | Context |
|-------|--------------|-----|---------|
| GLM-5.1 (assigned) | Via ? (LangChain or OpenCode) | ~8 GB at full context | 600+ tool calls endurance |
| Qwen 3.6 Plus | Via OpenCode | ~4 GB | 1M token window |
| A smaller model | Via Ollama | ~2 GB | Faster, lower quality |

Note: The orchestrator never reads full content — only summaries. A smaller model may suffice for routing decisions.

### 10.5 Task Dispatch Mechanism

**D-005: Signal files or HTTP API for task dispatch?**

| Mechanism | Pros | Cons |
|-----------|------|------|
| **Signal files** (current design) | Simple, file-based, no network code | Polling loop adds latency (~5s max) |
| **HTTP API** | Real-time dispatch | Agents need HTTP servers, more code |
| **inotify / filesystem watcher** | Near-real-time, no polling | Linux-only, complex error handling |

### 10.6 Flox vs apt Fallback

**D-006: What if a dependency is NOT in Flox?**

Current design: if a tool isn't in Flox catalog, install it via apt in the Dockerfile (as fallback). Must decide the threshold — how many apt packages before it's simpler to just use apt for everything? Currently only 1 identified gap (opencode-cli), installed via bun.

### 10.7 OpenCode CLI Installation

**D-007: How is OpenCode installed in agent containers?**

| Option | Size Impact | Complexity |
|--------|------------|------------|
| `bun install -g @anthropic-ai/claude-code` in Dockerfile | +50 MB | Low |
| Prebuilt binary layer | +0 MB (shared layer) | Medium |
| Volume mount from host | +0 MB | Violates "no host access" |

### 10.8 User Interaction Model (for Approach A)

**D-008: How does the user interact with a LangGraph orchestrator?**

If Approach A is chosen, the orchestrator is no longer an OpenCode agent — it's a standalone LangGraph Python application. Options:

- **REPL loop:** stdin/stdout readline interface
- **Web UI:** Simple web interface on port 8000
- **File-based:** User writes goal to a file, orchestrator reads it, writes results to a file
- **MCP server:** Orchestrator exposes an MCP server; user connects via OpenCode or another client

### 10.9 Volume Naming Convention

**D-009: Confirm volume naming pattern `agent-{variation}-vol`?**

Current proposal: `agent-python_implementer-vol`, `agent-codebase_explorer-vol`, etc. This uses underscores in variation names (matching the variation matrix). Docker volume names are case-sensitive. Alternative: hyphens (`agent-python-implementer-vol`).

### 10.10 Multi-Project Support

**D-010: One project-vol or multiple?**

Current design assumes one `project-vol` (one project). For multi-project support, the orchestrator would need to manage multiple external volumes or a single volume with project subdirectories. Defer to a future phase.

