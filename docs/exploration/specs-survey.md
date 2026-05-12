# Specs Survey

**Generated:** 2026-05-12
**Scope:** All `.md` files under `docs/specs/`
**Total files:** 18

---

## Summary Table

| # | File | Category | Lines | Action |
|---|------|----------|-------|--------|
| 1 | `bootstrap-system-00-pre-read.md` | PARTIALLY_RELEVANT | 176 | KEEP |
| 2 | `bootstrap-system-01-overview.md` | ACTIVE | 123 | KEEP |
| 3 | `bootstrap-system-02-schema.md` | ACTIVE | 295 | KEEP |
| 4 | `bootstrap-system-03-bootstrap.md` | ACTIVE | 670 | KEEP |
| 5 | `bootstrap-system-04-entrypoint.md` | ACTIVE | 397 | KEEP |
| 6 | `bootstrap-system-05-skills.md` | ACTIVE | 343 | KEEP |
| 7 | `memory-manager-langgraph.md` | ACTIVE | 456 | KEEP |
| 8 | `topology-plan:overview.md` | SUPERSEDED | 12 | DELETE |
| 9 | `topology-plan:volume.md` | SUPERSEDED | 57 | DELETE |
| 10 | `topology-plan:docker-flox.md` | SUPERSEDED | 305 | DELETE |
| 11 | `topology-plan:context-injection.md` | SUPERSEDED | 676 | DELETE |
| 12 | `changes.md` | SCRATCH | 7 | DELETE |
| 13 | `container-volume-topology:overview copy 2.md` | DRAFT_COPY | 1050 | DELETE |
| 14 | `container-volume-topology:overview copy 3.md` | DRAFT_COPY | 1050 | DELETE |
| 15 | `container-volume-topology:overview copy 4.md` | DRAFT_COPY | 1050 | DELETE |
| 16 | `container-volume-topology:overview copy 5.md` | DRAFT_COPY | 1050 | DELETE |
| 17 | `container-volume-topology:overview copy 6.md` | DRAFT_COPY | 1050 | DELETE |
| 18 | `container-volume-topology:overview copy 7.md` | DRAFT_COPY | 1050 | DELETE |

---

## Detailed Findings (per file)

---

### `bootstrap-system-00-pre-read.md`
- **Category:** PARTIALLY_RELEVANT
- **Content summary:** Meta-instructions for an Implementer agent on which skills and context files to load before coding each part of the bootstrap system (Parts 01-05). Includes cross-cutting concerns (Python 3.14+, uv, Flox, env-only secrets) and domain knowledge guidance.
- **Implementation status:** The bootstrap system is in early stages — `src/agent_framework/bootstrap.py` exists as a 14-line placeholder. No `agent-project.yaml` found. The spec describes planned work.
- **Recommendation:** KEEP — useful as implementation instructions. However, it's more of a "work instruction for the implementer" than a spec. Consider moving to `docs/plans/` or `docs/context/` when the system is built.
- **Reason:** Contains actionable guidance for developers implementing the bootstrap system. Not a spec of current behavior but a build guide.

---

### `bootstrap-system-01-overview.md`
- **Category:** ACTIVE (current design direction)
- **Content summary:** High-level architecture of a bootstrap system that translates `agent-project.yaml` into Docker volumes, manifests, and docker-compose files. Describes the lifecycle (bootstrap vs. runtime), the file map, and key design decisions (config-driven, manifest as intermediate artifact, skills symlinked at bootstrap).
- **Implementation status:** Early stages. The spec references `bootstrap.py` which exists as a stub. No `agent-project.yaml` found in the project root.
- **Recommendation:** KEEP — this is the current architectural direction.
- **Reason:** Represents active design. References plans in `docs/plans/overhaul/`. Not yet fully implemented but still accurate as the target architecture.

---

### `bootstrap-system-02-schema.md`
- **Category:** ACTIVE (current design direction)
- **Content summary:** Defines the exact YAML schema for `agent-project.yaml` including field-by-field constraints, validation rules (project_name, agent_key, type, skills, graph_module, MCP endpoints, HITL), an agent type registry (7 registered types with defaults), and the manifest generation pattern.
- **Implementation status:** Schema not yet implemented — no validation code or `agent-project.yaml` found.
- **Recommendation:** KEEP — core schema for the active design.
- **Reason:** The schema is the foundation for the bootstrap system. Well-specified with pseudocode validation algorithms and acceptance criteria.

---

### `bootstrap-system-03-bootstrap.md`
- **Category:** ACTIVE (current design direction)
- **Content summary:** Full CLI spec for `bootstrap.py` with three commands: `validate`, `bootstrap`, `teardown`. Includes pseudocode for each operation: volume creation via docker-py, subdirectory pre-creation via Alpine init containers, project volume seeding, skills symlinking, manifest writing, and compose generation. Includes error handling table and acceptance criteria.
- **Implementation status:** `src/agent_framework/bootstrap.py` exists as a 14-line placeholder referencing this spec.
- **Recommendation:** KEEP — implementation spec for the active CLI.
- **Reason:** 670 lines of detailed pseudocode ready for implementation. Bootstrap stub references it directly.

