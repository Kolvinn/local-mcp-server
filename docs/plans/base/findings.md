# Findings & Decisions

## Requirements
- MCP server exposing memory tools to a single agent (OpenCode)
- Dual-layer memory: Mem0 (vector/semantic) + local metadata files (hierarchical, auto-discovered)
- Local metadata files act as lazy-loaded context injection — discovered per-folder
- Metadata must not go stale — temporal fields + validation + cleanup pipeline
- Extensible — new tools and new metadata fields must not break existing data
- Single user, no auth, no multi-tenancy (ADR-006)

## Research Findings

### Mem0 SDK Capabilities (from skill + src/main.py stubs)
- `Memory.from_config()` — init with Qdrant + Ollama
- `memory.add(text, user_id, metadata, infer=True)` — store with auto-fact extraction
- `memory.search(query, user_id, filters)` — semantic retrieval with metadata filters
- `memory.delete(memory_id)` — remove specific memory
- Supports `user_id`, `agent_id`, `project_id` scoping
- `metadata` dict is flexible — custom fields supported

### Existing Tool Stubs in src/main.py
1. `search_project_memory` — semantic search with project_id + collection filters
2. `detect_context_drift` — LLM-based drift detection vs manifest summary
3. `compact_and_promote` — session → permanent facts via Mem0
4. `sync_manifest_state` — update local memory-context.json
5. `forget_specific_fact` — delete single memory

### Problems with Current Stubs
- Hardcoded `user_id="roo_agent"` (ADR-009 violation)
- `sync_manifest_state` assumes single fixed manifest — doesn't support hierarchical discovery
- No validation/staleness logic
- No content hash tracking
- `detect_context_drift` is useful but depends on manifest concept that needs redesign
- Collection tags are manual — no auto-discovery from metadata files

### Hexagonal Architecture Application
- **Domain core**: Memory entity, metadata schema, validation rules
- **Ports**: MemoryRepository (CRUD), MetadataDiscovery (find/load files), ValidationService (check staleness)
- **Adapters**: Mem0Adapter (implements MemoryRepository), FileMetadataAdapter (implements MetadataDiscovery), HashValidator (implements ValidationService)
- Clean separation: domain never imports mem0ai or file I/O directly

## Technical Decisions
| Decision | Rationale |
|----------|-----------|
| Metadata files: YAML over JSON | Comments supported, more human-readable, easier to hand-edit |
| Hierarchical discovery like .gitignore | Proven pattern — cascade from root to cwd, specific wins |
| Git-first drift detection with hash fallback | git diff gives rich change context; hash covers uncommitted/non-repo |
| validated_at timestamp per record | Enables staleness window without scanning all data |
| Audit on retrieval mismatch | Catch problems at read time, not batch time |
| source_type removed → tags replace it | Flexible (fact, user_preference, compact, reingest as tags), no enum to maintain |
| No memory_ids in .memory-context.yaml | Shared vocabulary coupling (tags, project_id), not brittle record pointers |
| Local metadata = search lens, not record pointer | Metadata narrows search scope; memories inherit same tags at creation |

## Issues Encountered
| Issue | Resolution |
|-------|-----------|
| src/main.py duplicate imports + messy code | Will clean during implementation phase (after planning) |

## Resources
- Architecture patterns skill: hexagonal ports/adapters pattern
- Mem0 skill: SDK API reference
- Existing ADRs in docs/project_notes/decisions.md (ADR-001 through ADR-009)
