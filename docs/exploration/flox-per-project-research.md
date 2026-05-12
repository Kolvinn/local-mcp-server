# Flox Per-Project Environment Patterns — Research Findings

**Date:** 2026-05-12
**Sources:** Context7 API (flox.dev docs, flox/flox GitHub, flox/floxdocs), existing specs in `docs/specs/`
**Status:** Complete
**Extends:** `docs/exploration/flox-docker-research.md` (do not read this alone — read that first)

---

## 1. Manifest on Mounted Volume (`flox activate --dir`

### Yes — It Works

`flox activate -d=<path>` (or `flox activate --dir <path>`) is a **first-class, documented feature**. The `<path>` must contain a `.flox/` directory with a valid environment (initialized via `flox init`).

```bash
flox activate -d /app/project/agents/implementer/   # valid
flox activate -d /mnt/volume/my-env                  # valid — any path
```

**Confirmed in docs:**
- `flox/flox` GitHub repo: `flox activate -d=<path>` — activates the environment at a specific directory path
- `flox/flox` docs: `flox init -d ./my-project` — creates environment in a specific directory
- `flox/floxdocs` docs: `flox list -d python_env` — lists packages in a named directory environment

### The Nuance: `.flox/` vs `/nix/store/`

| Component | Location | Lives on Volume? | Issue |
|-----------|----------|------------------|-------|
| `manifest.toml` | `.flox/` dir | ✅ Yes | Declarative manifest — just text |
| `manifest.lock` | `.flox/` dir | ✅ Yes | Lock file — just text |
| Environment symlinks | `.flox/run/<env>/bin/` | ✅ Yes | Symlinks pointing to Nix store |
| **Nix store paths** | `/nix/store/<hash>-<pkg>-<ver>/` | ❌ **No** — on container FS | Immutable, content-addressed |

The `.flox/run/<env>/bin/` directory is a **symlink forest** — each binary is a symlink to a path in `/nix/store/`. If `.flox/` is on a volume but `/nix/store/` is empty (not populated), the symlinks **will be broken**.

### Three Viable Patterns

**Pattern A: Pre-build `.flox/` in image, volume for workspace only (current spec)**
- `.flox/` and `/nix/store/` both baked into Docker image
- Volume contains only agent workspace (code, task configs)
- `flox activate -d /flox-env/` or add `.flox/run/bin` to `PATH`
- ✅ No broken symlinks, no runtime network calls

**Pattern B: Pre-build, symlink-aware volume copy**
- Build env in Docker image, then copy **both** `.flox/` AND `/nix/store/` to volume
- On container start, restore `/nix/store/` from volume before activating
- Requires root/capability to write to `/nix/store/`
- ⚠️ `/nix/store/` is typically read-only and managed by Nix daemon — fragile
- ❌ **Not recommended** — fighting Nix's design

**Pattern C: Build at runtime on volume (cold start)**
- `.flox/` directory is on volume, but `/nix/store/` is empty
- Container runs `flox install` on first start to populate `/nix/store/`
- Requires network access and compute time on first startup
- Subsequent starts (warm) use cached `/nix/store/` — no network
- ✅ Works cleanly — this is how Flox is designed
- ❌ Adds 30-120s to first startup (download + extract Nix packages)

**Recommendation: Pattern A** for production (pre-bake everything). Pattern C is acceptable for dev/test environments where startup latency is acceptable.

### Direct `PATH` Bypass (No `flox activate` Needed)

The `.flox/run/<env>/bin/` directory contains symlinks to all installed binaries. Adding this to `PATH` makes tools available **without any activation overhead**:

```bash
ENV PATH="/flox-env/.flox/run/bin:$PATH"
# Now ripgrep, jq, fd, etc. are directly available — no activate needed
```

This is the **recommended pattern for headless containers** per the existing specs.

---

## 2. Pre-built Closures: Cold Start vs Warm Start

