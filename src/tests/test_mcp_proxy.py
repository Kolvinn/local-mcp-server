#!/usr/bin/env python3
"""
MCP Proxy Server Test Suite

Translates the mcp-test.sh bash test suite into Python for easier testing and debugging.
Tests the MCP proxy server (mcp_proxy_server.py) using the MCP protocol.
"""

import json
import uuid
import argparse
from typing import Optional
import requests


class MCPTester:
    """Test client for MCP proxy server."""

    def __init__(
        self,
        host: str = "http://localhost",
        port: int = 8001,
        session_id: Optional[str] = None,
        verbose: bool = False,
    ):
        self.host = host
        self.port = port
        self.session_id = session_id
        self.verbose = verbose
        self.protocol_version = "2024-11-05"
        self.base_url = f"{host}:{port}/mcp"
        if session_id:
            self.base_url += f"?session_id={session_id}"

        self.headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
            "mcp-protocol-version": self.protocol_version,
        }

    def send_request(self, method: str, params: Optional[dict] = None) -> dict:
        """Send an MCP JSON-RPC request to the server."""
        payload = {
            "jsonrpc": "2.0",
            "id": str(uuid.uuid4()),
            "method": method,
            "params": params or {},
        }

        if self.verbose:
            print("\n=== OUTGOING REQUEST ===")
            print(f"Target URL: {self.base_url}")
            print("Payload:")
            print(json.dumps(payload, indent=2))
            print("========================\n")

        response = requests.post(
            self.base_url, headers=self.headers, json=payload, timeout=30
        )

        if self.verbose:
            print("\n--- CURL OUTPUT ---")
            print(f"Status Code: {response.status_code}")
            print(f"Response Headers: {dict(response.headers)}")
            print(f"Response Body:\n{response.text}")
            print("-------------------\n")

        try:
            return response.json()
        except json.JSONDecodeError:
            return {"error": "Invalid JSON response", "raw": response.text}

    def init(self) -> dict:
        """Send the 'initialize' handshake."""
        params = {
            "protocolVersion": self.protocol_version,
            "capabilities": {},
            "clientInfo": {"name": "python-cli-tester", "version": "1.0.0"},
        }
        return self.send_request("initialize", params)

    def ping(self) -> dict:
        """Send a 'ping' to check server liveliness."""
        return self.send_request("ping", {})

    def tools(self) -> dict:
        """List available tools (tools/list)."""
        return self.send_request("tools/list", {})

    def call(self, name: str, arguments: Optional[dict] = None) -> dict:
        """Call a specific tool."""
        params = {"name": name, "arguments": arguments or {}}
        return self.send_request("tools/call", params)

    def resources(self) -> dict:
        """List available resources (resources/list)."""
        return self.send_request("resources/list", {})

    def prompts(self) -> dict:
        """List available prompts (prompts/list)."""
        return self.send_request("prompts/list", {})


def main():
    parser = argparse.ArgumentParser(
        description="MCP Proxy Server Test Client",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python test_mcp_proxy.py init
  python test_mcp_proxy.py -v tools
  python test_mcp_proxy.py call my_tool '{"arg1": "value"}'
  python test_mcp_proxy.py -s xyz-123 call my_tool '{}'
        """,
    )

    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Show detailed request/response"
    )
    parser.add_argument(
        "-s", "--session", type=str, help="Append a session ID to the URL"
    )
    parser.add_argument(
        "-p",
        "--port",
        type=int,
        default=8001,
        help="Override default port (default: 8001)",
    )
    parser.add_argument(
        "--host",
        type=str,
        default="http://localhost",
        help="Host URL (default: http://localhost)",
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    subparsers.add_parser("init", help="Send the 'initialize' handshake")
    subparsers.add_parser("ping", help="Send a 'ping' to check server liveliness")
    subparsers.add_parser("tools", help="List available tools")
    subparsers.add_parser("resources", help="List available resources")
    subparsers.add_parser("prompts", help="List available prompts")

    call_parser = subparsers.add_parser("call", help="Call a specific tool")
    call_parser.add_argument("name", type=str, help="Tool name")
    call_parser.add_argument(
        "args", type=str, nargs="?", default="{}", help="Tool arguments as JSON string"
    )

    args = parser.parse_args()

    # if not args.command:
    #     parser.print_help()
    #     return

    tester = MCPTester(
        host=args.host,
        port=args.port,
        session_id=args.session,
        verbose=args.verbose,
    )

    result = None
    args.command = "init"
    if args.command == "init":
        result = tester.init()
    elif args.command == "ping":
        result = tester.ping()
    elif args.command == "tools":
        result = tester.tools()
    elif args.command == "resources":
        result = tester.resources()
    elif args.command == "prompts":
        result = tester.prompts()
    elif args.command == "call":
        try:
            tool_args = json.loads(args.args)
        except json.JSONDecodeError as e:
            print(f"Error: Invalid JSON for tool arguments: {e}")
            return
        result = tester.call(args.name, tool_args)

    if result:
        print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
