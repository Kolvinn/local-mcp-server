# Agent Variation Matrix

**Date:** 2026-05-08
**Status:** Approved. Core 5 types + variation profiles solidified.
**Source:** SESSION_HANDOFF.md, architecture_chat.md, agent prompt redesign session

---

## 1. Design Principle

Agents are **generic types with config-driven variations**. The prompt defines interaction mechanics (how to think, communicate, what to read/write). Domain expertise comes from skills loaded at spawn time and context files pointed to by the orchestrator. Variations are configuration, not prompt changes.

**Prompt stays generic. Variation = model + skills + context injection.**

---

## 2. Core Types (5)

| Type | Role | Prompt | Key Property |
|------|------|--------|-------------|
| **Orchestrator** | Sole user contact, delegation, approval gates | orchestrator.md | Never reads full content, only summaries + file paths |
| **System Thinker** | Domain design, briefs, pseudocode specs | system_thinker.md | Wide-before-deep. Writes briefs → architect reads them |
| **Implementer** | Code translation from approved specs | implementer.md | Reads specs, never briefs. Literal translation only |
| **Auditor** | 5-check verification framework | auditor.md | Reads specs + code, never briefs. Never fixes, only reports |
| **Explorer** | Read-only codebase scout | explorer.md | Returns only "complete"/"error", writes to docs/exploration/ |

**Retired types:**
- ~~Reviewer~~ → absorbed into Auditor (5-check framework supersedes single-dimension review)
- ~~Coordinator~~ → redundant with Orchestrator
- ~~RAG Architect~~ → absorbed into System Thinker as `rag_thinker` variation

**Backlog types:** Researcher, Tester (not in MVP scope)

---

## 3. Variation Profiles

| Variation | Base Type | Model | Skills (injected at spawn) | Context Files (pointed to) |
|-----------|-----------|-------|---------------------------|---------------------------|
| **orchestrator** | — (primary) | glm-5.1 | planning-with-files | All `docs/context/*` (pointers only) |
| **strategic_thinker** | system_thinker | qwen-3.6-plus | sequential-thinking, create-specification | constraints.md, services.md, stack.md |
| **rag_thinker** | system_thinker | qwen-3.6-plus | qdrant-vector-search, qdrant-search-quality, langchain-rag, sequential-thinking | constraints.md, stack.md, RAG specs |
| **architect_thinker** | system_thinker | qwen-3.6-plus | architecture-patterns, agent-pseudocode, create-specification, mermaid-diagrams, sequential-thinking | constraints.md, stack.md, conventions.md, the brief |
| **python_implementer** | implementer | deepseek-v4-flash | python-expert, python-best-practices, pydantic, python-type-safety | constraints.md, conventions.md, stack.md, the spec |
| **infra_implementer** | implementer | deepseek-v4-flash | context7 | constraints.md, stack.md, the spec |
| **code_auditor** | auditor | deepseek-v4-pro | python-code-review, pytest, pytest-coverage | constraints.md, conventions.md, the spec, implemented files |
| **codebase_explorer** | explorer | deepseek-v4-flash | (none — built-in tools sufficient) | Targeted query + paths |
| **dependency_explorer** | explorer | deepseek-v4-flash | (none) | Targeted query + paths |

**Orchestrator has no variations.** It's always the same — GLM-5.1, generic orchestration skills only.

**Explorer doesn't need skills.** Its tools are built-in (glob, grep, rg, git, read). Context is whatever the orchestrator points it at.

---

## 4. File-Based Handoff Protocol

### Flow

