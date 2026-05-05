"""Tests for Stage A1 core models, enums, edge contract, and validation.

Covers acceptance criteria AC-001 through AC-015 and all examples from §9
of the Stage A1 spec.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from memory.edge_validator import (
    _BOOTSTRAP_MATRIX,
    get_registered_edges,
    register_edge,
    validate,
)
from memory.models import (
    Category,
    EdgeType,
    NodeType,
    TagDimension,
    TagRegistry,
    is_edge_type,
    register_edge_type,
)

# ---------------------------------------------------------------------------
# Path to the edge contract — loaded here for contract-level tests
# ---------------------------------------------------------------------------
_CONTRACT_PATH = (
    Path(__file__).resolve().parent.parent.parent
    / "docs"
    / "rag-dev"
    / "edge-contract.json"
)


# ===================================================================
# Enum tests
# ===================================================================


class TestCategoryEnum:
    """AC-001 (partial): Category has exactly 8 values with correct names."""

    def test_category_enum_values(self) -> None:
        assert len(Category) == 8
        expected = {
            "TECHNICAL_FACT",
            "BUG",
            "DECISION",
            "GOAL",
            "CODE_SYMBOL",
            "DOCUMENTATION",
            "EXPLORATION_FINDING",
            "SESSION_MEMORY",
        }
        assert set(Category.__members__) == expected

    def test_category_enum_roundtrip(self) -> None:
        assert Category("bug") == Category.BUG
        assert Category("technical_fact") == Category.TECHNICAL_FACT
        assert Category("decision") == Category.DECISION
        assert Category("goal") == Category.GOAL
        assert Category("code_symbol") == Category.CODE_SYMBOL
        assert Category("documentation") == Category.DOCUMENTATION
        assert Category("exploration_finding") == Category.EXPLORATION_FINDING
        assert Category("session_memory") == Category.SESSION_MEMORY


class TestNodeTypeEnum:
    """AC-001 (partial): NodeType has exactly 11 PascalCase values."""

    def test_node_type_enum_values(self) -> None:
        assert len(NodeType) == 11
        expected = {
            "AGENT",
            "COMPONENT",
            "DOCUMENT",
            "SESSION",
            "GOAL",
            "DECISION",
            "BUG",
            "CODE_ENTITY",
            "ENVIRONMENT",
            "CONFIGURATION",
            "CHUNK",
        }
        assert set(NodeType.__members__) == expected

    def test_node_type_enum_roundtrip(self) -> None:
        assert NodeType("Bug") == NodeType.BUG
        assert NodeType("Agent") == NodeType.AGENT
        assert NodeType("Component") == NodeType.COMPONENT
        assert NodeType("CodeEntity") == NodeType.CODE_ENTITY
        assert NodeType("Chunk") == NodeType.CHUNK


class TestEdgeTypeEnum:
    """AC-001 (partial): EdgeType has exactly 38 bootstrap members."""

    def test_edge_type_enum_values(self) -> None:
        assert len(EdgeType) == 38
        expected = {
            "AFFECTS",
            "LOCATED_IN",
            "TRIGGERED_BY",
            "REPRODUCED_IN",
            "DISCOVERED_IN",
            "DUPLICATE_OF",
            "CAUSED_BY",
            "RESOLVES",
            "SELECTS",
            "SATISFIES",
            "SUPERSEDES",
            "CONFLICTS_WITH",
            "IMPLEMENTED_BY",
            "PARENT_OF",
            "BLOCKS",
            "MOTIVATED",
            "BLOCKED_BY",
            "REPORTED",
            "PROPOSED",
            "OWNS",
            "PARTICIPATED_IN",
            "CALLS",
            "EXTENDS",
            "IMPLEMENTS",
            "OVERRIDES",
            "DEPENDS_ON",
            "BELONGS_TO",
            "READS",
            "HOSTS",
            "DEFINED_IN",
            "SETS",
            "DEPLOYED_IN",
            "FOLLOWS",
            "PRODUCED",
            "WORKED_ON",
            "RECORDS",
            "DOCUMENTS",
            "EXTRACTED_TO",
        }
        assert set(EdgeType.__members__) == expected

    def test_edge_type_enum_roundtrip(self) -> None:
        assert EdgeType("AFFECTS") == EdgeType.AFFECTS
        assert EdgeType("DEPENDS_ON") == EdgeType.DEPENDS_ON
        assert EdgeType("EXTRACTED_TO") == EdgeType.EXTRACTED_TO


# ===================================================================
# TagRegistry tests
# ===================================================================


class TestTagRegistry:
    """TagRegistry bootstrap, registration, dedup, reset (AC-011, AC-012, AC-015)."""

    def setup_method(self) -> None:
        """Reset the registry before each test so state is clean."""
        TagRegistry().reset()

    def test_tag_registry_bootstrap(self) -> None:
        """All 4 dimensions have correct bootstrap sets (AC-001 partial)."""
        registry = TagRegistry()
        assert registry.list_all() == {
            "scope": sorted(["ollama", "qdrant", "memgraph", "traefik", "opencode"]),
            "domain": sorted(
                [
                    "infra",
                    "code",
                    "architecture",
                    "testing",
                    "data",
                    "security",
                    "ux",
                    "devops",
                ]
            ),
            "quality": sorted(
                [
                    "bug",
                    "workaround",
                    "verified",
                    "deprecated",
                    "unstable",
                    "critical",
                ]
            ),
            "phase": sorted(["orient", "gather", "spec", "code", "review", "deploy"]),
        }

    def test_tag_registry_singleton(self) -> None:
        """TagRegistry() returns the same instance every time."""
        r1 = TagRegistry()
        r2 = TagRegistry()
        assert r1 is r2

    def test_tag_registry_register_new(self) -> None:
        """Registering a new tag returns True and shows up (AC-011)."""
        registry = TagRegistry()
        result = registry.register("scope", "kubernetes")
        assert result is True
        assert registry.is_valid("scope", "kubernetes") is True
        assert "kubernetes" in registry.list_dimension("scope")

    def test_tag_registry_register_duplicate(self) -> None:
        """Registering an existing tag returns False (AC-012)."""
        registry = TagRegistry()
        result = registry.register("scope", "ollama")
        assert result is False

    def test_tag_registry_register_invalid_dimension(self) -> None:
        """Invalid dimension name raises ValueError."""
        registry = TagRegistry()
        with pytest.raises(ValueError, match="Invalid dimension"):
            registry.register("nonexistent", "foo")

    def test_tag_registry_register_empty_value(self) -> None:
        """Empty tag value raises ValueError."""
        registry = TagRegistry()
        with pytest.raises(ValueError, match="non-empty"):
            registry.register("scope", "")

    def test_tag_registry_is_valid(self) -> None:
        """is_valid returns True for bootstrap values, False for unknown."""
        registry = TagRegistry()
        assert registry.is_valid("scope", "ollama") is True
        assert registry.is_valid("domain", "infra") is True
        assert registry.is_valid("domain", "nonexistent") is False

    def test_tag_registry_list_dimension(self) -> None:
        """list_dimension returns sorted list for a dimension."""
        registry = TagRegistry()
        scopes = registry.list_dimension("scope")
        assert scopes == sorted(scopes)
        assert "ollama" in scopes

    def test_tag_registry_list_all(self) -> None:
        """list_all returns dict with 4 keys, each a sorted list."""
        registry = TagRegistry()
        all_tags = registry.list_all()
        assert set(all_tags.keys()) == {"scope", "domain", "quality", "phase"}
        for values in all_tags.values():
            assert values == sorted(values)

    def test_tag_registry_reset(self) -> None:
        """reset() clears registered tags and restores bootstrap only (AC-015)."""
        registry = TagRegistry()
        registry.register("scope", "kubernetes")
        registry.register("domain", "ml")
        assert registry.is_valid("scope", "kubernetes") is True
        registry.reset()
        assert registry.is_valid("scope", "kubernetes") is False
        assert registry.is_valid("scope", "ollama") is True


# ===================================================================
# Edge type registration tests  (AC-013, AC-014)
# ===================================================================


class TestEdgeTypeRegistration:
    """register_edge_type and is_edge_type."""

    def setup_method(self) -> None:
        """Reset internal runtime set.  We do this by registering known
        duplicates until we can't; for isolation we use unique labels per test."""
        # No clean public reset for _runtime_edge_types, so each test uses
        # a unique edge type label to avoid cross-test pollution.
        pass

    # --- AC-013: register_edge_type valid ---

    def test_register_edge_type_valid(self) -> None:
        """A valid uppercase label is accepted and is_edge_type confirms it."""
        result = register_edge_type("CONFIGURES")
        assert result is True
        assert is_edge_type("CONFIGURES") is True

    # --- AC-014 and 9§ Example 8: invalid patterns ---

    def test_register_edge_type_lowercase_rejected(self) -> None:
        """Lowercase label raises ValueError."""
        with pytest.raises(ValueError, match="Invalid edge type label"):
            register_edge_type("configures")

    def test_register_edge_type_spaces_rejected(self) -> None:
        """Label with spaces raises ValueError."""
        with pytest.raises(ValueError, match="Invalid edge type label"):
            register_edge_type("INVALID ")

    def test_register_edge_type_empty_rejected(self) -> None:
        """Empty string raises ValueError."""
        with pytest.raises(ValueError, match="Invalid edge type label"):
            register_edge_type("")

    def test_register_edge_type_edge_type_collision(self) -> None:
        """Colliding with existing EdgeType member raises ValueError."""
        with pytest.raises(ValueError, match="already a member"):
            register_edge_type("AFFECTS")

    def test_register_edge_type_duplicate(self) -> None:
        """Re-registering the same runtime label returns False."""
        register_edge_type("CONFIGURES_XYZZY")
        result = register_edge_type("CONFIGURES_XYZZY")
        assert result is False

    # --- is_edge_type ---

    def test_is_edge_type(self) -> None:
        """is_edge_type returns True for bootstrap and registered, False for unknown."""
        assert is_edge_type("AFFECTS") is True  # bootstrap
        assert is_edge_type("EXTRACTED_TO") is True  # bootstrap
        register_edge_type("CONFIGURES_XYZZY_EXTRA")
        assert is_edge_type("CONFIGURES_XYZZY_EXTRA") is True  # registered
        assert is_edge_type("BOGUS_EDGE") is False  # unknown


