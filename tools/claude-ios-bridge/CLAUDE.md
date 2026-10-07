# Claude iOS Bridge

Local bridge service connecting Catalyst iOS app to Claude Code via Agent SDK.

## Commands

```bash
bun install        # Install dependencies
bun run start      # Start the server
bun run dev        # Start with auto-reload
bun run typecheck  # Type check TypeScript
```

## Architecture

```
iOS App (ClaudeSSEService.swift)
    ↓ HTTP/SSE (port 5200)
Claude iOS Bridge (this service)
    ↓ Claude Agent SDK
Claude Code CLI
    ↓ CLI auth (subscription)
Claude API
```

## Key Files

- `src/index.ts` - Hono HTTP server with SSE endpoints
- `src/session.ts` - Claude Agent SDK wrapper with streaming
- `src/config.ts` - Environment configuration, MCP servers
- `src/types.ts` - TypeScript type definitions

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check |
| GET | `/api/status` | Service status (auth required) |
| POST | `/api/claude/sse` | Send message (SSE stream) |
| GET | `/api/session/:deviceId` | Get session status |
| POST | `/api/session/:deviceId/new` | Create new session |
| POST | `/api/session/:deviceId/stop` | Stop current query |
| DELETE | `/api/session/:deviceId/close` | Close session |

### Health Sync Endpoints (for Protect The Asset)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/health-sync/push` | Push health metrics from iOS |
| GET | `/api/health-sync/pull` | Pull health metrics to iOS |
| GET | `/api/health-sync/status` | Check sync status |

**Push Request:**
```json
{
  "device_id": "string",
  "metrics": [
    {
      "type": "steps" | "weight" | "heartRate" | ...,
      "value": number,
      "unit": "string",
      "timestamp": "ISO8601",
      "source": "healthkit"
    }
  ],
  "sync_timestamp": "ISO8601"
}
```

**Pull Query Params:**
- `device_id` (required)
- `since` (optional ISO8601)
- `types` (optional comma-separated list)

**Data Storage:**
- Metrics: `{{CATALYST_ROOT}}/capsules/protect-the-asset/data/health_metrics.jsonl`
- Sync log: `{{CATALYST_ROOT}}/capsules/protect-the-asset/data/sync_log.json`

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `CLAUDE_BRIDGE_PORT` | 5200 | Server port |
| `CLAUDE_BRIDGE_HOST` | 0.0.0.0 | Server host |
| `CLAUDE_BRIDGE_API_KEY` | required | API key for iOS app |
| `CLAUDE_WORKING_DIR` | ~/Catalyst | Working directory |

## iOS App Integration

The iOS app's `APIConfig.swift` now supports two service modes:

```swift
// Local bridge mode (default, recommended)
APIConfig.serviceMode = .localBridge

// Remote Cloudflare tunnel mode
APIConfig.serviceMode = .cloudflare
```

## Running as Service

```bash
# Copy plist
cp launchagent/com.claude-ios-bridge.plist.template ~/Library/LaunchAgents/com.claude-ios-bridge.plist

# Edit with your API key
nano ~/Library/LaunchAgents/com.claude-ios-bridge.plist

# Load service
launchctl load ~/Library/LaunchAgents/com.claude-ios-bridge.plist

# View logs
tail -f /tmp/claude-ios-bridge.log
```

## MCP Servers

Configured MCP servers (in `config.ts`):
- `agent-memory` - Persistent learning (HTTP SSE)
- `builder-memory` - Knowledge graph
- `context7` - Library documentation
- `supabase` - Database operations
- `filesystem` - File access
- `siri-shortcuts` - macOS automation

## Session Management

Sessions are per-device (keyed by `device_id` from iOS app).
Session files stored at: `/tmp/claude-ios-bridge-session-{deviceId}.json`

Sessions persist across service restarts and can be resumed.
