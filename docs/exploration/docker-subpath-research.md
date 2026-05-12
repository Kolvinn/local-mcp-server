# Docker Named Volume Subpath — Research Findings

**Date:** 2026-05-12  
**Source:** Docker official documentation via Context7 API (library IDs: `/docker/docs`, `/docker/compose`)  
**Research agent:** Explorer (codebase scout)

---

## 1. Subpath with External Volumes

**Question:** Can `subpath` be used with `external: true` named volumes in docker-compose?

**Finding:** Yes, `subpath` and `external: true` are **orthogonal concepts** and should be compatible. No documented restriction was found forbidding this combination.

- `subpath` is a property of the **mount specification** (how the volume is attached to the container), not the volume declaration.
- `external: true` is a property of the **volume declaration** (whether Docker Compose should auto-create the volume or expect it to exist).
- The long-syntax compose example at `content/reference/compose-file/services.md` shows `subpath` used on a named volume without `external`:

  ```yaml
  services:
    backend:
      image: example/backend
      volumes:
        - type: volume
          source: db-data
          target: /data
          volume:
            nocopy: true
            subpath: sub

  volumes:
    db-data:
  ```

  Adding `external: true` to `db-data` would simply tell Compose not to create it — the mount behavior (including subpath resolution) is unaffected.

**Limitations noted:**
- `subpath` is only available in the **long syntax** (`type: volume, ... volume: { subpath: ... }`). The short syntax (`source:target`) does not support it.
- The subpath must already exist in the volume (see §2).
- No explicit documentation was found that says "external volumes cannot use subpath" — this combination is **not called out as unsupported**.

---

## 2. Pre-creating Subpaths

**Question:** Must subpaths exist before a container mounts them? What happens if they don't?

**Finding:** The subpath **must already exist** in the volume. Docker does **not** auto-create it. If it does not exist, the **mount fails**.

**Official documentation, verbatim** (from `content/manuals/engine/storage/volumes.md`):

> *"The `volume-subpath` option allows mounting a specific subdirectory from within the volume into the container. The specified subdirectory must already exist in the volume before it is mounted."* — **Syntax > Options for --mount**

> *"When you mount a volume to a container, you can specify a subdirectory of the volume to use, with the `volume-subpath` parameter for the `--mount` flag. The subdirectory that you specify must exist in the volume before you attempt to mount it into a container; if it doesn't exist, the mount fails."* — **Mount a volume subdirectory**

**Canonical workflow** (from docs):

```console
# Step 1: Create the volume
$ docker volume create logs

# Step 2: Pre-create subdirectories inside the volume
$ docker run --rm \
  --mount src=logs,dst=/logs \
  alpine mkdir -p /logs/app1 /logs/app2

# Step 3: Mount specific subdirectories
$ docker run -d \
  --name=app1 \
  --mount src=logs,dst=/var/log/app1,volume-subpath=app1 \
  app1:latest
```

**Summary:** Docker does **NOT** auto-create subpaths. The user is responsible for creating them (typically via an init container or a one-shot `docker run`). If the subpath is missing at mount time, the container fails to start.

---

## 3. Same Volume, Multiple Mounts in One Container

**Question:** Is mounting the same named volume twice in one container — once read-only at `/app/project` and once read-write at `/app/project/subdir` with `subpath` — supported or undefined?

**Finding:** This is a **gray area** with little explicit documentation.

**What the docs say:**

- **Cross-container, same volume, different modes:** Explicitly supported.
  > *"Docker allows volumes to be mounted in either read-write or read-only mode depending on the application's requirements. Multiple containers can mount the same volume simultaneously, with the flexibility to assign different access levels to each container."* — **Use a read-only volume**

- **Multiple mounts of same volume name per container:** The volume plugin API docs indicate Docker calls `VolumeDriver.Mount` once per container start (not once per mount entry), and the plugin tracks mount requests by ID. This suggests a single mount at the kernel level, even if specified multiple times in the compose file.

- **Compose file merging:** When the **same mount path** appears in multiple compose files, the last one wins. Different mount paths are additive. This is about multi-file merge behavior, not same-volume-dual-mount.

**No explicit documentation was found** for the specific pattern:
```
volumes:
  - type: volume
    source: mydata
    target: /app/project
    read_only: true
  - type: volume
    source: mydata
    target: /app/project/subdir
    volume: { subpath: subdir }
    read_only: false
```

**Risks of this pattern:**
- **Mount order is undefined**: Docker does not guarantee the order in which volume mounts are processed. If the sub-mount is processed first, it could be shadowed by the parent mount.
- **Overlapping mount paths**: Mounting `/app/project` (non-subpath) on top of `/app/project/subdir` (subpath) creates a nested mount situation where kernel-level mount propagation may behave unpredictably.
- **Subpath constraint conflict**: The full-volume mount at `/app/project` makes the entire volume contents visible at that path. The subpath mount at `/app/project/subdir` is a narrower view. Depending on mount ordering, one may obscure the other.
- **No official "supported" or "unsupported" designation**: This pattern is not documented as either supported or denied — it lives in undefined territory.

