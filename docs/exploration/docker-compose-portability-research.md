# Docker Compose Portable Multi-Instance Research

**Date:** 2026-05-12  
**Source:** Docker Compose official documentation (context7 API) + Docker CLI docs  
**Scope:** Patterns for running multiple isolated stacks from a shared compose template

---

## 1. Project Name Isolation

### How `--project-name` / `-p` Isolates Stacks

Docker Compose assigns every stack a **project name** that acts as the isolation boundary. The precedence order (highest to lowest) is:

1. `--project-name` / `-p` CLI flag
2. `COMPOSE_PROJECT_NAME` environment variable
3. Top-level `name:` field in compose YAML
4. Basename of the project directory containing the config file
5. Basename of the current working directory (fallback)

**Project name constraints:** lowercase letters, digits, dashes, underscores only; must start with a letter or digit.

### What the Project Name Controls

The project name is used as a **prefix** for implicitly-named resources:
- **Containers:** Labeled with `com.docker.compose.project=<name>` for lifecycle management
- **Networks:** Implicit networks are named `{project_name}_default`, `{project_name}_<custom-name>`
- **Volumes:** Implicit named volumes are created as `{project_name}_<volume-name>` (e.g., `my-project_db_data`)

This means **two compose stacks with different project names but the same compose file get fully isolated networks and implicitly-named volumes** — no collision.

### Different External Volumes Per Project

If a compose file declares:

```yaml
volumes:
  data:
    external: true
    name: master_agent_data
```

Two stacks with different project names (`tenant-a`, `tenant-b`) using the **same exact file** will **both point to the same Docker volume** `master_agent_data` — because `external: true` + an explicit `name:` bypasses project-name prefixing. This is a collision.

**To use different external volumes per project**, parameterize the `name:` field with variable substitution:

```yaml
volumes:
  data:
    external: true
    name: ${PROJECT_NAME:-default}_agent_data
```

Then pass `PROJECT_NAME=tenant-a` via `.env` or environment. Each project gets its own volume.

### Separate Networks Per Project Automatically

**Yes — Docker Compose creates separate networks per project name automatically.** For implicit (non-external) networks, Compose prefixes the network name with the project name. Two `docker compose -p tenant-a up` and `docker compose -p tenant-b up` using the same compose file — even when neither specifies a `networks:` block — get:

- `tenant-a_default` network (bridge)
- `tenant-b_default` network (bridge)

Containers in `tenant-a` cannot reach containers in `tenant-b` by DNS name.

### What Stacks Share

If **external networks** are used (e.g., to place all stacks behind a shared reverse proxy like Traefik), the compose file would declare:

```yaml
networks:
  proxy:
    external: true
    name: traefik-shared
```

All stacks attaching to `traefik-shared` can communicate via that external bridge, while remaining isolated on their own project-specific networks for internal service-to-service traffic.

---

## 2. External Volume Namespacing

### Core Problem

External volumes are referenced **by their exact Docker volume name**. There is no automatic project-name prefixing for external volumes.

```yaml
volumes:
  agent_data:
    external: true
```

This resolves to a Docker volume literally named `agent_data`. Two stacks referencing the same `agent_data` external volume **share the same data** — they do not get separate copies.

### The Collision Case

```yaml
# compose.yml shared by tenant-a and tenant-b
volumes:
  agent_data:
    external: true
```

| Stack | Volume Resolved To | Isolated? |
|-------|-------------------|-----------|
| `tenant-a` | `agent_data` | No — same as tenant-b |
| `tenant-b` | `agent_data` | No — same as tenant-a |

### The Namespacing Pattern

**Use the `name:` field with variable interpolation to externalize per-project volumes:**

```yaml
volumes:
  agent_data:
    external: true
    name: ${COMPOSE_PROJECT_NAME:-default}_agent_data
```

Or, more explicitly:

```yaml
volumes:
  agent_data:
    external: true
    name: ${VOLUME_PREFIX:-default}_agent_data
```

Run with:

