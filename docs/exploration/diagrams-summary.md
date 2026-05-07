# Diagrams Summary

**7 .mmd files + 1 session-summary.md** modeling a multi-agent orchestrator architecture.

## What Each Diagram Models

| File | Type | Focus |
|------|------|-------|
| `orchestrator-overview-v1.mmd` | LR flowchart | 5-phase overview: Clarify → Assess → Gather → Synthesize → Gate |
| `orchestrator-overview-v2.mmd` | LR flowchart | v1 + **ORIENT phase 0** with Light RAG baseline retrieval |
| `orchestrator-sequence-v1.mmd` | Sequence diagram | Temporal agent interactions: User ↔ Orchestrator ↔ MemoryMgr, Explorer, MemoryAgent, Implementer, Reviewer |
| `orchestrator-thinking-loop.mmd` | TD flowchart | Drill-down thinking loop: specificity → chunk → complexity → context → 4-gate pipeline |
| `orchestrator-thinking-loop-v2.mmd` | TD flowchart | v1 + **Memory Manager** companion subgraph (Goal Graph, Phase Tracker, Context Index, Session State) |
| `loopold.mmd` | TD flowchart | Earlier iteration with clarification loop and anti-pattern guard nodes |

## Key Architectural Relationships

- **Orchestrator** is central — spawns Explorer (filesystem), Memory Agent (GraphRAG+Qdrant), Specialist (domain), Implementer, and Reviewer
- **Memory Manager** (v2 only) is a persistent companion storing goals, phase, context cache, session handoff
- Two-tier RAG: light retrieval at ORIENT (phase/goals/decisions), deep at GATHER (GraphRAG + Qdrant vector)
- **4-gate user approval pipeline**: Approach → Spec → Code → Review, each with explicit user sign-off (red diamonds)
- Rework paths always return to ORIENT, not just the previous phase

## Agent Flow Design Insights

- Anti-patterns codified as explicit decision nodes (over-delegating, going deep too early, autonomous gate-skipping)
- Progressive deepening guard prevents narrow deep-dives before broad context is gathered
- Continuous loop — no terminal endpoint; session boundary at handoff.md write

## Session Summary Key Points

The design is in-progress with 8 open questions: complexity thresholds, Memory Manager implementation (agent vs MCP vs service), context buffer limits, deepening granularity, specialist spawn heuristics, anti-pattern coverage, light vs deep RAG scope, and goal registration context inheritance.
