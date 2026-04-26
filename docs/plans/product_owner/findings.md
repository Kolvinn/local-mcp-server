# Findings: Product Owner Agent Design

## Context

User wants to design a "product_owner" agent — an improved version of the coordinator agent focused on strategic "why" rather than tactical coordination. The existing agent team architecture (coordinator/expert/explorer/implementer/reviewer) focuses on 3-layer delegation (why/how/what). This new product_owner would be a strategic layer above that, owning the "why" for both user context and project direction.

## Design Constraints (from user)

- **Strategic focus**: product_owner should own the "why" — strategic direction of user intent AND project goals
- **Aggressive offloading**: All menial tasks (exploring files, getting summaries) should be delegated to sub-agents
- **Single point of contact**: User works with product_owner, product_owner coordinates specialist teams
- **Project-agnostic**: Should work in ANY project without modification — no project-specific baked in
- **Teams, not solo agents**: Coordinates teams of agents (planners, engineers, implementers)
- **Not specific to current project**: Design should allow dropping into any project

## Initial Observations

### What makes product_owner different from coordinator?

| Aspect | Coordinator | Product Owner |
|--------|-------------|---------------|
| Focus | Tactical orchestration | Strategic direction |
| Primary question | "How do we build this?" | "Why are we building this?" |
| Ownership | Project context | User intent + project purpose |
| Delegation depth | 3-layer (why/how/what) | Strategic layer above 3-layer |
| User relationship | Multiple agents interact | Single point of contact |
| Project knowledge | Project-specific (ADRs, key facts) | Project-agnostic |
| Memory | Owns project memory | No baked project memory |

### Potential Agent Teams product_owner might coordinate

Based on user's mention of "planners and engineers and implementers":

1. **planners** — Strategic planning, roadmapping, priority-setting
2. **engineers** — Technical implementation specialists
3. **implementers** — Execution-focused (similar to existing implementer)
4. **reviewers** — Quality verification

But this needs clarification — are these specific named agents, or tiers/roles?

### Delegation Categories

**Always Delegate (Menial Tasks):**
- File exploration and searching
- Codebase comprehension
- Summarization of findings
- Pattern discovery
- Directory structure analysis
- Git history queries

**Keep Strategic (product_owner):**
- Interpreting user intent
- Translating user goals into project direction
- Prioritization decisions
- Trade-off discussions with user
- Approval gate decisions
- Communication with user

### Key Design Questions

1. **Memory model**: Does product_owner need any persistent memory?
   - Option A: No memory — purely reactive to user input + project files
   - Option B: Minimal memory — only user preferences, not project data
   - Option C: User context memory — remembers user across sessions but not project

2. **Project context handling**: If project-agnostic, how does it learn about a project?
   - Option A: Reads project files (CLAUDE.md, AGENTS.md) at session start
   - Option B: Explorer agent provides summary on-demand
   - Option C: User provides context explicitly at start

3. **Triggering model**: What makes product_owner activate?
   - User directly addresses it?
   - Project-level goal discussions?
   - Strategy requests?
   - All user communication goes through it?

## References

### Existing Agent Patterns

- **coordinator**: Tactical 3-layer delegation (why→expert, how→expert, what→implementer)
- **expert**: Domain knowledge advisor (read-only, returns options)
- **explorer**: File search, codebase mapping (read-only, fast)
- **implementer**: Code writing from specs (write-capable, spec-driven)
- **reviewer**: Verification against spec (read-only, priority-based feedback)

### Agent Development Skill Templates

- System prompt structure: role, responsibilities, process, quality standards, output format, edge cases
- Triggering: 2-4 examples with context/user/assistant/commentary format
- Configuration: name (lowercase-hyphen), model (inherit/specific), color, tools (least privilege)

## Design Decisions (from user)

| Decision | Rationale |
|----------|-----------|
| Replaces coordinator | Absorbs strategic role; coordinator kept for backward compat |
| Agent team reference | Link to `agent-team` file for team structure (filled later) |
| User spawns agents | User invokes agents directly; if talking to PO, route through PO |
| Strategic keeps | Intent interpretation, prioritization, trade-offs, approval gates |
| Always delegates | File exploration, summarization, pattern discovery, code work |
| Project context via reference | Same as agent-team — blank section to fill via memory/skill/RAG |
| Smart write delegation | Small write + low context cost → do it; otherwise always delegate |

## Mental Model

### What product_owner OWNS (Strategic)
- **User intent** — What the user is actually trying to achieve
- **Project purpose** — Why this project exists, what it serves
- **Priority decisions** — What matters most, what to defer
- **Trade-off discussions** — Present options to user, facilitate decisions
- **Translation layer** — User language ↔ technical agent language
- **Approval gates** — User sign-off on strategic directions
- **Single point of contact** — All communication flows through PO

### What product_owner DELEGATES (Tactical/Menial)
- **File/codebase exploration** — Spawn explorer or search agent
- **Summarization** — Delegate, then present to user
- **Pattern discovery** — Delegate to specialist teams
- **Agent team coordination** — Planners, engineers, implementers do the work
- **Most writes** — Almost all writes delegated per rule above
- **Technical decisions** — Hand off to appropriate specialist

### Write Delegation Heuristic
```
IF write is small AND context_cost(generate) > context_cost(write):
    DO IT DIRECTLY  # Small edits, log entries, minor updates
ELSE:
    DELEGATE        # Code, docs, specs, anything substantial
```

### Communication Flow
```
User ←→ product_owner ←→ [agents user spawns]
                      └→ [agents PO spawns for exploration/summarization]
```

**Rule:** If an agent is talking to product_owner, it stays talking to product_owner. User can spawn agents directly but should route communication through PO.

### Project Context Handling
```
project_context_source = [
    "agent-team file (describes specialist teams)",
    "project context file (CLAUDE.md, key_facts, etc. — via RAG/skill/memory)",
    "user-provided context (explicit at session start)",
    "direct user input (on-demand)"
]
```

product_owner does NOT bake in project specifics. Context comes from these sources, not from baked prompts.

### Relationship to Coordinator
- **Coordinator:** Kept (not deleted) — potentially becomes tactical fallback
- **product_owner:** Strategic layer above; owns "why" and user relationship
- **共存:** Both exist; coordinator may handle tactical tasks PO delegates

## Notes

- User explicitly wants this project-agnostic — must not bake in local-mcp-server specifics
- "Aggressive offloading" is a key requirement — explicit rules about what to delegate
- "Single point of contact with user" means other agents don't communicate directly with user
- Planning files in `docs/plans/product_owner/`