```bash
COMPOSE_PROJECT_NAME=tenant-a docker compose up -d
# Volume resolved: tenant-a_agent_data

COMPOSE_PROJECT_NAME=tenant-b docker compose up -d
# Volume resolved: tenant-b_agent_data
```

**Key insight:** When `external: true` is set **without** a `name:` field, Compose uses the logical volume name from the YAML key as-is (no prefixing). When `external` is **not** set (the default), Compose auto-prefixes with the project name. This means the safe default for multi-instance is: **omit `external: true`** and let Compose auto-name volumes with the project prefix.

### When to Use `external: true`

| Use Case | Pattern |
|----------|---------|
| **Per-project isolation** | Omit `external: true` — let Compose prefix with project name |
| **Shared data across stacks** | `external: true` + fixed `name:` |
| **Pre-created volumes per project** | `external: true` + parameterized `name:` with `${VAR}` |
| **Data seeded from backup** | `external: true` + `name:` pointing to restored/renamed volume |

---

## 3. Port Collision Avoidance

### The Problem

Running N identical stacks means all expose the same ports (e.g., `8000:8000`). The second stack fails because port `8000` on the host is already bound.

### Pattern A: Omit Host Ports (Internal-Only Communication)

If services only need to talk to each other (not to the host or external clients), **omit host port mappings entirely**:

```yaml
services:
  app:
    ports:
      - "8000"       # container port only — no host binding
```

Or remove the `ports:` block entirely. Containers can still reach each other by service name on the project's internal network. The `docker compose run` command follows this same principle — it does **not** map ports by default to avoid collisions, requiring `--service-ports` to opt in.

### Pattern B: Parameterized Host Ports

Use environment variable substitution in the compose file:

```yaml
services:
  app:
    ports:
      - "${HOST_PORT:-8000}:8000"
```

Each project provides a unique `HOST_PORT`:

```bash
# Stack 1
HOST_PORT=8000 docker compose -p tenant-a up -d

# Stack 2
HOST_PORT=8001 docker compose -p tenant-b up -d
```

### Pattern C: Dynamic Port Allocation

Set host port to empty (Docker picks a random free port):

```yaml
services:
  app:
    ports:
      - "8000"   # = :8000 — Docker assigns random host port
```

Retrieve the dynamically-assigned port with:

```bash
docker compose port app 8000
# Output: 0.0.0.0:32768
```

For scripting:

```bash
ACTUAL_PORT=$(docker compose port app 8000 | cut -d: -f2)
```

### Pattern D: Shared Reverse Proxy (Recommended for Multi-Instance)

Use a single Traefik/nginx reverse proxy as the **only** service with host port bindings. All application stacks attach to a shared external network but expose **zero host ports**:

```yaml
# Each tenant stack
services:
  app:
    # No ports: block at all
    networks:
      - internal    # project-local network for inter-service
      - proxy       # shared external network for reverse proxy
    labels:
      - "traefik.http.routers.app.rule=Host(`${TENANT}.example.com`)"

networks:
  proxy:
    external: true
    name: traefik-shared
```

The reverse proxy stack:

```yaml
services:
  traefik:
    ports:
      - "80:80"
      - "443:443"
    networks:
      - traefik-shared
```

### Summary of Port Patterns

| Pattern | Host Port Collision? | External Access | Complexity |
|---------|---------------------|-----------------|------------|
| Omit host ports | No | No (internal only) | Simple |
| Parameterized `${HOST_PORT}` | Manual coordination | Yes | Medium |
| Dynamic `:8000` (no host port) | No (Docker picks) | Yes (random port) | Medium |
| Shared reverse proxy | No (single entry point) | Yes (routed by hostname) | Complex but scalable |

---

## 4. Compose File Generation Patterns

### Pattern A: Environment Variable Substitution (Recommended)

**Single template compose file**, values injected at runtime:

```yaml
services:
  app:
    image: myapp:${TAG:-latest}
    ports:
      - "${HOST_PORT:-8000}:8000"
    environment:
      - DB_NAME=${PROJECT_NAME:-default}_db
    volumes:
      - data:/var/lib/data

volumes:
  data:
    name: ${PROJECT_NAME:-default}_data
```