```
USER → ORCHESTRATOR (summary + file pointers only)
         │
         ├─► STRATEGIC/ARCHITECT THINKER
         │     Reads: docs/context/*, docs/exploration/*
         │     Writes: docs/briefs/{name}.md
         │     Returns: 2-3 bullet summary
         │
         ├─► ARCHITECT THINKER (after brief approval)
         │     Reads: docs/context/*, docs/briefs/*, docs/exploration/*
         │     Writes: docs/specs/{name}.md
         │     Returns: 2-3 bullet summary
         │
         ├─► IMPLEMENTER (after spec approval)
         │     Reads: docs/specs/*, docs/context/*, source code
         │     Writes: source code files
         │     Returns: change summary + spec compliance
         │
         ├─► AUDITOR (after implementation)
         │     Reads: docs/specs/*, source code, docs/context/conventions.md, dependency maps
         │     Writes: audit findings (inline return)
         │     Returns: structured findings
         │
         └─► EXPLORER (on demand)
               Reads: whatever the orchestrator points to
               Writes: docs/exploration/{name}.md
               Returns: "complete" or "error" only
```

### Key Rule: After Every Agent, Bubble to User

The orchestrator never pipelines stages autonomously. After each agent completes:
1. Receive 2-3 bullet summary
2. Present to user
3. Get approval
4. Then spawn next agent

### Read/Write Boundaries Per Type

| Type | READS | WRITES | NEVER READS |
|------|-------|--------|-------------|
| Orchestrator | Summaries, file paths | Pointers, delegation prompts | Full content of briefs/specs/code |
| System Thinker | `docs/context/*`, `docs/exploration/*` | `docs/briefs/{name}.md`, `docs/specs/{name}.md`, `docs/learnings/*` | Source code, other agents' specs |
| Implementer | `docs/specs/*`, `docs/context/*`, source code | Source code files, `docs/learnings/*` | Briefs (gets spec, not brief) |
| Auditor | `docs/specs/*`, source code, `docs/context/conventions.md`, dependency maps | Audit findings (inline), `docs/learnings/*` | Briefs (gets spec, not brief) |
| Explorer | Whatever orchestrator points to | `docs/exploration/{name}.md` | Briefs, specs (gets targeted queries) |

---

## 5. Model Rationale

| Model | Assigned To | Why |
|-------|------------|-----|
| **GLM-5.1** | Orchestrator | Long-horizon endurance (600+ iteration loops, SWE-bench Pro 58.4%). Maintains global state and user intent across delegation chains. |
| **Qwen 3.6 Plus** | System Thinker (all variations) | 1M token context window. Essential for reading entire system architecture in one pass. Hybrid Gated DeltaNet maintains retrieval accuracy across window. |
| **DeepSeek V4 Pro** | Auditor | Zero-shot precision, lowest hallucination rate. Critical for catching logic flaws and security vulnerabilities. BenchLM 87. |
| **DeepSeek V4 Flash** | Implementer, Explorer | 15x cheaper than Pro with near-parity for boilerplate and standard logic. Fast iteration for code writing and codebase scanning. |

---

## 6. Upgrade Path

When the container system comes online (Phase 5-6 implementation):

- Each variation maps to a Dockerfile template + Flox manifest
- New variations = new row in config, no code or prompt changes
- Model swaps = model field change, no prompt changes
- Skill upgrades = swap skills in config, prompts untouched
- `flox_packages` field gets filled during container design phase

---

## 7. Decisions Log

| Decision | Rationale |
|----------|-----------|
| RAG Architect absorbed into System Thinker | Same base type (domain design). Different skills = different variation. Avoids type proliferation. |
| Code Auditor + Integration Auditor merged | Same thinking style, same 5-check framework. Context injection differentiates per task. |
| Architect is a System Thinker variation, not separate type | Architects ask "how does it fit?" not "why?" — but the interaction mechanics (wide-deep, file output, skill loading) are identical. Only skills + context differ. |
| Orchestrator never reads full content | Token conservation. Orchestrator owns context direction, not content depth. |
| Prompts stay generic | Variations are config. When containers arrive, config becomes environment injection. Zero prompt changes needed. |
| Explorer doesn't get skills | Built-in tools (glob, grep, rg, read, git) cover all exploration needs. Adding skills would violate the "scout" role definition. |