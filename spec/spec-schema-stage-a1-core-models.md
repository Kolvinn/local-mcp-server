---
title: Stage A1 — Core Models, Enums, and Edge Contract
version: 1.1
date_created: 2026-05-05
last_updated: 2026-05-05
owner: RAG Flow Architect
tags: [schema, stage-a1, models, edge-contract, enums, graphrag]
---

# Introduction

This specification defines Stage A1 of the GraphRAG Memory Manager implementation plan (Option A: Qdrant-First, Graph-Later). Stage A1 delivers the foundational data models — Pydantic enums, the edge contract JSON, and a validation function — that all subsequent stages depend on. It produces zero infrastructure dependencies and is fully testable with `pytest` alone.

Parent spec: `docs/rag-dev/spec.md` §10 (Implementation Plan — Option A).

---

## 1. Purpose & Scope

**Purpose:** Establish the canonical enums (Category, Tag, NodeType, EdgeType) and the machine-readable edge contract that governs legal relationships between graph node types. Provide a reusable validation function that answers: *"Is edge `(source_label) -[relation]-> (target_label)` legal?"*

**Scope:**
- **IN:** 8-value Category enum, 4-dimension Tag taxonomy, 10 node type labels, ~50 edge type labels, edge-contract.json, `validate()` function, pytest tests.
- **OUT:** Qdrant client, graph DB client, embeddings, LLM calls, ingestion pipeline, chunker, classifier, extractor.

**Audience:** Implementer agents executing Stage A1; reviewer agents verifying output; downstream stages (A2–A6) referencing these models.

**Assumptions:**
- Python 3.13+ with `pydantic>=2.10.6` and `pytest>=8.3.4` (already in `pyproject.toml`).
- The `src/memory/` package does not yet exist and must be created.
- The `docs/rag-dev/edge-contract.json` file does not yet exist and must be generated.

---

## 2. Definitions

| Term | Definition |
|------|------------|
| **Category** | A singular, mutually exclusive classification assigned to each ingested chunk. One of 8 values. |
| **Tag** | A cross-cutting label in one of 4 dimensions (scope, domain, quality, phase). A chunk can have multiple tags. Managed by `TagRegistry` — bootstrap set from spec, extensible at runtime. |
| **NodeType** | The label applied to a graph node (e.g., `Bug`, `Component`, `Decision`). 10 types, nouns only. Closed set. |
| **EdgeType** | The label applied to a directed relationship between exactly two node types. Must be legal per the edge contract. Bootstrap set via `StrEnum`, extensible at runtime via `register_edge_type()`. |
| **Edge Contract** | A JSON file defining the bootstrap `(source_label, edge_label, target_label)` triples. Extended at runtime via `register_edge()`. Acts as a whitelist. |
| **TagRegistry** | A singleton registry class that holds the canonical tag taxonomy (4 dimensions, bootstrapped from spec values). Supports runtime registration of new tag values per dimension. |
| **Adjacency Matrix** | The internal representation of the edge contract: `{SourceLabel: {TargetLabel: [EdgeLabel, ...], ...}, ...}`. Merges bootstrap JSON with runtime-registered edges. |

---

## 3. Requirements, Constraints & Guidelines

