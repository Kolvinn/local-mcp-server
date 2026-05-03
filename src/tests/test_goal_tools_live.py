#!/usr/bin/env python3
"""
Live integration tests for goal-tree MCP tools.

Connects to a running main.py server via MCP JSON-RPC protocol,
tests all 5 goal-tree tools with real data, and cleans up.

Usage:
    python scripts/test_goal_tools_live.py              # Quick summary
    python scripts/test_goal_tools_live.py -v           # Verbose output
    python scripts/test_goal_tools_live.py --port 8001  # Via proxy
"""

import json
import uuid
import sys
import time
from typing import Optional
import argparse
import requests


class GoalTester:
    """Test client for goal-tree MCP tools over JSON-RPC."""

    def __init__(
        self, host: str = "http://localhost", port: int = 8000, verbose: bool = False
    ):
        self.host = host
        self.session_id: Optional[str] = None
        self._last_response: Optional[requests.Response] = None
        self.port = port
        self.verbose = verbose
        self.protocol_version = "2024-11-05"
        self.base_url = f"{host}:{port}/mcp"
        self.headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
            "mcp-protocol-version": self.protocol_version,
        }
        # Track created nodes for cleanup
        self.created_nodes: list[str] = []

    # ------------------------------------------------------------------
    # Low-level MCP helpers
    # ------------------------------------------------------------------

    def send_request(self, method: str, params: Optional[dict] = None) -> dict:
        """Send an MCP JSON-RPC request to the server.

        Handles both JSON and SSE (streamable-http) response formats.
        """
        payload = {
            "jsonrpc": "2.0",
            "id": str(uuid.uuid4()),
            "method": method,
            "params": params or {},
        }
        if self.verbose:
            print(f"\n>>> {method}")
            print(json.dumps(payload, indent=2))

        response = requests.post(
            self.base_url, headers=self.headers, json=payload, timeout=30
        )
        self._last_response = response
        return self._parse_response(response)

    @staticmethod
    def _parse_response(response: requests.Response) -> dict:
        """Parse an MCP response, handling both JSON and SSE formats."""
        content_type = response.headers.get("content-type", "")
        text = response.text

        # Try direct JSON parse first (for error responses and plain JSON)
        try:
            return response.json()
        except json.JSONDecodeError:
            pass

        # Handle SSE format: event: message\ndata: {...}\n\n
        if "text/event-stream" in content_type:
            for line in text.split("\n"):
                if line.startswith("data: "):
                    try:
                        return json.loads(line[6:])
                    except json.JSONDecodeError:
                        continue

        return {"error": "Invalid response", "raw": text}

    def init(self) -> dict:
        """Initialize MCP session and extract session ID."""
        params = {
            "protocolVersion": self.protocol_version,
            "capabilities": {},
            "clientInfo": {"name": "goal-tester", "version": "1.0.0"},
        }
        response = self.send_request("initialize", params)

        # Extract session ID for streamable-http MCP
        if self._last_response is not None:
            session_id = self._last_response.headers.get("mcp-session-id")
            if not session_id:
                meta = response.get("result", {}).get("_meta", {})
                session_id = meta.get("session_id")
            if session_id:
                self.session_id = session_id
                self.headers["mcp-session-id"] = (
                    session_id  # Add to headers for subsequent requests
                )
                if self.verbose:
                    print(f"  Session ID: {session_id}")

        return response

    def call_tool(self, name: str, arguments: dict) -> dict:
        """Call an MCP tool by name with arguments."""
        params = {"name": name, "arguments": {"input": arguments}}
        return self.send_request("tools/call", params)

    def tool_result(self, response: dict) -> Optional[str]:
        """Extract text content from a tools/call JSON-RPC response."""
        try:
            content = response.get("result", {}).get("content", [])
            if content:
                return content[0].get("text", "")
            return None
        except (AttributeError, IndexError, KeyError):
            return str(response)

    # ------------------------------------------------------------------
    # Goal-tree operations
    # ------------------------------------------------------------------

    def add_goal_node(self, **kwargs) -> tuple[Optional[str], Optional[str]]:
        """
        Add a goal node and return (response_text, node_id).
        Parses node_id from response text if successful.
        """
        response = self.call_tool("add_goal_node", kwargs)
        text = self.tool_result(response) or str(response)
        node_id = None
        if text and "id=" in text:
            try:
                # Parse format: "Goal node created. id=<uuid>, type=goal. Created 1 entries."
                node_id = text.split("id=")[1].split(",")[0].strip()
            except (IndexError, ValueError):
                pass
        return text, node_id

    def search_goal_nodes(self, **kwargs) -> Optional[str]:
        """Search goal nodes by query and optional filters."""
        response = self.call_tool("search_goal_nodes", kwargs)
        return self.tool_result(response) or str(response)

    def get_goal_tree(self, root_id: str) -> Optional[str]:
        """Fetch the goal tree for a given root_id."""
        response = self.call_tool("get_goal_tree", {"root_id": root_id})
        return self.tool_result(response) or str(response)

    def update_goal_node(self, **kwargs) -> Optional[str]:
        """Update a goal node's fields."""
        response = self.call_tool("update_goal_node", kwargs)
        return self.tool_result(response) or str(response)

    def delete_goal_node(self, node_id: str) -> Optional[str]:
        """Delete a single goal node by ID."""
        response = self.call_tool("delete_goal_node", {"node_id": node_id})
        return self.tool_result(response) or str(response)

    # ------------------------------------------------------------------
    # Cleanup
    # ------------------------------------------------------------------

    def cleanup(self):
        """Delete all created test nodes."""
        for node_id in list(self.created_nodes):
            try:
                result = self.delete_goal_node(node_id)
                if self.verbose:
                    snippet = (result or "")[:60]
                    print(f"  Cleanup deleted {node_id[:8]}...: {snippet}")
            except Exception as e:
                print(f"  Cleanup error for {node_id[:8]}...: {e}")

    # ------------------------------------------------------------------
    # Test runner
    # ------------------------------------------------------------------

    def run_tests(self) -> bool:
        """Run all goal-tree tool tests. Returns True if all pass."""
        uid = uuid.uuid4().hex[:8]
        tag = f"test-goal-{uid}"
        prefix = f"test_goal_{uid}"
        passed = 0
        failed = 0
        root_id: Optional[str] = None
        child_id: Optional[str] = None

        def check(name: str, condition: bool, detail: str = ""):
            nonlocal passed, failed
            if condition:
                print(f"  PASS: {name}")
                passed += 1
            else:
                print(f"  FAIL: {name} -- {detail}")
                failed += 1

        try:
            # =============================================================
            # 1. add_goal_node
            # =============================================================
            print("\n[Test: add_goal_node]")

            # 1a. Create root goal
            text, root_id = self.add_goal_node(
                content=f"{prefix}_root_goal",
                node_type="goal",
                tags=[tag],
                status="active",
            )
            check(
                "Root goal created",
                text and "error" not in text.lower() and root_id is not None,
                f"text={text}",
            )
            if root_id:
                self.created_nodes.append(root_id)
                print(f"  Root goal ID: {root_id}")

            # 1b. Create child task
            text, child_id = self.add_goal_node(
                content=f"{prefix}_child_task",
                node_type="task",
                parent_id=root_id,
                root_id=root_id,
                tags=[tag],
            )
            check(
                "Child task created",
                text and "error" not in text.lower() and child_id is not None,
                f"text={text}",
            )
            if child_id:
                self.created_nodes.append(child_id)
                print(f"  Child task ID: {child_id}")

            # 1c. Invalid node_type
            text, _ = self.add_goal_node(content="test", node_type="invalid")
            check(
                "Invalid node_type rejected",
                text and "error" in text.lower(),
                f"text={text}",
            )

            # 1d. parent_id without root_id
            text, _ = self.add_goal_node(
                content="test", node_type="task", parent_id="some-id"
            )
            check(
                "parent_id without root_id rejected",
                text and "error" in text.lower(),
                f"text={text}",
            )

            # Wait briefly for async indexing
            time.sleep(2)

            # =============================================================
            # 2. search_goal_nodes
            # =============================================================
            print("\n[Test: search_goal_nodes]")

            text = self.search_goal_nodes(query=prefix, tags=[tag])
            check(
                "Search finds goal nodes",
                text and "Goal Node Search Results" in text,
                f"text={text[:100] if text else 'None'}",
            )

            text = self.search_goal_nodes(query=prefix, node_type="goal")
            check(
                "Search filters by node_type",
                text and "[GOAL]" in text,
                f"text={text[:100] if text else 'None'}",
            )

            text = self.search_goal_nodes(query="ZZZZNONEXISTENT", tags=[tag])
            check(
                "Search with no matches",
                text and "No matching goal nodes found" in text,
                f"text={text}",
            )

            # =============================================================
            # 3. get_goal_tree
            # =============================================================
            print("\n[Test: get_goal_tree]")

            if root_id:
                text = self.get_goal_tree(root_id=root_id)
                check(
                    "Tree returned without error",
                    text and "error" not in text.lower(),
                    f"text={text[:100] if text else 'None'}",
                )

                # Verify valid JSON
                try:
                    json.loads(text) if text else None
                    check("Tree is valid JSON", True)
                except (json.JSONDecodeError, TypeError):
                    check("Tree is valid JSON", False, f"not JSON: {text[:100]}")

                # Verify tree structure
                if text:
                    try:
                        tree = json.loads(text)
                        check(
                            "Tree has correct root_id",
                            tree.get("id") == root_id,
                        )
                        check(
                            "Tree contains child node",
                            len(tree.get("children", [])) >= 1,
                        )
                        child_in_tree = any(
                            c.get("id") == child_id for c in tree.get("children", [])
                        )
                        if child_id:
                            check(
                                "Child found in tree",
                                child_in_tree,
                            )
                    except (json.JSONDecodeError, TypeError):
                        pass

            # Missing root
            text = self.get_goal_tree(root_id="nonexistent-root-uuid")
            check(
                "Missing root returns error",
                text and "error" in text.lower(),
                f"text={text}",
            )

            # =============================================================
            # 4. update_goal_node
            # =============================================================
            print("\n[Test: update_goal_node]")

            if child_id:
                text = self.update_goal_node(node_id=child_id, status="completed")
                check(
                    "Update status to completed",
                    text and "updated" in text.lower(),
                    f"text={text}",
                )

                text = self.update_goal_node(node_id=child_id, tags=[tag, "updated"])
                check(
                    "Update tags",
                    text and "updated" in text.lower(),
                    f"text={text}",
                )

            # Invalid status
            test_id = child_id or root_id
            if test_id:
                text = self.update_goal_node(node_id=test_id, status="bad_status")
                check(
                    "Invalid status rejected",
                    text and "error" in text.lower(),
                    f"text={text}",
                )

            # =============================================================
            # 5. delete_goal_node
            # =============================================================
            print("\n[Test: delete_goal_node]")

            # Create a temp node specifically for delete testing
            text, temp_id = self.add_goal_node(
                content=f"{prefix}_to_delete",
                node_type="goal",
                tags=[tag],
            )
            if temp_id:
                text = self.delete_goal_node(node_id=temp_id)
                check(
                    "Delete succeeded",
                    text and "deleted" in text.lower(),
                    f"text={text}",
                )
                if temp_id in self.created_nodes:
                    self.created_nodes.remove(temp_id)

        finally:
            # Cleanup all created nodes
            print("\n[Cleanup]")
            self.cleanup()

        print(f"\n{'=' * 40}")
        print(f"Results: {passed} passed, {failed} failed out of {passed + failed}")
        return failed == 0


def main():
    parser = argparse.ArgumentParser(
        description="Test goal-tree MCP tools against a live server"
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Show detailed request/response"
    )
    parser.add_argument(
        "--host",
        type=str,
        default="http://localhost",
        help="Server host (default: http://localhost)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Server port (default: 8000; use 8001 for proxy)",
    )
    args = parser.parse_args()

    tester = GoalTester(host=args.host, port=args.port, verbose=args.verbose)

    # Initialize session
    try:
        init_resp = tester.init()
        server_info = init_resp.get("result", {}).get("serverInfo", {})
        print(f"Session initialized: {server_info}")
    except requests.ConnectionError as e:
        print(f"ERROR: Cannot connect to {args.host}:{args.port} - {e}")
        print("Make sure main.py (or the proxy) is running.")
        sys.exit(1)

    success = tester.run_tests()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
