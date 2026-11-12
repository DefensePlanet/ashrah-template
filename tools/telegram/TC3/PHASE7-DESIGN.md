# Phase 7: Configuration & Launch - Design Document

**Status:** 🔨 In Progress
**Goal:** Production-ready deployment with LaunchAgent, environment configuration, and automated setup

---

## Overview

Phase 7 transforms the Telegram {{ORCHESTRATOR_NAME}} Bot from a development prototype into a production service that runs persistently on {{USER_NAME}}'s Mac. This includes:

1. Environment variable configuration
2. LaunchAgent setup for automatic startup
3. Installation/deployment scripts
4. Error handling and logging
5. Deployment testing and validation

---

## Requirements

### Functional Requirements
- ✅ Bot starts automatically on system boot
- ✅ Bot restarts automatically on crashes
- ✅ All environment variables properly configured
- ✅ Logs accessible and rotated
- ✅ Simple installation process
- ✅ Safe uninstallation process

### Non-Functional Requirements
- ✅ Zero manual steps after installation
- ✅ Survives system reboots
- ✅ Clear error messages for misconfiguration
- ✅ Minimal resource usage
- ✅ Compatible with existing Catalyst infrastructure

---

## Environment Variables

### Required Variables

| Variable | Description | Example | Source |
|----------|-------------|---------|--------|
| `TELEGRAM_BOT_TOKEN` | Bot token from @BotFather | `123456:ABC-DEF...` | Telegram |
| `TELEGRAM_ALLOWED_USERS` | Comma-separated user IDs | `12345678,87654321` | Telegram |

### Optional Variables (with defaults)

| Variable | Description | Default | Notes |
|----------|-------------|---------|-------|
| `CLAUDE_WORKING_DIR` | Working directory for Claude | `$HOME` | Usually Catalyst root |
| `OPENAI_API_KEY` | For voice transcription | - | Optional, voice disabled without it |
| `TRANSCRIPTION_CONTEXT` | Extra context for transcription | - | Improves accuracy |
| `THINKING_KEYWORDS` | Keywords for extended thinking | `think,pensa,ragiona` | Comma-separated |
| `THINKING_DEEP_KEYWORDS` | Keywords for deep thinking | `ultrathink,think hard` | Comma-separated |
| `AUDIT_LOG_PATH` | Path for audit logs | `/tmp/claude-telegram-audit.log` | - |
| `AUDIT_LOG_JSON` | JSON format for logs | `false` | `true` or `false` |
| `RATE_LIMIT_ENABLED` | Enable rate limiting | `true` | `true` or `false` |
| `RATE_LIMIT_REQUESTS` | Max requests per window | `20` | Integer |
| `RATE_LIMIT_WINDOW` | Window in seconds | `60` | Integer |

### MCP-Related Variables

**Note:** MCP servers are configured in `mcp-config.ts`, but some require environment variables.

| Variable | Required For | Notes |
|----------|--------------|-------|
| `SUPABASE_ACCESS_TOKEN` | supabase-toolkit | From Supabase dashboard |
| `SUPABASE_PROJECT_ID` | supabase-toolkit | Project reference ID |
| `SUPABASE_DB_PASSWORD` | supabase-toolkit | Database password |
| `APPLE_DOCS_PATH` | apple-doc-mcp | Path to Apple docs cache |
| (others) | Various MCPs | See mcp-config.ts |

---

## LaunchAgent Configuration

### File Location
```
~/Library/LaunchAgents/com.catalyst.telegram-{{ORCHESTRATOR_NAME_LOWER}}-bot.plist
```

### Key Configuration Points

1. **Program Path:** Use absolute path to `bun` binary
2. **Working Directory:** Project root (`{{CATALYST_ROOT}}/tools/telegram-{{ORCHESTRATOR_NAME_LOWER}}-bot`)
3. **Environment:** Load from `.env` file
4. **Logging:** Stdout/stderr to files
5. **Auto-restart:** On crashes, but not on normal exit
6. **Keep Alive:** Always running

### Sample Structure
```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.catalyst.telegram-{{ORCHESTRATOR_NAME_LOWER}}-bot</string>

    <key>ProgramArguments</key>
    <array>
        <string>/opt/homebrew/bin/bun</string>
        <string>run</string>
        <string>src/index.ts</string>
    </array>

    <key>WorkingDirectory</key>
    <string>{{CATALYST_ROOT}}/tools/telegram-{{ORCHESTRATOR_NAME_LOWER}}-bot</string>

    <key>EnvironmentVariables</key>
    <dict>
        <!-- Loaded from .env file -->
    </dict>

    <key>StandardOutPath</key>
    <string>{{CATALYST_ROOT}}/tools/telegram-{{ORCHESTRATOR_NAME_LOWER}}-bot/logs/stdout.log</string>

    <key>StandardErrorPath</key>
    <string>{{CATALYST_ROOT}}/tools/telegram-{{ORCHESTRATOR_NAME_LOWER}}-bot/logs/stderr.log</string>

    <key>RunAtLoad</key>
    <true/>

    <key>KeepAlive</key>
    <dict>
        <key>SuccessfulExit</key>
        <false/>
    </dict>
</dict>
</plist>
```

