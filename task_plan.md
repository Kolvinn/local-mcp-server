# Task Plan: Mem0 MCP Server Architecture

## Goal
Design the complete architecture for a dual-layer memory MCP server: Mem0 (semantic vector) + local metadata (hierarchical file discovery), with staleness validation and self-healing metadata.

## Current Phase
Phase 1

## Phases

### Phase 1: MCP Tool Interface
- [x] Define tool surface — 7 tools for v1
- [x] Map tools to layers (Mem0 vs local metadata)
- [x] Define input/output contracts
- **Status:** complete

### Phase 2: Data Model
- [x] Memory entity — fields, metadata schema (temporal, git-backed drift)
- [x] Local metadata file spec (.memory-context.yaml — minimal, YAML)
- [x] Temporal fields — created_at, edited_at, validated_at
- [x] related_files: [{path, entered}] — no hashes, git log at audit time
- [x] source_path — directory context at creation time
- [x] tags replace source_type — flexible categorization
- [x] No memory_ids in local files — shared vocabulary coupling only
- [x] Merge/hierarchy — folder-local > project-level, tags accumulate
- **Status:** complete

### Phase 3: Validation & Staleness System
- [x] On-retrieval validation — built into search_memory (git log check + staleness flags)
- [x] validate_memories — re-check flagged, update validated_at or flag for delete
- [x] audit_stale — on-demand scan, read-only, returns condensed report
- [x] Staleness window — 30d default, env var STALENESS_WINDOW_DAYS, per-memory override
- [x] related_files drift — git log --since on retrieval, no hashes stored
- [x] cleanup_stale → DEFERRED to v2 (insufficient data volume to warrant)
- [x] check_drift → DEFERRED to v2 (LLM cost not justified for v1)
- [x] reingest pipeline → DEFERRED to v2 (add_memory covers manual reingest)
- **Status:** complete

### Phase 4: Configuration Surface
- [x] Env vars defined (9 total: QDRANT_HOST/PORT, OLLAMA_URL, EMBEDDING_MODEL, LLM_MODEL, AGENT_ID, STALENESS_WINDOW_DAYS, HOST, PORT)
- [x] Mem0 config constructed from env vars
- [x] user_id → AGENT_ID env var (default: default_agent)
- [x] project_id → from .memory-context.yaml
- [x] source_user → optional, passed at add_memory time (for human/partner references)
- [x] Scoping: who created (user_id), what project (project_id), who about (source_user)
- **Status:** complete

### Phase 5: Failure Modes & Extensibility
- [x] Qdrant down → structured error, local metadata still works, semantic search returns context-only
- [x] Ollama down → write tools fail, read tools work (pre-computed embeddings), sync_metadata works
- [x] Both down → sync_metadata only, agent told "memory unavailable"
- [x] Corrupt metadata file → skip + warn, don't crash
- [x] Missing metadata → no local context, search uses AGENT_ID default scope
- [x] Git unavailable → staleness skips git log, validated_at window only
- [x] Mem0 init failure → server stays up, Mem0 tools return error on call
- [x] New tools → new use case + existing adapters (hexagonal)
- [x] New metadata fields → schema_version migration path
- [x] New .memory-context.yaml fields → version field + parser ignores unknowns
- **Status:** complete

## Key Questions
1. ~~Metadata schema version~~ → version field in file, parser checks it
2. ~~Reingestion trigger~~ → DEFERRED v2
3. ~~Merge semantics~~ → folder-local wins, tags accumulate
4. ~~Cleanup tool vs background~~ → DEFERRED v2 (audit_stale read-only in v1)
5. ~~Minimum metadata file~~ → project_id + tags + scope_summary

## Decisions Made
| Decision | Rationale |
|----------|-----------|
| Dual-layer: Mem0 + local metadata files | Mem0 for semantic search, local files for hierarchical context injection |
| Folder-local overrides project-level | More specific context wins, like .gitignore cascading |
| Temporal metadata on every record | created_at, edited_at, validated_at enable staleness detection |
| On-retrieval validation (staleness + git) | Catch drift at read time, surface flags to user |
| 30-day staleness window (configurable) | Default threshold, STALENESS_WINDOW_DAYS env var |
| Git-first drift, no stored hashes | git log --since at audit time, no duplication of git's job |
| related_files: [{path, entered}] | Lightweight, queries git on demand |
| source_type removed → tags | Flexible, no enum to maintain |
| YAML for .memory-context.yaml | Comments, readability, hand-editable |
| AGENT_ID env var for user_id | Generic, replaces "roo_agent", configurable |
| source_user field in metadata | Future-proof for business partners/clients |
| 3-dimension scoping | user_id (creator) + project_id (project) + source_user (subject) |
| No subagent in v1 | 10GB VRAM constraint, tools return condensed summaries |
| cleanup_stale/check_drift → DEFERRED v2 | Insufficient data volume, LLM cost not justified |
| Hexagonal architecture | Clean layer separation, extensibility via new use cases + adapters |
| schema_version on memories | Migration path for future metadata field additions |

## Errors Encountered
| Error | Attempt | Resolution |
|-------|---------|------------|

## Notes
- No code written until all 5 phases complete (ADR-008)
- Existing src/main.py has 5 stubs — will be redesigned against this plan
- Architecture-patterns skill: use hexagonal ports/adapters for clean layer separation
