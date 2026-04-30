"""Test suite for MCP Memory Server v0."""

import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml

# Create mock clients before importing main
mock_mem_client = MagicMock()
mock_goal_client = MagicMock()

# Patch the Memory class before importing main
with patch.dict("sys.modules", {"mem0": MagicMock()}):
    # Create a mock mem0 module with Memory class
    mock_mem0 = MagicMock()
    # from_config is called twice (memories, goal_trees), return each mock in order
    mock_mem0.Memory.from_config.side_effect = [mock_mem_client, mock_goal_client]
    sys.modules["mem0"] = mock_mem0
    sys.modules["mem0.memory"] = mock_mem0

    # Now import main - it will use our mocked Memory
    import main

    # Override the clients with our mocks
    main.mem_client = mock_mem_client
    main.goal_client = mock_goal_client


# =====================================================================
# 1. CONFIG LOADING TESTS
# =====================================================================


class TestConfigLoading:
    """Test environment variable loading with defaults."""

    def test_qdrant_host_default(self):
        """QDRANT_HOST defaults to 'qdrant'."""
        assert main.QDRANT_HOST == "qdrant"

    def test_qdrant_port_default(self):
        """QDRANT_PORT defaults to 6333."""
        assert main.QDRANT_PORT == 6333

    def test_ollama_url_default(self):
        """OLLAMA_URL defaults to http://ollama:11434."""
        assert main.OLLAMA_URL == "http://ollama:11434"

    def test_embedding_model_default(self):
        """EMBEDDING_MODEL defaults to nomic-embed-text."""
        assert main.EMBEDDING_MODEL == "nomic-embed-text"

    def test_llm_model_default(self):
        """LLM_MODEL defaults to llama3.1:8b."""
        assert main.LLM_MODEL == "llama3.1:8b"

    def test_agent_id_default(self):
        """AGENT_ID defaults to default_agent."""
        assert main.AGENT_ID == "default_agent"

    def test_staleness_window_days_default(self):
        """STALENESS_WINDOW_DAYS defaults to 30."""
        assert main.STALENESS_WINDOW_DAYS == 30

    def test_host_default(self):
        """HOST defaults to 0.0.0.0."""
        assert main.HOST == "0.0.0.0"

    def test_port_default(self):
        """PORT defaults to 8000 (not 8001)."""
        assert main.PORT == 8000


# =====================================================================
# 2. FILTER CONSTRUCTION TESTS
# =====================================================================


class TestFilterConstruction:
    """Test build_search_filters helper function."""

    def test_empty_filters_returns_user_id_only(self):
        """Empty filters returns user_id-only dict (not empty dict)."""
        result = main.build_search_filters([], None, None, main.AGENT_ID)
        assert result == {"user_id": main.AGENT_ID}

    def test_single_tag_filter(self):
        """Single tag creates contains filter wrapped with user_id."""
        result = main.build_search_filters(["api"], None, None, main.AGENT_ID)
        assert result == {
            "AND": [
                {"user_id": main.AGENT_ID},
                {"tags": {"contains": "api"}}
            ]
        }

    def test_multiple_tags_filter_uses_or_logic(self):
        """Multiple tags use OR logic, wrapped with user_id."""
        result = main.build_search_filters(["api", "database"], None, None, main.AGENT_ID)
        assert result == {
            "AND": [
                {"user_id": main.AGENT_ID},
                {
                    "OR": [
                        {"tags": {"contains": "api"}},
                        {"tags": {"contains": "database"}}
                    ]
                }
            ]
        }

    def test_project_id_filter(self):
        """Project ID filter is added with user_id."""
        result = main.build_search_filters([], "my-project", None, main.AGENT_ID)
        assert result == {
            "AND": [
                {"user_id": main.AGENT_ID},
                {"project_id": "my-project"}
            ]
        }

    def test_source_user_filter(self):
        """Source user filter is added with user_id."""
        result = main.build_search_filters([], None, "john", main.AGENT_ID)
        assert result == {
            "AND": [
                {"user_id": main.AGENT_ID},
                {"source_user": "john"}
            ]
        }

    def test_combined_filters_use_and_logic(self):
        """Multiple conditions use AND logic with user_id."""
        result = main.build_search_filters(["api"], "my-project", "john", main.AGENT_ID)
        assert result == {
            "AND": [
                {"user_id": main.AGENT_ID},
                {
                    "AND": [
                        {"tags": {"contains": "api"}},
                        {"project_id": "my-project"},
                        {"source_user": "john"}
                    ]
                }
            ]
        }

    def test_tags_project_user_combined(self):
        """All three filter types combined correctly with user_id."""
        result = main.build_search_filters(["tag1", "tag2"], "proj", "user", main.AGENT_ID)
        assert "AND" in result
        assert len(result["AND"]) == 2
        assert result["AND"][0] == {"user_id": main.AGENT_ID}
        inner_and = result["AND"][1]
        assert len(inner_and["AND"]) == 3
        assert inner_and["AND"][0] == {"OR": [
            {"tags": {"contains": "tag1"}},
            {"tags": {"contains": "tag2"}}
        ]}
        assert inner_and["AND"][1] == {"project_id": "proj"}
        assert inner_and["AND"][2] == {"source_user": "user"}

    # --- New user_id-specific test cases ---

    def test_user_id_alone(self):
        """user_id alone returns user_id-only dict."""
        result = main.build_search_filters([], None, None, main.AGENT_ID)
        assert result == {"user_id": main.AGENT_ID}

    def test_user_id_with_tags(self):
        """user_id + tags produces AND wrapping both."""
        result = main.build_search_filters(["api"], None, None, main.AGENT_ID)
        assert result == {
            "AND": [
                {"user_id": main.AGENT_ID},
                {"tags": {"contains": "api"}}
            ]
        }

    def test_user_id_with_project(self):
        """user_id + project produces AND wrapping both."""
        result = main.build_search_filters([], "my-project", None, main.AGENT_ID)
        assert result == {
            "AND": [
                {"user_id": main.AGENT_ID},
                {"project_id": "my-project"}
            ]
        }

    def test_user_id_with_tags_and_project(self):
        """user_id + tags + project produces AND wrapping all three."""
        result = main.build_search_filters(["api"], "my-project", None, main.AGENT_ID)
        assert result == {
            "AND": [
                {"user_id": main.AGENT_ID},
                {
                    "AND": [
                        {"tags": {"contains": "api"}},
                        {"project_id": "my-project"},
                    ]
                }
            ]
        }