- **REQ-001**: Category enum SHALL contain exactly 8 values: `technical_fact`, `bug`, `decision`, `goal`, `code_symbol`, `documentation`, `exploration_finding`, `session_memory`.
- **REQ-002**: Tag taxonomy SHALL define 4 dimensions (`scope`, `domain`, `quality`, `phase`), each with its own set of allowed values as defined in the parent spec §4 (Tags table).
- **REQ-003**: NodeType enum SHALL contain exactly 10 labels matching the Node Taxonomy table in parent spec §2: `Agent`, `Component`, `Document`, `Session`, `Goal`, `Decision`, `Bug`, `CodeEntity`, `Environment`, `Configuration`, `Chunk`.
- **REQ-004**: EdgeType enum SHALL contain every unique relationship label from the Edge Contract table in parent spec §3.
- **REQ-005**: Edge contract JSON SHALL use the adjacency matrix format: `{"SourceLabel": {"TargetLabel": ["EdgeType", ...], ...}, ...}`.
- **REQ-006**: `validate(source_label: str, relation: str, target_label: str) -> bool` SHALL return `True` iff the triple exists in the adjacency matrix.
- **REQ-007**: Enums SHALL be implemented as Python `StrEnum` (or compatible `Enum`) for string serialization compatibility.
- **REQ-008**: `TagRegistry` SHALL bootstrap with canonical tag values per dimension (from parent spec §4). `TagRegistry.register(dimension, value)` SHALL allow runtime addition of new tag values.
- **REQ-009**: `TagRegistry.is_valid(dimension, value) -> bool` SHALL return `True` if the value is known for the given dimension.
- **REQ-010**: `register_edge_type(label: str)` SHALL add a new edge type to the runtime-validated set. The label SHALL be uppercase, snake_case-valid (regex: `^[A-Z][A-Z_]*$`), and NOT collide with existing bootstrap or runtime edges.
- **REQ-011**: `register_edge(source: str, relation: str, target: str)` SHALL add a new triple to the runtime adjacency matrix. `source` must be a valid `NodeType`. `relation` must be a valid edge type (bootstrap or registered). `target` must be a valid `NodeType` (or wildcard `"*"`).
- **REQ-012**: `validate()` SHALL check both the bootstrap adjacency matrix (loaded from `edge-contract.json`) AND the runtime-registered adjacency matrix. Runtime-registered edges take precedence (override), but never remove bootstrap edges.
- **CON-001**: No external network calls, no database connections, no LLM calls. Pure Python, testable offline.
- **CON-002**: The edge contract JSON SHALL be loaded at module import time (eager loading) so validation failures surface immediately.
- **CON-003**: Enum values and edge contract are canonical. All downstream stages MUST import from these modules — no hardcoding string literals.
- **GUD-001**: Use `pathlib` for resolving the edge-contract.json path relative to the package directory.
- **GUD-002**: ValueError messages from `validate()` should indicate which part of the triple failed (source, relation, target, or combination).

---

## 4. Interfaces & Data Contracts

### 4.1 Category Enum (`src/memory/models.py`)

```python
from enum import StrEnum

class Category(StrEnum):
    TECHNICAL_FACT = "technical_fact"
    BUG = "bug"
    DECISION = "decision"
    GOAL = "goal"
    CODE_SYMBOL = "code_symbol"
    DOCUMENTATION = "documentation"
    EXPLORATION_FINDING = "exploration_finding"
    SESSION_MEMORY = "session_memory"
```

### 4.2 Tag Taxonomy & Registry (`src/memory/models.py`)

Tags are managed by a `TagRegistry` singleton rather than fixed enums. This allows the Memory Manager to register new tag values discovered during operation without code changes.

```python
from typing import ClassVar

class TagDimension(StrEnum):
    SCOPE = "scope"
    DOMAIN = "domain"
    QUALITY = "quality"
    PHASE = "phase"


class TagRegistry:
    """
    Singleton registry for tag values across 4 dimensions.

    Bootstrap values are loaded from the canonical taxonomy. New values
    can be registered at runtime via register().
    """
    _instance: ClassVar["TagRegistry | None"] = None

    # Canonical bootstrap values per dimension (from parent spec §4)
    _BOOTSTRAP: ClassVar[dict[str, set[str]]] = {
        "scope":    {"ollama", "qdrant", "memgraph", "traefik", "opencode"},
        "domain":   {"infra", "code", "architecture", "testing", "data", "security", "ux", "devops"},
        "quality":  {"bug", "workaround", "verified", "deprecated", "unstable", "critical"},
        "phase":    {"orient", "gather", "spec", "code", "review", "deploy"},
    }

    def __new__(cls) -> "TagRegistry":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._tags: dict[str, set[str]] = {
                dim: values.copy() for dim, values in cls._BOOTSTRAP.items()
            }
        return cls._instance

    def register(self, dimension: str, value: str) -> bool:
        """
        Register a new tag value for a dimension.

        Args:
            dimension: Must be a member of TagDimension.
            value: The tag string (lowercase, non-empty).

        Returns:
            True if the value was newly added, False if already present.

        Raises:
            ValueError: If dimension is not a valid TagDimension or value is empty.
        """
        ...

    def is_valid(self, dimension: str, value: str) -> bool:
        """Check if a tag value is known for the given dimension."""
        ...

    def list_dimension(self, dimension: str) -> list[str]:
        """Return all tag values for a dimension, sorted alphabetically."""
        ...

    def list_all(self) -> dict[str, list[str]]:
        """Return {dimension: [values]} for all dimensions."""
        ...

    def reset(self) -> None:
        """Reset to bootstrap values. For testing only."""
        ...
```