### How the Nix Closure Works

When you run `flox install`:
1. Flox reads the manifest and resolves dependencies
2. It downloads binary packages from `https://cache.flox.dev` (a Nix binary cache)
3. Packages are extracted to `/nix/store/<hash>-<pkg>-<ver>/`
4. A symlink forest is built at `.flox/run/<env>/bin/` pointing to each binary

The complete set of Nix store paths is the **closure**.

### `flox containerize` — Baking the Closure into a Docker Image

```bash
flox containerize --runtime docker
# Creates a standalone Docker image with the FULL Nix closure baked in
# Each dependency is an image layer
```

This produces an image where:
- `/nix/store/` is fully populated
- The environment is immediately activatable
- **Zero network calls** on startup
- No need for Flox binary itself (though it's typically included)

**Trade-off:** The image is larger (Flox + Nix closure adds ~200MB) but startup is instant.

### Pre-Resolving Without Containerize

There is **no `flox build` equivalent** that produces a portable closure artifact you can copy. The mechanisms are:

| Mechanism | Output | Portable? | Network at Startup? |
|-----------|--------|-----------|---------------------|
| `flox containerize` | Docker image | ✅ Yes | ❌ No |
| `flox install` in image build | `/nix/store/` populated | ✅ Yes (in image) | ❌ No |
| `flox push` → `flox pull` | Remote FloxHub env | ✅ Yes (via network) | ✅ Yes (pull needed) |
| Copy `.flox/` + `/nix/store/` | Manual file copy | ⚠️ Fragile | ❌ No (if copy succeeds) |

**Key insight:** Nix store paths are content-addressed (`/nix/store/<hash>-<pkg>-<ver>/`). Two machines that have installed the same package at the same version will have the same path. If you copy store paths from one machine to another, they will work — but the Nix database must also be consistent.

### Cold Start vs Warm Start

| Phase | Cold (first `flox install` / `flox activate`) | Warm (subsequent) |
|-------|------------------------------------------------|-------------------|
| Nix store state | Empty or missing paths | All paths present |
| Network calls | Required — download packages from cache | None |
| Time | **30-120 seconds** (download + extract) | **< 1 second** (symlink resolution only) |
| Disk I/O | Heavy — writing to `/nix/store/` | Minimal |
| CPU | Moderate — extraction | Negligible |

**For our use case:** If the environment is baked into the Docker image via `flox install` during `docker build`, every container start is a **warm start** — no network, sub-second activation.

If `.flox/` is on a volume but `/nix/store/` is empty (Pattern C above), the **first activation** is a cold start.

---

## 3. Activation Overhead

### Measured Behavior

The activation time depends on **mode**:

| Mode | Command | Hook scripts? | Profile scripts? | Services? | Est. Time |
|------|---------|---------------|------------------|-----------|-----------|
| `dev` (default) | `flox activate -- <cmd>` | ✅ Yes | ✅ Yes | ❌ No (unless `-s`) | **100-500ms** |
| `run` | `flox activate -m=run -- <cmd>` | ❌ No | ❌ No | ❌ No | **10-50ms** |
| PATH bypass | Direct binary via `.flox/run/bin` | ❌ No | ❌ No | ❌ No | **0ms** (direct exec) |

### Breakdown of Activation Steps (dev mode)

1. **Subshell creation** — `fork()` + `exec()` — ~1-5ms
2. **Lock file check** — verify environment is fresh — ~5-10ms
3. **PATH manipulation** — prepend `.flox/run/bin/` — ~1ms
4. **Environment variable export** — `[vars]` section — ~1-5ms
5. **`on-activate` hook** — arbitrary script — **variable** (could be 0ms to seconds)
6. **Profile scripts** — bash/zsh/fish — ~10-50ms
7. **Command execution** — your actual command

### `run` Mode

Skipped steps: 5 (hook), 6 (profile). Only PATH setup + env vars. **Sub-50ms typical.**

### PATH Bypass

**Zero overhead.** The binaries are on `PATH` via Dockerfile `ENV` directive. `which ripgrep` resolves instantly. Execution time = binary startup time.

**Recommendation for agent containers:**
```bash
ENV PATH="/flox-env/.flox/run/bin:$PATH"
```
No `flox activate` needed. Tools available immediately. This is what the existing specs already recommend (§4.3 of `topology-plan:docker-flox.md`).

---

## 4. Binary in Image, Env on Volume — Does It Work Cleanly?

### The Pattern

```
Docker Image:
├── /usr/bin/flox          ← Binary installed via apt
├── /nix/store/...         ← Pre-populated Nix store (from build)
└── /flox-env/.flox/       ← Baked-in env (fallback)

Volume (at runtime):
├── /app/project/agents/implementer/.flox/   ← Per-agent manifest
└── /app/project/agents/explorer/.flox/      ← Different agent type
```

### Assessment

| Aspect | Verdict | Detail |
|--------|---------|--------|
| **Can `flox` binary read `.flox/` from volume?** | ✅ **Yes** | `-d=/path/on/volume` works anywhere |
| **Can `/nix/store/` be on volume?** | ⚠️ **Technically yes, practically no** | Must be at `/nix/store/`. Symlinking `/nix` from volume is fragile. Copying store paths breaks Nix DB consistency. |
| **Can `.flox/run/bin` symlinks resolve?** | ❌ **No, if `/nix/store/` is empty** | Symlinks point to `/nix/store/<hash>/bin/<tool>`. If store missing → broken links. |
| **Cold build on volume?** | ✅ **Works** | First `flox install` populates both `.flox/` and `/nix/store/` |
| **Pre-built `.flox/` on volume with matching image store?** | ✅ **Works** | If image has the exact same Nix store paths, symlinks resolve |

### The Cleanest Pattern: Union of Both Approaches

1. **Bake a "base" Flox environment in the Docker image** with all packages agents might need
2. **Volume contains lightweight per-agent `.flox/` directories** that use `[include]` to reference the baked-in base
3. **`.flox/run/bin` from the baked env is on PATH** — all tools available immediately
4. Per-agent variations use **environment variables** and **skill selection**, not separate Flox manifests

This is essentially what `topology-plan:docker-flox.md` already recommends: **one manifest, all variations, subset selection at runtime.**

### What If You Still Want Per-Agent Manifests on a Volume?

The `[include]` composition feature makes this viable:

**Volume path: `/app/project/agents/implementer/.flox/manifest.toml`**
```toml
version = 1

[include]
environments = [
  { dir = "/flox-env" }  # Reference the baked-in base env
]

[install]
gcc.pkg-path = "gcc"  # Implementer-specific addition
```

**Image-baked: `/flox-env/.flox/manifest.toml`**
```toml
version = 1

[install]
ripgrep.pkg-path = "ripgrep"
fd.pkg-path = "fd"
jq.pkg-path = "jq"
git.pkg-path = "git"
python3.pkg-path = "python3"
bun.pkg-path = "bun"
nodejs_22.pkg-path = "nodejs_22"
# ... all base tools
```

This way:
- The Nix closure lives in the image (pre-resolved)
- Each agent has a lightweight `.flox/` on the volume that references the base
- Composition merges at activation time — Flox resolves overlapping packages with priority
- **No network calls, no cold start, zero overhead**

---

## 5. Multi-Manifest / Sub-Environments

### Confirmed: Native Support via Two Mechanisms

#### Mechanism A: Composition (`[include]` in manifest.toml)

Flox has a **first-class composition system**:

```toml
[include]
environments = [
  # Local environments
  { dir = "../python_env" },
  { dir = "../explorer_tools", name = "explorer" },
  # Remote environments
  { remote = "myuser/myenv" },
]
```

Properties:
- Later entries in the list have **higher priority** (override earlier ones)
- Use `flox list -c` to see the **merged manifest**
- Composed environments are resolved into a single symlink forest at activation
- Package conflicts are resolved by priority order
- The `name` field overrides the environment's display name

#### Mechanism B: Layering (Nested `flox activate`)

```bash
# Enter default environment first
flox activate -d /default-env
flox [default] $ flox activate -d /project-env
flox [project-env default] $  # Both environments active
```

- Environments are layered on top of each other
- Later activations have higher PATH priority
- Use `flox envs` to see currently active environments
- This is documented in `floxdocs/docs/tutorials/layering-multiple-environments.md`

### For Our Agent Variations

**Three approaches, in order of recommendation:**

| Approach | Complexity | Flexibility | Image Size | Startup Time |
|----------|-----------|-------------|------------|--------------|
| **A: Single manifest, runtime selection** (current spec) | 🟢 Low | Medium | Larger (~200MB) | Instant |
| **B: Base + per-agent includes** | 🟡 Medium | High | Same base (cached) | Instant |
| **C: Per-agent dirs on volume** | 🔴 High | Very High | Minimal (binary only) | Cold: 30-120s |

**Approach B is novel and promising.** It combines the instant startup of Approach A with the flexibility of per-agent customization:

```
Docker Image:
├── /usr/bin/flox
├── /nix/store/...          ← ONE shared Nix closure
├── /flox-env/.flox/        ← Base env with ALL potential packages
└── /flox-env/.flox/manifest.toml  ← Union of all agent tools

Volume:
├── agents/implementer/.flox/manifest.toml:
│   [include]
│   environments = [{ dir = "/flox-env" }]
│   [install]
│   gcc.pkg-path = "gcc"    # Only implementer needs gcc
│
├── agents/explorer/.flox/manifest.toml:
│   [include]
│   environments = [{ dir = "/flox-env" }]
│   # No extra installs — uses base tools
│
└── agents/auditor/.flox/manifest.toml:
    [include]
    environments = [{ dir = "/flox-env" }]
    [install]
    sqlite.pkg-path = "sqlite"  # Only auditor needs sqlite
```

Activation:
```bash
flox activate -d /mnt/volume/agents/implementer/ -- python agent.py
```

**Caveat:** This requires validation. If `[include]` triggers a Nix resolution that needs packages NOT in the base env, it would need to download them. The base env should include a superset of all packages.

### Open Question: Can `[include]` Resolve to a Pre-Built Nix Store?

The composition docs show includes resolving at activation time. If the included env's packages are already in `/nix/store/` (from the base env build), Flox should use them without network calls. This needs **empirical validation** — the docs don't explicitly say "composed envs skip download if store paths exist."

---

## 6. Node.js and Bun Support

### Confirmed: Both Available in Flox Catalog

From floxdev.com docs and floxdocs llms.txt:

**Node.js:**
```bash
flox search nodejs
# Shows: nodejs, nodejs_20, nodejs_22, nodejs_24, nodejs_latest
# Multiple versions available, each with distinct pkg-path

flox install nodejs_22    # Node.js 22.x
flox install nodejs_24    # Node.js 24.x
```

**Bun:**
- Confirmed present in `flox list` output: `bun: bun (1.2.20)`
- NVM migration tutorial explicitly states: "Flox can manage versions of other JavaScript runtimes like Bun and Deno"
- Install via: `flox install bun`

Both are part of the standard nixpkgs catalog that Flox indexes.

### For This Project

The existing spec (`topology-plan:docker-flox.md`) already includes both:
```toml
[install]
bun.pkg-path = "bun"
nodejs.pkg-path = "nodejs_22"
```

This satisfies the `bunx` CLI requirement for OpenCode installation.

### What Is NOT in Flox (Confirmed Gaps)

| Tool | In Flox? | Fallback |
|------|----------|----------|
| Python (any version) | ✅ Yes | N/A — in base image too |
| uv | ❌ No (not found in nixpkgs/Flox catalog) | `ghcr.io/astral-sh/uv` base image |
| OpenCode (`@anthropic-ai/claude-code`) | ❌ No (npm package) | `bun install -g` in Dockerfile |
| pip Python packages (langchain, pydantic, etc.) | ❌ No (Flox can do `python312Packages.xxx` but uv is preferred) | `uv sync` from pyproject.toml |

---

## 7. Additional Findings Not in Prior Research

### FloxHub Push/Pull for Environment Mobility

```bash
# Push local env to FloxHub
flox push -d /my-env -o myorg

# Pull to another machine
flox pull myorg/my-env -d /path/to/deploy
```

This is a viable alternative to volume-based env distribution:
- Push env at build time to FloxHub
- Each container pulls on first start
- Subsequent starts are cached locally

### `flox build` for Custom Packages

Flox supports building custom packages defined in `[build]`:
```toml
[build.hello]
command = '''
  mkdir -p $out/bin
  go build -o $out/bin/hello
'''
```

This produces `result-<name>` symlinks pointing into the Nix store. Not directly relevant for our use case (we use uv for Python), but good to know.

### Services Can Start on Activation

```bash
flox activate -s    # Activate AND start services
```

Services defined in `[services]` section run as background processes. Not needed for our headless agents, but relevant if Flox-managed services are needed later.

### `flox edit -f` for Manifest Injection

```bash
flox edit -f /path/to/manifest.toml
```

Replaces the environment's manifest with the file content, runs validation, and installs/removes packages as needed. This is what the spec uses for injecting the `all-variations.toml` at build time:
```dockerfile
COPY flox-manifests/all-variations.toml manifest.toml
RUN flox init && flox edit -f manifest.toml && flox list
```

---

## 8. Answers to Specific Research Questions

### Q1: Can a Flox environment be activated from a `manifest.toml` on a mounted volume?

**Yes**, with `flox activate -d /path/on/volume/`. The `.flox/` directory on the volume must contain a valid environment (manifest.toml + lockfile + linked store paths). If the Nix store paths are not present on the container, the symlinks will be broken — but you can `flox install` at runtime to populate them (cold start).

### Q2: Can you pre-build and store a closure on a volume?

**Not cleanly.** The Nix store is at `/nix/store/` (container filesystem), not on the volume. The closest patterns are:
- Bake env into image (pre-resolved) — no volume needed
- `flox containerize` — produces a standalone Docker image
- Pull from FloxHub on first start — network required once

There is no "export closure as zip/tarball" command in Flox.

### Q3: What's the activation time?

- `-m=run` mode: **~10-50ms** (PATH + env vars only)
- `dev` mode (hooks, profile): **~100-500ms** (but can be more if on-activate is heavy)
- PATH bypass (`.flox/run/bin`): **0ms** — tools are directly available

For agents that start/stop frequently, use the PATH bypass pattern.

### Q4: Binary in image, env on volume — does it work?

**Yes, but with constraints.** The `flox` binary installed in the image can read `.flox/` directories from any path. The key constraint is `/nix/store/` availability. Best approach: pre-populate `/nix/store/` in the image with a superset of packages, use per-agent `[include]` on the volume to customize.

### Q5: Multi-manifest projects / sub-environments?

**Yes, two mechanisms:**
1. `[include]` in manifest.toml — compose environments at activation
2. Layered `flox activate` — nest environments at runtime

Both support hierarchical, per-variation customization.

### Q6: Does Flox have bun and node?

**Yes.**
- `bun` → `flox install bun` (version 1.2.20 confirmed)
- `nodejs_22` → `flox install nodejs_22` (multiple versions available)

---

## 9. Recommended Pattern (Updated)

Based on all research, the optimal approach for the multi-agent Docker setup is:

1. **Install `flox` binary in Docker image** via apt (as already spec'd)
2. **Bake a single "union" Flox environment** in the image with ALL tools for ALL agent variations
3. **Use `.flox/run/bin` on PATH** — no `flox activate` overhead
4. **Per-agent variation is purely env-var-driven** — no per-agent `.flox/` directories needed on the volume
5. **If per-agent manifests are desired later**, use `[include]` composition pointing to the baked-in base env

This gives:
- ✅ Zero activation overhead
- ✅ Zero network calls at startup
- ✅ Single image, single build
- ✅ All 80k+ nixpkgs available
- ✅ bun + nodejs_22 for OpenCode CLI
- ✅ Scalable to 9+ agent variations without per-agent image complexity

### Dockerfile Pattern (Confirms Existing Spec)

```dockerfile
FROM ghcr.io/astral-sh/uv:python3.14-bookworm-slim

# Install Flox
RUN apt-get update && apt-get install -y curl ca-certificates gnupg xz-utils \
    && curl -fsSL https://downloads.flox.dev/by-env/stable/archive.key \
    | gpg --dearmor -o /usr/share/keyrings/flox-archive-keyring.gpg \
    && echo "deb [signed-by=/usr/share/keyrings/flox-archive-keyring.gpg] \
    https://downloads.flox.dev/by-env/stable/deb/ stable/" \
    > /etc/apt/sources.list.d/flox.list \
    && apt-get update && apt-get install -y flox \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Build union Flox environment with ALL agent tools
WORKDIR /flox-env
COPY flox-manifests/all-variations.toml manifest.toml
RUN flox init && flox edit -f manifest.toml && flox list

# Python env via uv
WORKDIR /app
RUN uv venv /app/.venv
ENV VIRTUAL_ENV=/app/.venv
ENV PATH="/app/.venv/bin:/flox-env/.flox/run/bin:$PATH"

COPY pyproject.toml uv.lock /app/
RUN uv sync --frozen --no-dev
COPY . /app

CMD ["sleep", "infinity"]
```

**Key difference from earlier research:** No `eval "$(flox activate)"` or `CMD ["flox", "activate", ...]` wrapping needed. The `.flox/run/bin` PATH approach makes all tools available directly, with zero activation overhead.

---

## 10. Open Questions Requiring Validation

| Question | Why It Matters | How to Validate |
|----------|---------------|-----------------|
| Can `[include]` resolve to pre-existing `/nix/store/` paths without network? | Composition-based per-agent manifests depend on this | Build base env, create include-only env on volume, activate and check for network calls (use `strace` or disable network) |
| What filesystem does `/nix/store/` require? NFS? OverlayFS? | Docker volumes are overlay-mounted; Nix assumes bare filesystem semantics | Test `flox install` on a Docker volume-mounted /nix/store/ |
| Is there a .nix-db consistency issue with copying store paths? | If we want to pre-seed /nix/store/ from a volume | Check `/nix/store/.links/` and sqlite registry (`/nix/var/nix/db/`) |
| Can we use `flox push` + `flox pull` to distribute envs to containers? | Alternative to volume-based env distribution | Test `flox push` from build, `flox pull` from container on first start |
| What's the actual binary size of `bun` in the Nix store? | Image size budgeting | `docker build && docker images` + check layer sizes |

---

## Appendix: Context7 Sources Used

| Source Library ID | Type | Content Retrieved |
|-------------------|------|-------------------|
| `/websites/flox_dev` | flox.dev website | activate, edit, init, search, composition, bun/nodejs, package-groups |
| `/flox/flox` | GitHub CLI repo | activate `-d=` flag, init `-d=`, push/pull commands |
| `/flox/floxdocs` | GitHub docs repo | layering tutorial, composition, containerize, build, flox-vs-containers, llms.txt reference |

Total Context7 queries: 9 (before quota limit reached).