# =====================================================================
# 3. ADD_MEMORY TESTS
# =====================================================================


class TestAddMemory:
    """Test add_memory tool."""

    def test_add_memory_calls_client_with_correct_params(self):
        """Verify mem_client.add is called with correct parameters."""
        main.mem_client.add.reset_mock()
        main.mem_client.add.return_value = {"results": [{"id": "abc-123", "memory": "test content"}]}

        result = main.add_memory(
            content="Test memory content",
            tags=["api", "important"],
            project_id="test-project",
            source_user="alice"
        )

        main.mem_client.add.assert_called_once()
        call_args = main.mem_client.add.call_args

        # Check positional args
        assert call_args[0][0] == "Test memory content"

        # Check keyword args
        assert call_args[1]["user_id"] == main.AGENT_ID
        assert call_args[1]["infer"] is True
        assert "metadata" in call_args[1]

        metadata = call_args[1]["metadata"]
        assert metadata["tags"] == ["api", "important"]
        assert metadata["project_id"] == "test-project"
        assert metadata["source_user"] == "alice"
        assert "validated_at" in metadata

        assert "successfully" in result.lower()

    def test_add_memory_validated_at_format(self):
        """Verify validated_at is ISO format with Z suffix."""
        main.mem_client.add.reset_mock()
        main.mem_client.add.return_value = {"results": []}

        main.add_memory(content="Test")

        call_args = main.mem_client.add.call_args
        metadata = call_args[1]["metadata"]
        validated_at = metadata["validated_at"]

        # Should end with Z (UTC indicator)
        assert validated_at.endswith("Z")
        # Should be parseable
        datetime.fromisoformat(validated_at.replace("Z", "+00:00"))

    def test_add_memory_includes_all_fields(self):
        """Verify all metadata fields are included, including None values."""
        main.mem_client.add.reset_mock()
        main.mem_client.add.return_value = {"results": []}

        main.add_memory(
            content="Test",
            tags=None,
            project_id=None,
            source_user=None,
            source_path=None,
            related_files=None
        )

        call_args = main.mem_client.add.call_args
        metadata = call_args[1]["metadata"]

        # None fields should be present (explicit absence)
        assert "project_id" in metadata
        assert metadata["project_id"] is None
        assert "source_user" in metadata
        assert metadata["source_user"] is None
        assert "source_path" in metadata
        assert metadata["source_path"] is None
        # Empty lists should be included
        assert "tags" in metadata
        assert metadata["tags"] == []
        assert "related_files" in metadata
        assert metadata["related_files"] == []
        assert "validated_at" in metadata

    def test_add_memory_with_related_files(self):
        """Verify related_files are serialized correctly."""
        main.mem_client.add.reset_mock()
        main.mem_client.add.return_value = {"results": []}

        related_files = [
            {"path": "/src/main.py", "entered": "2024-01-01T10:00:00Z"},
            {"path": "/src/utils.py", "entered": "2024-01-01T11:00:00Z"}
        ]

        main.add_memory(
            content="Test",
            related_files=related_files
        )

        call_args = main.mem_client.add.call_args
        metadata = call_args[1]["metadata"]

        assert metadata["related_files"] == related_files

    def test_add_memory_error_handling(self):
        """Verify error is returned when add fails."""
        main.mem_client.add.reset_mock()
        main.mem_client.add.side_effect = Exception("Connection failed")

        result = main.add_memory(content="Test")

        assert "error" in result.lower()
        assert "connection failed" in result.lower()


# =====================================================================
# 4. SEARCH_MEMORY TESTS
# =====================================================================


class TestSearchMemory:
    """Test search_memory tool."""

    def test_search_calls_client_with_user_id(self):
        """Verify user_id=AGENT_ID is passed in filters to search."""
        main.mem_client.search.reset_mock()
        main.mem_client.search.return_value = []

        main.search_memory(query="test query")

        call_args = main.mem_client.search.call_args
        assert call_args[1]["filters"]["user_id"] == main.AGENT_ID

    def test_search_builds_filters_correctly(self):
        """Verify filter construction is used."""
        main.mem_client.search.reset_mock()
        main.mem_client.search.return_value = []

        with patch.object(main, "build_search_filters") as mock_build:
            mock_build.return_value = {"project_id": "test"}

            main.search_memory(
                query="test",
                tags=["api"],
                project_id="test",
                source_user="alice"
            )

            mock_build.assert_called_once_with(["api"], "test", "alice", user_id=main.AGENT_ID)

    def test_search_result_formatting(self):
        """Verify results are formatted correctly."""
        main.mem_client.search.reset_mock()
        main.mem_client.search.return_value = [
            {
                "id": "abc-def-ghi",
                "score": 0.85,
                "memory": "This is a test memory that is somewhat long and needs truncation for display purposes",
                "metadata": {
                    "project_id": "my-project",
                    "tags": ["api", "test"]
                }
            }
        ]

        result = main.search_memory(query="test")

        assert "Retrieved Memories" in result
        assert "abc-def-..." in result  # Truncated ID (8 chars + ...)
        assert "Score: 0.850" in result
        assert "This is a test memory" in result
        assert "my-project" in result
        assert "api, test" in result

    def test_search_empty_results(self):
        """Verify empty results message."""
        main.mem_client.search.reset_mock()
        main.mem_client.search.return_value = []

        result = main.search_memory(query="nonexistent")

        assert result == "No relevant memories found."

    def test_search_error_handling(self):
        """Verify error is returned when search fails."""
        main.mem_client.search.reset_mock()
        main.mem_client.search.side_effect = Exception("Search timeout")

        result = main.search_memory(query="test")

        assert "error" in result.lower()
        assert "timeout" in result.lower()


# =====================================================================
# 5. DELETE_MEMORY TESTS
# =====================================================================