**Design note:** The old `ScopeTag`, `DomainTag`, `QualityTag`, `PhaseTag` enums are **removed**. Downstream code uses `TagRegistry().is_valid("scope", "ollama")` instead of `ScopeTag.OLLAMA`.

### 4.3 NodeType Enum (`src/memory/models.py`)

```python
class NodeType(StrEnum):
    AGENT = "Agent"
    COMPONENT = "Component"
    DOCUMENT = "Document"
    SESSION = "Session"
    GOAL = "Goal"
    DECISION = "Decision"
    BUG = "Bug"
    CODE_ENTITY = "CodeEntity"
    ENVIRONMENT = "Environment"
    CONFIGURATION = "Configuration"
    CHUNK = "Chunk"
```

Labels match parent spec §2 (Node Taxonomy) exactly, including PascalCase to match Cypher node label conventions.

### 4.4 EdgeType (`src/memory/models.py`)

**Bootstrap:** A `StrEnum` with the following members (the canonical set from parent spec §3):

> AFFECTS, LOCATED_IN, TRIGGERED_BY, REPRODUCED_IN, DISCOVERED_IN, DUPLICATE_OF, CAUSED_BY, RESOLVES, SELECTS, SATISFIES, SUPERSEDES, CONFLICTS_WITH, IMPLEMENTED_BY, PARENT_OF, BLOCKS, MOTIVATED, BLOCKED_BY, REPORTED, PROPOSED, OWNS, PARTICIPATED_IN, CALLS, EXTENDS, IMPLEMENTS, OVERRIDES, DEPENDS_ON, BELONGS_TO, READS, HOSTS, DEFINED_IN, SETS, DEPLOYED_IN, FOLLOWS, PRODUCED, WORKED_ON, RECORDS, DOCUMENTS, EXTRACTED_TO

**Runtime extensibility:** The `src/memory/models.py` module SHALL also expose:

- `register_edge_type(label: str) -> bool` — registers a new edge type at runtime. Constraint: must be uppercase, match `^[A-Z][A-Z_]*$`, and not collide with existing members or prior registrations. Returns `True` if newly added, `False` if duplicate.
- `is_edge_type(label: str) -> bool` — returns `True` if the label is a known edge type (bootstrap or registered).

### 4.5 Edge Contract JSON (`docs/rag-dev/edge-contract.json`)

Format: adjacency matrix where outer key = source node label, inner key = target node label, value = list of legal edge type strings.