### Important Notes

1. **Environment Variables:** LaunchAgents don't inherit shell environment
   - Must explicitly set in plist or load from file
   - Use absolute paths for everything

2. **PATH Variable:** Must include:
   - `/opt/homebrew/bin` (Homebrew)
   - `/usr/local/bin` (local installs)
   - `$HOME/.bun/bin` (Bun)
   - `$HOME/.local/bin` (user binaries)

3. **Auto-Restart Behavior:**
   - `SuccessfulExit = false` means: only restart on crashes (exit code ≠ 0)
   - Prevents restart loops if bot intentionally exits
   - Manual restart: `launchctl kickstart -k gui/$(id -u)/com.catalyst.telegram-{{ORCHESTRATOR_NAME_LOWER}}-bot`

---

## Installation Script

### Purpose
Automate the deployment process with a single command.

### Script: `install.sh`

**Features:**
- ✅ Validate environment variables
- ✅ Check dependencies (Bun, Node, etc.)
- ✅ Create logs directory
- ✅ Copy plist to LaunchAgents
- ✅ Load LaunchAgent
- ✅ Verify bot is running

**Usage:**
```bash
./install.sh
```

**Steps:**
1. Check if `.env` exists, prompt to create if missing
2. Validate required environment variables
3. Check Bun installation (`bun --version`)
4. Create logs directory (`logs/`)
5. Generate plist from template with current user/paths
6. Copy plist to `~/Library/LaunchAgents/`
7. Load LaunchAgent (`launchctl load`)
8. Wait 3 seconds
9. Check if bot is running (`launchctl list | grep telegram-{{ORCHESTRATOR_NAME_LOWER}}`)
10. Print success message with next steps

### Script: `uninstall.sh`

**Features:**
- ✅ Stop running bot
- ✅ Unload LaunchAgent
- ✅ Remove plist file
- ✅ Optional: clean logs

**Usage:**
```bash
./uninstall.sh [--clean-logs]
```

---

## Log Management

### Log Files

| File | Purpose | Rotation |
|------|---------|----------|
| `logs/stdout.log` | Normal output | Manual |
| `logs/stderr.log` | Error output | Manual |
| `/tmp/claude-telegram-audit.log` | Audit trail | Manual |

### Log Rotation Strategy

**Option 1: Manual (Phase 7)**
- User can manually archive/delete logs
- Simple, no dependencies

**Option 2: Automated (Future)**
- Use `newsyslog` or custom script
- Rotate daily, keep 7 days
- Compress old logs

**Phase 7 Decision:** Manual rotation is sufficient for personal use.

### Viewing Logs

```bash
# Real-time stdout
tail -f logs/stdout.log

# Real-time stderr
tail -f logs/stderr.log

# Real-time combined
tail -f logs/*.log

# Last 50 lines
tail -n 50 logs/stdout.log

# Search for errors
grep -i error logs/stderr.log
```

---

## Error Handling

### Startup Validation

**Already implemented in `src/config.ts`:**
- ✅ Validates `TELEGRAM_BOT_TOKEN` (exits if missing)
- ✅ Validates `TELEGRAM_ALLOWED_USERS` (exits if missing)
- ✅ Warns if MCP environment variables missing (but continues)

### Runtime Error Handling

**Already implemented:**
- ✅ Bot error handler (`bot.catch()`)
- ✅ Graceful shutdown on SIGINT/SIGTERM
- ✅ Session error handling

### LaunchAgent Error Handling

**New additions needed:**
1. **Startup delay:** 5-second delay before first start (wait for network)
2. **Throttle restarts:** Prevent restart loops (max 3 restarts per 60s)
3. **Exit on fatal errors:** Distinguish crash vs intentional exit

---

## Deployment Process

### Initial Deployment

```bash
# 1. Navigate to project
cd {{CATALYST_ROOT}}/tools/telegram-{{ORCHESTRATOR_NAME_LOWER}}-bot

# 2. Create .env file (if not exists)
cp .env.example .env
# Edit .env with actual values

# 3. Install dependencies
bun install

# 4. Test bot manually (optional)
bun run src/index.ts

# 5. Install as LaunchAgent
./install.sh

# 6. Verify running
launchctl list | grep telegram-{{ORCHESTRATOR_NAME_LOWER}}
```

### Updates and Redeployment

