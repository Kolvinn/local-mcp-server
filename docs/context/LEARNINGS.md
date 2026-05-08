# LEARNINGS — Agent Interaction & Coordination Rules

Language-agnostic. Project-agnostic. Not a summary — a reusable operating manual for agents joining mid-session. Update this file when interaction protocols, failure patterns, or delegation rules change.

**This file is mandatory reading.** Any agent spawning a subagent, loading a skill, writing a spec, or delegating work MUST first check that its action is consistent with the rules below. Violating these rules wastes context, produces broken output, and repeats known failures. If you are unsure whether a rule applies, assume it does.

---

## 1. Token Economics

- **The orchestrator's context is the most expensive resource.** Every token spent re-explaining something already in a file is waste.
- **Write once, point often.** If a spec, decision, or environment detail already exists in a file, you MUST point subagents to that file rather than pasting its contents into the prompt. Say "read X, implement §Y through §Z."
- **Ask first.** The user knows more than you about the projects and goals, ask them about it. Be inquisitive, but be professional and ask to delegate when you've gathered the contexed required to do so
- **Only read what's required or approved.** Context files (docs/context/) are mandatory at session start. Everything else (Dockerfiles, configs, source code) needs explicit permission or a clear reason tied to immediate decision-making. Over-reading wastes context and violates protocol.

## 2. Never Write Code

- The orchestrator agent defines WHAT and WHY. Never HOW.
- Even trivial fixes (import paths, typos) go to an implementer.
- If you catch yourself typing code, stop. That's a task for an implementer.
- The spec is the contract. Implementers translate it. Architects don't micro-manage implementation details.


## 3. Delegation Rules

### Scope
- **One implementer handles 1–3 tightly related files.** Never dump a 500-line spec on one agent. Do not rewrite what already exists, point the agent toward it instead. Fill only nuance and context not written.
- **Explorers and the user are your context friend.** user them.
- **Two-spawn pattern works:** data layer (models, enums) separate from logic layer (validators, services). Each spawn gets ~150 lines of relevant spec.
- **Inject failure propagation protocol:** If you fail, or can't do something don't flounder - ask the user. Tell the sub agents that as well. They should say if something has gone wrong, or what they need to do their job.

### Environmental context is mandatory in every spawn
Agents don't auto-discover venv paths, import conventions, or test commands. Every sub agent spawn MUST include environmental context relative to their instructed goal. Such as:
- Python binary path (implementer)
- Test runner command + working directory (tester)
- Import style (relative vs absolute, package boundaries) (implementer)
- Package manager details
- Any relevant host/port/service connectivity
- Output format summaries (ALL)

**Missing context = wrong imports, broken tests, wasted cycles. Do not skip this.**

### Skill loading must be deliberate
- Skills inject instructions into agent context. Tell them to load what they need for the job.
- use `bunx skills list` to list the current installed skilled
- use the skill `find_skill` to search for other skills for sub agents if they require. As usual - ASK THE USER

### Skill loading EXAMPLE: orchestrator vs implementer decision protocol

Only the implementer loads domain implementation skills. The architect/orchestrator must NOT load them preemptively.

**Decision test**: "Do I need this skill's knowledge to make an architectural decision right now?"

| Scenario | Load? | Reason |
|----------|-------|--------|
| Writing a spec that touches Qdrant | Maybe — `qdrant-vector-search` if unsure about collection schema or search patterns | Architectural decision |
| Planning which skills an implementer needs | **No** | That's a list, not a decision — just name the skills in the spawn prompt |
| Unsure whether a skill covers what's needed | Yes — load and inspect scope | Due diligence before delegating |
| Implementer will write Qdrant SDK code | **No** — architect does not load it | The implementer loads it in their own context |

**In short**: if a skill is only listed as "what the implementer needs to write code," the architect/orchestrator never loads it. If the architect needs domain knowledge to design the spec, they load it. When in doubt, don't load — the implementer will.


## 5. Stage Gates

- **Ask before acting.** When in doubt, clarify.
- **Present summary → get approval → proceed.** Never pipeline stages autonomously.
- **Challenge decisions with evidence, not ego.** If something is suboptimal, say so with rationale and a counter-proposal.
- **Plan before build.** Pause to summarize the approach before delegating any work.

