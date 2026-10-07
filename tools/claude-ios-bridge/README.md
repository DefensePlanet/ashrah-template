# Claude iOS Bridge

Local bridge service that connects the Catalyst iOS app to Claude Code via the Agent SDK.

## Architecture

```
iOS App (ClaudeSSEService.swift)
    ↓ HTTP/SSE
Claude iOS Bridge (this service)
    ↓ Claude Agent SDK
Claude Code CLI
    ↓ CLI auth (subscription)
Claude API
```

## Why This Exists

The iOS app previously connected through a remote backend (`api.builderos.app`), which added latency and required internet infrastructure. This local bridge:

1. **Uses CLI auth** - Subscription-based, not API credits
2. **Direct connection** - No remote server intermediary
3. **Full MCP support** - Access to agent-memory, context7, etc.
4. **Session persistence** - Resume conversations after app restart
5. **Local network** - Works over LAN or Tailscale

## Quick Start

```bash
# Install dependencies
bun install

# Create .env file
cp .env.example .env
# Edit .env with your API key

# Run the service
bun run start

# Or with auto-reload
bun run dev
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check |
| GET | `/api/status` | Service status |
| POST | `/api/claude/sse` | Send message (SSE stream) |
| GET | `/api/session/:deviceId` | Get session status |
| POST | `/api/session/:deviceId/new` | Create new session |
| POST | `/api/session/:deviceId/stop` | Stop current query |
| DELETE | `/api/session/:deviceId/close` | Close session |

## iOS App Configuration

Update `APIConfig.swift` to point to the local bridge:

```swift
// For local development (Mac running bridge service)
static var tunnelURL = "http://192.168.x.x:5200"  // Your Mac's IP

// For same machine (Simulator)
static var tunnelURL = "http://localhost:5200"
```

## Running as a Service (macOS)

1. Copy the template plist:
```bash
cp launchagent/com.claude-ios-bridge.plist.template ~/Library/LaunchAgents/com.claude-ios-bridge.plist
```

2. Edit the plist with your API key:
```bash
nano ~/Library/LaunchAgents/com.claude-ios-bridge.plist
# Replace REPLACE_WITH_YOUR_API_KEY with your actual key
```

3. Load the service:
```bash
launchctl load ~/Library/LaunchAgents/com.claude-ios-bridge.plist
```

4. Check logs:
```bash
tail -f /tmp/claude-ios-bridge.log
tail -f /tmp/claude-ios-bridge.err
```

5. Restart/stop:
```bash
# Restart
launchctl kickstart -k gui/$(id -u)/com.claude-ios-bridge

# Stop
launchctl unload ~/Library/LaunchAgents/com.claude-ios-bridge.plist
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `CLAUDE_BRIDGE_PORT` | 5200 | Server port |
| `CLAUDE_BRIDGE_HOST` | 0.0.0.0 | Server host (0.0.0.0 for LAN access) |
| `CLAUDE_BRIDGE_API_KEY` | (required) | API key for iOS app auth |
| `CLAUDE_WORKING_DIR` | ~/Catalyst | Working directory for Claude |
| `ALLOWED_PATHS` | (auto) | Allowed directories for file access |
| `CLAUDE_CLI_PATH` | (auto) | Path to Claude CLI |

## Security

- **API Key**: The iOS app must send `X-API-Key` header with every request
- **Local network**: Only accessible on your local network or Tailscale
- **CLI auth**: Uses Claude Code subscription, not API credits
- **Session isolation**: Each device gets its own session

## Comparison to Telegram Bot

This service is adapted from the [Claude Telegram Bot](../claude-telegram-bot-new/). Key differences:

| Feature | Telegram Bot | iOS Bridge |
|---------|-------------|------------|
| Transport | grammY (Telegram API) | Hono (HTTP/SSE) |
| Client | Telegram app | Catalyst iOS app |
| Session scope | Per Telegram user | Per device ID |
| Rate limiting | Token bucket | None (single user) |
| Safety prompt | Telegram-specific | iOS-specific |

## Troubleshooting

### "Cannot find Claude CLI"
```bash
# Check if claude is in PATH
which claude

# If not found, install Claude Code CLI
# Or set CLAUDE_CLI_PATH in .env
```

### "Connection refused on iOS"
1. Check that the bridge is running: `curl http://localhost:5200/health`
2. Check your Mac's firewall settings
3. Ensure iOS device is on the same network
4. Use Mac's IP address, not `localhost`, on physical device

### Session not resuming
Sessions are stored in `/tmp/claude-ios-bridge-session-{deviceId}.json`. If the file is corrupted or missing, the bridge creates a new session.
