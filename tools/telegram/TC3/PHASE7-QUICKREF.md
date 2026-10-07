# Phase 7 Quick Reference - Configuration & Launch

## Installation

### One-Command Install
```bash
cd {{CATALYST_ROOT}}/tools/telegram-{{ORCHESTRATOR_NAME_LOWER}}-bot
./install.sh
```

### Prerequisites
1. Create `.env` file from template:
   ```bash
   cp .env.example .env
   nano .env  # Add your TELEGRAM_BOT_TOKEN and TELEGRAM_ALLOWED_USERS
   ```

2. Ensure Bun is installed:
   ```bash
   bun --version
   ```

---

## Required Environment Variables

Add these to `.env` file:

```bash
# Required - Bot will not start without these
TELEGRAM_BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz
TELEGRAM_ALLOWED_USERS=12345678,87654321
```

Get bot token: https://t.me/BotFather
Get user ID: https://t.me/userinfobot

---

## Optional Environment Variables

```bash
# Recommended
CLAUDE_WORKING_DIR={{CATALYST_ROOT}}
OPENAI_API_KEY=sk-...  # For voice transcription

# Optional MCP Services
SUPABASE_ACCESS_TOKEN=sbp_...
SUPABASE_PROJECT_ID=...
CONTEXT7_API_KEY=...
N8N_API_URL=http://localhost:5678/api/v1
OBS_WEBSOCKET_URL=ws://localhost:4455
```

See `.env.example` for full list.

---

## LaunchAgent Management

### Check Status
```bash
# Is bot running?
launchctl list | grep telegram-{{ORCHESTRATOR_NAME_LOWER}}

# Get PID
launchctl list | grep telegram-{{ORCHESTRATOR_NAME_LOWER}} | awk '{print $1}'
```

### Start/Stop/Restart
```bash
# Stop
launchctl unload ~/Library/LaunchAgents/com.catalyst.telegram-{{ORCHESTRATOR_NAME_LOWER}}-bot.plist

# Start
launchctl load ~/Library/LaunchAgents/com.catalyst.telegram-{{ORCHESTRATOR_NAME_LOWER}}-bot.plist

# Restart
launchctl kickstart -k gui/$(id -u)/com.catalyst.telegram-{{ORCHESTRATOR_NAME_LOWER}}-bot
```

---

## Log Management

### View Logs
```bash
# Real-time stdout
tail -f logs/stdout.log

# Real-time stderr
tail -f logs/stderr.log

# Real-time both
tail -f logs/*.log

# Last 50 lines
tail -n 50 logs/stdout.log

# Search for errors
grep -i error logs/stderr.log
```

### Log Locations
- **Stdout:** `logs/stdout.log` (normal output)
- **Stderr:** `logs/stderr.log` (errors)
- **Audit:** `/tmp/claude-telegram-audit.log` (optional)

### Log Rotation
```bash
# Archive current logs
mv logs/stdout.log logs/stdout.log.$(date +%Y%m%d)
mv logs/stderr.log logs/stderr.log.$(date +%Y%m%d)

# Restart to create new logs
launchctl kickstart -k gui/$(id -u)/com.catalyst.telegram-{{ORCHESTRATOR_NAME_LOWER}}-bot
```

---

## Uninstallation

### Uninstall (keep logs)
```bash
./uninstall.sh
```

### Uninstall (remove logs)
```bash
./uninstall.sh --clean-logs
```

---

## Troubleshooting

### Bot Won't Start
1. Check environment variables:
   ```bash
   cat .env | grep TELEGRAM
   ```

2. Test manually:
   ```bash
   bun run src/index.ts
   ```

3. Check stderr:
   ```bash
   tail -f logs/stderr.log
   ```

### Bot Crashes
1. Check crash logs:
   ```bash
   grep -i error logs/stderr.log
   tail -n 100 logs/stderr.log
   ```

2. Check LaunchAgent status:
   ```bash
   launchctl list | grep telegram-{{ORCHESTRATOR_NAME_LOWER}}
   ```

3. Restart bot:
   ```bash
   launchctl kickstart -k gui/$(id -u)/com.catalyst.telegram-{{ORCHESTRATOR_NAME_LOWER}}-bot
   ```

