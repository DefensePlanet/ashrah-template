# Telegram Bot Setup Skill

Automate creation of dedicated Telegram bots for Catalyst capsules.

## What This Does

Creates and configures TypeScript-based Telegram bots that connect capsules to Telegram messenger, allowing mobile access to Claude with full capsule context.

## Architecture

**Based on:** [linuz90/claude-telegram-bot](https://github.com/linuz90/claude-telegram-bot)

**Catalyst Adaptation:**
- Multi-capsule support via separate .env files
- Each bot = isolated Claude instance with capsule-specific working directory
- Shared TypeScript codebase, per-bot configuration
- Bot launcher script for managing multiple bots

## Usage

When user says:
```
Create a telegram bot for [capsule-name]
```

The skill will:
1. Guide user through creating bot with @BotFather
2. Generate .env configuration file
3. Add bot to bot_tokens.json
4. Launch the bot
5. Verify it works

## Example

```
User: Create a telegram bot for Mapping Agon

{{ORCHESTRATOR_NAME}}:
1. Guides {{USER_NAME}} to message @BotFather
2. Provides bot name/username suggestions
3. Waits for bot token from BotFather
4. Creates agon.env with capsule config
5. Launches bot with bot-launcher.sh
6. Tests bot responds with Agon context
```

## Files Created

For a new bot named "agon":

```
{{CATALYST_ROOT}}/tools/bots/claude-telegram-bot-new/
├── bots/
│   ├── agon.env                    # Bot configuration
│   └── bot_tokens.json             # Updated with new bot token
└── [bot launches via bot-launcher.sh]
```

## Existing Bots

Current Catalyst bots:
- `{{ORCHESTRATOR_NAME_LOWER}}.env` - Root Catalyst (main assistant)
- `family.env` - Family Room capsule
- `mid.env` - Example Partners capsule
- `merchant.env` - Merchant CRM capsule
- `protect.env` - Protect The Asset capsule
- `jelly.env` - Jellyfin Server Ops
- `home.env` - Home Automation
- `mobile.env` - Catalyst Mobile

## Privacy Note

For sensitive capsules (e.g., Mapping Agon):
- Voice transcriptions go through OpenAI API
- All Claude processing stays local
- Recommend private Telegram groups
- Note sensitivity in TRANSCRIPTION_CONTEXT

## Reference

See full skill documentation: `SKILL.md`