**Recommendation:** This pattern is **likely unsupported and fragile**. A safer approach would be:
- Use two separate volumes if RW/RO separation by subdirectory is needed, or
- Mount the full volume RW and enforce RO at the application level, or
- Use a single mount and manage permissions inside the container via user namespaces.

---

## 4. Volume Inspection — Subpath Visibility

**Question:** Can `docker volume inspect` show subpath contents? Are there CLI/API commands for managing subpaths independently?

**Finding:** No. `docker volume inspect` shows only volume-level metadata. There is no Docker CLI or API for managing subpaths independently.

**`docker volume inspect` output** (from docs):
```json
[
    {
        "Driver": "local",
        "Labels": {},
        "Mountpoint": "/var/lib/docker/volumes/my-vol/_data",
        "Name": "my-vol",
        "Options": {},
        "Scope": "local"
    }
]
```

**What it shows:**
- `Name`, `Driver`, `Mountpoint` (host path), `Scope`, `Labels`, `Options`
- No subpath-level info, no contents listing, no file tree

**To inspect subpath contents, you have these options:**

1. **Browse the host filesystem** (requires root):
   ```bash
   sudo ls /var/lib/docker/volumes/my-vol/_data/subdir/
   ```

2. **Run a temporary container:**
   ```bash
   docker run --rm -v my-vol:/vol alpine ls /vol/subdir/
   ```

3. **Docker Desktop Volumes view** — lets you browse files and folders in volumes interactively (`content/manuals/desktop/use-desktop/volumes.md`).

4. **`docker compose volumes`** — lists volumes associated with a compose project, but only shows volume names, driver, and scope — not subpaths.

**No CLI or API command exists** for:
- Listing subpaths within a volume
- Creating/deleting subpaths atomically (outside of using a container to run `mkdir`/`rm`)
- Inspecting which mounts use which subpaths (beyond `docker inspect <container>` and reading the `Mounts` section)

---

## 5. Volume Lifecycle — `external: true` and `docker compose down`

**Question:** Does `docker compose down` touch external volumes? Does `docker compose down -v` delete them?

**Finding:** **External volumes are never removed by Docker Compose**, regardless of flags.

**Official docs, verbatim** (from `docker compose down` reference):

> *"By default, only containers and networks are removed. External networks and volumes are never removed."*

> *"Networks and volumes defined as external are never removed, ensuring that external resources persist across compose operations."* — **docker compose down > Overview**

**`-v` flag behavior:**
The `-v` flag is described as: *"Also remove named volumes declared in compose file."* (from the CLI reference).

However, "volumes declared in compose file" refers to **non-external** named volumes. The external qualifier explicitly exempts the volume from Compose lifecycle management.

| Command | Removes external volumes? |
|---|---|
| `docker compose down` | ❌ Never |
| `docker compose down -v` | ❌ Never (ignores external) |
| `docker compose down --volumes` | ❌ Never (same as -v) |
| `docker compose rm -v` | ❌ Only anonymous volumes |

**To remove an external volume, you must do so explicitly:**
```bash
docker volume rm <volume-name>
```

**API confirmation:** The Compose Go API's `DownOptions.Volumes` field (bool) controls removal of "named volumes" — the same docs for `docker compose down` confirm external volumes are excluded.

---

## Summary Table

| Question | Answer | Confidence |
|---|---|---|
| Subpath + external volumes | Compatible (orthogonal concepts) | High — no contradicting docs found |
| Must subpath exist? | Yes — mount fails if missing | High — explicitly documented |
| Same volume, dual mount in one container | Undefined / fragile | Medium — no explicit docs, risks identified |
| `docker volume inspect` shows subpaths? | No — metadata only | High — explicitly documented |
| CLI for subpath management? | None exists | High |
| `docker compose down` touches ext. volumes? | No | High — explicitly documented |
| `docker compose down -v` deletes ext. volumes? | No | High — explicitly documented |

---

## Sources

All documentation sourced from Docker's official docs repository (`github.com/docker/docs`) and Docker Compose repository (`github.com/docker/compose`) via Context7 API:

1. **Storage > Volumes** — `content/manuals/engine/storage/volumes.md`
   - Mount a volume subdirectory
   - Syntax > Options for --mount
   - Use a read-only volume
   - Inspect a Docker Volume
   - A volume's lifecycle

2. **Compose File Reference** — `content/reference/compose-file/services.md`
   - Long syntax volume mount with subpath example

3. **Compose CLI Reference** — `docs/reference/compose_down.md`
   - External volumes never removed
   - -v flag semantics

4. **Volume Plugin API** — `_vendor/github.com/docker/cli/docs/extend/plugins_volume.md`
   - VolumeDriver.Mount called once per container start

5. **Docker Desktop** — `content/manuals/desktop/use-desktop/volumes.md`
   - Volumes view browsing capability

**Note:** Context7 API quota was exhausted after ~10 queries; some additional detail may be in sections of the Docker docs not retrieved. The key findings above are sourced from verified documentation snippets.

---

## Key Takeaway

The most critical finding is **§2**: the subpath **must pre-exist** in the volume. This is the most common source of confusion. The second most important finding is **§5**: external volumes are completely exempt from Compose lifecycle management — even `-v` will not remove them.