# ===================================================================
# Edge contract tests  (AC-008, AC-009, VC-002, VC-003, VC-004, VC-005)
# ===================================================================


class TestEdgeContract:
    """Structural tests on the edge-contract.json file."""

    def test_edge_contract_parseable(self) -> None:
        """edge-contract.json is valid JSON (AC-009)."""
        with open(_CONTRACT_PATH) as f:
            data = json.load(f)
        assert isinstance(data, dict)

    def test_edge_contract_source_labels_valid(self) -> None:
        """Every key in edge-contract.json is a valid NodeType (VC-003)."""
        with open(_CONTRACT_PATH) as f:
            data = json.load(f)
        for source_label in data:
            assert source_label in NodeType.__members__.values(), (
                f"Source label {source_label!r} is not a valid NodeType"
            )

    def test_edge_contract_target_labels_valid(self) -> None:
        """Every inner key (except '*') in edge-contract.json is a valid NodeType (VC-004)."""
        with open(_CONTRACT_PATH) as f:
            data = json.load(f)
        for source_label, targets in data.items():
            for target_label in targets:
                if target_label == "*":
                    continue
                assert target_label in NodeType.__members__.values(), (
                    f"Target label {target_label!r} (source={source_label}) is not a valid NodeType"
                )

    def test_edge_contract_edge_labels_valid(self) -> None:
        """Every edge value in edge-contract.json is a valid EdgeType (VC-005)."""
        with open(_CONTRACT_PATH) as f:
            data = json.load(f)
        for source_label, targets in data.items():
            for target_label, edges in targets.items():
                for edge in edges:
                    assert edge in EdgeType.__members__, (
                        f"Edge {edge!r} in {source_label}->{target_label} is not a valid EdgeType"
                    )

    def test_edge_contract_all_sources_nonempty(self) -> None:
        """AC-008: every source has at least one target entry."""
        with open(_CONTRACT_PATH) as f:
            data = json.load(f)
        for source_label, targets in data.items():
            assert len(targets) > 0, (
                f"Source {source_label!r} has empty adjacency list"
            )


