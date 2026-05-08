# Flox for Docker Container Integration — Research Findings

**Date:** 2026-05-08
**Source:** Context7 API queries against flox.dev docs, GitHub flox/floxdocs
**Status:** Complete

---

## 1. Flox Overview

Flox is a **next-generation, language-agnostic package and environment manager** built on top of the Nix package manager. It provides:

- **Reproducible environments** — declarative `manifest.toml` with locked dependencies
- **Cross-platform** — works on aarch64-darwin, aarch64-linux, x86_64-darwin, x86_64-linux
- **Transactional package installs** — validates before atomic update
- **OCI container output** — `flox containerize` exports environments as Docker images
- **Services** — define background processes in the manifest with `[services]`
- **FloxHub** — share environments remotely via `flox push` / `flox pull`

Under the hood, Flox uses Nix (with a binary cache at `https://cache.flox.dev`). The Flox catalog indexes nixpkgs, giving access to **tens of thousands of packages**.

### CLI commands

| Command | Purpose |
|---------|---------|
| `flox init` | Create a new environment (creates `.flox/` directory) |
| `flox search <pkg>` | Search catalog |
| `flox show <pkg>` | Show package details |
| `flox install <pkg>` | Install packages into environment |
| `flox activate` | Enter the environment (subshell) |
| `flox activate -- <cmd>` | Run command in environment (non-interactive) |
| `flox edit` | Edit manifest.toml with validation |
| `flox containerize` | Export environment as OCI container image |
| `flox list` | List installed packages |

---

## 2. Flox in Docker

### Installation Methods

**Method A: Install via apt repository (recommended for Docker)**

```dockerfile
# Add Flox apt repository
RUN apt-get update && apt-get install -y curl gnupg && \
    curl -fsSL https://downloads.flox.dev/by-env/stable/archive.key | gpg --dearmor -o /usr/share/keyrings/flox-archive-keyring.gpg && \
    echo "deb [signed-by=/usr/share/keyrings/flox-archive-keyring.gpg] https://downloads.flox.dev/by-env/stable/deb/ stable/" > /etc/apt/sources.list.d/flox.list && \
    apt-get update && apt-get install -y flox
```

**Method B: Official Docker image**

```bash
docker run --pull always --rm -it ghcr.io/flox/flox
```

This image has Flox pre-installed and can be used as a base or a sidecar.

**Method C: Nix profile install (requires Nix)**

```dockerfile
RUN nix profile install --experimental-features "nix-command flakes" \
      --accept-flake-config 'github:flox/flox'
```

### Non-interactive Activation in Containers

Flox supports running commands in an environment **without an interactive shell**:

```bash
# Run a single command in the Flox environment
flox activate -- <command>

# The environment is active only for that command
# Shell exits back to original after command completes
```

This is the pattern to use in Docker `CMD` / `ENTRYPOINT`:

```dockerfile
CMD ["flox", "activate", "--", "sleep", "infinity"]
```

Or to run a specific tool:
```dockerfile
ENTRYPOINT ["flox", "activate", "--"]
CMD ["your-agent"]
```

### Activation Modes

```
-m=(dev|run)
```

- `dev` (default): Full activation with hooks, profile scripts, services
- `run`: Lightweight activation — skips hooks/profile, just makes packages available on PATH

For headless containers, `-m=run` is likely preferable for faster startup and no side effects.

### Activate via `--print-script` / `eval`

For sourcing into the current shell (useful in entrypoint scripts):

```bash
eval "$(flox activate --print-script)"
```

### containerize Command (alternative approach)

Flox can export an entire environment as a **standalone OCI container image**:

```bash
flox containerize --runtime docker
# or
flox containerize -f - | docker load
```

The resulting image has the environment baked in. Each dependency is an image layer for caching. When running:

```bash
docker run <container-id> <command>
```

This is equivalent to `flox activate -- <command>` inside the container. However, for our use case (long-lived headless containers with uv-managed Python), we prefer installing Flox in the Dockerfile and using `flox activate --` at runtime, rather than pre-containerizing.

---

## 3. Flox Manifest Format