```json
{
  "Bug": {
    "Component": ["AFFECTS"],
    "CodeEntity": ["LOCATED_IN"],
    "Configuration": ["TRIGGERED_BY"],
    "Environment": ["REPRODUCED_IN"],
    "Session": ["DISCOVERED_IN"],
    "Bug": ["DUPLICATE_OF", "CAUSED_BY"]
  },
  "Decision": {
    "Bug": ["RESOLVES"],
    "Component": ["SELECTS"],
    "Goal": ["SATISFIES"],
    "Decision": ["SUPERSEDES", "CONFLICTS_WITH"],
    "CodeEntity": ["IMPLEMENTED_BY"]
  },
  "Goal": {
    "Goal": ["PARENT_OF", "BLOCKS", "SUPERSEDES"],
    "Bug": ["BLOCKED_BY"],
    "Decision": ["MOTIVATED"]
  },
  "Agent": {
    "Bug": ["REPORTED"],
    "Decision": ["PROPOSED"],
    "CodeEntity": ["OWNS"],
    "Session": ["PARTICIPATED_IN"]
  },
  "CodeEntity": {
    "CodeEntity": ["CALLS", "EXTENDS", "IMPLEMENTS", "OVERRIDES", "DEPENDS_ON"],
    "Component": ["BELONGS_TO"],
    "Configuration": ["READS"]
  },
  "Component": {
    "Component": ["DEPENDS_ON", "HOSTS"],
    "Environment": ["DEPLOYED_IN"]
  },
  "Configuration": {
    "Environment": ["DEFINED_IN"],
    "Component": ["SETS"]
  },
  "Session": {
    "Session": ["FOLLOWS"],
    "Document": ["PRODUCED"],
    "Goal": ["WORKED_ON"]
  },
  "Document": {
    "Decision": ["RECORDS"],
    "CodeEntity": ["DOCUMENTS"]
  },
  "Chunk": {
    "*": ["EXTRACTED_TO"]
  }
}
```

**Special handling for `"*"` target in Chunk:** The `"*"` wildcard means `(:Chunk)-[:EXTRACTED_TO]->(:ANY)` is always legal. The validator must handle this.

**Runtime extensibility:** The `edge_validator.py` module SHALL also expose:

- `register_edge(source: str, relation: str, target: str) -> bool` — registers a new legal triple in the in-memory adjacency matrix. `source` and `target` must be valid `NodeType` values (or `"*"` for wildcard target). `relation` must be a known edge type (bootstrap `EdgeType` or via `register_edge_type()`). Returns `True` if newly added, `False` if already present.
- `get_registered_edges() -> list[tuple[str, str, str]]` — returns all runtime-registered triples (for testing/debugging).

Runtime-registered edges DO NOT persist to `edge-contract.json` in Stage A1. They live in memory only. Persistence is a future concern.

### 4.6 Validation Function (`src/memory/edge_validator.py`)

```python
def validate(source_label: str, relation: str, target_label: str) -> bool:
    """
    Check if a proposed edge triple is legal per the edge contract.

    Args:
        source_label: The label of the source node (e.g., "Bug", "Component").
        relation: The edge type (e.g., "AFFECTS", "DEPENDS_ON").
        target_label: The label of the target node (e.g., "Component", "Environment").

    Returns:
        True if the triple exists in the edge contract, False otherwise.

    Raises:
        ValueError: If source_label or relation is not a recognized enum value.
    """
    ...
```

**Behavior:**
1. Validate that `source_label` is a member of `NodeType`.
2. Validate that `relation` is a known edge type (bootstrap `EdgeType` OR runtime-registered via `register_edge_type()`).
3. Check BOTH the bootstrap adjacency matrix (from `edge-contract.json`) AND the runtime-registered adjacency matrix. If either contains the triple → return `True`.
4. Special case: if source's target mapping includes `"*"` in either matrix, ALL target labels are accepted for that relation.
5. Return `False` for illegal combinations.

---

## 5. Acceptance Criteria

