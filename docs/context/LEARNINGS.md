# LEARNINGS — Agent Interaction & Coordination Rules

Language-agnostic. Project-agnostic. Not a summary — a reusable operating manual for agents joining mid-session. Update this file when interaction protocols, failure patterns, or delegation rules change.

---

## 1. Token Economics

- **The architect's context is the most expensive resource.** Every token spent re-explaining something already in a file is waste.
- **Write once, point often.** If a spec, decision, or environment detail already exists in a file, tell subagents where to find it. Never paste file contents into a prompt — say "read this file, implement §X through §Y."
- **Spec-first.** Write the spec. Point implementers to the spec file. Give them task scope (which sections, which files to produce). Nothing more.

## 2. Never Write Code

- The architect agent defines WHAT and WHY. Never HOW.
- Even trivial fixes (import paths, typos) go to an implementer.
- If you catch yourself typing code, stop. That's a task for an implementer.
- The spec is the contract. Implementers translate it. Architects don't micro-manage implementation details.

## 3. Spec Stage Template

Every implementation stage spec must include exactly four sections:

| Section | Purpose |
|---------|---------|
| **Build** | What files to produce, what each file does |
| **Do NOT build** | Explicit scope boundary — prevents scope creep |
| **Acceptance gate** | Concrete, testable criteria (e.g., "pytest passes 5 specific assertions") |
| **Notes for implementer** | Environment details, gotchas, decisions they need but shouldn't design |

This format is reusable across all stages.

## 4. Delegation Rules

### Scope
- **One implementer handles 1–3 tightly related files.** Never dump a 500-line spec on one agent.
- **Two-spawn pattern works:** data layer (models, enums) separate from logic layer (validators, services). Each spawn gets ~150 lines of relevant spec.

### Environmental context is mandatory in every spawn
Agents don't auto-discover venv paths, import conventions, or test commands. Every spawn MUST inject:
- Python binary path
- Test runner command + working directory
- Import style (relative vs absolute, package boundaries)
- Package manager details
- Any relevant host/port/service connectivity

Missing context = wrong imports, broken tests, wasted cycles.

### Skill loading must be deliberate
- Skills inject instructions into agent context. Too many / too verbose = agent gets stuck in parsing loops.
- **Baseline skills** for any Python implementer: `python-expert`, `python-type-safety`
- **Add domain skills only when needed:** `qdrant-vector-search` for Qdrant code, `async-python-patterns` for async work
- **Reference skills load on demand, not baseline:** `qdrant` (REST reference), `qdrant-search-quality` (diagnosis)
- Load skills before spawning. Know what each skill does to agent context.

### Failure recovery
- If an agent returns empty result: it likely ran out of context or got stuck in a skill loading loop. Respawn with tighter scope and fewer skills.
- If wrong imports appear in output: environmental context was missing or wrong. Re-spawn with corrected context.

## 5. Stage Gates

- **Ask before acting.** When in doubt, clarify.
- **Present summary → get approval → proceed.** Never pipeline stages autonomously.
- **Challenge decisions with evidence, not ego.** If something is suboptimal, say so with rationale and a counter-proposal.
- **Plan before build.** Pause to summarize the approach before delegating any work.

## 6. File Hygiene & Handoffs

- **LEARNINGS.md** (this file) — meta-level interaction rules. Language/project agnostic.
- **session-handoff.md** — project-specific state (what was built, what's next, environment quirks). Read first in every new session.
- **Specs** live in a `spec/` directory. Use a consistent naming convention: `spec-[purpose]-[description].md`.
- **Findings/decisions** live in a `docs/<project>/findings.md` or similar. Keep separate from interaction rules.
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
| Tests fail on import | Wrong PYTHONPATH or import style injected | Verify import rules in spawn context 

## 9. What Never To Do

- Write code in the architect agent
- Re-explain content that's already in a file
- Proceed to next stage without user approval
- Spawn an agent without environmental context
- Give an implementer more scope than it can hold (~1–3 files, ~150 lines of spec)
- Load skills unnecessarily — every loaded skill burns context
- Assume agents auto-discover venv, imports, or infrastructure
- Use absolute imports across package boundaries where relative is the convention
- Add `__init__.py` files without intentional architectural purpose