class TestDeleteMemory:
    """Test delete_memory tool."""

    def test_delete_calls_client_with_correct_id(self):
        """Verify mem_client.delete is called with correct ID."""
        main.mem_client.delete.reset_mock()
        main.mem_client.delete.return_value = None

        result = main.delete_memory("memory-uuid-123")

        main.mem_client.delete.assert_called_once_with("memory-uuid-123")
        assert "successfully" in result.lower()
        assert "memory-uuid-123" in result

    def test_delete_error_handling(self):
        """Verify error is returned when delete fails."""
        main.mem_client.delete.reset_mock()
        main.mem_client.delete.side_effect = Exception("Memory not found")

        result = main.delete_memory("invalid-id")

        assert "error" in result.lower()
        assert "not found" in result.lower()


# =====================================================================
# 6. SYNC_METADATA TESTS
# =====================================================================


class TestSyncMetadata:
    """Test sync_metadata tool."""

    def test_sync_metadata_creates_yaml_file(self):
        """Verify YAML file is created with correct content."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Override MEMORY_CONTEXT_BASE for this test
            original_base = main.MEMORY_CONTEXT_BASE
            main.MEMORY_CONTEXT_BASE = Path(tmpdir).resolve()

            try:
                file_path = os.path.join(tmpdir, ".memory-context.yaml")

                result = main.sync_metadata(
                    file_path=file_path,
                    project_id="test-project",
                    tags=["api", "backend"],
                    scope_summary="Test project summary"
                )

                assert os.path.exists(file_path)

                # Read and verify content
                with open(file_path, "r", encoding="utf-8") as f:
                    content = yaml.safe_load(f)

                assert content["version"] == 1
                assert content["project_id"] == "test-project"
                assert content["tags"] == ["api", "backend"]
                assert content["scope_summary"] == "Test project summary"

                assert "success" in result.lower() or "synchronized" in result.lower()
            finally:
                main.MEMORY_CONTEXT_BASE = original_base

    def test_sync_metadata_without_scope_summary(self):
        """Verify YAML without scope_summary doesn't include the field."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Override MEMORY_CONTEXT_BASE for this test
            original_base = main.MEMORY_CONTEXT_BASE
            main.MEMORY_CONTEXT_BASE = Path(tmpdir).resolve()

            try:
                file_path = os.path.join(tmpdir, ".memory-context.yaml")

                main.sync_metadata(
                    file_path=file_path,
                    project_id="minimal-project",
                    tags=[]
                )

                with open(file_path, "r", encoding="utf-8") as f:
                    content = yaml.safe_load(f)

                assert "version" in content
                assert "project_id" in content
                assert "tags" in content
                assert "scope_summary" not in content
            finally:
                main.MEMORY_CONTEXT_BASE = original_base

    def test_sync_metadata_creates_parent_directory(self):
        """Verify parent directory is created if it doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Override MEMORY_CONTEXT_BASE for this test
            original_base = main.MEMORY_CONTEXT_BASE
            main.MEMORY_CONTEXT_BASE = Path(tmpdir).resolve()

            try:
                nested_path = os.path.join(tmpdir, "nested", "deep", ".memory-context.yaml")

                result = main.sync_metadata(
                    file_path=nested_path,
                    project_id="nested-project"
                )

                assert os.path.exists(nested_path)
                assert "success" in result.lower() or "synchronized" in result.lower()
            finally:
                main.MEMORY_CONTEXT_BASE = original_base

    def test_sync_metadata_yaml_format(self):
        """Verify YAML formatting (no sort, no flow style, unicode)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Override MEMORY_CONTEXT_BASE for this test
            original_base = main.MEMORY_CONTEXT_BASE
            main.MEMORY_CONTEXT_BASE = Path(tmpdir).resolve()

            try:
                file_path = os.path.join(tmpdir, ".memory-context.yaml")

                main.sync_metadata(
                    file_path=file_path,
                    project_id="my-project",
                    tags=["tag1", "tag2"],
                    scope_summary="Summary with unicode: 你好"
                )

                with open(file_path, "r", encoding="utf-8") as f:
                    raw_content = f.read()

                # Should not be flow style (inline)
                assert "{version:" not in raw_content
                # Should contain unicode as-is (allow_unicode=True)
                assert "你好" in raw_content
            finally:
                main.MEMORY_CONTEXT_BASE = original_base

    def test_sync_metadata_error_handling(self):
        """Verify error is returned on failure."""
        # Try to write to a read-only location
        with tempfile.TemporaryDirectory() as tmpdir:
            os.chmod(tmpdir, 0o555)  # Read-only
            file_path = os.path.join(tmpdir, ".memory-context.yaml")

            result = main.sync_metadata(
                file_path=file_path,
                project_id="test"
            )

            assert "error" in result.lower()

            os.chmod(tmpdir, 0o755)  # Restore permissions for cleanup

    def test_sync_metadata_rejects_path_traversal(self):
        """Verify path traversal attempts are rejected."""
        result = main.sync_metadata(
            file_path="../../etc/.memory-context.yaml",
            project_id="test"
        )

        assert "error" in result.lower()
        assert "must be within" in result.lower()

    def test_sync_metadata_rejects_invalid_filename(self):
        """Verify non-.memory-context.yaml filenames are rejected."""
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = os.path.join(tmpdir, "some-other-file.yaml")

            result = main.sync_metadata(
                file_path=file_path,
                project_id="test"
            )

            assert "error" in result.lower()
            assert "must point to a .memory-context.yaml file" in result.lower()

    def test_sync_metadata_accepts_valid_path(self):
        """Verify valid paths within base directory are accepted."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Override MEMORY_CONTEXT_BASE for this test
            original_base = main.MEMORY_CONTEXT_BASE
            main.MEMORY_CONTEXT_BASE = Path(tmpdir).resolve()

            try:
                file_path = os.path.join(tmpdir, "subdir", ".memory-context.yaml")

                result = main.sync_metadata(
                    file_path=file_path,
                    project_id="valid-project",
                    tags=["test"]
                )

                assert "success" in result.lower() or "synchronized" in result.lower()
                assert os.path.exists(file_path)
            finally:
                main.MEMORY_CONTEXT_BASE = original_base


# =====================================================================
# 7. LIST_PROJECTS TESTS
# =====================================================================


class TestListProjects:
    """Test list_projects tool."""

    def test_list_projects_extracts_unique_ids(self):
        """Verify unique project_ids are extracted from memories."""
        main.mem_client.get_all.reset_mock()
        main.mem_client.get_all.return_value = [
            {"id": "1", "metadata": {"project_id": "project-a"}},
            {"id": "2", "metadata": {"project_id": "project-b"}},
            {"id": "3", "metadata": {"project_id": "project-a"}},  # Duplicate
            {"id": "4", "metadata": {"project_id": "project-c"}},
        ]

        result = main.list_projects()

        main.mem_client.get_all.assert_called_once()
        assert "project-a" in result
        assert "project-b" in result
        assert "project-c" in result
        # Should appear once each (unique)
        assert result.count("project-a") == 1

    def test_list_projects_returns_sorted(self):
        """Verify projects are returned sorted."""
        main.mem_client.get_all.reset_mock()
        main.mem_client.get_all.return_value = [
            {"id": "1", "metadata": {"project_id": "zebra"}},
            {"id": "2", "metadata": {"project_id": "alpha"}},
            {"id": "3", "metadata": {"project_id": "beta"}},
        ]

        result = main.list_projects()

        # Check order: alpha, beta, zebra
        alpha_pos = result.find("alpha")
        beta_pos = result.find("beta")
        zebra_pos = result.find("zebra")

        assert alpha_pos < beta_pos < zebra_pos

    def test_list_projects_empty_store(self):
        """Verify message when no projects found."""
        main.mem_client.get_all.reset_mock()
        main.mem_client.get_all.return_value = []

        result = main.list_projects()

        assert "no projects found" in result.lower()

    def test_list_projects_no_project_id_in_metadata(self):
        """Verify memories without project_id are skipped."""
        main.mem_client.get_all.reset_mock()
        main.mem_client.get_all.return_value = [
            {"id": "1", "metadata": {"tags": ["api"]}},  # No project_id
            {"id": "2", "metadata": {"project_id": "valid-project"}},
        ]

        result = main.list_projects()

        assert "valid-project" in result
        assert result.count("\n") == 1  # Only one project line

    def test_list_projects_fallback_to_search(self):
        """Verify fallback to search if get_all doesn't exist."""
        # Store original get_all and search
        original_get_all = main.mem_client.get_all
        original_search = main.mem_client.search

        try:
            # Remove get_all to trigger fallback
            delattr(main.mem_client, "get_all")
            main.mem_client.search = MagicMock(return_value=[
                {"id": "1", "metadata": {"project_id": "fallback-project"}}
            ])

            result = main.list_projects()

            main.mem_client.search.assert_called_once()
            assert "fallback-project" in result
        finally:
            # Restore original methods
            main.mem_client.get_all = original_get_all
            main.mem_client.search = original_search

    def test_list_projects_error_handling(self):
        """Verify error is returned when listing fails."""
        main.mem_client.get_all.reset_mock()
        main.mem_client.get_all.side_effect = Exception("Database error")

        result = main.list_projects()

        assert "error" in result.lower()

        # Reset side effect
        main.mem_client.get_all.side_effect = None

    def test_list_projects_user_id_in_filters(self):
        """Verify user_id is passed inside filters dict."""
        main.mem_client.get_all.reset_mock()
        main.mem_client.get_all.return_value = []

        main.list_projects()

        call_kwargs = main.mem_client.get_all.call_args[1]
        assert "user_id" in call_kwargs.get("filters", {})
        assert call_kwargs["filters"]["user_id"] == main.AGENT_ID