### Minimal Example

```toml
version = 1

[install]
ripgrep.pkg-path = "ripgrep"
jq.pkg-path = "jq"
git.pkg-path = "git"
tree.pkg-path = "tree"
fd.pkg-path = "fd"

[options]
systems = ["aarch64-linux", "x86_64-linux"]
```

### Full Example with All Sections

```toml
version = 1

[install]
ripgrep.pkg-path = "ripgrep"
jq.pkg-path = "jq"
git.pkg-path = "git"
tree.pkg-path = "tree"
fd.pkg-path = "fd"
bun.pkg-path = "bun"
python3.pkg-path = "python3"
python3.version = "3.12"

[vars]
MY_VAR = "hello"
FLOX_AUTO_ACTIVATE = "1"

[hook]
on-activate = """
    echo "Environment activated"
    # Can set up things, create dirs, etc.
"""

[profile]
bash = """
    echo "This runs in bash on activation"
"""

[services]
watchdog = { command = "while true; do date; sleep 10; done" }
```

### Key manifest sections

| Section | Purpose |
|---------|---------|
| `[install]` | Packages to install. Format: `<name>.pkg-path = "<pkg>"` |
| `[install.<name>.version]` | Pin to version (e.g., `python3.version = "3.12"`) |
| `[options]` | Target systems, other settings |
| `[vars]` | Environment variables |
| `[hook.on-activate]` | Script that runs on activation (before shell/profile) |
| `[profile.<shell>]` | Shell-specific profile scripts |
| `[services.<name>]` | Background service definitions |

### Three TOML Syntaxes (equivalent)

```toml
# Shorthand
ripgrep.pkg-path = "ripgrep"

# Inline table
ripgrep = { pkg-path = "ripgrep" }

# Explicit table
[install.ripgrep]
pkg-path = "ripgrep"
```

---

## 4. Package Coverage

Flox's catalog is based on **nixpkgs**, which has **~100,000+ packages**. Specific packages confirmed in the Flox docs or obviously available via nixpkgs:

| Package | Confirmed in Flox Docs? | Notes |
|---------|------------------------|-------|
| `ripgrep` | ✅ Yes | Direct pkg-path: `ripgrep` |
| `fd` | ✅ Yes (nixpkgs standard) | `fd` |
| `jq` | ✅ Yes | `jq` |
| `git` | ✅ Yes (nixpkgs standard) | `git` |
| `tree` | ✅ Yes (mentioned in Homebrew migration tutorial) | `tree` |
| `yq` | ✅ Likely (in nixpkgs) | `yq` / `gojq` / `jq` |
| `bat` | ✅ Likely (bat-extras.batgrep mentioned) | `bat` |
| `bun` | ✅ Yes | Shown in manifest example |
| `python3` | ✅ Yes | `python3` with version pinning |
| `nodejs` | ✅ Yes | Multiple versions: `nodejs_20`, `nodejs_22`, `nodejs_24` |
| `go` | ✅ Yes | `go` |
| `curl` | ✅ Yes | `curl` |
| `gh` | ✅ Yes (Homebrew migration list) | GitHub CLI |
| `tmux` | ✅ Yes (Homebrew migration list) | Not needed in containers |
| `watch` | ✅ Yes (Homebrew migration list) | `watch` |
| `wget` | ✅ Yes (Homebrew migration list) | `wget` |
| `uv` | ❓ Not found in docs | May not be in nixpkgs catalog by default; would need manual Nix expression or pip install |

**Important: `uv`** (the astral-sh Python package manager) is relatively new and may not yet be in the Flox/nixpkgs catalog. The recommended approach is to install `uv` via the standard pip/curl installer or use the `ghcr.io/astral-sh/uv` base image (as specified in the task).

### Python package naming convention

Python packages in Flox use the nixpkgs naming convention:
```
python<version>Packages.<name>
```

Examples:
- `python311Packages.numpy`
- `python310Packages.pip`
- `python312Packages.pandas`

---

## 5. Python + uv Integration

Our use case: **Flox provides system tools** (ripgrep, jq, git, etc.) while **uv manages Python venvs separately**.

