# Telegram Integration - Catalyst

**Location:** `global/integrations/telegram/`
**Implementations:** `{{CATALYST_ROOT}}/tools/telegram/` (3 architectures)

## Overview

Catalyst uses TypeScript-based Telegram bots (via grammY + Anthropic Agent SDK) to provide mobile access to Claude Code capabilities. Three distinct architectures are available, each suited for different use cases.

## Multi-Bot Response Protocol

**CRITICAL: When multiple AI assistants share the same chat, strict response etiquette prevents interference.**

### {{ORCHESTRATOR_NAME}} Response Rules

**✅ {{ORCHESTRATOR_NAME}} WILL respond when:**
- You tag `@{{ORCHESTRATOR_NAME}}CatalystBot` directly
- You say "{{ORCHESTRATOR_NAME}}" in your message
- You're clearly addressing {{ORCHESTRATOR_NAME}} contextually (no other bot mentioned)

**❌ {{ORCHESTRATOR_NAME}} WILL NOT respond when:**
- You tag `@iamspartacusbot` or address "{{ORCHESTRATOR_NAME}}"
- You're clearly having a conversation with {{ORCHESTRATOR_NAME}}/another bot
- You explicitly tell {{ORCHESTRATOR_NAME}} not to respond

**🎯 Purpose:** Keeps conversations clean and prevents bot interference in shared chats.

**🔧 Implementation:** Each bot monitors for these patterns before responding to avoid conflicts.

**📋 Implementation Checklist for Bot Code:**
```typescript
// Early in message handler, before processing
function shouldIgnoreMessage(message: string): boolean {
  const text = message.toLowerCase();
  
  // Don't respond if user is addressing {{ORCHESTRATOR_NAME}}
  if (text.includes('@iamspartacusbot') || 
      text.includes('spartacus') ||
      text.includes('ask spartacus') ||
      text.includes('tell spartacus')) {
    return true;
  }
  
  // Don't respond if explicitly told not to
  if (text.includes('{{ORCHESTRATOR_NAME_LOWER}} don\'t respond') ||
      text.includes('don\'t respond {{ORCHESTRATOR_NAME_LOWER}}')) {
    return true;
  }
  
  return false;
}
```

## Three Architectures

| ID | Name | Location | Process Model | Status |
|----|------|----------|---------------|--------|
| **TC1** | Capsule Bots | `tools/telegram/TC1-capsule-bots/` | 12 separate processes | Legacy/Reference |
| **TC2** | Gateway | `tools/telegram/TC2-gateway/` | 1 unified process | Production |
| **TC3** | {{ORCHESTRATOR_NAME}} Hybrid | `tools/telegram/TC3/` | 1 process + full Catalyst | Premium |

**See:** `tools/telegram/README.md` for detailed architecture comparison.

### TC1: Capsule Bots (Legacy)
- 12 independent bot processes, one per capsule
- Individual `.env` files for each bot
- Good for reference/learning, superseded by TC2

### TC2: Gateway (Recommended)
- Single BotManager process handles all 12 bots
- Lower memory footprint, unified rate limiting
- Centralized configuration in `registry.json`
- **Recommended for multi-bot deployment**

### TC3: {{ORCHESTRATOR_NAME}} Hybrid (Premium)
- Full Catalyst integration (28+ agents, 323 skills, 17 MCP servers)
- Session context optimization (30K→2K chars)
- Hot reload capability
- **Recommended for full {{ORCHESTRATOR_NAME}} experience**

## Stack

- **Runtime:** Bun 1.0+
- **Framework:** grammY (Telegram bot framework)
- **AI:** `@anthropic-ai/claude-agent-sdk` V2
- **Language:** TypeScript

## The 12 Capsule Bots

| Bot ID | Capsule | Working Directory |
|--------|---------|------------------|
| `{{ORCHESTRATOR_NAME_LOWER}}` | Catalyst Core | `{{CATALYST_ROOT}}` |
| `mobile` | Catalyst Mobile | `capsules/catalyst-mobile` |
| `mid` | Example Partners | `capsules/example-partners` |
| `family` | Family Room | `capsules/family-room` |
| `protect` | Protect The Asset | `capsules/protect-the-asset` |
| `finu` | Financial Untethering | `capsules/financial-untethering` |
| `big` | Big Sky Tags | `capsules/example-team-tags` |
| `jelly` | Jellyfin Ops | `capsules/jellyfin-ops` |
| `home` | Home Automation | `capsules/home-automation` |
| `idea` | Idea Incubator | `capsules/idea-incubator` |
| `agon` | Mapping Agon | `capsules/mapping-agon` |
| `operation` | Operation Embroidery | `capsules/operation-embroidery` |