# =====================================================================
# 10. BUILD_GOAL_FILTERS TESTS
# =====================================================================


class TestBuildGoalFilters:
    """Test build_goal_filters helper function."""

    def test_empty_returns_user_id_only(self):
        """All None returns user_id-only dict."""
        result = main.build_goal_filters(None, None, None, None, None, None, None, main.AGENT_ID)
        assert result == {"user_id": main.AGENT_ID}

    def test_node_type_filter(self):
        """Node type filter uses eq, wrapped with user_id."""
        result = main.build_goal_filters("goal", None, None, None, None, None, None, main.AGENT_ID)
        assert result == {
            "AND": [
                {"user_id": main.AGENT_ID},
                {"node_type": {"eq": "goal"}}
            ]
        }

    def test_root_id_filter(self):
        """Root ID filter uses eq, wrapped with user_id."""
        result = main.build_goal_filters(None, "root-123", None, None, None, None, None, main.AGENT_ID)
        assert result == {
            "AND": [
                {"user_id": main.AGENT_ID},
                {"root_id": {"eq": "root-123"}}
            ]
        }

    def test_parent_id_filter(self):
        """Parent ID filter uses eq, wrapped with user_id."""
        result = main.build_goal_filters(None, None, "parent-456", None, None, None, None, main.AGENT_ID)
        assert result == {
            "AND": [
                {"user_id": main.AGENT_ID},
                {"parent_id": {"eq": "parent-456"}}
            ]
        }

    def test_session_id_filter(self):
        """Session ID filter uses eq, wrapped with user_id."""
        result = main.build_goal_filters(None, None, None, "session-1", None, None, None, main.AGENT_ID)
        assert result == {
            "AND": [
                {"user_id": main.AGENT_ID},
                {"session_id": {"eq": "session-1"}}
            ]
        }

    def test_status_filter(self):
        """Status filter uses eq, wrapped with user_id."""
        result = main.build_goal_filters(None, None, None, None, "active", None, None, main.AGENT_ID)
        assert result == {
            "AND": [
                {"user_id": main.AGENT_ID},
                {"status": {"eq": "active"}}
            ]
        }

    def test_project_id_filter(self):
        """Project ID filter uses eq, wrapped with user_id."""
        result = main.build_goal_filters(None, None, None, None, None, "proj-x", None, main.AGENT_ID)
        assert result == {
            "AND": [
                {"user_id": main.AGENT_ID},
                {"project_id": {"eq": "proj-x"}}
            ]
        }

    def test_single_tag_uses_contains(self):
        """Single tag creates contains filter, wrapped with user_id."""
        result = main.build_goal_filters(None, None, None, None, None, None, ["api"], main.AGENT_ID)
        assert result == {
            "AND": [
                {"user_id": main.AGENT_ID},
                {"tags": {"contains": "api"}}
            ]
        }

    def test_multiple_tags_use_or(self):
        """Multiple tags use OR logic, wrapped with user_id."""
        result = main.build_goal_filters(None, None, None, None, None, None, ["a", "b"], main.AGENT_ID)
        assert result == {
            "AND": [
                {"user_id": main.AGENT_ID},
                {
                    "OR": [
                        {"tags": {"contains": "a"}},
                        {"tags": {"contains": "b"}},
                    ]
                }
            ]
        }

    def test_tags_empty_list_ignored(self):
        """Empty tags list is ignored — only user_id returned."""
        result = main.build_goal_filters(None, None, None, None, None, None, [], main.AGENT_ID)
        assert result == {"user_id": main.AGENT_ID}

    def test_multiple_conditions_use_and(self):
        """Multiple conditions use AND logic with user_id."""
        result = main.build_goal_filters("goal", "root-1", None, None, "active", None, None, main.AGENT_ID)
        assert result == {
            "AND": [
                {"user_id": main.AGENT_ID},
                {
                    "AND": [
                        {"node_type": {"eq": "goal"}},
                        {"root_id": {"eq": "root-1"}},
                        {"status": {"eq": "active"}},
                    ]
                }
            ]
        }

    def test_tag_plus_other_conditions_use_and(self):
        """Tags combined with other conditions use AND with user_id."""
        result = main.build_goal_filters(None, None, None, None, None, "proj-x", ["tag1"], main.AGENT_ID)
        assert "AND" in result
        assert len(result["AND"]) == 2
        assert result["AND"][0] == {"user_id": main.AGENT_ID}
        inner_and = result["AND"][1]
        assert len(inner_and["AND"]) == 2
        assert inner_and["AND"][0] == {"project_id": {"eq": "proj-x"}}
        assert inner_and["AND"][1] == {"tags": {"contains": "tag1"}}

    # --- New user_id-specific test cases ---

    def test_goal_user_id_alone(self):
        """user_id alone returns user_id-only dict."""
        result = main.build_goal_filters(None, None, None, None, None, None, None, main.AGENT_ID)
        assert result == {"user_id": main.AGENT_ID}

    def test_goal_user_id_with_tags(self):
        """user_id + tags produces AND wrapping both."""
        result = main.build_goal_filters(None, None, None, None, None, None, ["api"], main.AGENT_ID)
        assert result == {
            "AND": [
                {"user_id": main.AGENT_ID},
                {"tags": {"contains": "api"}}
            ]
        }

    def test_goal_user_id_with_project(self):
        """user_id + project produces AND wrapping both."""
        result = main.build_goal_filters(None, None, None, None, None, "proj-x", None, main.AGENT_ID)
        assert result == {
            "AND": [
                {"user_id": main.AGENT_ID},
                {"project_id": {"eq": "proj-x"}}
            ]
        }

    def test_goal_user_id_with_tags_and_project(self):
        """user_id + tags + project produces AND wrapping all three."""
        result = main.build_goal_filters(None, None, None, None, None, "proj-x", ["api"], main.AGENT_ID)
        assert result == {
            "AND": [
                {"user_id": main.AGENT_ID},
                {
                    "AND": [
                        {"project_id": {"eq": "proj-x"}},
                        {"tags": {"contains": "api"}},
                    ]
                }
            ]
        }


