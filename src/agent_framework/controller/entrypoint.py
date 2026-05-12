"""Container entrypoint for the agent controller."""

from __future__ import annotations

import os
import sys

from agent_framework.controller.mcp_server import mcp


def main() -> None:
    """Start the controller MCP server.

    Environment:
        CONTROLLER_PORT: Port for SSE transport (default: 8000)
        CONTROLLER_STATE_DIR: Path to state directory (default: /state)
    """
    port = int(os.environ.get("CONTROLLER_PORT", "8000"))
    state_dir = os.environ.get("CONTROLLER_STATE_DIR", "/state")

    os.makedirs(state_dir, exist_ok=True)
    os.makedirs(f"{state_dir}/compose", exist_ok=True)

    print(f"Agent Controller starting on port {port} ...", file=sys.stderr)
    mcp.run(transport="sse", port=port)


if __name__ == "__main__":
    main()