### Voice Transcription Not Working
- Ensure `OPENAI_API_KEY` is set in `.env`
- Check key is valid: https://platform.openai.com/api-keys

### MCP Servers Not Working
- Check MCP-specific environment variables in `.env`
- See `mcp-config.ts` for required variables per server

---

## Updates and Maintenance

### Update Code
```bash
# Stop bot
launchctl unload ~/Library/LaunchAgents/com.catalyst.telegram-{{ORCHESTRATOR_NAME_LOWER}}-bot.plist

# Update code (git pull, edit files, etc.)
git pull

# Restart bot
launchctl load ~/Library/LaunchAgents/com.catalyst.telegram-{{ORCHESTRATOR_NAME_LOWER}}-bot.plist
```

### Update Agents/Skills
**No restart needed!** Phase 6 hot reload detects changes automatically.

Just edit files in:
- `catalyst-agents/`
- `catalyst-skills/`

Changes reload within 500ms.

---

## Validation

### Test Installation
```bash
bun run test-phase7-deployment.ts
```

Expected: 61/61 tests passed

### Verify Bot Running
```bash
# 1. Check process
launchctl list | grep telegram-{{ORCHESTRATOR_NAME_LOWER}}

# 2. Check logs
tail -f logs/stdout.log

# 3. Test via Telegram
# Send /start command to bot
```

---

## File Locations

### Project Files
- **Source:** `{{CATALYST_ROOT}}/tools/telegram-{{ORCHESTRATOR_NAME_LOWER}}-bot/src/`
- **Config:** `.env` (gitignored)
- **Logs:** `logs/` (created by install.sh)

### System Files
- **LaunchAgent:** `~/Library/LaunchAgents/com.catalyst.telegram-{{ORCHESTRATOR_NAME_LOWER}}-bot.plist`
- **Audit Log:** `/tmp/claude-telegram-audit.log` (optional)

### Catalyst Resources (symlinked)
- **Agents:** `catalyst-agents/` → `{{CATALYST_ROOT}}/.claude/agents/`
- **Skills:** `catalyst-skills/` → `{{CATALYST_ROOT}}/.claude/skills/`
- **Identity:** `CATALYST_{{ORCHESTRATOR_NAME_UPPER}}.md` → `{{CATALYST_ROOT}}/CLAUDE.md`

---

## Key Features

### From Phase 6 (Auto-Sync)
- ✅ Hot reload for agents/skills (500ms debounce)
- ✅ `/sync` - Manual resource reload
- ✅ `/context` - View session state
- ✅ `/specialist` - Manage active specialist
- ✅ `/skills` - Manage loaded skills

### From Phase 5 (Session Context)
- ✅ Specialist persistence across messages
- ✅ Skill loading on-demand
- ✅ Context optimization (30K → 2K on follow-ups)

### From Phase 4 (Identity)
- ✅ Full {{ORCHESTRATOR_NAME}} personality (30K chars)
- ✅ Specialist detection and loading
- ✅ TTS summary stripping

---

## Security

### File Permissions
```bash
# Set .env permissions (owner read/write only)
chmod 600 .env

# Verify plist permissions (standard LaunchAgent)
ls -l ~/Library/LaunchAgents/com.catalyst.telegram-{{ORCHESTRATOR_NAME_LOWER}}-bot.plist
# Should be: -rw-r--r--
```

### Safety Features
- ✅ Blocked dangerous commands (rm -rf /, fork bombs)
- ✅ Allowed directories enforcement
- ✅ Confirmation for destructive operations
- ✅ Audit logging
- ✅ Rate limiting

---

## Performance

### Resource Usage
- **Memory:** ~50-100MB
- **CPU:** <1% idle, 5-10% active
- **Disk:** ~500MB (node_modules) + ~10MB (project)

### Timing
- **Installation:** ~15 seconds
- **Bot startup:** 2-3 seconds
- **First response:** 5-10 seconds
- **Subsequent:** 1-2 seconds

---

## Next Steps: Phase 8

Phase 8 will add comprehensive documentation:
- User guide
- Developer guide
- Architecture documentation
- Command reference
- FAQ and troubleshooting

---

*Phase 7 Complete - Production Ready*
