#!/bin/bash

# MCP Server Warmer - Pre-loads servers to reduce health check timeouts
# This script sends initialization requests to all configured MCP servers

echo "Warming up MCP servers..."

INIT_MSG='{"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2024-11-05", "capabilities": {"roots": {"listChanged": true}, "sampling": {}}, "clientInfo": {"name": "claude", "version": "1.0"}}}'

# Warm up apple-doc server
echo "Warming apple-doc server..."
timeout 5s bash -c "echo '$INIT_MSG' | node {{CATALYST_ROOT}}/global/apple-doc-mcp/src/web/site/apple-doc-mcp/dist/index.js" > /dev/null 2>&1

# Warm up filesystem server  
echo "Warming filesystem server..."
timeout 5s bash -c "echo '$INIT_MSG' | npx @modelcontextprotocol/server-filesystem {{CATALYST_ROOT}} /tmp" > /dev/null 2>&1

# Warm up iterm server
echo "Warming iterm server..."
timeout 5s bash -c "echo '$INIT_MSG' | npx -y enhanced-iterm-mcp-server" > /dev/null 2>&1

echo "Server warmup complete."