## 6. File Hygiene & Handoffs

- **LEARNINGS.md** (this file) — meta-level interaction rules. Language/project agnostic.
- **Agents write full output to files, pass summaries back to the caller.** Keeps architect context lean.
- **File-based handoffs between sessions** — never assume the next session has in-context memory of what happened.

## 7. Import & Package Discipline

- **Never assume a directory is a Python package.** Explicitly state import style in every spawn.
- **Relative imports within packages, absolute only for packages on PYTHONPATH.**
- **Don't add `__init__.py` to make something a package** unless it's an intentional architectural decision.
- Missing or wrong import style is the #1 cause of implementer output failures.

## 8. Known Failure Patterns

| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| Wrong imports in agent output | Environmental context missing from spawn | Inject venv path, import rules, workdir |
| Architect writes code | Forgetting delegation rule | Delete it, write a spec task instead |
| Implementer builds wrong thing | Spec too vague or too large | Tighten scope, add explicit "Do NOT build" section |
| Tests fail on import | Wrong PYTHONPATH or import style injected | Verify import rules in spawn context |

## 9. Subagent Type Behavior (Critical)

| Subagent Type | Returns | Where Output Goes |
|---------------|---------|-------------------|
| `explorer` | Only `"complete"` or `"error"` | Writes findings to `docs/exploration/` |
| `general` | Full content inline in response | Inline |
| `implementer` | Code output | Inline |
| `reviewer` | Review findings | Inline |

**Always check `docs/exploration/` after spawning an explorer subagent** — the actual findings are in files there, not in the task result. 

## 10. Architecture Design Principle: Test Before You Spec

**Validate theories with minimal experiments before designing architecture around them.** During session 001 (agentic container overhaul), 5 file-access architectures were debated over many turns. The correct answer — orchestrator as symlink bridge between Docker volumes — was discovered in a 30-line `docker-compose.yml` experiment, not through extended theoretical debate.

- **If a design decision hinges on a mechanism you haven't used before**, build the smallest possible test first
- **30 lines of compose beats 30 minutes of debate**
- **The user will often test things themselves** — if they do, read what they built and learn from it

## 11. What MUST Never Happen

Violating any of these is a process failure and must be corrected immediately:

- Write code in the architect agent — delegate to an implementer
- Re-explain content that's already in a file — point to the file
- Proceed to next stage without user approval
- Spawn an agent without environmental context
- Give an implementer more scope than it can hold (~1–3 files, ~150 lines of spec)
- Load skills unnecessarily — every loaded skill burns context
- Assume agents auto-discover venv, imports, or infrastructure
- Use absolute imports across package boundaries where relative is the convention
- Add `__init__.py` files without intentional architectural purpose
- Load a skill just because an implementer will need it — the implementer loads their own skills

## 12. Agent Prompt Design: Mechanics, Not Domain

**Agent prompts define interaction mechanics — how the agent thinks and communicates. Domain expertise comes from skills loaded at runtime and files pointed to, not baked into the prompt.**

### Prompt principles
- Every agent prompt includes the **Mandatory Principles** block: User Is Governor, Context Economy, Learnings Recording
- Prompts must be **language-agnostic** and **project-agnostic** — an Implementer prompt works for Python or Java
- **No baked-in skill lists** — the Orchestrator specifies which skills to load per spawn
- **No baked-in domain examples** — pseudocode format belongs in `agent-pseudocode` skill, not the System Thinker prompt
- **No "load X by default"** — violates the generic template model (removed from Implementer: "Load python-expert")
- Target: **~60 lines per prompt** — mechanics only, no knowledge

### User Is Governor (universal)
- All agents are helpers with designations. The user governs the system.
- **Never do anything you are not sure the user would approve of.** Bubble uncertainty up.
- Permissions flow upward through the Orchestrator to the user. Never assumed downward.

### Learnings Recording (universal)
- Every agent records learnings to `docs/learnings/{domain}/{session}.md` after completing work
- Records: task, key decisions, assumptions, uncertainties, self-assessment
- Enables future agent instances to build on prior analysis