---

### `bootstrap-system-04-entrypoint.md`
- **Category:** ACTIVE (current design direction)
- **Content summary:** Spec for the container entrypoint script that runs inside each agent container. Defines how it reads `manifest.json`, resolves system prompts, loads graph modules (via `get_graph()`), loads MCP tools via `MultiServerMCPClient`, creates a Deep Agent via `create_deep_agent()`, and exposes it over ACP. Includes environment variables, error handling, graph module contract, and ACP transport limitations.
- **Implementation status:** No entrypoint implementation found yet.
- **Recommendation:** KEEP — spec for the active entrypoint design.
- **Reason:** Well-specified with clear algorthms. Framework-heavy spec depending on deepagents, langgraph, langchain-mcp-adapters.

---

### `bootstrap-system-05-skills.md`
- **Category:** ACTIVE (current design direction)
- **Content summary:** Defines the skills symlinking model (directory layout on volumes, relative symlinks resolved at container runtime), SKILL.md validation requirements, and the MCP proxying two-phase model (build phase: through governance; post-build: direct). Includes per-agent endpoint allowlist design and MVP simplification (direct connections, no governance yet).
- **Implementation status:** Not yet implemented — no symlink logic or governance proxy.
- **Recommendation:** KEEP — spec for the active skills/MCP model.
- **Reason:** Describes how skills and MCP tools are injected. The MCP proxying model has clear MVP vs. future distinction.

---

### `memory-manager-langgraph.md`
- **Category:** ACTIVE (matches `src/memory/` implementation)
- **Content summary:** LangGraph pseudocode spec for the Memory Manager — a 3-node ingestion pipeline: `validate_classify → build_payload → embed_ingest`. Covers: data structures (Pydantic models, state schema, EmbedType enum), 5 target modules (`taxonomy_loader.py`, `embedder.py`, `qdrant_client.py`, `graph.py`, `__init__.py`), error handling strategy, retry strategy, and test plan.
- **Implementation status:** **IMPLEMENTED** — all 5 specified files exist in `src/memory/` plus extra files (`ingest.py`, `sparse_embed.py`, `edge_validator.py`, `classifier.py`, `models.py`, `chunker.py`). The graph structure and module exports match the spec.
- **Recommendation:** KEEP — accurate documentation of current behavior. Consider marking as "documented" or updating if future changes occur.
- **Reason:** This spec accurately describes the current `src/memory/` package. It matches the implementation closely (same module names, same 3-node graph, same imports/exports).

---

### `topology-plan:overview.md`
- **Category:** SUPERSEDED
- **Content summary:** Brief 12-line overview of the old container/volume topology using the "symlink bridge" pattern, 9 agent variations, Flox/uv stack, and OpenCode headless agent framework. Dated 2026-05-08, Phase 2, status "Draft awaiting user approval."
- **What replaced it:** The bootstrap system specs (above) which use Deep Agents/LangGraph instead of OpenCode. The current `docker-compose.yml` is completely different (single mcp-server service with Traefik routing, no agent volumes).
- **Content to extract before deletion:** None — the symlink bridge concept and file-based handoff protocol are preserved/replaced by the bootstrap system's volume+manifest approach.
- **Recommendation:** DELETE
- **Reason:** Superseded design. The current compose file and bootstrap specs represent a different architectural direction.

---

### `topology-plan:volume.md`
- **Category:** SUPERSEDED
- **Content summary:** Defines the old volume topology: `project-vol` + 9 per-agent volumes (`agent-orchestrator-vol`, `agent-strategic_thinker-vol`, etc.), mount matrix (orchestrator mounts all volumes RW, agents mount only own), symlink bridge mechanics via `ln -s`.
- **What replaced it:** The bootstrap system uses `{project}_project_vol` / `{project}_agent_vol` with Docker subpath mounts instead of per-agent volumes.
- **Content to extract before deletion:** The symlink bridge concept (dynamic grants via symlinks, zero copies) is an interesting pattern but hasn't been carried into the new design. Evaluate whether to archive this concept.
- **Recommendation:** DELETE
- **Reason:** Superseded by bootstrap system's volume model (2 volumes per project, subpath isolation).

---

### `topology-plan:docker-flox.md`
- **Category:** SUPERSEDED
- **Content summary:** Detailed Docker compose layout (parameterized template), Dockerfile design using Flox for system tools and uv for Python, Flox manifest for all 9 agent variations, OpenCode CLI installation approach. Dated 2026-05-08.
- **What replaced it:** No Flox-based Dockerfile exists. The current `docker-compose.yml` is lightweight with mcp-server only. The bootstrap system doesn't use Flox.
- **Content to extract before deletion:** The Flox manifest patterns (unified manifest approach) and the analysis of per-variation tool requirements could be useful reference, but none of this has been implemented.
- **Recommendation:** DELETE
- **Reason:** Superseded. The Flox approach and per-variation agent images are no longer the planned architecture.

