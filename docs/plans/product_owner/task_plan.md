# Task Plan: Product Owner Agent Design

## Goal

Design a **product_owner** agent — a strategic orchestration layer that owns the "why" for both user context and project direction. This agent is project-agnostic, delegates all exploration/summarization to sub-agents, and serves as the single point of contact with the user. It will coordinate with specialist agent teams (planners, engineers, implementers) rather than executing directly.

## Scope

This is **agent design only** — no implementation. The output is a designed agent specification ready for creation.

## Current Phase

Phase 1

## Phases

### Phase 1: Requirements Gathering & Clarification
- [x] Clarify triggering conditions
- [x] Clarify relationship to existing coordinator (replacement, keep coordinator)
- [x] Clarify team structure (reference to agent-team file)
- [x] Clarify offloading behavior (strategic keeps, menial delegates)
- [x] Clarify project-agnostic nature (via reference files, not baked)
- [x] Clarify write delegation heuristic (small+low-context-cost → do, else delegate)
- [x] Clarify communication flow (PO is single point of contact)
- [x] **Status:** complete

### Phase 2: Role Definition & Mental Model
- [x] Define product_owner as strategic layer (vs tactical coordinator)
- [x] Define what it OWNS vs what it DELEGATES
- [x] Define relationship to user (single point of contact)
- [x] Define relationship to project goals
- [x] Define relationship to specialist agent teams
- [x] Draft conceptual model with boundaries and responsibilities
- [x] **Status:** complete (captured in SPEC.md)

### Phase 3: Triggering Design
- [x] Define triggering description with examples
- [x] Cover user interaction patterns (goal setting, direction requests, strategic questions)
- [x] Cover project interaction patterns (goal alignment, priority discussions)
- [x] Cover delegation triggering (when it spawns specialist agents)
- [x] Ensure triggering is clear and distinct from coordinator/expert/explorer
- [x] **Status:** complete (captured in SPEC.md)

### Phase 4: System Prompt Drafting
- [x] Draft role description (who it is, what it does)
- [x] Draft core responsibilities (strategic OWNERSHIP, not execution)
- [x] Draft delegation rules (what goes to whom)
- [x] Draft user interaction model (single point of contact, context translation)
- [x] Draft project context model (project-agnostic vs project-specific handling)
- [x] Draft output format for user communications
- [x] Draft edge cases (ambiguous goals, conflicting priorities, scope creep)
- [x] **Status:** complete (captured in SPEC.md)

### Phase 5: Agent Configuration
- [x] Choose agent identifier (product-owner)
- [x] Choose color for UI identification (magenta — strategic)
- [x] Choose model (inherit)
- [x] Define tool permissions (read allow, write deny by default, bash deny, webfetch/search allow, task allow all)
- [x] Define task permissions (all agents allowed)
- [x] **Status:** complete (captured in SPEC.md)

### Phase 6: Review & Refinement
- [ ] Review triggering for clarity and completeness
- [ ] Review system prompt for consistency and completeness
- [ ] Review agent configuration for least privilege
- [ ] Refine based on feedback
- [ ] **Status:** pending

### Phase 7: Final Specification
- [ ] Produce final agent specification document
- [ ] Confirm ready for file creation
- [ ] **Status:** pending

## Key Questions (ANSWERED)

| Question | Answer |
|----------|--------|
| 1. Replace coordinator? | Yes, but keep coordinator for backward compat |
| 2. Agent teams structure? | Reference to `agent-team` file (filled later) |
| 3. Communication flow? | User spawns agents directly; if talking to PO, route through PO |
| 4. Offloading scope? | Strategic keeps (intent, priorities, trade-offs); menial delegates |
| 5. Project context? | Via reference file(s) — memory/skill/RAG/user-provided |
| 6. Project memory writes? | Small+low-context-cost → do directly; otherwise always delegate |

## Decisions Made

| Decision | Rationale |
|----------|-----------|
| Project-agnostic design | Can be dropped into any project without modification |
| Aggressive delegation | Focuses on strategy, not exploration/summarization |
| User as single point of contact | Clarifies communication flow, avoids mixed messages |
| Separate from coordinator | Different mental model (strategic vs tactical orchestration) |

## Notes

- This plan is for **agent design only** — no code implementation
- Output will be a complete agent specification ready for creation
- Planning files live in `docs/plans/product_owner/`