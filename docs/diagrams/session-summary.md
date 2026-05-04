# Orchestrator Diagrams — Session Summary

## Files

| # | File | Type | Focus |
|---|------|------|-------|
| 1 | `orchestrator-thinking-loop.mmd` | Flowchart (TD) | Drill-down thinking loop with 6 subgraphs |
| 2 | `orchestrator-thinking-loop-v2.mmd` | Flowchart (TD) | + Memory Manager companion, goal tracking, gate logging |
| 3 | `orchestrator-overview-v1.mmd` | Flowchart (LR) | 5-phase high-level overview |
| 4 | `orchestrator-overview-v2.mmd` | Flowchart (LR) | + ORIENT phase with light RAG baseline |
| 5 | `orchestrator-sequence-v1.mmd` | Sequence Diagram | Temporal agent interactions across full session |

## Design Decisions

- **Complexity = f(specificity, context)**: Vague requests decompose into sub-chunks; specific requests assessed per-chunk
- **Anti-patterns as decision nodes**: Over-delegating trivial tasks, going deep too early, autonomous gate-skipping — each redirects to correct path
- **Progressive deepening guard**: Before drilling deeper, check if scope is sufficiently broad for current stage
- **Two-tier RAG**: Light baseline retrieval at ORIENT (phase, goals, decisions); deep retrieval at GATHER (GraphRAG + Qdrant)
- **Memory Manager as companion entity**: Purple subgraph tracking Goal Graph, Phase Tracker, Context Index, Session State; dotted line integration with orchestrator flow
- **4-gate pipeline**: Approach → Spec → Code → Review, each with explicit user approval (red diamonds)
- **Continuous loop**: No terminal endpoint; rework paths go to ORIENT; session boundary at handoff

## Open Questions

- **Complexity thresholds**: What objectively distinguishes trivial/moderate/complex? Token count? Domain match confidence? Prior session knowledge?
- **Memory Manager implementation**: Agent, MCP tool, or internal service? What does "query memory manager" actually call?
- **Context buffer capacity**: Hard limit that forces mandatory synthesis? Or soft guidance?
- **Deepening granularity**: Is 3 layers (broad → medium → deep) sufficient, or should this be parameterized?
- **Specialist spawn conditions**: Beyond domain mismatch — token budget threshold? Cost/benefit heuristic?
- **Anti-pattern saturation**: Are there enough defined guardrails, or will edge cases slip through uncovered branches?
- **Light RAG scope**: Exactly which fields from project_notes constitute "light" vs "deep" retrieval?
- **Goal registration**: When a new goal is registered, does it auto-inherit parent project context or start clean?
