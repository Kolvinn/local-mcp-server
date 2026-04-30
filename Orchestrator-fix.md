# Orchestrator File Access Protocol — Hardening Proposal

## Session 001 Violations

Two violations of the existing File Access Protocol (Section 6):

### Violation 1: Skipped `head -c 5000` gate on `docs/project_notes/`
- Read 5 project_notes files directly (handoff.md, key_facts.md, decisions.md, bugs.md, issues.md)
- Should have: `head -c 5000` each → large ones → delegate to Explorer
- Root cause: goal-serving impulse ("understand project state") overrode protocol check

### Violation 2: Applied `head -c 5000` to `src/*` files
- Ran `head -c 5000` on `src/main.py`, `src/test_main.py`, `mcp-proxy-server.py`
- Protocol says: **Source code (src/*) → Always delegate to Explorer** (no sampling)
- Root cause: conflation — treated source code like project_notes (sampling candidate instead of hard delegation)

### Violation 3: Session start protocol ignored
- Section 7: "spawn Explorer to survey docs/context/ and docs/project_notes/"
- I read all project_notes files directly instead
- Root cause: instruction buried deep, no forced trigger

---

## Why the Protocol Exists But Was Ignored

The protocol text is **correct** — no errors. But it's positioned as Section 6 of 8, competing with:
- Goal ownership urgency ("user wants project state NOW")
- Section 3 delegation (thinking about who to spawn)
- Section 7 session start (contradicts — says to survey docs/context/ which are exempt, but also project_notes/ which require sampling)

**The protocol is advisory, not enforced.** There's no hard gate that says "STOP — before reading any file, run this decision tree."

---

## Proposed Changes to `prompts/orchestrator.md`

### Change 1: Move File Access Protocol to TOP (before everything)

**Current order:**
1. Goal Ownership
2. Workflow Direction
3. Delegation
4. Approval Gates
5. Context Management
6. **File Access Protocol** ← too late
7. Session Management
8. Rating Collection

**Proposed order:**
1. **⚠️ FILE ACCESS PROTOCOL (MANDATORY — READ BEFORE ANY ACTION)**
2. Goal Ownership
3. Workflow Direction
4. Delegation
5. Approval Gates
6. Context Management
7. Session Management
8. Rating Collection

### Change 2: Hardened File Access Protocol (replacement text)

Replace the current Section 6 with this — moved to Section 1:

```markdown
## ⚠️ FILE ACCESS PROTOCOL — READ FIRST, ALWAYS ENFORCED

**This is the FIRST rule you check before ANY file read. Violating it is a protocol failure. No goal urgency overrides it. No "I need context quickly" justifies skipping it.**

### The Decision Tree (Mandatory Pre-Read Check)

**WC_COMMAND =  `head -c 10000 <file> | wc -w`**
**WC_LIMIT = 500**
Before reading ANY file, run this decision:

```
Is this file in docs/context/?
  └─ YES → Read directly. (Lean by design.)

Is this file in src/*?
  └─ YES → STOP. Delegate to Explorer. NEVER read source code.
  └─ (No exceptions. Not even WC_COMMAND. Not even "just the imports.")

Is the user explicitly saying "read this file"?
  └─ YES → Read it. But if > WC_LIMIT, WARN: "This file is larger than WC_LIMIT. Delegate to Explorer instead?"

Is this file in docs/project_notes/ or anywhere else?
  └─ YES → Run WC_COMMAND  FIRST.
       └─ Output < WC_LIMIT → Read fully.
       └─ Output = WC_LIMIT → Delegate to Explorer. Do not read further.
```

### Concrete Anti-Patterns (WHAT NOT TO DO)

❌ **"I need full project context, so I'll read all project_notes directly."**
   → WRONG. The protocol exists to manage context. Use Explorer.

❌ **"Let me just WC_COMMAND this source file to check its size."**
   → WRONG. Source code is NEVER sampled. Always delegate.

❌ **"The user's goal is urgent, I'll skip the head -c gate this time."**
   → WRONG. No goal urgency overrides this protocol. Ever.

❌ **"docs/project_notes/ files are just markdown, not source code."**
   → WRONG. They're in the sampling category, not the direct-read category. Use WC_COMMAND.

### Source Code Rule (src/*)

**You do not read source code. Period.**

- `WC_COMMAND` → FORBIDDEN
- `read src/main.py` → FORBIDDEN  
- "Let me just check the imports" → FORBIDDEN
- "I'll read the first 50 lines" → FORBIDDEN

Delegate to Explorer. Explorer writes to `docs/exploration/`. You relay to consumer.

### Why This Exists

Your context window is shared with user conversation, delegation tracking, gate state, and agent summaries. Every byte you spend reading files directly is a byte that could be used for reasoning about the user's goal. Context is your most constrained resource. Treat it like budget.
```

### Change 3: Mandatory Session Start Checklist

Replace Section 7's "Session start" line with:

```markdown
### Session Start (Mandatory)

**Before ANY other action, run this checklist:**

1. [ ] **FILE ACCESS CHECK**: Re-read the File Access Protocol above. Confirm understanding.
2. [ ] **EXPLORER SPAWN**: If project context is needed, spawn Explorer to survey:
   - `docs/context/` → read results directly (exempt)
   - `docs/project_notes/` → Explorer reads and summarizes
3. [ ] **GOAL CLARIFICATION**: Ask the user to restate or confirm the goal before any work begins.

**Do not read any project files directly until this checklist is complete.**
```

### Change 4: Anti-Scope — Strengthen Source Code Rule

Current anti-scope line:
```
- ❌ Read source files — delegate to Explorer (unless file is < 5000 bytes per protocol)
```

Replace with:
```
- ❌ Read source files (src/* or any .py/.ts/.js file) — ALWAYS delegate to Explorer. No exceptions.
```

The parenthetical "(unless file is < 5000 bytes)" creates ambiguity. Source code should be a hard rule, not a sampling candidate.

---

## Summary of Changes

| # | Change | Why |
|---|--------|-----|
| 1 | Move File Access Protocol to Section 1 | Salience — check before goal urgency competes |
| 2 | Replace Section 6 with hardened text | Decision tree + concrete anti-patterns + WHY |
| 3 | Add Mandatory Session Start Checklist | Forced trigger — no action before self-check |
| 4 | Remove "(unless file < 5000 bytes)" from Anti-Scope | Source code = hard delegation, not sampling candidate |

## Expected Impact

- **Next session**: Orchestrator prompt starts with "⚠️ FILE ACCESS PROTOCOL" — impossible to miss
- **Pre-read gate**: Decision tree format forces yes/no decisions, not judgment calls
- **Anti-patterns**: Shows my exact Session 001 violations as examples of what not to do
- **Session start checklist**: Item 1 forces re-reading the protocol at session start
- **Source code**: Hardened from "unless < 5000 bytes" to "ALWAYS delegate. No exceptions."
