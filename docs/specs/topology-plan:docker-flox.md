

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