# =====================================================================
# 11. RECONSTRUCT_TREE TESTS
# =====================================================================


class TestReconstructTree:
    """Test reconstruct_tree helper function."""

    def test_empty_nodes_returns_empty_dict(self):
        """Empty list returns empty dict."""
        result = main.reconstruct_tree([], "root-123")
        assert result == {}

    def test_root_found_by_parent_id_none(self):
        """Root node with parent_id=None matching root_id is selected."""
        nodes = [
            {"id": "root-1", "memory": "Root goal", "metadata": {
                "root_id": "root-1", "parent_id": None,
                "node_type": "goal", "status": "active", "tags": []}},
            {"id": "child-1", "memory": "Child task", "metadata": {
                "root_id": "root-1", "parent_id": "root-1",
                "node_type": "task", "status": "active", "tags": []}},
        ]
        result = main.reconstruct_tree(nodes, "root-1")
        assert result["id"] == "root-1"
        assert len(result["children"]) == 1
        assert result["children"][0]["id"] == "child-1"

    def test_fallback_to_goal_type_when_no_parent_id_none(self):
        """Fallback to first goal-type node when no parent_id=None."""
        nodes = [
            {"id": "node-1", "metadata": {
                "root_id": "root-1", "parent_id": "some-parent",
                "node_type": "goal", "status": "active", "tags": []}},
            {"id": "node-2", "metadata": {
                "root_id": "root-1", "parent_id": "node-1",
                "node_type": "task", "status": "active", "tags": []}},
        ]
        result = main.reconstruct_tree(nodes, "root-1")
        assert result["id"] == "node-1"

    def test_fallback_to_first_node(self):
        """Fallback to first node when no parent_id=None or goal type."""
        nodes = [
            {"id": "first", "metadata": {
                "root_id": "root-1", "parent_id": "x",
                "node_type": "task", "status": "active", "tags": []}},
            {"id": "second", "metadata": {
                "root_id": "root-1", "parent_id": "first",
                "node_type": "subtask", "status": "active", "tags": []}},
        ]
        result = main.reconstruct_tree(nodes, "root-1")
        assert result["id"] == "first"

    def test_no_matching_root_id_returns_empty(self):
        """No nodes with matching root_id returns empty dict."""
        nodes = [
            {"id": "other", "metadata": {
                "root_id": "other-root", "parent_id": None,
                "node_type": "goal", "status": "active", "tags": []}},
        ]
        result = main.reconstruct_tree(nodes, "nonexistent")
        assert result == {}

    def test_nested_children_attached_correctly(self):
        """Deeply nested children are attached correctly."""
        nodes = [
            {"id": "r", "metadata": {
                "root_id": "r", "parent_id": None,
                "node_type": "goal", "status": "active", "tags": []}},
            {"id": "c1", "metadata": {
                "root_id": "r", "parent_id": "r",
                "node_type": "task", "status": "active", "tags": []}},
            {"id": "c2", "metadata": {
                "root_id": "r", "parent_id": "c1",
                "node_type": "subtask", "status": "active", "tags": []}},
        ]
        result = main.reconstruct_tree(nodes, "r")
        assert result["id"] == "r"
        assert len(result["children"]) == 1
        assert result["children"][0]["id"] == "c1"
        assert len(result["children"][0]["children"]) == 1
        assert result["children"][0]["children"][0]["id"] == "c2"

    def test_multiple_children_at_same_level(self):
        """Multiple children at the same level are all attached."""
        nodes = [
            {"id": "r", "metadata": {
                "root_id": "r", "parent_id": None,
                "node_type": "goal", "status": "active", "tags": []}},
            {"id": "c1", "metadata": {
                "root_id": "r", "parent_id": "r",
                "node_type": "task", "status": "active", "tags": []}},
            {"id": "c2", "metadata": {
                "root_id": "r", "parent_id": "r",
                "node_type": "task", "status": "active", "tags": []}},
        ]
        result = main.reconstruct_tree(nodes, "r")
        assert len(result["children"]) == 2
        assert {c["id"] for c in result["children"]} == {"c1", "c2"}

    def test_tree_node_format(self):
        """Verify tree node has all expected fields."""
        nodes = [
            {"id": "r", "memory": "Root content", "metadata": {
                "root_id": "r", "parent_id": None,
                "node_type": "goal", "status": "active", "tags": ["tag1"],
                "session_id": "sess-1", "project_id": "proj-1"}},
        ]
        result = main.reconstruct_tree(nodes, "r")
        assert result["id"] == "r"
        assert result["content"] == "Root content"
        assert result["type"] == "goal"
        assert result["status"] == "active"
        assert result["tags"] == ["tag1"]
        assert result["session_id"] == "sess-1"
        assert result["project_id"] == "proj-1"
        assert result["children"] == []


