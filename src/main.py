from fastmcp import FastMCP
from fastmcp.server import create_proxy
import os

# 1. Initialize the central orchestrator
mcp = FastMCP("CompositeOrchestrator")

# 2. Mount external servers
# HTTP Proxy
mcp.mount(create_proxy("http://mcp-memory-service:8000/mcp"), namespace="remote_api")


# @mcp.custom_route("/health")
# def health_check():
#     return {"status": "ok"}
# Python Script Proxy
#mcp.mount(create_proxy("./my_external_server.py"), namespace="local_server")

# 3. Mount npm package (e.g., GitHub)
# github_config = {
#     "mcpServers": {
#         "github": {
#             "command": "npx",
#             "args": ["-y", "@modelcontextprotocol/server-github"],
#             "env": {"GITHUB_PERSONAL_ACCESS_TOKEN": os.environ.get("GITHUB_TOKEN")}
#         }
#     }
# }
#mcp.mount(create_proxy(github_config), namespace="github")

if __name__ == "__main__":
    # IMPORTANT: Use transport="sse" or "streamable-http" for network access
    # Use host="0.0.0.0" to allow connections from outside the container
    mcp.run(transport="streamable-http", host="0.0.0.0", port=8001)