Per-project `.env` file:

```bash
# .env.tenant-a
PROJECT_NAME=tenant-a
HOST_PORT=8000
TAG=v1.0
```

```bash
# .env.tenant-b
PROJECT_NAME=tenant-b
HOST_PORT=8001
TAG=v1.0
```

Invocation:

```bash
docker compose --env-file .env.tenant-a -p tenant-a up -d
docker compose --env-file .env.tenant-b -p tenant-b up -d
```

### Pattern B: Multiple Override Files (`-f`)

Base + overrides:

```yaml
# compose.base.yml — shared by all projects
services:
  app:
    image: myapp:latest
    ports:
      - "8000"
    volumes:
      - data:/var/lib/data

volumes:
  data:
```

```yaml
# compose.tenant-a.yml — overrides for tenant-a
services:
  app:
    ports:
      - "8000:8000"   # override base definition

volumes:
  data:
    name: tenant-a_data
```

```bash
docker compose -f compose.base.yml -f compose.tenant-a.yml -p tenant-a up -d
```

### Pattern C: Fully Generated Compose Files

A script/CLI generates per-project compose files from a template:

```bash
#!/bin/bash
# generate-compose.sh
PROJECT_NAME=$1
HOST_PORT=$2
TAG=${3:-latest}

sed -e "s/\${PROJECT_NAME}/${PROJECT_NAME}/g" \
    -e "s/\${HOST_PORT}/${HOST_PORT}/g" \
    -e "s/\${TAG}/${TAG}/g" \
    compose.template.yml > "compose.${PROJECT_NAME}.yml"
```

### Pattern D: `COMPOSE_FILE` Environment Variable

```bash
export COMPOSE_FILE=compose.base.yml:compose.override.yml
export COMPOSE_PROJECT_NAME=tenant-a
docker compose up -d
```

### Recommendation

| Approach | Best For |
|----------|----------|
| **Env substitution** (A) | Most projects — single file, no code generation |
| **Override files** (B) | When overrides are complex or per-tenant configs are large |
| **Generated files** (C) | When tenants need fundamentally different topologies |
| **COMPOSE_FILE** (D) | Development workflows, CI/CD pipelines |

**Verdict:** Variable substitution (Pattern A) with per-project `.env` files is the recommended approach for portable multi-instance Docker Compose. It requires zero code generation, is debuggable (`docker compose config` shows the resolved file), and composes naturally with `--project-name`.

---

## 5. Network Isolation

### Default Behavior: Project-Prefixed Network Names

When a compose file declares a network **without** `external: true`, Compose creates it with the project name as a prefix:

```yaml
networks:
  backend:
    driver: bridge
```

| Project | Created Network | Container DNS Scope |
|---------|----------------|-------------------|
| `tenant-a` | `tenant-a_backend` | Services see each other as `app.tenant-a_backend` |
| `tenant-b` | `tenant-b_backend` | Services see each other as `app.tenant-b_backend` |

These are **fully isolated** — no cross-project DNS resolution or connectivity.

### Explicit Network Name Breaks Isolation

```yaml
networks:
  backend:
    name: my-shared-network
    driver: bridge
```

Now both projects create/use the same `my-shared-network` bridge — **no isolation**.

### External Shared Networks

When stacks **intentionally** share a network (e.g., reverse proxy):

```yaml
networks:
  proxy:
    external: true
    name: traefik-shared
```

- All stacks on this network **can** communicate
- Used for cross-stack concerns (routing, monitoring, logging)
- Does not affect project-internal networks — stack A's `backend` is still isolated from stack B's `backend`

### Default Network Isolation

Even without explicit network config, Compose creates a `{project_name}_default` network. Two projects with the same compose file (no `networks:` section) are **completely isolated at the network layer**.

### Two-Network Pattern for Multi-Instance

Recommended: each stack has one internal (project-scoped) network and attaches to one shared (external) network:

```yaml
services:
  app:
    networks:
      - internal    # project-local, auto-isolated
      - proxy       # shared external for routing

networks:
  internal:
    driver: bridge
  proxy:
    external: true
    name: traefik-shared
```