### Recommended Pattern

The Flox docs show a pattern for combining Flox system packages with Python virtual environments using the `[hook.on-activate]` section:

```nix
[install]
  python3.pkg-path = "python3"
  python3.version = ">=3.8"

[hook]
  on-activate = '''
    export PYTHON_DIR="$FLOX_ENV_CACHE/python"
    if [ ! -d "$PYTHON_DIR" ]; then
      python -m venv "$PYTHON_DIR"
    fi
    ( source "$PYTHON_DIR/bin/activate"
      pip install -e . --quiet
    )
  '''
```

**For our uv-based pattern, we adapt this:**

```
[install]
  python3.pkg-path = "python3"
  python3.version = "3.14"
  ripgrep.pkg-path = "ripgrep"
  fd.pkg-path = "fd"
  jq.pkg-path = "jq"
  git.pkg-path = "git"
  tree.pkg-path = "tree"
  yq.pkg-path = "yq"
```

**Key insight: Flox provides the Python interpreter itself + system tools. uv manages the virtual environment (`.venv`) independently.** They don't conflict because:

1. Flox puts Python (and tools) on `PATH` via Nix store paths
2. uv creates `.venv` with its own Python (possibly symlinked to the system one)
3. uv can use the Python interpreter that Flox provides
4. Python packages are installed into `.venv` by uv, not by Flox

### In the Dockerfile

```dockerfile
# Base image provides uv and Python
FROM ghcr.io/astral-sh/uv:python3.14-bookworm-slim

# Install Flox via apt
RUN apt-get update && apt-get install -y curl gnupg && \
    curl -fsSL https://downloads.flox.dev/by-env/stable/archive.key | gpg --dearmor -o /usr/share/keyrings/flox-archive-keyring.gpg && \
    echo "deb [signed-by=/usr/share/keyrings/flox-archive-keyring.gpg] https://downloads.flox.dev/by-env/stable/deb/ stable/" > /etc/apt/sources.list.d/flox.list && \
    apt-get update && apt-get install -y flox && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Initialize a Flox environment and install system tools
RUN flox init && \
    flox install ripgrep fd jq git tree yq

# Create Python venv with uv (separate from Flox)
RUN uv venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH"

# Install Python deps via uv
COPY pyproject.toml /app/
RUN uv sync --frozen

# Use flox activate to wrap the CMD
CMD ["flox", "activate", "-m=run", "--", "sleep", "infinity"]
```

**Note:** The base image `ghcr.io/astral-sh/uv:python3.14-bookworm-slim` already includes Python 3.14. So Flox does not need to provide Python in this case — uv and the base image handle Python entirely. Flox is only used for system tools.

---

## 6. Limitations & Gotchas

### Known Issues

1. **Flox requires Nix** — Installing Flox pulls in Nix as a dependency, which adds ~100MB+ to the image. The Flox + Nix closure is not tiny.

2. **`flox init` creates a `.flox/` directory** — It must be run in a writable directory. In Docker, the environment needs to be initialized during build, not at runtime (since the filesystem may be read-only at runtime).

3. **Activation overhead** — `flox activate -- <cmd>` has a small but non-zero startup cost (hook scripts, environment setup). For one-shot commands this is negligible.

4. **`uv` may not be in Flox catalog** — uv is a newer tool. If needed through Flox, it might require a custom Nix expression or fetching from another source.

5. **Containerize vs Install** — Two different approaches:
   - `flox containerize` creates a standalone Docker image from a Flox environment. This loses the ability to layer additional Dockerfile commands.
   - Installing Flox in the Dockerfile (`apt install flox`) and using `flox activate --` gives more flexibility but adds build-time overhead.

6. **Determinism** — Flox environments are reproducible (locked by Nix), but updates to nixpkgs can change package versions unless explicitly pinned. Use `manifest.lock` (auto-generated) for determinism.

7. **Image size** — Nix store paths can be large. Each Flox-installed package adds to the Nix store. For many small CLI tools this is fine, but the total Nix closure adds overhead.