- **AC-001**: Given `import src.memory.models`, When all enums are accessed, Then `Category`, `NodeType`, `EdgeType`, and all Tag enums are importable and contain exactly the values specified above.
- **AC-002**: Given a valid triple `("Bug", "AFFECTS", "Component")`, When `validate("Bug", "AFFECTS", "Component")` is called, Then return `True`.
- **AC-003**: Given an illegal triple `("Bug", "PROPOSED", "Component")`, When `validate("Bug", "PROPOSED", "Component")` is called, Then return `False`.
- **AC-004**: Given `(:Chunk)-[:EXTRACTED_TO]->(:Session)`, When `validate("Chunk", "EXTRACTED_TO", "Session")` is called, Then return `True` (wildcard target).
- **AC-005**: Given `(:Chunk)-[:EXTRACTED_TO]->(:ANY)`, When `validate("Chunk", "EXTRACTED_TO", "ArbitraryLabel")` is called, Then return `True`.
- **AC-006**: Given an invalid node label `"Foo"`, When `validate("Foo", "AFFECTS", "Component")` is called, Then raise `ValueError`.
- **AC-007**: Given an invalid edge label `"FOO"`, When `validate("Bug", "FOO", "Component")` is called, Then raise `ValueError`.
- **AC-008**: All 11 source labels in edge-contract.json SHALL have at least one target entry (non-empty adjacency list).
- **AC-009**: The edge-contract.json SHALL be valid JSON, parseable by `json.load()`.
- **AC-010**: `pytest` executed from `src/` passes with zero failures.
- **AC-011**: Given `TagRegistry().register("scope", "new-service")`, When `is_valid("scope", "new-service")` is called, Then return `True`.
- **AC-012**: Given duplicate registration `TagRegistry().register("scope", "ollama")`, When called, Then return `False` (already present).
- **AC-013**: Given `register_edge_type("CONFIGURES")`, When `validate("Agent", "CONFIGURES", "Component")` after also calling `register_edge("Agent", "CONFIGURES", "Component")`, Then return `True`.
- **AC-014**: Given `register_edge_type("INVALID lowercase")`, When called, Then raise `ValueError`.
- **AC-015**: Given `TagRegistry().reset()`, When checking after reset, Then only bootstrap values are present.

---

## 6. Test Automation Strategy

- **Test Level:** Unit (no integration required — all pure logic).
- **Framework:** `pytest` (already in `pyproject.toml`).
- **Test Location:** `src/tests/test_models.py` (new file).
- **Test Structure:**
  - `test_category_enum_values` — verify 8 values, no extras.
  - `test_node_type_enum_values` — verify 11 values.
  - `test_edge_type_enum_values` — verify exact count of bootstrap edge types.
  - `test_tag_registry_bootstrap` — verify all 4 dimensions have expected bootstrap values.
  - `test_tag_registry_register_new` — register new tag, verify is_valid returns True.
  - `test_tag_registry_register_duplicate` — duplicate registration returns False.
  - `test_tag_registry_reset` — reset clears registered tags back to bootstrap.
  - `test_tag_registry_list_all` — verify list_all() returns structured dict.
  - `test_register_edge_type_valid` — register new edge type, verify is_edge_type returns True.
  - `test_register_edge_type_invalid` — invalid format raises ValueError.
  - `test_register_edge` — register new triple, verify validate() accepts it.
  - `test_register_edge_rejects_unknown_relation` — edge type not registered → ValueError.
  - `test_register_edge_wildcard_target` — register edge with `"*"` target, verify wildcard behavior.
  - `test_edge_contract_parseable` — verify JSON loads without error.
  - `test_edge_contract_coverage` — every source node in contract maps to valid NodeType.
  - `test_validate_legal_edge` — parametrized: feed every legal triple from contract, assert True.
  - `test_validate_illegal_edge` — feed known-bad combinations, assert False.
  - `test_validate_wildcard_chunk` — Chunk→EXTRACTED_TO→any target returns True.
  - `test_validate_invalid_source_label` — raises ValueError.
  - `test_validate_invalid_relation` — raises ValueError.
  - `test_validate_enum_roundtrip` — NodeType("Bug") == NodeType.BUG, etc.
- **Test Data:** No fixtures needed — the edge contract JSON itself is the ground truth. Parametrized tests read the contract to generate legal triple test cases.

---

## 7. Rationale & Context

**Why models first:** Every subsequent stage (A2 classifier, A3 extractor, A4 linkage, A5 sessions, A6 retrieval) depends on these enums. Building them first with strict validation prevents cascading typos and contract violations later.