This gives:
- **Isolation:** `tenant-a_internal` vs `tenant-b_internal` — no cross-talk
- **Routing:** Both on `traefik-shared` — reverse proxy can reach them

---

## 6. Volume Data Portability

### Can You Back Up and Restore Across Projects?

**Yes.** Named Docker volumes are independent of compose project names. A volume created by `tenant-a` is just a Docker volume — it can be mounted into `tenant-b` or any other stack.

### Backup Pattern

```bash
# Create a backup from the source volume
docker run --rm \
  -v tenant-a_agent_data:/source \
  -v $(pwd)/backups:/backup \
  alpine \
  tar -czf /backup/tenant-a_agent_data-2026-05-12.tar.gz \
    -C /source .
```

### Restore Pattern

```bash
# Restore into the destination volume
docker run --rm \
  -v tenant-b_agent_data:/destination \
  -v $(pwd)/backups:/backup \
  alpine \
  tar -xzf /backup/tenant-a_agent_data-2026-05-12.tar.gz \
    -C /destination
```

### Cross-Project Migration

```bash
# 1. Create the target volume if it doesn't exist
docker volume create tenant-b_agent_data

# 2. Copy directly from source to target (no intermediary tar file)
docker run --rm \
  -v tenant-a_agent_data:/from \
  -v tenant-b_agent_data:/to \
  alpine \
  sh -c "cp -a /from/. /to/"
```

### Key Commands Reference

| Command | Purpose |
|---------|---------|
| `docker volume create <name>` | Create a named volume explicitly |
| `docker volume ls` | List all volumes |
| `docker volume inspect <name>` | Show volume metadata and mountpoint |
| `docker volume rm <name>` | Remove a volume |
| `docker run --rm -v <vol>:/data ...` | Mount volume for backup/restore |
| `tar -czf /backup/out.tar.gz -C /source .` | Compress volume contents |
| `tar -xzf /backup/in.tar.gz -C /dest` | Extract into volume |
| `docker compose volumes --format json` | List volumes for current project |

### Volume Name Resolution

When restoring across projects, ensure the target volume name matches what the project expects:

```bash
# See what the project will create/resolve
docker compose config --volumes
```

If using `external: true` with parameterized names, the target volume must be pre-created with the correct name:

```bash
docker volume create tenant-b_agent_data
# Then run: docker compose -p tenant-b up -d
# The external volume tenant-b_agent_data is ready
```

---

## 7. Resource Constraints

### Compose Syntax

```yaml
services:
  app:
    deploy:
      resources:
        limits:
          cpus: '0.50'
          memory: 512M
        reservations:
          cpus: '0.25'
          memory: 256M
```

### Swarm Mode vs. Compose Standalone

| Runtime | Behavior |
|---------|----------|
| **Swarm mode** | `deploy.resources.limits` **enforced** — container is throttled/killed if exceeded |
| **Compose standalone** | `deploy.resources` is **ignored** by default |
| **Compose + `COMPOSE_COMPATIBILITY=true`** | Respects `deploy.resources` in standalone mode |

### Standalone-Compose Direct Equivalents

For non-swarm setups, use top-level resource fields (which work in standalone):

```yaml
services:
  app:
    mem_limit: 512m
    mem_reservation: 256m
    cpus: '0.50'
    cpuset: 0-1  # pin to specific CPUs
```

### Enforcement vs. Reservation

| Directive | Type | Docker Behavior |
|-----------|------|-----------------|
| `memory` (limits) | Hard limit | **Enforced** — container gets OOM-killed if exceeded |
| `memory` (reservations) | Soft request | **Best-effort** — guaranteed when available, container can use more if idle |
| `cpus` (limits) | Hard cap | **Enforced** — CPU throttled to this ceiling |
| `cpus` (reservations) | Soft request | **Best-effort** — scheduler preference, not enforced |

### Multi-Instance Considerations

