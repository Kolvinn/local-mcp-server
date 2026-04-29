#!/bin/bash

# ==========================================
# Configuration
# ==========================================
DEFAULT_PORT=8001
HOST="http://localhost"
PROTOCOL_VERSION="2024-11-05"

# ==========================================
# Globals & Flags
# ==========================================
VERBOSE=false
SESSION_ID=""
PORT=$DEFAULT_PORT

# ==========================================
# Helper: Print Usage
# ==========================================
print_usage() {
    echo "Usage: ./mcp-tester.sh [OPTIONS] COMMAND [ARGS]"
    echo ""
    echo "Options:"
    echo "  -v, --verbose      Show detailed request/response headers and raw payloads"
    echo "  -s, --session ID   Append a session ID to the URL (for SSE testing)"
    echo "  -p, --port PORT    Override default port (default: 8001)"
    echo "  -h, --help         Show this help message"
    echo ""
    echo "Commands:"
    echo "  init               Send the 'initialize' handshake"
    echo "  ping               Send a 'ping' to check server liveliness"
    echo "  tools              List available tools (tools/list)"
    echo "  call <name> [args] Call a specific tool. Args must be a valid JSON string."
    echo "  resources          List available resources (resources/list)"
    echo "  prompts            List available prompts (prompts/list)"
    echo ""
    echo "Examples:"
    echo "  ./mcp-tester.sh init"
    echo "  ./mcp-tester.sh -v tools"
    echo "  ./mcp-tester.sh call my_tool '{\"arg1\": \"value\"}'"
    echo "  ./mcp-tester.sh -s xyz-123 call my_tool '{}'"
}

# ==========================================
# Parse Global Options
# ==========================================
while [[ "$#" -gt 0 ]]; do
    case $1 in
        -v|--verbose) VERBOSE=true; shift ;;
        -s|--session) SESSION_ID="$2"; shift 2 ;;
        -p|--port) PORT="$2"; shift 2 ;;
        -h|--help) print_usage; exit 0 ;;
        *) break ;; # Stop parsing options, the rest is the command
    esac
done

COMMAND=$1
shift # Remove command from arguments, leaving only args

# ==========================================
# Construct Base URL
# ==========================================
URL="${HOST}:${PORT}/mcp"
if [ -n "$SESSION_ID" ]; then
    URL="${URL}?session_id=${SESSION_ID}"
fi

# ==========================================
# Core Request Function
# ==========================================
send_request() {
    local method="$1"
    local params="${2:-{}}"
    local id=$RANDOM # Generate a random request ID for tracing

    # Construct the JSON payload
    local payload=$(cat <<EOF
{
  "jsonrpc": "2.0",
  "id": "${id}",
  "method": "${method}",
  "params": ${params}
}
EOF
)

    # Setup standard MCP headers
    local headers=(
        -H "Content-Type: application/json"
        -H "Accept: application/json, text/event-stream"
        -H "mcp-protocol-version: ${PROTOCOL_VERSION}"
    )

    if [ "$VERBOSE" = true ]; then
        echo -e "\n\033[1;34m=== OUTGOING REQUEST ===\033[0m"
        echo "Target URL: $URL"
        echo "Payload:"
        # Pretty print outgoing JSON if jq is available, otherwise raw
        if command -v jq &> /dev/null; then
            echo "$payload" | jq .
        else
            echo "$payload"
        fi
        echo -e "\033[1;34m========================\033[0m\n"
        
        # Use curl with -v for full HTTP protocol insight
        echo -e "\033[1;33m--- CURL OUTPUT ---\033[0m"
        curl -v -X POST "$URL" "${headers[@]}" -d "$payload"
        echo -e "\n\033[1;33m-------------------\033[0m\n"
    else
        # Silent curl, just output the response body
        response=$(curl -s -X POST "$URL" "${headers[@]}" -d "$payload")
        
        # Pretty print response if jq is available
        if command -v jq &> /dev/null; then
            echo "$response" | jq .
        else
            echo "$response"
        fi
    fi
}

# ==========================================
# Command Router
# ==========================================
case "$COMMAND" in
    init)
        params=$(cat <<EOF
{
  "protocolVersion": "${PROTOCOL_VERSION}",
  "capabilities": {},
  "clientInfo": {
    "name": "bash-cli-tester",
    "version": "1.0.0"
  }
}
EOF
)
        send_request "initialize" "$params"
        ;;
        
    ping)
        send_request "ping" "{}"
        ;;
        
    tools)
        send_request "tools/list" "{}"
        ;;
        
    call)
        TOOL_NAME="$1"
        TOOL_ARGS="${2:-{}}"
        
        if [ -z "$TOOL_NAME" ]; then
            echo "Error: Tool name is required."
            echo "Usage: ./mcp-tester.sh call <name> [args]"
            exit 1
        fi
        
        params=$(cat <<EOF
{
  "name": "${TOOL_NAME}",
  "arguments": ${TOOL_ARGS}
}
EOF
)
        send_request "tools/call" "$params"
        ;;
        
    resources)
        send_request "resources/list" "{}"
        ;;
        
    prompts)
        send_request "prompts/list" "{}"
        ;;
        
    "")
        echo "Error: No command provided."
        print_usage
        exit 1
        ;;
        
    *)
        echo "Error: Unknown command '$COMMAND'"
        print_usage
        exit 1
        ;;
esac