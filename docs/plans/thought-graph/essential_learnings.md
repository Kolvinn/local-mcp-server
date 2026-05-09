# Essential Learnings — Thought Graph Design Session

## Session Mechanics
- **Mermaid config format matters** — skills had outdated YAML-style config; the canonical format is JSON-style inside `---` frontmatter. See `docs/diagrams/orchestrator-overview-v2.mmd` lines 1-25 for the template. Triple-dash frontmatter with `config: { "key": "value" }` syntax, all keys/values double-quoted, includes `"look": "classic"` and border color variants.
- **Write diagrams to files, don't paste in chat** — user can't use inline mermaid. Always write `.mmd` files to `docs/diagrams/`.
- **Version your diagrams** — v1 → v4. Don't overwrite old versions without user approval (user rejected overwriting v3, directed to create v4).

## Design Learnings
- **Learnings started complex, got simplified** — original variants had weighted learnings stores modifying confidence. User simplified to: Decision Log (append-only), backed by LangSmith traces. Training agent (backlog) will eventually consume this.
- **LangSmith is sufficient** — Explorer+context7 research confirmed LangSmith traces capture full agent decision trees (agent → LLM → tool call → args → result), with feedback API for scoring. No custom decision storage needed.
- **Node taxonomy evolved** — from GraphRAG types (Goal, Decision, Bug) to thought-graph-specific types (Concept, Question, OptionNode, Option, Static). The existing edge contract (`docs/rag-dev/edge-contract.json`) is still relevant but the thought graph may use its own relationship vocabulary.
- **Confidence proposes, user gates** — not auto-progression. The orchestrator computes confidence and suggests moving to next stage; user confirms or rejects.
- **Three input types** — Specific (by ID, Qdrant lookup), General (semantic search), Direct Order (check for conflicts, then execute or ask). This pre-stage gates everything before WIDE expansion.
- **WIDE before DEEP is the core philosophy** — the orchestrator must map the full goal tree breadth-first before diving into any single branch. Confidence bar measures coverage completeness as the signal for "wide enough."

## Explorer Delegation
- **Use correct agent type** — `explorer` (our defined agent), not `explore` (thin search). Lesson already recorded in `docs/context/LEARNINGS.md` §16 but worth reinforcing.
- **context7 skill works well** — loaded by Explorer, produced thorough LangSmith research (340 lines, 6 questions answered).

## What We Didn't Do (by design)
- No node taxonomy for the training/auditor agent beyond the backlog diagram
- No confidence formula defined (f(coverage, question count, domain spread) is placeholder)
- No LangGraph state schema mapping
- No mapping of thought graph nodes to existing GraphRAG edge contract
- No decision on whether thought graph lives in same graph DB as RAG or separate