**Why StrEnum:** Downstream code will serialize these to JSON (Qdrant payloads, Cypher queries, MCP tool responses). `StrEnum` gives `str` compatibility with zero conversion code.

**Why eager JSON loading:** If the edge contract file is malformed or missing, the `validate()` function should fail fast at import time rather than silently accepting all edges later in the pipeline.

**Why adjacency matrix format:** `{Source: {Target: [Edges]}}` is the minimal representation that answers "what edges can go from X to Y?" in O(1) lookup. Flat lists of triples would require O(n) scan.

**Why `"*"` wildcard for Chunk:** The `:Chunk` reference node bridges Qdrant to the graph. It needs to point to ANY node type (`EXTRACTED_TO`). Enumerating all 10 node types would create 10 redundant entries and require updates whenever a new node type is added.

**Design trade-off — case sensitivity:** The contract uses exact string matching (case-sensitive). This is intentional — Cypher labels are case-sensitive, and relaxing this would hide bugs.

---

## 8. Dependencies & External Integrations

### Infrastructure Dependencies
- **INF-001**: None. This stage requires no running services (no Qdrant, no Memgraph, no Ollama).

### Technology Platform Dependencies
- **PLT-001**: Python 3.13+ (already satisfied by `pyproject.toml` `requires-python>=3.13`).
- **PLT-002**: Pydantic >=2.10.6 (already in `pyproject.toml`).
- **PLT-003**: pytest >=8.3.4 (already in `pyproject.toml`).

### Data Dependencies
- **DAT-001**: `docs/rag-dev/edge-contract.json` — generated by this stage, consumed by A3 (extractor) and A6 (retrieval).

---

## 9. Examples & Edge Cases

### Example 1: Valid triple — direct match

```python
from src.memory.edge_validator import validate
validate("Bug", "AFFECTS", "Component")  # → True
```

### Example 2: Valid triple — multiple edges between same pair

```python
validate("Bug", "CAUSED_BY", "Bug")   # → True (Bug→Bug self-loop with CAUSED_BY)
validate("Bug", "DUPLICATE_OF", "Bug") # → True (Bug→Bug self-loop with DUPLICATE_OF)
```

### Example 3: Illegal triple — right edge, wrong direction

```python
validate("Component", "AFFECTS", "Bug")  # → False
# AFFECTS only goes Bug→Component, not Component→Bug
```

### Example 4: Chunk wildcard

```python
validate("Chunk", "EXTRACTED_TO", "Bug")          # → True
validate("Chunk", "EXTRACTED_TO", "Component")    # → True
validate("Chunk", "EXTRACTED_TO", "Nonexistent")  # → True (wildcard)
```

### Example 5: Non-`EXTRACTED_TO` edge from Chunk

```python
validate("Chunk", "AFFECTS", "Component")  # → False
# Chunk only has EXTRACTED_TO, and only to wildcard target
```

### Example 6: ValueError for unknown labels

```python
validate("Foobar", "AFFECTS", "Component")  # → ValueError: "Foobar" is not a valid NodeType
validate("Bug", "FROBNICATES", "Component") # → ValueError: "FROBNICATES" is not a valid EdgeType
```

### Example 7: Runtime tag registration

```python
from src.memory.models import TagRegistry

registry = TagRegistry()
registry.register("scope", "kubernetes")     # → True (new)
registry.register("scope", "kubernetes")     # → False (duplicate)
registry.is_valid("scope", "kubernetes")     # → True
registry.is_valid("scope", "nonexistent")    # → False
registry.reset()                             # back to bootstrap
```

### Example 8: Runtime edge registration

```python
from src.memory.edge_validator import validate, register_edge_type, register_edge

# Register a new edge type discovered at runtime
register_edge_type("CONFIGURES")             # → True
register_edge_type("configures")             # → ValueError: must match ^[A-Z][A-Z_]*$

# Register the triple in the adjacency matrix
register_edge("Agent", "CONFIGURES", "Component")  # → True
validate("Agent", "CONFIGURES", "Component")        # → True (runtime-registered)
validate("Component", "CONFIGURES", "Agent")        # → False (wrong direction)

# register_edge validates inputs
register_edge("Foo", "CONFIGURES", "Component")     # → ValueError: "Foo" not a NodeType
register_edge("Agent", "UNKNOWN", "Component")      # → ValueError: "UNKNOWN" not a known edge type
```

