# Handoff Notes

Cross-session handoff. Each entry is a short note for the next session's coordinator. Read this file first when starting a new session.

---

## Handoff 002 — 2026-04-23

**Who**: Coordinator (opencode-go/minimax-m2.7)
**What was done**:
- Read and absorbed all `.memory/` files — fully updated coordinator state
- Confirmed understanding with user on key architectural questions:
  - mem0 runs in-process (ADR-007 accepted)
  - Qdrant + Ollama are external user-managed infrastructure (not in compose)
  - Agent context is OpenCode, not Roo Code — "roo_agent" user_id is stale (ADR-009 accepted)
  - Serving port: 8000 (settled)
  - Planning-first approach (ADR-008 accepted) — no code until planning is done
- Searched for relevant skills to support planning phase:
  - `mem0ai/mem0@mem0` (already installed, 604 installs) — official mem0 SDK skill
  - `wshobson/agents@architecture-patterns` (13.4K installs) — for agentic memory patterns
  - `othmanadi/planning-with-files@planning-with-files` (17.9K installs) — structured planning workflow
- User approved installation of all three skills
- Updated all four `.memory/` files: CONTEXT.md (full snapshot), STACK.md (with agent context change), DECISIONS.md (ADRs 007-009), handoff.md (this entry)

**What to do next**:
1. **Planning phase — do this first**: Define MCP tool interface, data model, configuration surface, failure modes, extensibility points. Use the installed skills as reference.
2. **Then**: Fix server entry point (one main.py, port 8000, remove broken proxy reference)
3. **Then**: Wire mem0 with env var config, expose MCP tools
4. **Then**: Add `.env.example`
5. **Then**: Update user_id from "roo_agent" to generic agent identifier

**Known gotchas**:
- No `npx` in this environment — use `bunx` or `conda`
- `src/index.ts` is dead code, don't waste time on it
- `framework-base:latest` is a custom image — not on Docker Hub, must be pre-built
- `.memory/` is temporary git-tracked — delete and gitignore when mem0 takes over
- Port 6274 in docker-compose is vestigial inspector cruft, can be ignored
- **Skills just installed**: mem0, architecture-patterns, planning-with-files — use them for planning reference
- Both `main.py` files currently run on port 8001 — must change to 8000

---

## How to Use This Memory System

### For a new session coordinator:
1. **Read `CONTEXT.md` first** — current project state, what exists, what doesn't, blockers, next steps
2. **Read `STACK.md`** — tech stack, versions, do-nots, port reference
3. **Skim `DECISIONS.md`** — scan ADR titles for relevant past decisions before making new ones
4. **Check `handoff.md`** — the latest entry tells you where the last session left off

### Update rules:
- **CONTEXT.md** — Overwrite each session with current state snapshot
- **DECISIONS.md** — Append only. Never edit past entries. Add new ADRs for significant choices.
- **STACK.md** — Update when stack changes (versions, ports, services, do-nots)
- **handoff.md** — Append a new entry at end of each session

### When mem0 takes over:
- Delete `.memory/` directory
- Add `.memory/` to `.gitignore`
- Remove `.memory/` from git tracking
- mem0 handles persistence from that point

---

<!-- Template for future handoffs:
## Handoff 003 — YYYY-MM-DD

**Who**: [agent/model]
**What was done**: [bullet list]
**What to do next**: [ordered list]
**Known gotchas**: [bullet list]
-->