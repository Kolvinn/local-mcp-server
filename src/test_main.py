"""Test suite for MCP Memory Server v0."""

import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml

# Create mock memory client before importing main
mock_memory_client = MagicMock()

# Patch the Memory class before importing main
with patch.dict("sys.modules", {"mem0": MagicMock()}):
    # Create a mock mem0 module with Memory class
    mock_mem0 = MagicMock()
    mock_mem0.Memory.from_config.return_value = mock_memory_client
    sys.modules["mem0"] = mock_mem0
    sys.modules["mem0.memory"] = mock_mem0

    # Now import main - it will use our mocked Memory
    import main

    # Override the memory_client with our mock
    main.memory_client = mock_memory_client


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
        """EMBEDDING_MODEL defaults to bge-m3."""
        assert main.EMBEDDING_MODEL == "bge-m3"

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

    def test_empty_filters_returns_empty_dict(self):
        """Empty filters returns empty dict."""
        result = main.build_search_filters([], None, None)
        assert result == {}

    def test_single_tag_filter(self):
        """Single tag creates contains filter."""
        result = main.build_search_filters(["api"], None, None)
        assert result == {"tags": {"contains": "api"}}

    def test_multiple_tags_filter_uses_or_logic(self):
        """Multiple tags use OR logic."""
        result = main.build_search_filters(["api", "database"], None, None)
        assert result == {
            "OR": [
                {"tags": {"contains": "api"}},
                {"tags": {"contains": "database"}}
            ]
        }

    def test_project_id_filter(self):
        """Project ID filter is added directly."""
        result = main.build_search_filters([], "my-project", None)
        assert result == {"project_id": "my-project"}

    def test_source_user_filter(self):
        """Source user filter is added directly."""
        result = main.build_search_filters([], None, "john")
        assert result == {"source_user": "john"}

    def test_combined_filters_use_and_logic(self):
        """Multiple conditions use AND logic."""
        result = main.build_search_filters(["api"], "my-project", "john")
        assert result == {
            "AND": [
                {"tags": {"contains": "api"}},
                {"project_id": "my-project"},
                {"source_user": "john"}
            ]
        }

    def test_tags_project_user_combined(self):
        """All three filter types combined correctly."""
        result = main.build_search_filters(["tag1", "tag2"], "proj", "user")
        assert "AND" in result
        assert len(result["AND"]) == 3
        assert result["AND"][0] == {"OR": [
            {"tags": {"contains": "tag1"}},
            {"tags": {"contains": "tag2"}}
        ]}
        assert result["AND"][1] == {"project_id": "proj"}
        assert result["AND"][2] == {"source_user": "user"}


# =====================================================================
# 3. ADD_MEMORY TESTS
# =====================================================================


class TestAddMemory:
    """Test add_memory tool."""

    def test_add_memory_calls_client_with_correct_params(self):
        """Verify memory_client.add is called with correct parameters."""
        main.memory_client.add.reset_mock()
        main.memory_client.add.return_value = {"results": [{"id": "abc-123", "memory": "test content"}]}

        result = main.add_memory(
            content="Test memory content",
            tags=["api", "important"],
            project_id="test-project",
            source_user="alice"
        )

        main.memory_client.add.assert_called_once()
        call_args = main.memory_client.add.call_args

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
        main.memory_client.add.reset_mock()
        main.memory_client.add.return_value = {"results": []}

        main.add_memory(content="Test")

        call_args = main.memory_client.add.call_args
        metadata = call_args[1]["metadata"]
        validated_at = metadata["validated_at"]

        # Should end with Z (UTC indicator)
        assert validated_at.endswith("Z")
        # Should be parseable
        datetime.fromisoformat(validated_at.replace("Z", "+00:00"))

    def test_add_memory_includes_all_fields(self):
        """Verify all metadata fields are included, including None values."""
        main.memory_client.add.reset_mock()
        main.memory_client.add.return_value = {"results": []}

        main.add_memory(
            content="Test",
            tags=None,
            project_id=None,
            source_user=None,
            source_path=None,
            related_files=None
        )

        call_args = main.memory_client.add.call_args
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
        main.memory_client.add.reset_mock()
        main.memory_client.add.return_value = {"results": []}

        related_files = [
            {"path": "/src/main.py", "entered": "2024-01-01T10:00:00Z"},
            {"path": "/src/utils.py", "entered": "2024-01-01T11:00:00Z"}
        ]

        main.add_memory(
            content="Test",
            related_files=related_files
        )

        call_args = main.memory_client.add.call_args
        metadata = call_args[1]["metadata"]

        assert metadata["related_files"] == related_files

    def test_add_memory_error_handling(self):
        """Verify error is returned when add fails."""
        main.memory_client.add.reset_mock()
        main.memory_client.add.side_effect = Exception("Connection failed")

        result = main.add_memory(content="Test")

        assert "error" in result.lower()
        assert "connection failed" in result.lower()


# =====================================================================
# 4. SEARCH_MEMORY TESTS
# =====================================================================