## Bot Management

### TC1 (Individual Bots)
```bash
cd {{CATALYST_ROOT}}/tools/telegram/TC1-capsule-bots/bots
./bot-launcher.sh <bot-name> start|stop|restart|status
./manage-all.sh start|stop  # All bots
```

### TC2 (Gateway)
```bash
cd {{CATALYST_ROOT}}/tools/telegram/TC2-gateway
bun run start  # Starts all 12 bots in one process
```

### TC3 ({{ORCHESTRATOR_NAME}} Hybrid)
```bash
cd {{CATALYST_ROOT}}/tools/telegram/TC3
bun run start  # Starts {{ORCHESTRATOR_NAME}} with full Catalyst integration
```

## Telegram Commands

- `/start` - Show bot info and commands
- `/new` - Start fresh conversation (clear history)
- `/resume` - Resume last session
- `/stop` - Interrupt current message processing
- `/status` - Show session and bot info
- `/restart` - Kill and restart Claude session

**TC3 Additional Commands:**
- `/sync` - Sync Catalyst context
- `/context` - Show loaded context
- `/specialist` - List available specialists
- `/skills` - List available skills

## Message Features

**Text:** Normal messages continue conversation. Prefix with `!` to interrupt.

**Voice:** Auto-transcribed via OpenAI Whisper, processed as text.

**Photos:** Vision analysis via Claude, album support (1-second buffering).

**Documents:** PDFs via `pdftotext`, text files direct, archives extracted.

## Configuration

**TC1:** `tools/telegram/TC1-capsule-bots/bots/<bot-name>.env`
**TC2:** `tools/telegram/TC2-gateway/src/config/registry.json`
**TC3:** `tools/telegram/TC3/.env`

**Shared tokens:** `tools/bots/bot_tokens.json`

## Security

Multi-layer protection:
1. User allowlist (TELEGRAM_ALLOWED_USERS)
2. Rate limiting (token bucket algorithm)
3. Path validation (ALLOWED_PATHS)
4. Command safety checks (blocked patterns)
5. System prompt constraints
6. Audit logging (`/tmp/claude-telegram-audit.log`)

## LaunchAgents

| Architecture | Plist Location |
|--------------|----------------|
| TC1 | `TC1-capsule-bots/launchagent/*.plist` (archived) |
| TC2 | `TC2-gateway/launchd/com.catalyst.telegram-gateway.plist` |
| TC3 | `TC3/com.catalyst.telegram-{{ORCHESTRATOR_NAME_LOWER}}-bot.plist` |

## Logs

Each bot logs to `/tmp/`:
- `/tmp/claude-telegram-<bot-name>.log` - Standard output
- `/tmp/claude-telegram-<bot-name>.err` - Error output
- `/tmp/claude-telegram-<bot-name>.pid` - Process ID

## Adding a New Bot

### TC1 Method
1. Create `TC1-capsule-bots/bots/<bot-name>.env`
2. Set TELEGRAM_BOT_TOKEN, TELEGRAM_ALLOWED_USERS, CLAUDE_WORKING_DIR
3. Launch: `./bot-launcher.sh <bot-name> start`

### TC2 Method
1. Add entry to `TC2-gateway/src/config/registry.json`
2. Restart gateway

### TC3 Method ({{ORCHESTRATOR_NAME}} only)
TC3 is specifically for {{ORCHESTRATOR_NAME}} with full Catalyst integration - not for adding new bots.

## Authentication

Uses Claude Code CLI authentication (subscription mode), not API keys.

Environment vars explicitly unset:
- `ANTHROPIC_API_KEY`
- `ANTHROPIC_BASE_URL`

## Troubleshooting

**Bot not responding:**
1. Check if running: `ps aux | grep "bun.*index.ts"`
2. Check logs: `tail -50 /tmp/claude-telegram-<bot-name>.err`
3. Restart bot

**Session issues:**
1. Send `/new` to start fresh session
2. Check session file: `cat /tmp/claude-telegram-session.json`

**Permission errors:**
1. Verify ALLOWED_PATHS in config
2. Check audit log: `tail -50 /tmp/claude-telegram-audit.log`

## References

- **Architecture overview:** `tools/telegram/README.md`
- **grammY docs:** https://grammy.dev/
- **Agent SDK:** https://github.com/anthropics/anthropic-sdk-typescript
