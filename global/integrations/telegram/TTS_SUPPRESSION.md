# Telegram TTS Suppression Configuration

## Overview

When accessing BuilderOS through Telegram bots remotely, TTS (text-to-speech) audio should not play on the Mac server. This document explains how TTS suppression works for Telegram sessions.

## How It Works

The TTS hook checks for the `BUILDEROS_TELEGRAM_SESSION` environment variable. When set to `true`, TTS audio is skipped.

```
Telegram Bot → LaunchAgent (sets env var) → Claude Agent SDK → Claude Code → TTS Hook (checks env var) → Skip audio
```

## Configuration Files

### 1. TTS Hook
**Location:** `~/.claude/simple_tts_hook_fast.py`

The hook checks for Telegram sessions at startup:
```python
# Skip TTS for Telegram sessions (remote access - audio shouldn't play on Mac)
if os.environ.get("BUILDEROS_TELEGRAM_SESSION") == "true":
    log_debug("Telegram session detected, skipping TTS (user is remote)")
    return
```

### 2. Bot Environment Files
**Location:** `tools/bots/claude-telegram-bot-new/bots/*.env`

Each bot's `.env` file includes:
```bash
# Disable TTS on Mac when accessed via Telegram (audio should not play locally)
BUILDEROS_TELEGRAM_SESSION=true
```

**Files:**
- `{{ORCHESTRATOR_NAME_LOWER}}.env` - Main BuilderOS orchestrator
- `family.env` - Family Room capsule
- `finu.env` - FinU capsule
- `home.env` - Home Automation capsule
- `jelly.env` - Jellyfin Server capsule
- `merchant.env` - Merchant CRM capsule
- `mid.env` - Example Partners capsule
- `mobile.env` - Mobile capsule
- `protect.env` - Protect The Asset capsule
- `exampleteamtags.env` - Big Sky Tags capsule

### 3. LaunchAgent Plists
**Location:** `~/Library/LaunchAgents/com.claude-telegram-*.plist`
**Source:** `tools/bots/claude-telegram-bot-new/bots/launchagents/`

Each plist includes the environment variable in `EnvironmentVariables`:
```xml
<key>EnvironmentVariables</key>
<dict>
    <key>PATH</key>
    <string>{{HOME_DIR}}/.bun/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin</string>
    <key>BUILDEROS_TELEGRAM_SESSION</key>
    <string>true</string>
</dict>
```

## Behavior Summary

| Session Type | Environment Variable | TTS Audio |
|--------------|---------------------|-----------|
| iTerm/Terminal Claude Code | Not set | Plays on Mac |
| Telegram Bot Session | `BUILDEROS_TELEGRAM_SESSION=true` | Suppressed |
| iOS Bridge Session | `BUILDEROS_MOBILE_SESSION=true` | Suppressed |

## Troubleshooting

### TTS Still Playing on Telegram Sessions

1. **Check LaunchAgent has env var:**
   ```bash
   grep BUILDEROS_TELEGRAM ~/Library/LaunchAgents/com.claude-telegram-{{ORCHESTRATOR_NAME_LOWER}}.plist
   ```

2. **Reload the LaunchAgent:**
   ```bash
   launchctl unload ~/Library/LaunchAgents/com.claude-telegram-{{ORCHESTRATOR_NAME_LOWER}}.plist
   launchctl load ~/Library/LaunchAgents/com.claude-telegram-{{ORCHESTRATOR_NAME_LOWER}}.plist
   ```

3. **Check TTS hook log:**
   ```bash
   tail -20 ~/.claude/tts_client.log
   ```
   Should show: `Telegram session detected, skipping TTS (user is remote)`

### TTS Not Playing on Local Sessions

1. **Verify env var is NOT set locally:**
   ```bash
   echo $BUILDEROS_TELEGRAM_SESSION
   ```
   Should be empty for local sessions.

2. **Check TTS server is running:**
   ```bash
   cat ~/.claude/tts_server.pid && ps aux | grep tts_server
   ```

## Adding a New Telegram Bot

When creating a new Telegram bot:

1. **Create `.env` file** with `BUILDEROS_TELEGRAM_SESSION=true`
2. **Create LaunchAgent plist** with env var in `EnvironmentVariables`
3. **Copy plist to** `~/Library/LaunchAgents/`
4. **Load the LaunchAgent:**
   ```bash
   launchctl load ~/Library/LaunchAgents/com.claude-telegram-newbot.plist
   ```

## Related Documentation

- `global/integrations/telegram/README.md` - Telegram integration overview
- `global/integrations/telegram/QUICK_START.md` - Quick start guide
- `tools/bots/claude-telegram-bot-new/README.md` - Bot architecture

## Change History

- **2026-01-19**: Initial implementation of TTS suppression for Telegram sessions
  - Added `BUILDEROS_TELEGRAM_SESSION` check to TTS hook
  - Updated all 10 bot `.env` files
  - Updated all 10 LaunchAgent plists
  - Fixed path issue in plists (`tools/claude-telegram-bot-new` → `tools/bots/claude-telegram-bot-new`)