---

### `topology-plan:context-injection.md`
- **Category:** SUPERSEDED
- **Content summary:** Detailed spec for the old file-based handoff protocol between containers: `task-config.json` schema, signal files (`task-ready.signal`, `task-done.signal`), container lifecycle (startup, task dispatch flow, shutdown, idle, concurrency, failure recovery), and an extensive analysis of OpenCode+LangGraph coexistence approaches (A: Clean Separation, B: Minimal Disruption, C: Deep Agents as Orchestrator). Includes 10 decisions requiring user approval.
- **What replaced it:** The bootstrap system's manifest-based approach replaces the handoff protocol. The OpenCode+LangGraph coexistence analysis is partially reflected in the bootstrap system's Deep Agents approach (which was approach C).
- **Content to extract before deletion:** The OpenCode+LangGraph coexistence comparison (Sections 8.1-8.8) is thorough architectural analysis. The decisions list (Section 10) may have unresolved questions. Consider extracting Section 8 (coexistence analysis) and Section 10 (decisions required) before deletion.
- **Recommendation:** EXTRACT_THEN_DELETE
- **Reason:** Superseded, but contains valuable architectural analysis (Sections 8, 10) that may still be relevant to ongoing design decisions.

---

### `changes.md`
- **Category:** SCRATCH
- **Content summary:** 4-line bullet list: "OpenCode architecture will become redundant, replaced by langchain ecosystem. opencode tui/server → deep-agents-cli. agents wrapped in deep agent cli. flox assumed to contain all packages."
- **Recommendation:** DELETE — these are informal notes, not a spec. If important, condense into a commit message or brief entry. The first two points are already reflected in the bootstrap system direction.
- **Reason:** Scratch note, 7 lines, no structural value. Information already captured in bootstrap-system specs.

---

### `container-volume-topology:overview copy 2.md` through `copy 7.md`
- **Category:** DRAFT_COPY (6 files, all identical)
- **Content summary:** Each is a 1050-line megadoc combining all sections from the topology-plan series (overview + volume + docker-flox + context-injection) into a single file. The original `container-volume-topology:overview.md` (without "copy") appears to have been deleted — only copies 2-7 remain.
- **What they describe:** The same old topology plan (symlink bridge, 9 variations, Flox, OpenCode headless) that the `topology-plan:*` files describe.
- **Recommendation:** DELETE all 6 files. The content is preserved in the individual `topology-plan:*` files.
- **Reason:** Accidental duplicates. 6,300 lines of unnecessary file bloat. No original file to preserve — the content is fully represented in `topology-plan:overview.md`, `topology-plan:volume.md`, `topology-plan:docker-flox.md`, and `topology-plan:context-injection.md`.

---

## Summary of Actions

| Action | Count | Files |
|--------|-------|-------|
| **DELETE** | 12 | `topology-plan:overview.md`, `topology-plan:volume.md`, `topology-plan:docker-flox.md`, `changes.md`, all 6 copy files, `topology-plan:context-injection.md` (after extract) |
| **EXTRACT_THEN_DELETE** | 1 | `topology-plan:context-injection.md` (extract §8 and §10 first) |
| **KEEP** | 5 | `memory-manager-langgraph.md`, `bootstrap-system-*-*.md` (6 files total with pre-read) |
| **Total** | 18 | |

## Recommended Cleanup Order

1. Delete 6 copy files first (no content loss — pure duplicates)
2. Delete `changes.md` (scratch note, no spec value)
3. Delete `topology-plan:overview.md` and `topology-plan:volume.md` (both fully superseded)
4. Extract §8 (coexistence analysis) and §10 (decisions) from `topology-plan:context-injection.md` to a reference document, then delete the original
5. Delete `topology-plan:docker-flox.md` (superseded, no content worth extracting)
6. Keep all 6 `bootstrap-system-*` files (active design direction)
7. Keep `memory-manager-langgraph.md` (matches current implementation)

## Potential Issues

- **No `agent-project.yaml`** exists in the project root, yet the bootstrap specs describe it as the central config file. Either it hasn't been created yet, or it's expected to be generated.
- **`topology-plan:context-injection.md` §8** contains the most thorough OpenCode→LangGraph migration analysis in the repo. Before deletion, verify this analysis is captured elsewhere (e.g., `docs/plans/overhaul/`).
- **The copy files** have no original (`container-volume-topology:overview.md` is missing). It's unclear whether copies 2-7 were created by a tool or manually. The numbering implies an original existed.
- **`memory-manager-langgraph.md`** has more files in `src/memory/` than it describes (6 extra files: `ingest.py`, `sparse_embed.py`, `edge_validator.py`, `classifier.py`, `models.py`, `chunker.py`). The implementation has grown beyond the spec.