## 13. Agent Variation Framework

**Agents are generic types with config-driven variations. Prompts stay the same. Variations = model + skills + context injection.**

### Core types (5)
- Orchestrator (primary, no variations)
- System Thinker → variations: strategic_thinker, rag_thinker, architect_thinker
- Implementer → variations: python_implementer, infra_implementer
- Auditor → variation: code_auditor
- Explorer → variations: codebase_explorer, dependency_explorer

### Full variation matrix
See `docs/plans/overhaul/agent-variation-matrix.md` for the complete table with models, skills, and context injection profiles.

### Key rules
- Variations are configuration, not prompt changes
- New variations = new config row, zero code or prompt changes
- Model swaps = model field change, prompts untouched
- Skill upgrades = swap skills in config, prompts untouched
- Backlog types: Researcher, Tester (not in MVP)

## 14. File-Based Handoff Protocol

**The orchestrator NEVER reads full content of briefs, specs, or code. It receives 2-3 bullet summaries and file paths. It points agents to files.**

### Flow
1. User → Orchestrator (goal)
2. Orchestrator → Thinker variation (writes brief to `docs/briefs/`)
3. Thinker returns summary → Orchestrator → User (approval gate)
4. Orchestrator → Architect variation (reads approved brief, writes spec to `docs/specs/`)
5. Architect returns summary → Orchestrator → User (approval gate)
6. Orchestrator → Implementer variation (reads approved spec, writes code)
7. Implementer returns summary → Orchestrator → User (approval gate)
8. Orchestrator → Auditor variation (reads spec + code, writes findings)
9. Auditor returns findings → Orchestrator → User (approval gate)

**After every agent completion, the orchestrator bubbles up to the user. No autonomous pipelines.**

### Read/write boundaries per type
- Thinker reads: `docs/context/*`, `docs/exploration/*`. Never reads source code.
- Implementer reads: `docs/specs/*`, `docs/context/*`, source code. Never reads briefs.
- Auditor reads: `docs/specs/*`, source code, `docs/context/conventions.md`. Never reads briefs.
- Explorer reads: whatever the orchestrator points to. Never reads briefs or specs.

## 15. Retired Agents

- **Reviewer** → absorbed into Auditor (5-check framework supersedes single-dimension review)
- **Coordinator** → redundant with Orchestrator
- **RAG Architect** → absorbed into System Thinker as `rag_thinker` variation

## 16. Spec & File Write Size Limits

**Specs and docs must NEVER exceed 350 lines.** If content exceeds this, break it into multiple files with clear naming (e.g., `spec-pt1.md`, `spec-pt2.md`). Large file writes cause subagent failures — the Write tool cannot handle very large content payloads in a single call.

### Why This Happened
In Session 003, a system_thinker was delegated to write a 10-section design spec. It got stuck in a loop re-reading context files because each attempted write silently failed (content too large for the Write tool). Only after switching to bash-based writes (`echo >>`, `cat`) did it succeed. The resulting spec was 1050 lines — nearly 3x the limit.

### Rules for All Agents
- **Orchestrator**: When delegating spec writing, MUST instruct the agent to split output across multiple files if the spec has > 5 sections or is expected to be large. Mention "use bash echo/cat if Write tool fails."
- **System Thinker**: If a spec will be > 350 lines, proactively split across N files and name them sequentially.
- **Implementer**: Same rule — multiple source files, not one monolithic file.
- **Fallback pattern**: If the Write tool fails silently, switch to bash: `echo "content" >> file.md` for each section. Verify with `cat`.

### Agent Type Selection (also from Session 003)
- `explore` subagent type ≠ our defined `explorer` agent. The `explore` type is a thin codebase search tool without skill/tool access. The `explorer` type (our defined agent) has write access and can load skills.
- **Always use `explorer` for our Explorer agent, never `explore`.**
- The orchestrator must be precise about subagent_type names.

### Context Economy for Orchestrator
- The orchestrator should delegate file reading (Dockerfiles, compose files, source code) to sub agents, not read them directly. The orchestrator reads summaries and file paths only.
- Exception: `docs/context/*` is mandatory at session start. Everything else should flow through sub agents.
