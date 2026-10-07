---
name: telegram-bot-setup
description: Create and configure dedicated Telegram bots for Catalyst capsules using TypeScript bot infrastructure
when: User requests a new Telegram bot for a capsule, or says "create telegram bot for [capsule]"
allowed-tools:
  - Bash
  - Read
  - Write
  - Edit
metadata:
  version: "2.0.0"
  automation: "Full - Telethon API"
  infrastructure: "TypeScript + Bun + Grammy"
  bot_directory: "{{CATALYST_ROOT}}/tools/bots/claude-telegram-bot-new"
  telethon_session: "{{CATALYST_ROOT}}/tools/builder_session"
  last_updated: "2026-01-19"
---

# Telegram Bot Setup Skill (Fully Automated)

## Purpose
**Fully automate** creation of dedicated Telegram bots for Catalyst capsules using the Telethon API to interact with BotFather programmatically.

## What This Skill Does (End-to-End)
1. Creates a new bot via @BotFather using Telethon
2. Extracts the bot token automatically
3. Configures bot description and about text
4. Creates the `.env` configuration file for the capsule
5. Starts the bot using `bot-launcher.sh`
6. Opens a conversation with the bot in Telegram
7. Reports success with bot details

**No manual steps required** - {{ORCHESTRATOR_NAME}} handles everything programmatically.

## When to Use
- "Create a telegram bot for [capsule]"
- "Set up telegram for [capsule]"
- "I need a bot for [capsule-name]"
- Setting up a new capsule with mobile access

**NOTE:** Telegram limits accounts to 20 bots total. Bot creation is now opt-in rather than automatic during capsule creation. Only create bots for capsules that truly need mobile Telegram access.

## Prerequisites
- Telethon session authenticated at `{{CATALYST_ROOT}}/tools/builder_session.session`
- If session expired, run: `python3.12 {{CATALYST_ROOT}}/tools/telegram/telethon_auth.py`

## Execution Flow

### Step 1: Validate Inputs
```python
# Required: capsule_name (e.g., "mapping-agon", "family-room")
# Derived:
#   - short_name: "agon", "family"
#   - display_name: "Mapping Agon", "Family Room"
#   - bot_username: "MappingAgonBot", "FamilyRoomBot"
#   - capsule_path: {{CATALYST_ROOT}}/capsules/[capsule_name]
```

### Step 2: Create Bot via BotFather (Telethon)
```bash
python3.12 {{CATALYST_ROOT}}/tools/bots/telegram_bot_creator.py \
  --capsule "[capsule-name]" \
  --display-name "[Display Name]" \
  --bot-username "[BotUsername]Bot" \
  --description "[Bot description]"
```

The script:
1. Connects to Telegram via Telethon
2. Sends `/newbot` to @BotFather
3. Provides display name and username
4. Extracts token from BotFather's response
5. Sets bot description and about text
6. Outputs JSON with bot details

### Step 3: Create Environment File
```bash
# Location: {{CATALYST_ROOT}}/tools/bots/claude-telegram-bot-new/bots/[short_name].env
```

**Template:**
```bash
# Claude Telegram Bot - [Display Name]
# Bot: @[BotUsername]

TELEGRAM_BOT_TOKEN=[extracted_token]
TELEGRAM_ALLOWED_USERS={{TELEGRAM_CHAT_ID}}

# Capsule-specific working directory
CLAUDE_WORKING_DIR={{CATALYST_ROOT}}/capsules/[capsule-name]

# Paths Claude can access
ALLOWED_PATHS={{CATALYST_ROOT}},{{HOME_DIR}}/Documents,{{HOME_DIR}}/Downloads,{{HOME_DIR}}/Desktop,{{HOME_DIR}}/.claude,{{HOME_DIR}}/Development

# Voice transcription context
TRANSCRIPTION_CONTEXT="Common names: {{USER_NAME}}. Context: [capsule description]"

# Extended thinking keywords
THINKING_KEYWORDS="think,reason,analyze,consider"
THINKING_DEEP_KEYWORDS="ultrathink,think hard,deep analysis"

# Rate limiting
RATE_LIMIT_ENABLED=true
RATE_LIMIT_REQUESTS=30
RATE_LIMIT_WINDOW=60

# Claude Code executable path
CLAUDE_CODE_PATH={{HOME_DIR}}/.local/bin/claude

# Disable TTS on Mac when accessed via Telegram
BUILDEROS_TELEGRAM_SESSION=true
```

### Step 4: Start the Bot
```bash
cd {{CATALYST_ROOT}}/tools/bots/claude-telegram-bot-new/bots
./bot-launcher.sh [short_name] start
```

### Step 5: Start Conversation (Telethon)
```bash
python3.12 -c "
import asyncio
from telethon import TelegramClient
# ... connect and send /start to bot
"
```

### Step 6: Report Success
```
✅ Bot Created and Running

📱 Bot: @[BotUsername]
📂 Capsule: [capsule-name]
🔧 Config: bots/[short_name].env
📍 Status: Running (PID: XXXX)

💬 Conversation started - check your Telegram app!
```

## Quick Command Reference

**Create bot for capsule:**
```bash
python3.12 {{CATALYST_ROOT}}/tools/bots/telegram_bot_creator.py \
  --capsule "capsule-name" \
  --display-name "Display Name" \
  --bot-username "DisplayNameBot"
```

**Start bot:**
```bash
./bot-launcher.sh [short_name] start
```

**Check status:**
```bash
./bot-launcher.sh [short_name] status
```

**View logs:**
```bash
tail -f /tmp/claude-telegram-[short_name].log
```

## Naming Conventions

| Capsule | Short Name | Display Name | Bot Username |
|---------|------------|--------------|--------------|
| mapping-agon | agon | Mapping Agon | MappingAgonBot |
| family-room | family | Family Room | FamilyRoomBot |
| example-partners | mid | Example Partners | examplepartnersBot |
| protect-the-asset | protect | Protect The Asset | ProtectAssetBot |

## Troubleshooting

**Telethon not authenticated:**
```bash
cd {{CATALYST_ROOT}}/tools/telegram
python3.12 telethon_auth.py
```

**Bot username taken:**
- BotFather requires unique usernames
- Try variations: `[Name]BuilderBot`, `[Name]AssistantBot`

**Bot not responding:**
```bash
./bot-launcher.sh [name] status
tail -20 /tmp/claude-telegram-[name].err
./bot-launcher.sh [name] restart
```

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      Telethon Session                        │
│            {{CATALYST_ROOT}}/tools/builder_session         │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                    telegram_bot_creator.py                   │
│  - Connects to Telegram via Telethon                        │
│  - Creates bot via @BotFather                               │
│  - Configures description/about                             │
│  - Returns token + bot details                              │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                    Bot Configuration                         │
│  bots/[name].env → Token, working dir, allowed users        │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                     bot-launcher.sh                          │
│  - Starts bun process with env file                         │
│  - Manages PID and logs                                     │
│  - Keep-awake integration                                   │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                  Grammy Bot (TypeScript)                     │
│  - Handles Telegram messages                                │
│  - Streams to Claude Agent SDK                              │
│  - Working dir = capsule context                            │
└─────────────────────────────────────────────────────────────┘
```

## Privacy Notes

- All bot traffic stays local (Mac-hosted)
- Claude conversations not logged externally
- Voice transcriptions use OpenAI Whisper (external)
- Sensitive capsules: use private Telegram groups