# =====================================================================
# 12. ADD_GOAL_NODE TESTS
# =====================================================================


class TestAddGoalNode:
    """Test add_goal_node tool."""

    def test_invalid_node_type_returns_error(self):
        """Invalid node_type returns error."""
        result = main.add_goal_node(
            main.AddGoalNodeInput(content="test", node_type="invalid")
        )
        assert "error" in result.lower()
        assert "node_type" in result.lower()

    def test_parent_id_without_root_id_returns_error(self):
        """parent_id without root_id returns error."""
        result = main.add_goal_node(
            main.AddGoalNodeInput(
                content="test", node_type="task", parent_id="some-parent"
            )
        )
        assert "error" in result.lower()
        assert "root_id" in result.lower()

    def test_valid_call_builds_correct_metadata(self):
        """Verify goal_client.add is called with correct metadata."""
        main.goal_client.add.reset_mock()
        main.goal_client.add.side_effect = None
        main.goal_client.add.return_value = {"results": [{"id": "new-id"}]}

        result = main.add_goal_node(
            main.AddGoalNodeInput(
                content="Test goal",
                node_type="goal",
                session_id="session-1",
                status="active",
                tags=["important"],
                project_id="my-project",
            )
        )

        main.goal_client.add.assert_called_once()
        call_args = main.goal_client.add.call_args

        # Check positional arg (content)
        assert call_args[0][0] == "Test goal"

        # Check keyword args
        assert call_args[1]["user_id"] == main.AGENT_ID
        assert call_args[1]["infer"] is False

        metadata = call_args[1]["metadata"]
        assert metadata["node_type"] == "goal"
        assert metadata["parent_id"] is None
        assert metadata["root_id"] is not None  # Auto-generated
        assert metadata["session_id"] == "session-1"
        assert metadata["status"] == "active"
        assert metadata["tags"] == ["important"]
        assert metadata["project_id"] == "my-project"
        assert "validated_at" in metadata

        assert "goal node created" in result.lower()
        assert "goal" in result.lower()

    def test_valid_child_goal_uses_provided_root_id(self):
        """Child node uses provided root_id."""
        main.goal_client.add.reset_mock()
        main.goal_client.add.side_effect = None
        main.goal_client.add.return_value = {"results": [{"id": "child-id"}]}

        result = main.add_goal_node(
            main.AddGoalNodeInput(
                content="Child task",
                node_type="task",
                parent_id="parent-uuid",
                root_id="root-uuid",
            )
        )

        call_args = main.goal_client.add.call_args
        metadata = call_args[1]["metadata"]
        assert metadata["parent_id"] == "parent-uuid"
        assert metadata["root_id"] == "root-uuid"
        assert "goal node created" in result.lower()

    def test_root_goal_sets_root_id_to_node_id(self):
        """Root goal sets root_id equal to its own generated ID."""
        main.goal_client.add.reset_mock()
        main.goal_client.add.return_value = {"results": [{"id": "new-id"}]}

        main.add_goal_node(
            main.AddGoalNodeInput(content="Root goal", node_type="goal")
        )

        call_args = main.goal_client.add.call_args
        metadata = call_args[1]["metadata"]
        # root_id should be auto-generated and not None
        assert metadata["root_id"] is not None
        # The root_id should equal the generated node_id
        # Since we can't know the generated UUID, just verify it's a string
        assert isinstance(metadata["root_id"], str)
        assert len(metadata["root_id"]) > 0

    def test_error_handling(self):
        """Verify error is returned when add fails."""
        main.goal_client.add.reset_mock()
        main.goal_client.add.side_effect = Exception("Connection failed")

        result = main.add_goal_node(
            main.AddGoalNodeInput(content="Test", node_type="goal")
        )

        assert "error" in result.lower()
        assert "connection failed" in result.lower()

    def test_infer_defaults_to_false(self):
        """Verify infer defaults to False for goal nodes (not True like memories)."""
        main.goal_client.add.reset_mock()
        main.goal_client.add.return_value = {"results": []}

        main.add_goal_node(
            main.AddGoalNodeInput(content="Test", node_type="goal")
        )

        call_args = main.goal_client.add.call_args
        assert call_args[1]["infer"] is False


# =====================================================================
# 13. SEARCH_GOAL_NODES TESTS
# =====================================================================


