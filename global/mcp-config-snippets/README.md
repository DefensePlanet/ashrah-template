# MCP Configuration Snippets

This directory contains MCP server configuration snippets for different clients.

## Bridge MCP

The Bridge MCP enables two-way communication between Codex and Claude Code.

### Claude Code Configuration

Add to your `~/.claude/mcp_servers.json`:

```json
{
  "bridge": {
    "command": "{{HOME_DIR}}/Documents/Builder/tools/bridge-mcp/start.sh",
    "args": [],
    "env": {}
  }
}
```

Or use: `claude mcp add bridge {{HOME_DIR}}/Documents/Builder/tools/bridge-mcp/start.sh`

### Codex Configuration  

Add to your Codex MCP configuration:

```json
{
  "mcp_servers": {
    "bridge": {
      "command": "{{HOME_DIR}}/Documents/Builder/tools/bridge-mcp/start.sh", 
      "args": [],
      "env": {}
    }
  }
}
```

## Available Tools

Once configured, both clients will have access to:

- `call_claude_code` - Execute Claude Code commands from Codex
- `call_codex` - Execute Codex commands from Claude Code

## Usage Examples

From Claude Code:
```
Use the call_codex tool to run a Python script in Codex
```

From Codex:
```
Use the call_claude_code tool to analyze this codebase with Claude Code
```