```bash
# 1. Stop bot
launchctl unload ~/Library/LaunchAgents/com.catalyst.telegram-{{ORCHESTRATOR_NAME_LOWER}}-bot.plist

# 2. Pull changes / make edits
git pull
# or edit files

# 3. Restart bot
launchctl load ~/Library/LaunchAgents/com.catalyst.telegram-{{ORCHESTRATOR_NAME_LOWER}}-bot.plist
```

**Alternative (hot reload):**
Since Phase 6 implements hot reload, most changes don't require restart:
- Agent changes: auto-reload
- Skill changes: auto-reload
- Code changes: require restart

---

## Testing Checklist

### Pre-Deployment Tests
- ✅ Manual run: `bun run src/index.ts` works
- ✅ Environment variables loaded correctly
- ✅ MCP servers connect successfully
- ✅ Catalyst resources load (28 agents, 323 skills)
- ✅ Bot responds to /start command

### Deployment Tests
- ✅ LaunchAgent loads without errors
- ✅ Bot starts automatically
- ✅ Bot survives system reboot
- ✅ Bot restarts on crash
- ✅ Logs are written correctly
- ✅ All commands work (/start, /new, /sync, etc.)

### Integration Tests
- ✅ Voice transcription (if OPENAI_API_KEY set)
- ✅ Photo handling
- ✅ Document handling
- ✅ Specialist detection and loading
- ✅ Skill detection and loading
- ✅ Hot reload on file changes

---

## Security Considerations

### Environment Variables
- ✅ `.env` file should be in `.gitignore` (already is)
- ✅ Never commit tokens/keys to git
- ✅ Use secure storage (already using Strongbox via Catalyst)

### File Permissions
- ✅ `.env` should be 600 (owner read/write only)
- ✅ plist should be 644 (standard LaunchAgent permissions)
- ✅ Logs should be 644 (readable by owner)

### Safety Prompts
- ✅ Already implemented (SAFETY_PROMPT in config.ts)
- ✅ Blocked command patterns (rm -rf /, fork bomb, etc.)
- ✅ Allowed directories enforcement

---

## Documentation Updates

### README.md Updates
- ✅ Add installation section
- ✅ Add configuration section
- ✅ Add troubleshooting section
- ✅ Update command reference

### New Files
- ✅ `.env.example` - Environment variable template
- ✅ `install.sh` - Installation script
- ✅ `uninstall.sh` - Uninstallation script
- ✅ `com.catalyst.telegram-{{ORCHESTRATOR_NAME_LOWER}}-bot.plist` - LaunchAgent configuration

---

## Implementation Checklist

### Step 1: Environment Configuration
- [ ] Create `.env.example` with all variables documented
- [ ] Add validation for critical variables
- [ ] Test with minimal configuration

### Step 2: LaunchAgent Setup
- [ ] Create plist template
- [ ] Test plist syntax (`plutil -lint`)
- [ ] Test manual load/unload
- [ ] Verify auto-restart behavior

### Step 3: Installation Scripts
- [ ] Write `install.sh`
- [ ] Write `uninstall.sh`
- [ ] Make scripts executable
- [ ] Test installation process
- [ ] Test uninstallation process

### Step 4: Logging
- [ ] Create `logs/` directory
- [ ] Test log output
- [ ] Document log viewing commands
- [ ] Add log rotation notes

### Step 5: Documentation
- [ ] Update README.md
- [ ] Create troubleshooting guide
- [ ] Document deployment process
- [ ] Add examples

### Step 6: Testing
- [ ] Test manual run
- [ ] Test LaunchAgent deployment
- [ ] Test auto-restart on crash
- [ ] Test system reboot
- [ ] Test all commands

### Step 7: Completion
- [ ] Create Phase 7 completion report
- [ ] Create quick reference
- [ ] Mark Phase 7 as complete

---

## Known Issues and Limitations

1. **LaunchAgent delays:** May take 2-3 seconds to start on system boot
   - Solution: Add 5-second `StartInterval` if needed

2. **Environment variables:** Must be explicitly set in plist
   - Solution: Use `envsubst` or similar to generate plist from .env

3. **Log rotation:** Manual only
   - Solution: Acceptable for personal use, document process

4. **No web UI:** All control via Telegram commands
   - Solution: Not needed for Phase 7, potential future enhancement

---

## Success Criteria

Phase 7 is complete when:
- ✅ Bot can be installed with a single command
- ✅ Bot starts automatically on system boot
- ✅ Bot restarts automatically on crashes
- ✅ All configuration is documented
- ✅ All tests pass
- ✅ Logs are accessible and useful

---

## Next Phase: Phase 8 (Documentation)

Phase 8 will focus on comprehensive documentation:
- User guide
- Developer guide
- Architecture documentation
- Troubleshooting guide
- Command reference

---

*Phase 7 Design Complete - Ready for Implementation*