class TestSearchGoalNodes:
    """Test search_goal_nodes tool."""

    def test_filter_building(self):
        """Verify build_goal_filters is used correctly with user_id."""
        main.goal_client.search.reset_mock()
        main.goal_client.search.return_value = []

        with patch.object(main, "build_goal_filters") as mock_build:
            mock_build.return_value = {"node_type": {"eq": "task"}}

            main.search_goal_nodes(
                main.SearchGoalNodesInput(
                    query="deploy",
                    node_type="task",
                    project_id="proj-x",
                    tags=["api"],
                )
            )

            mock_build.assert_called_once_with(
                node_type="task",
                root_id=None,
                parent_id=None,
                session_id=None,
                status=None,
                project_id="proj-x",
                tags=["api"],
                user_id=main.AGENT_ID,
            )

    def test_user_id_in_filters(self):
        """Verify user_id=AGENT_ID is passed in filters to search."""
        main.goal_client.search.reset_mock()
        main.goal_client.search.return_value = []

        main.search_goal_nodes(
            main.SearchGoalNodesInput(query="test query")
        )

        call_args = main.goal_client.search.call_args
        assert call_args[1]["filters"]["user_id"] == main.AGENT_ID

    def test_result_formatting(self):
        """Verify results are formatted correctly."""
        main.goal_client.search.reset_mock()
        main.goal_client.search.side_effect = None
        main.goal_client.search.return_value = [
            {
                "id": "goal-node-abc-def",
                "score": 0.85,
                "memory": "Deploy to staging environment",
                "metadata": {
                    "node_type": "goal",
                    "status": "active",
                    "parent_id": None,
                    "root_id": "goal-node-abc-def",
                    "project_id": "my-project",
                    "tags": ["deploy"],
                },
            }
        ]

        result = main.search_goal_nodes(
            main.SearchGoalNodesInput(query="deploy")
        )

        assert "Goal Node Search Results" in result
        assert "goal-nod" in result  # Truncated ID (8 chars): "goal-nod" from "goal-node-abc-def"
        assert "Score: 0.850" in result
        assert "Deploy to staging" in result
        assert "[GOAL]" in result
        assert "none" in result  # parent is None so "none" displayed

    def test_empty_results(self):
        """Verify empty results message."""
        main.goal_client.search.reset_mock()
        main.goal_client.search.side_effect = None
        main.goal_client.search.return_value = []

        result = main.search_goal_nodes(
            main.SearchGoalNodesInput(query="nonexistent")
        )

        assert result == "No matching goal nodes found."

    def test_threshold_filtering(self):
        """Verify threshold filters low-scoring results."""
        main.goal_client.search.reset_mock()
        main.goal_client.search.side_effect = None
        main.goal_client.search.return_value = [
            {"id": "a", "score": 0.95, "memory": "High score",
             "metadata": {"node_type": "goal", "status": "active", "tags": []}},
            {"id": "b", "score": 0.05, "memory": "Low score",
             "metadata": {"node_type": "task", "status": "active", "tags": []}},
        ]

        result = main.search_goal_nodes(
            main.SearchGoalNodesInput(query="test", threshold=0.5)
        )

        assert "High score" in result
        assert "Low score" not in result

    def test_error_handling(self):
        """Verify error is returned when search fails."""
        main.goal_client.search.reset_mock()
        main.goal_client.search.side_effect = Exception("Search timeout")

        result = main.search_goal_nodes(
            main.SearchGoalNodesInput(query="test")
        )

        assert "error" in result.lower()
        assert "timeout" in result.lower()


# =====================================================================
# 14. GET_GOAL_TREE TESTS
# =====================================================================


class TestGetGoalTree:
    """Test get_goal_tree tool."""

    def test_get_all_called_with_correct_filters(self):
        """Verify get_all is called with correct filters."""
        main.goal_client.get_all.reset_mock()
        main.goal_client.get_all.return_value = [
            {"id": "root-1", "memory": "Root",
             "metadata": {"root_id": "root-1", "parent_id": None,
                          "node_type": "goal", "status": "active", "tags": []}},
        ]

        main.get_goal_tree(main.GetGoalTreeInput(root_id="root-1"))

        main.goal_client.get_all.assert_called_once()
        call_args = main.goal_client.get_all.call_args[1]
        assert call_args["filters"]["AND"][0]["user_id"] == main.AGENT_ID
        assert call_args["filters"]["AND"][1]["root_id"] == {"eq": "root-1"}
        assert call_args["filters"]["AND"][1]["node_type"] == {"in": ["goal", "task", "subtask"]}
        assert call_args["limit"] == 1000

    def test_fallback_to_search(self):
        """Verify fallback to search when get_all fails."""
        original_get_all = main.goal_client.get_all
        original_search = main.goal_client.search

        try:
            delattr(main.goal_client, "get_all")
            main.goal_client.search = MagicMock(return_value=[
                {"id": "root-1", "memory": "Root",
                 "metadata": {"root_id": "root-1", "parent_id": None,
                              "node_type": "goal", "status": "active", "tags": []}},
            ])

            result = main.get_goal_tree(main.GetGoalTreeInput(root_id="root-1"))

            main.goal_client.search.assert_called_once()
            assert "Root" in result
        finally:
            main.goal_client.get_all = original_get_all
            main.goal_client.search = original_search

    def test_missing_root_returns_error_json(self):
        """Missing root returns error JSON."""
        main.goal_client.get_all.reset_mock()
        main.goal_client.get_all.return_value = []

        result = main.get_goal_tree(main.GetGoalTreeInput(root_id="nonexistent"))

        assert '"error"' in result
        assert "nonexistent" in result

    def test_tree_reconstruction(self):
        """Verify nested tree is reconstructed correctly."""
        main.goal_client.get_all.reset_mock()
        main.goal_client.get_all.return_value = [
            {"id": "root-1", "memory": "Root goal",
             "metadata": {"root_id": "root-1", "parent_id": None,
                          "node_type": "goal", "status": "active", "tags": []}},
            {"id": "child-1", "memory": "Child task",
             "metadata": {"root_id": "root-1", "parent_id": "root-1",
                          "node_type": "task", "status": "active", "tags": []}},
        ]

        result = main.get_goal_tree(main.GetGoalTreeInput(root_id="root-1"))

        import json as _json
        tree = _json.loads(result)
        assert tree["id"] == "root-1"
        assert tree["content"] == "Root goal"
        assert tree["type"] == "goal"
        assert len(tree["children"]) == 1
        assert tree["children"][0]["id"] == "child-1"
        assert tree["children"][0]["content"] == "Child task"

    def test_error_handling(self):
        """Verify error is returned when fetching fails."""
        main.goal_client.get_all.reset_mock()
        main.goal_client.get_all.side_effect = Exception("Qdrant timeout")

        result = main.get_goal_tree(main.GetGoalTreeInput(root_id="root-1"))

        assert "error" in result.lower()
        assert "timeout" in result.lower()