- **No cross-stack conflicts on enforcement.** Each container's cgroup is independent. Stack A's limits don't interact with stack B's limits — Docker's kernel-level cgroups enforce per-container.
- **Reservations ensure availability**, not isolation. If total reservations exceed host capacity, new containers may fail to start.
- **Memory limits are absolute.** Two stacks each with `memory: 1G` on a 2GB host will compete — both may be OOM-killed under load. Plan total capacity: `total_limit <= host_memory - overhead`.
- **CPU limits are relative to total CPU cores.** `cpus: '0.50'` means 50% of one core. Two stacks each at `0.50` on a single-core host will share the core 50/50 when both busy.

### Practical Multi-Instance Resource Strategy

```yaml
services:
  app:
    deploy:
      resources:
        limits:
          memory: ${MEM_LIMIT:-512M}
        reservations:
          memory: ${MEM_RESERVATION:-256M}
```

For N instances on a host:

```bash
# Calculate per-instance limits
TOTAL_RAM_GB=8
INSTANCE_COUNT=4
PER_INSTANCE_MB=$((TOTAL_RAM_GB * 1024 / INSTANCE_COUNT))

docker compose -p tenant-a up -d -e MEM_LIMIT=${PER_INSTANCE_MB}M
```

---

## Synthesis: Recommended Multi-Instance Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                        Host Machine                              │
│                                                                  │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐        │
│  │  tenant-a    │    │  tenant-b    │    │  tenant-c    │        │
│  │              │    │              │    │              │        │
│  │ app  db      │    │ app  db      │    │ app  db      │        │
│  │  │    │      │    │  │    │      │    │  │    │      │        │
│  │  └─┬──┘      │    │  └─┬──┘      │    │  └─┬──┘      │        │
│  │  a_int  net  │    │  b_int  net  │    │  c_int  net  │        │
│  └─────┬────────┘    └─────┬────────┘    └─────┬────────┘        │
│        │                   │                   │                  │
│        └──────────┬────────┴─────────┬─────────┘                  │
│                   │                  │                            │
│           ┌───────▼──────────────────▼───────┐                    │
│           │     traefik-shared (external)     │                    │
│           │         :80 :443                 │                    │
│           └───────────────┬───────────────────┘                    │
│                           │                                        │
└───────────────────────────┼────────────────────────────────────────┘
                            │
                     🌐 Internet
```

### Design Principles

1. **One compose template, N `.env` files** — no code generation, fully debuggable with `docker compose config`
2. **No host port bindings in app stacks** — single reverse proxy handles ingress
3. **Omit `external: true` on volumes** — let Compose auto-prefix with project name for isolation
4. **Two networks per stack** — one project-internal (auto-isolated), one shared (for routing)
5. **Parameterize everything** — ports, volume names, labels, environment variables
6. **Resource budgets calculated upfront** — `MEM_LIMIT`, `CPU_LIMIT` per stack, ensure `N * limit <= host_capacity`

### Startup Sequence

```bash
# Create shared resources
docker network create traefik-shared

# Deploy reverse proxy
docker compose -f compose.traefik.yml -p traefik up -d

# Deploy N tenant stacks
for i in 0 1 2 3; do
  PROJECT="tenant-${i}"
  PORT=$((8080 + i))
  docker compose \
    --env-file ".env.${PROJECT}" \
    -p "${PROJECT}" \
    up -d
done
```

### Shutdown Sequence

```bash
# Tear down all tenant stacks
for i in 0 1 2 3; do
  docker compose -p "tenant-${i}" down
done

# Tear down shared infrastructure (after verifying no tenants remain)
docker compose -f compose.traefik.yml -p traefik down
docker network rm traefik-shared
```

---

## Sources

- Docker Compose CLI Reference (`compose.md`): project name precedence, `-f` flag, environment variables
- Docker Compose Volumes Reference (`compose_volumes.md`): volume naming pattern `{project}_{name}`
- Docker Compose Run Reference (`compose_run.md`): default port avoidance for collision prevention
- Docker Compose Down Reference (`compose_down.md`): external resources never removed
- Docker Compose Extension docs: project name tagging for resource lifecycle
- Docker Compose SDK/Create: `deploy.resources.limits` and `deploy.resources.reservations` struct handling