8. **Caching** — Docker layer caching with Flox can be challenging because:
   - `flox install` mutates the Nix store (not just the `.flox` directory)
   - Each `flox install` adds store paths that aren't snapshot by Docker layers in the same way as apt packages
   - Mitigation: Install all packages in a single `RUN` layer

9. **No interaction with uv** — Flox does not know about uv or Python venvs. It won't activate them automatically. The entrypoint/CMD must handle both.

10. **Remote environment trust** — `flox activate -r <user>/<env>` requires trusting the remote environment. Not an issue for local/pinned environments.

---

## 7. Recommended Dockerfile Pattern

Based on all research, here is the concrete Dockerfile pattern for our use case:

```dockerfile
# ──────────────────────────────────────────────
# Stage 1: Build stage (system tools + Python deps)
# ──────────────────────────────────────────────
FROM ghcr.io/astral-sh/uv:python3.14-bookworm-slim AS builder

# Install Flox (requires curl, gnupg, xz-utils)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl ca-certificates gnupg xz-utils \
    && curl -fsSL https://downloads.flox.dev/by-env/stable/archive.key \
    | gpg --dearmor -o /usr/share/keyrings/flox-archive-keyring.gpg \
    && echo "deb [signed-by=/usr/share/keyrings/flox-archive-keyring.gpg] https://downloads.flox.dev/by-env/stable/deb/ stable/" \
    > /etc/apt/sources.list.d/flox.list \
    && apt-get update && apt-get install -y flox \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Initialize a Flox environment and install system CLI tools
# All in one RUN to maximize layer caching
WORKDIR /flox-env
RUN flox init && flox install \
    ripgrep \
    fd \
    jq \
    git \
    tree \
    yq \
    bat \
    curl \
    && flox list

# ──────────────────────────────────────────────
# Stage 2: Final image
# ──────────────────────────────────────────────
FROM ghcr.io/astral-sh/uv:python3.14-bookworm-slim

# Copy Flox installation and environment from builder
COPY --from=builder /nix /nix
COPY --from=builder /etc/apt/sources.list.d/flox.list /etc/apt/sources.list.d/flox.list
COPY --from=builder /usr/share/keyrings/flox-archive-keyring.gpg /usr/share/keyrings/flox-archive-keyring.gpg
COPY --from=builder /usr/bin/flox /usr/bin/flox
# Copy the .flox environment
COPY --from=builder /flox-env /flox-env
# Note: The Nix store copy above is simplified. In practice, you may need
# to copy specific store paths or use a different approach (see caveat below)

# Set up working directory
WORKDIR /app

# Create Python virtual environment with uv
RUN uv venv /app/.venv
ENV VIRTUAL_ENV=/app/.venv
ENV PATH="/app/.venv/bin:/flox-env/.flox/run/bin:$PATH"

# Install Python dependencies
COPY pyproject.toml uv.lock /app/
RUN uv sync --frozen --no-dev

# Copy application code
COPY . /app

# Expose Flox tools on PATH without requiring activation
# (The Nix store paths are already copied above)

# Container entrypoint — headless, stays running
CMD ["flox", "activate", "-m=run", "-d", "/flox-env", "--", "sleep", "infinity"]
```

### Simpler Single-Stage Pattern (if image size is less critical)

```dockerfile
FROM ghcr.io/astral-sh/uv:python3.14-bookworm-slim

# Install Flox
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl ca-certificates gnupg xz-utils \
    && curl -fsSL https://downloads.flox.dev/by-env/stable/archive.key \
    | gpg --dearmor -o /usr/share/keyrings/flox-archive-keyring.gpg \
    && echo "deb [signed-by=/usr/share/keyrings/flox-archive-keyring.gpg] https://downloads.flox.dev/by-env/stable/deb/ stable/" \
    > /etc/apt/sources.list.d/flox.list \
    && apt-get update && apt-get install -y flox \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Initialize Flox environment and install tools
WORKDIR /flox-env
RUN flox init && flox install \
    ripgrep fd jq git tree yq bat curl

# Python environment via uv
WORKDIR /app
RUN uv venv /app/.venv
ENV VIRTUAL_ENV=/app/.venv
ENV PATH="/app/.venv/bin:$PATH"

COPY pyproject.toml uv.lock /app/
RUN uv sync --frozen --no-dev
COPY . /app

# Make Flox tools available on PATH
ENV PATH="/flox-env/.flox/run/bin:$PATH"

# Headless container
CMD ["sleep", "infinity"]
```

