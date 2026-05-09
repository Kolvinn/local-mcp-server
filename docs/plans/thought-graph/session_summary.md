# Session Summary — Orchestrator Thought Graph Design

**Date:** 2026-05-09
**Status:** Goal refinement (WIDE). No implementation.

## What We're Designing

An evolving **thought graph** (stored in GraphRAG: Qdrant + graph DB) that the orchestrator builds, queries, and modifies as conversation with the user grows. The orchestrator goes **WIDE before DEEP** — expanding the goal tree breadth-first, placing :Question nodes at unresolved leaves, then resolving via user input or agent delegation once coverage is satisfactory.

## What We Produced

### Diagrams (in `docs/diagrams/`)
| File | Description |
|------|-------------|
| `thought-graph-concept-v1.mmd` | Rough first sketch (superseded) |
| `thought-graph-concept-v2-confidence.mmd` | Confidence-gated variant with staged expansion |
| `thought-graph-concept-v2-staged.mmd` | Explicit WIDE→ASSESS→DEEP gates with user approval |
| `thought-graph-concept-v2-weighted.mmd` | Weighted graph edges + confidence hybrid |
| `thought-graph-concept-v3-confidence.mmd` | Refined: new node taxonomy, concrete example, user gates |
| `thought-graph-concept-v4-confidence.mmd` | Adds PRE-STAGE input classification (superseded) |
| **`thought-graph-concept-v5-session-scope.mmd`** | **Active version**: persistent thought graph vs ephemeral session, scope checking, tangent detection, session-end merge |
| `trainer-auditor-agent-backlog.mmd` | Trainer/Auditor backlog concept (INGEST→REVIEW→PRODUCE) |

### Research
- `docs/exploration/langsmith-trace-granularity.md` — LangSmith traces are granular enough to serve as decision log; don't need custom storage.

## Active Design (v5)

### Core Distinction
- **Thought Graph**: persistent, cross-session project brain (all concepts, questions, decisions)
- **Session**: ephemeral lens positioned within the thought graph
- **Orchestrator**: constantly checks scope — is input on-scope (proceed), off-scope/tangent (ask user: update map? new session goal? ignore?), or direct order?

### Node Taxonomy
- **`:Concept`** — thing being explored (requirement, idea, goal)
- **`:Question`** — unresolved inquiry blocking a concept
- **`:OptionNode`** — groups resolution paths for a question
- **`:Option`** — single resolution path (delegate, ask user, research)
- **`:Static`** — known fact, doesn't need resolution

### Option Metadata (not yet in diagrams)
- Statuses: `approved`, `waiting`, `superseded_by`
- Edge states: `UNDECIDED`, `SELECTED`, `REJECTED`

### Relationships
- Concept → Question: `RELIES_ON`
- Question → OptionNode: `DEPENDS_ON`
- OptionNode → Option: `HAS_OPTION`
- Concept → Static: `INFORMS`

### Flow Stages
1. **Scope Check**: On-scope / off-scope (tangent) / direct order — positioned within thought graph
2. **PRE-STAGE**: Classify input (specific ID / general), Qdrant lookup, user confirms scope
3. **WIDE**: Expand session-scoped concepts, place questions, generate options, compute confidence, user gate
4. **DEEP**: Resolve questions via selected options, record decisions
5. **SYNTHESIZE → GATE**: Reduce to approach, user approval
6. **Session End**: Merge outcomes into persistent thought graph, update option statuses

### Key Mechanics
- **Confidence bar** (0.0–1.0) computed from coverage, question count, domain spread — proposes stage transitions, user approves
- **Decision Log** (append-only) backed by LangSmith traces — what + agent + action + outcome
- **Training Agent** (backlog) — will consume decision log, classify good/okay/bad with user, produce edge weights

## Next Session
- Continue refining v4 diagram
- Pressure-test node taxonomy completeness
- Define confidence formula details
- Map to LangGraph state schema (Phase 3 of overhaul plan)

## Files for Context (read, not followed)
- `docs/plans/overhaul/*` (variation matrix, findings, progress, task plan)
- `docs/rag-dev/*` (GraphRAG spec, edge contract, session handoff)
- `docs/diagrams/orchestrator-overview-v2.mmd`
- `docs/context/LEARNINGS.md`