# ===================================================================
# validate() tests  (AC-002 through AC-007)
# ===================================================================


def _iter_legal_triples():
    """Yield every (source, relation, target) triple from the contract."""
    with open(_CONTRACT_PATH) as f:
        data = json.load(f)
    for src, targets in data.items():
        for tgt, edges in targets.items():
            for edge in edges:
                yield (src, edge, tgt)


class TestValidate:
    """validate() function tests — legal, illegal, wildcard, errors."""

    # ---- AC-002: legal bootstrap edges, parametrized -----------------------

    @pytest.mark.parametrize(
        "source,relation,target",
        [pytest.param(s, r, t, id=f"{s}--{r}-->{t}") for s, r, t in _iter_legal_triples()],
    )
    def test_validate_legal_bootstrap_edges(
        self, source: str, relation: str, target: str
    ) -> None:
        """Every triple from edge-contract.json returns True (AC-002)."""
        assert validate(source, relation, target) is True

    # ---- AC-003: illegal combinations --------------------------------------

    def test_validate_illegal_wrong_direction(self) -> None:
        """Component->AFFECTS->Bug returns False (AC-003, Example 3)."""
        assert validate("Component", "AFFECTS", "Bug") is False

    def test_validate_illegal_wrong_relation(self) -> None:
        """Bug->PROPOSED->Component returns False (AC-003)."""
        assert validate("Bug", "PROPOSED", "Component") is False

    # ---- AC-004, AC-005: Chunk wildcard ------------------------------------

    def test_validate_chunk_wildcard(self) -> None:
        """Chunk->EXTRACTED_TO->(anything) returns True (AC-004, AC-005)."""
        for target in ("Bug", "Component", "Session", "Environment", "Nonexistent"):
            assert validate("Chunk", "EXTRACTED_TO", target) is True

    def test_validate_chunk_only_extracted_to(self) -> None:
        """Chunk->AFFECTS->Component returns False (Example 5)."""
        assert validate("Chunk", "AFFECTS", "Component") is False

    # ---- AC-006, AC-007: ValueError on invalid labels ----------------------

    def test_validate_invalid_source_raises_valueerror(self) -> None:
        """Unknown source label raises ValueError (AC-006, Example 6)."""
        with pytest.raises(ValueError, match="not a valid NodeType"):
            validate("Foobar", "AFFECTS", "Component")

    def test_validate_invalid_relation_raises_valueerror(self) -> None:
        """Unknown relation raises ValueError (AC-007, Example 6)."""
        with pytest.raises(ValueError, match="not a valid EdgeType"):
            validate("Bug", "FROBNICATES", "Component")

    # ---- Example 2: self-loop edges ---------------------------------------

    def test_validate_self_loop_edges(self) -> None:
        """Bug->CAUSED_BY->Bug and Bug->DUPLICATE_OF->Bug (Example 2)."""
        assert validate("Bug", "CAUSED_BY", "Bug") is True
        assert validate("Bug", "DUPLICATE_OF", "Bug") is True