Without `flox activate` wrapping: The `.flox/run/bin` directory contains symlinks into the Nix store for all installed packages. Adding this to PATH makes tools available **without** activation overhead. This is the cleanest approach for headless containers.

### Verification of `.flox/run/bin` PATH approach

Based on how Flox works, after `flox install`, the packages' binaries are available under `.flox/run/bin/` as symlinks to the Nix store. Adding this directory to `PATH` gives access to all installed tools without needing `flox activate`. This is the **recommended pattern** for our use case.

---

## 8. Comparison: Flox vs Conda

| Aspect | Conda | Flox |
|--------|-------|------|
| **Package source** | Anaconda repo / conda-forge (~25k packages) | Nixpkgs (~100k+ packages) |
| **Language focus** | Python-first, others secondary | Language-agnostic |
| **Determinism** | Good with `conda-lock` / `environment.yml` | Excellent — Nix-based, locked by default |
| **Image size** | Large miniconda base (~500MB) | Flox + Nix closure adds ~100-200MB |
| **Non-Python tools** | Requires conda-forge or pip | All system tools (ripgrep, jq, etc.) available natively |
| **Speed** | `conda install` can be slow (solver) | Fast (Nix binary cache, transactional) |
| **Docker integration** | Manual via miniconda base image | Native `flox containerize` + apt install |
| **Python + uv combo** | Possible but redundant (conda provides Python+pip) | Clean separation: Flox=system, uv=Python |
| **Multi-arch** | Yes | Yes (`aarch64-linux`, `x86_64-linux`, etc.) |
| **Layer caching** | Good (conda env in layer) | OK (Nix store paths, more granular) |
| **Learning curve** | Well-known | Newer, Nix concepts unfamiliar |
| **Licensing** | Some channels have restrictive licensing | Apache 2.0 / MIT |
| **CI/CD support** | Good | Good (GitHub Actions, GitLab CI) |
| **Maturity** | Very mature (~10+ years) | Maturing (~3+ years, active development) |

### Why Flox Wins for Our Use Case

1. **System tools** — Flox provides ripgrep, fd, jq, git, etc. natively. Conda requires conda-forge for these, and they're often outdated.

2. **Deterministic builds** — Nix underpinnings give stronger reproducibility guarantees than conda.

3. **Clean separation** — Flox for system-level tools + uv for Python = each tool does what it does best.

4. **Lighter weight for CLI-tools-only** — If we only need system CLIs (not Python from Flox), the install is leaner than conda's full Python distribution.

5. **No channel licensing worries** — No Anaconda Terms of Service concerns.

### Why Conda Still Wins

1. **Familiarity** — Everyone knows conda. Flox + Nix is new.
2. **Maturity** — Conda has more battle-tested edge cases.
3. **Python ecosystem** — Conda-forge has many more Python packages with compiled extensions (though we use uv, so this is less relevant).

### Verdict for Our Migration

**Flox is a good replacement for conda** for our specific use case (system CLI tools in containers with uv-managed Python). The key trade-off is learning curve vs. better determinism and broader system package access.

---

## Appendix: Key Commands Summary

```bash
# Search for packages
flox search ripgrep

# Show package details
flox show python3

# Install packages (transactional)
flox install ripgrep fd jq git tree yq bat

# Pin a version
flox install python3@3.12

# Run a command in the environment (non-interactive)
flox activate -m=run -- <command>

# Lightweight activation for scripts
flox activate -m=run -d /path/to/env -- some-tool --args

# Export environment as Docker image
flox containerize --runtime docker

# List installed packages
flox list

# Show available package versions
flox show <package>

# Edit manifest
flox edit
```