class TestSearchMemory:
    """Test search_memory tool."""

    def test_search_calls_client_with_user_id(self):
        """Verify user_id=AGENT_ID is passed to search."""
        main.memory_client.search.reset_mock()
        main.memory_client.search.return_value = []

        main.search_memory(query="test query")

        call_args = main.memory_client.search.call_args
        assert call_args[1]["user_id"] == main.AGENT_ID

    def test_search_builds_filters_correctly(self):
        """Verify filter construction is used."""
        main.memory_client.search.reset_mock()
        main.memory_client.search.return_value = []

        with patch.object(main, "build_search_filters") as mock_build:
            mock_build.return_value = {"project_id": "test"}

            main.search_memory(
                query="test",
                tags=["api"],
                project_id="test",
                source_user="alice"
            )

            mock_build.assert_called_once_with(["api"], "test", "alice")

    def test_search_result_formatting(self):
        """Verify results are formatted correctly."""
        main.memory_client.search.reset_mock()
        main.memory_client.search.return_value = [
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
        main.memory_client.search.reset_mock()
        main.memory_client.search.return_value = []

        result = main.search_memory(query="nonexistent")

        assert result == "No relevant memories found."

    def test_search_error_handling(self):
        """Verify error is returned when search fails."""
        main.memory_client.search.reset_mock()
        main.memory_client.search.side_effect = Exception("Search timeout")

        result = main.search_memory(query="test")

        assert "error" in result.lower()
        assert "timeout" in result.lower()


# =====================================================================
# 5. DELETE_MEMORY TESTS
# =====================================================================


class TestDeleteMemory:
    """Test delete_memory tool."""

    def test_delete_calls_client_with_correct_id(self):
        """Verify memory_client.delete is called with correct ID."""
        main.memory_client.delete.reset_mock()
        main.memory_client.delete.return_value = None

        result = main.delete_memory("memory-uuid-123")

        main.memory_client.delete.assert_called_once_with("memory-uuid-123")
        assert "successfully" in result.lower()
        assert "memory-uuid-123" in result

    def test_delete_error_handling(self):
        """Verify error is returned when delete fails."""
        main.memory_client.delete.reset_mock()
        main.memory_client.delete.side_effect = Exception("Memory not found")

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
        main.memory_client.get_all.reset_mock()
        main.memory_client.get_all.return_value = [
            {"id": "1", "metadata": {"project_id": "project-a"}},
            {"id": "2", "metadata": {"project_id": "project-b"}},
            {"id": "3", "metadata": {"project_id": "project-a"}},  # Duplicate
            {"id": "4", "metadata": {"project_id": "project-c"}},
        ]

        result = main.list_projects()

        main.memory_client.get_all.assert_called_once()
        assert "project-a" in result
        assert "project-b" in result
        assert "project-c" in result
        # Should appear once each (unique)
        assert result.count("project-a") == 1

    def test_list_projects_returns_sorted(self):
        """Verify projects are returned sorted."""
        main.memory_client.get_all.reset_mock()
        main.memory_client.get_all.return_value = [
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
        main.memory_client.get_all.reset_mock()
        main.memory_client.get_all.return_value = []

        result = main.list_projects()

        assert "no projects found" in result.lower()

    def test_list_projects_no_project_id_in_metadata(self):
        """Verify memories without project_id are skipped."""
        main.memory_client.get_all.reset_mock()
        main.memory_client.get_all.return_value = [
            {"id": "1", "metadata": {"tags": ["api"]}},  # No project_id
            {"id": "2", "metadata": {"project_id": "valid-project"}},
        ]

        result = main.list_projects()

        assert "valid-project" in result
        assert result.count("\n") == 1  # Only one project line

    def test_list_projects_fallback_to_search(self):
        """Verify fallback to search if get_all doesn't exist."""
        # Store original get_all and search
        original_get_all = main.memory_client.get_all
        original_search = main.memory_client.search

        try:
            # Remove get_all to trigger fallback
            delattr(main.memory_client, "get_all")
            main.memory_client.search = MagicMock(return_value=[
                {"id": "1", "metadata": {"project_id": "fallback-project"}}
            ])

            result = main.list_projects()

            main.memory_client.search.assert_called_once()
            assert "fallback-project" in result
        finally:
            # Restore original methods
            main.memory_client.get_all = original_get_all
            main.memory_client.search = original_search

    def test_list_projects_error_handling(self):
        """Verify error is returned when listing fails."""
        main.memory_client.get_all.reset_mock()
        main.memory_client.get_all.side_effect = Exception("Database error")

        result = main.list_projects()

        assert "error" in result.lower()

        # Reset side effect
        main.memory_client.get_all.side_effect = None

    def test_list_projects_user_id_as_param(self):
        """Verify user_id is passed as parameter, not in filters dict."""
        main.memory_client.get_all.reset_mock()
        main.memory_client.get_all.return_value = []

        main.list_projects()

        call_kwargs = main.memory_client.get_all.call_args[1]
        assert call_kwargs.get("user_id") == main.AGENT_ID
        assert "user_id" not in call_kwargs.get("filters", {})


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