---

## 10. Validation Criteria

| # | Criterion | Method |
|---|-----------|--------|
| VC-001 | All enums contain exact values per §4.1–4.4 | `assert len(Category) == 8`, etc. |
| VC-002 | `edge-contract.json` is valid JSON | `json.load()` succeeds |
| VC-003 | Every source label in contract is a valid NodeType | Check each key against `NodeType.__members__` |
| VC-004 | Every target label in contract (except `"*"`) is a valid NodeType | Check each inner key against `NodeType.__members__` |
| VC-005 | Every edge label in contract is a valid EdgeType | Check each value against `EdgeType.__members__` |
| VC-006 | `validate()` correctly classifies all legal triples from contract | Parametrized exhaustive test |
| VC-007 | `validate()` correctly classifies known-illegal triples | Negative test cases |
| VC-008 | `validate()` raises ValueError on invalid source/edge labels | Exception assertion |
| VC-009 | `TagRegistry` bootstraps correct values per dimension | Count assertion per dimension |
| VC-010 | `register_edge_type()` rejects invalid formats (lowercase, empty, special chars) | Parametrized negative tests |
| VC-011 | `register_edge()` accepts wildcard `"*"` target and validates source/relation | Positive + negative tests |
| VC-012 | `validate()` merges bootstrap + runtime edges correctly | Cross-check with registered triples |

---

## 11. Implementation Tasks (for implementer)

These are the discrete, digestible units of work. Each task produces exactly one file or one logical unit.

| Task | File | Description | Estimated Complexity |
|------|------|-------------|---------------------|
| **T1** | `docs/rag-dev/edge-contract.json` | Generate the adjacency matrix JSON from §4.5 — copy verbatim from the spec. | Trivial |
| **T2** | `src/memory/__init__.py` | Create package init. Re-export key symbols: `Category`, `NodeType`, `EdgeType`, `TagDimension`, `TagRegistry`, `register_edge_type`, `is_edge_type`, `validate`, `register_edge`, `get_registered_edges`. | Trivial |
| **T3** | `src/memory/models.py` | Implement: `Category` (StrEnum, 8 values), `NodeType` (StrEnum, 11 values), `EdgeType` (StrEnum, ~38 values), `TagDimension` (StrEnum, 4 values), `TagRegistry` (singleton with bootstrap, register(), is_valid(), list_dimension(), list_all(), reset()), `register_edge_type()`, `is_edge_type()`. | Medium |
| **T4** | `src/memory/edge_validator.py` | Implement `validate()`, `register_edge()`, `get_registered_edges()`. Load edge-contract.json at module level. Merge bootstrap + runtime adjacency matrices. Handle wildcard `"*"`. Raise ValueError on invalid labels. | Medium |
| **T5** | `src/tests/test_models.py` | Pytest suite covering AC-001 through AC-015 + examples from §9. Parametrize legal triple test from edge-contract.json. Test TagRegistry bootstrap, registration, dedup, reset. Test edge type registration validation. | Medium |

**Task dependencies:** T1 and T3 can run in parallel. T4 depends on T1 and T3. T5 depends on T3 and T4.

---

## 12. Related Specifications

- Parent: `docs/rag-dev/spec.md` — full GraphRAG Memory Manager specification v0.2
- Upstream: `docs/rag-dev/findings.md` — technical decisions and rationale
- Downstream: Stage A2 (`spec-schema-stage-a2-qdrant-pipeline.md` — not yet created)
- Downstream: Stage A3 (`spec-schema-stage-a3-graph-integration.md` — not yet created)
- Exploration: `docs/rag-dev/exploration-summary.md` — pre-A1 codebase analysis