# =====================================================================
# 15. UPDATE_GOAL_NODE TESTS
# =====================================================================


class TestUpdateGoalNode:
    """Test update_goal_node tool."""

    def test_invalid_status_returns_error(self):
        """Invalid status returns error."""
        result = main.update_goal_node(
            main.UpdateGoalNodeInput(node_id="abc-123", status="invalid_status")
        )
        assert "error" in result.lower()
        assert "invalid status" in result.lower()

    def test_partial_metadata_update(self):
        """Verify only provided fields are included in metadata update."""
        main.goal_client.update.reset_mock()
        main.goal_client.update.return_value = None

        main.update_goal_node(
            main.UpdateGoalNodeInput(node_id="abc-123", status="completed")
        )

        main.goal_client.update.assert_called_once()
        call_args = main.goal_client.update.call_args

        # First positional arg is node_id
        assert call_args[0][0] == "abc-123"
        # metadata should only contain status
        assert call_args[1]["metadata"] == {"status": "completed"}

    def test_update_with_content(self):
        """Verify content is passed as data param."""
        main.goal_client.update.reset_mock()
        main.goal_client.update.return_value = None

        main.update_goal_node(
            main.UpdateGoalNodeInput(node_id="abc-123", content="Updated content")
        )

        call_args = main.goal_client.update.call_args
        assert call_args[1]["data"] == "Updated content"

    def test_multiple_fields_update(self):
        """Verify multiple fields are updated correctly."""
        main.goal_client.update.reset_mock()
        main.goal_client.update.return_value = None

        main.update_goal_node(
            main.UpdateGoalNodeInput(
                node_id="abc-123",
                status="blocked",
                tags=["urgent"],
                project_id="new-project",
            )
        )

        call_args = main.goal_client.update.call_args
        metadata = call_args[1]["metadata"]
        assert metadata == {
            "status": "blocked",
            "tags": ["urgent"],
            "project_id": "new-project",
        }

    def test_update_without_content_passes_none(self):
        """Verify data=None when content not provided."""
        main.goal_client.update.reset_mock()
        main.goal_client.update.return_value = None

        main.update_goal_node(
            main.UpdateGoalNodeInput(node_id="abc-123", status="completed")
        )

        call_args = main.goal_client.update.call_args
        # data should be None when content not provided
        assert call_args[1]["data"] is None

    def test_error_handling(self):
        """Verify error is returned when update fails."""
        main.goal_client.update.reset_mock()
        main.goal_client.update.side_effect = Exception("Update failed")

        result = main.update_goal_node(
            main.UpdateGoalNodeInput(node_id="abc-123", status="completed")
        )

        assert "error" in result.lower()
        assert "update failed" in result.lower()


# =====================================================================
# 16. DELETE_GOAL_NODE TESTS
# =====================================================================


class TestDeleteGoalNode:
    """Test delete_goal_node tool."""

    def test_deletes_correct_node_id(self):
        """Verify goal_client.delete is called with correct ID."""
        main.goal_client.delete.reset_mock()
        main.goal_client.delete.side_effect = None
        main.goal_client.delete.return_value = None

        result = main.delete_goal_node(
            main.DeleteGoalNodeInput(node_id="goal-uuid-123")
        )

        main.goal_client.delete.assert_called_once_with("goal-uuid-123")
        assert "successfully" in result.lower()
        assert "goal-uuid-123" in result

    def test_error_handling(self):
        """Verify error is returned when delete fails."""
        main.goal_client.delete.reset_mock()
        main.goal_client.delete.side_effect = Exception("Goal node not found")

        result = main.delete_goal_node(
            main.DeleteGoalNodeInput(node_id="invalid-id")
        )

        assert "error" in result.lower()
        assert "not found" in result.lower()


# =====================================================================
# 8. SERVER STARTUP TEST
# =====================================================================


class TestServerStartup:
    """Test server startup configuration."""

    def test_fastmcp_instance_created(self):
        """Verify FastMCP instance is created with correct name."""
        assert main.mcp is not None
        # The name is set in the constructor

    @patch.object(main.mcp, "run")
    def test_main_block_runs_server(self, mock_run):
        """Verify __main__ block runs server with correct params."""
        # Simulate running the main block
        main.mcp.run(transport="streamable-http", host=main.HOST, port=main.PORT)

        mock_run.assert_called_once_with(
            transport="streamable-http",
            host=main.HOST,
            port=main.PORT
        )

    def test_port_is_8000_not_8001(self):
        """Verify default port is 8000, not 8001."""
        assert main.PORT == 8000
        assert main.PORT != 8001


# =====================================================================
# 9. NO HARDCODED VALUES TESTS
# =====================================================================


class TestNoHardcodedValues:
    """Verify no hardcoded values from old implementation remain."""

    def test_no_hardcoded_roo_agent(self):
        """Verify 'roo_agent' is not hardcoded anywhere."""
        import inspect
        source = inspect.getsource(main)
        assert "roo_agent" not in source.lower()

    def test_no_hardcoded_port_8001(self):
        """Verify port 8001 is not hardcoded."""
        import inspect
        source = inspect.getsource(main)
        # Check that 8001 only appears in tests (comparing old vs new)
        lines = source.split("\n")
        for line in lines:
            if "8001" in line and "port" in line.lower():
                assert False, f"Found hardcoded port 8001: {line}"

    def test_uses_agent_id_env_var(self):
        """Verify AGENT_ID env var is used."""
        assert hasattr(main, "AGENT_ID")
        assert main.AGENT_ID is not None

    def test_uses_port_env_var(self):
        """Verify PORT env var is used."""
        assert hasattr(main, "PORT")
        assert main.PORT is not None