# ===================================================================
# Runtime edge registration tests  (AC-013, AC-014, Example 8)
# ===================================================================


class TestRuntimeEdgeRegistration:
    """register_edge(), get_registered_edges() and interaction with validate()."""

    def setup_method(self) -> None:
        """Reset runtime state between tests.

        We re-initialize the runtime matrix by re-importing (cheap) or
        clearing the module-level state.  Since _runtime_matrix is a
        module-level dict we can clear it, but we must also clean up
        any registered edge types.
        """
        import memory.edge_validator as ev

        ev._runtime_matrix.clear()
        # Remove any runtime edge types we may have added.
        # We do this by directly clearing the set in models.
        import memory.models as m

        m._runtime_edge_types.clear()

    # ---- AC-013: full round-trip -------------------------------------------

    def test_register_edge_valid(self) -> None:
        """After register_edge_type + register_edge, validate returns True (AC-013)."""
        register_edge_type("CONFIGURES")
        result = register_edge("Agent", "CONFIGURES", "Component")
        assert result is True
        assert validate("Agent", "CONFIGURES", "Component") is True

    def test_register_edge_wrong_direction(self) -> None:
        """After registration, wrong direction returns False (Example 8)."""
        register_edge_type("CONFIGURES")
        register_edge("Agent", "CONFIGURES", "Component")
        assert validate("Component", "CONFIGURES", "Agent") is False

    # ---- Wildcard target ---------------------------------------------------

    def test_register_edge_wildcard_target(self) -> None:
        """register_edge with '*' target allows any target in validate."""
        register_edge_type("TEST_EDGE")
        register_edge("Agent", "TEST_EDGE", "*")
        assert validate("Agent", "TEST_EDGE", "Bug") is True
        assert validate("Agent", "TEST_EDGE", "Component") is True
        assert validate("Agent", "TEST_EDGE", "Session") is True

    # ---- ValueError for invalid inputs -------------------------------------

    def test_register_edge_unknown_relation_raises(self) -> None:
        """register_edge with unknown relation raises ValueError."""
        with pytest.raises(ValueError, match="not a known edge type"):
            register_edge("Agent", "UNKNOWN_RELATION", "Component")

    def test_register_edge_invalid_source_raises(self) -> None:
        """register_edge with invalid source raises ValueError."""
        register_edge_type("CONFIGURES")
        with pytest.raises(ValueError, match="not a valid NodeType"):
            register_edge("InvalidSource", "CONFIGURES", "Component")

    # ---- Duplicate ---------------------------------------------------------

    def test_register_edge_duplicate(self) -> None:
        """register_edge returns False for duplicate triple."""
        register_edge_type("CONFIGURES")
        register_edge("Agent", "CONFIGURES", "Component")
        result = register_edge("Agent", "CONFIGURES", "Component")
        assert result is False

    # ---- get_registered_edges ----------------------------------------------

    def test_get_registered_edges(self) -> None:
        """get_registered_edges returns all registered triples."""
        register_edge_type("CONFIGURES")
        register_edge_type("MANAGES")
        register_edge("Agent", "CONFIGURES", "Component")
        register_edge("Agent", "MANAGES", "Component")
        edges = get_registered_edges()
        assert ("Agent", "CONFIGURES", "Component") in edges
        assert ("Agent", "MANAGES", "Component") in edges
        assert len(edges) == 2
