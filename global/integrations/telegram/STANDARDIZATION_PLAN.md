# Telegram Bot Architecture Standardization

**Date:** 2026-01-14
**Status:** 🔄 In Progress

## Executive Summary

Standardize ALL Telegram bot implementations across BuilderOS to use the production TypeScript architecture (`linuz90/claude-telegram-bot`). Eliminate legacy Python implementations and ensure consistent, reliable behavior across all capsules.

## Current State Assessment

### ✅ Production Bots (TypeScript)

**Location:** `{{CATALYST_ROOT}}/tools/claude-telegram-bot-new/`

| Bot | Capsule | Working Dir | Status | Session File |
|-----|---------|-------------|--------|--------------|
| `{{ORCHESTRATOR_NAME_LOWER}}` | BuilderOS Core | `{{CATALYST_ROOT}}` | ✅ Running | `/tmp/claude-telegram-session.json` |
| `mid` | Example Partners | `{{CATALYST_ROOT}}/capsules/example-partners` | ✅ Running | `/tmp/claude-telegram-session-Users-{{USER_NAME}}-BuilderOS-capsules-example-partners.json` |
| `mobile` | BuilderOS Mobile | `{{CATALYST_ROOT}}/capsules/builderos-mobile` | 🟡 Stopped | `/tmp/claude-telegram-session-Users-{{USER_NAME}}-BuilderOS-capsules-builderos-mobile.json` |
| `merchant` | Merchant CRM | `{{CATALYST_ROOT}}/capsules/merchant-crm` | 🟡 Stopped | `/tmp/claude-telegram-session-Users-{{USER_NAME}}-BuilderOS-capsules-merchant-crm.json` |
| `family` | Family Room | `{{CATALYST_ROOT}}/capsules/family-room` | 🟡 Stopped | `/tmp/claude-telegram-session-Users-{{USER_NAME}}-BuilderOS-capsules-family-room.json` |
| `protect` | Protect The Asset | `{{CATALYST_ROOT}}/capsules/protect-the-asset` | 🟡 Stopped | `/tmp/claude-telegram-session-Users-{{USER_NAME}}-BuilderOS-capsules-protect-the-asset.json` |
| `finu` | Finu | `{{CATALYST_ROOT}}/capsules/finu` | 🟡 Stopped | `/tmp/claude-telegram-session-Users-{{USER_NAME}}-BuilderOS-capsules-finu.json` |
| `exampleteamtags` | Big Sky Tags | `{{CATALYST_ROOT}}/capsules/example-team-tags` | 🟡 Stopped | `/tmp/claude-telegram-session-Users-{{USER_NAME}}-BuilderOS-capsules-exampleteamtags.json` |

### ❌ Legacy Implementations (Deprecated)

**To Remove:**
1. `{{CATALYST_ROOT}}/tools/telegram/{{ORCHESTRATOR_NAME_LOWER}}_bot.py` - Old Python bot
2. `{{CATALYST_ROOT}}/tools/telegram/{{ORCHESTRATOR_NAME_LOWER}}_server.py` - Old server implementation
3. `{{CATALYST_ROOT}}/capsules/builderos-mobile/api/server.py` - Mobile API server (replaced)
4. Any Python-based Telegram bot implementations in capsules

**Status:** ✅ All stopped (no Python bots running)

## Standardization Actions

### 1. Architecture Standardization ✅

**Decision:** Use TypeScript architecture for ALL Telegram bots

**Rationale:**
- Production-grade implementation (3,300+ lines battle-tested code)
- Proper streaming with Agent SDK V2
- Session persistence across restarts
- Message queueing and interruption
- Multi-modal support (voice, photos, documents)
- MCP integration with inline buttons
- Security layers and audit logging
- Active maintenance and updates

**Implementation:** `{{CATALYST_ROOT}}/tools/claude-telegram-bot-new/`

### 2. Bot Naming Convention ✅

**Pattern:** `<capsule-short-name>` (lowercase, no prefix)

**Examples:**
- `{{ORCHESTRATOR_NAME_LOWER}}` - BuilderOS core (not "builderos-bot")
- `mid` - Example Partners (not "example-partners-bot")
- `mobile` - BuilderOS Mobile (not "builderos-mobile-bot")
- `merchant` - Merchant CRM
- `family` - Family Room
- `protect` - Protect The Asset
- `finu` - Finu
- `exampleteamtags` - Big Sky Tags

### 3. Configuration Location ✅

**Centralized:** `{{CATALYST_ROOT}}/global/integrations/telegram/`

**Structure:**
```
global/integrations/telegram/
├── README.md                          # Full documentation
├── QUICK_START.md                     # Quick reference
├── STANDARDIZATION_PLAN.md            # This file
├── bot-implementation -> ../../tools/claude-telegram-bot-new/
└── bots/                             # Symlink for easy access
```

**Bot-specific configs:** `tools/claude-telegram-bot-new/bots/<bot-name>.env`

### 4. Session File Convention ✅

**Pattern:**
- Main bot ({{ORCHESTRATOR_NAME_LOWER}}): `/tmp/claude-telegram-session.json`
- Capsule bots: `/tmp/claude-telegram-session-<working-dir-encoded>.json`

**Examples:**
- {{ORCHESTRATOR_NAME_LOWER}}: `/tmp/claude-telegram-session.json`
- mid: `/tmp/claude-telegram-session-Users-{{USER_NAME}}-BuilderOS-capsules-example-partners.json`
- mobile: `/tmp/claude-telegram-session-Users-{{USER_NAME}}-BuilderOS-capsules-builderos-mobile.json`

**Auto-managed by:** Bot implementation (based on CLAUDE_WORKING_DIR)

### 5. Log File Convention ✅

**Pattern:**
```
/tmp/claude-telegram-<bot-name>.log    # stdout
/tmp/claude-telegram-<bot-name>.err    # stderr
/tmp/claude-telegram-<bot-name>.pid    # process ID
```

### 6. Working Directory Convention ✅

**Pattern:**
- Main bot: `{{CATALYST_ROOT}}` (system root)
- Capsule bots: `{{CATALYST_ROOT}}/capsules/<capsule-name>`

**Configured in:** `bots/<bot-name>.env` → `CLAUDE_WORKING_DIR`

### 7. Bot Management Commands ✅

**Standardized interface:** `bot-launcher.sh`

```bash
# Single bot operations
./bot-launcher.sh <bot-name> start
./bot-launcher.sh <bot-name> stop
./bot-launcher.sh <bot-name> restart
./bot-launcher.sh <bot-name> status

# All bots operations
./all-bots.sh start
./all-bots.sh stop
./all-bots.sh status
```

**Location:** `{{CATALYST_ROOT}}/tools/claude-telegram-bot-new/bots/`

### 8. Keep-Awake Service ✅

**Purpose:** Prevent Mac sleep while bots are active

**Implementation:** `{{CATALYST_ROOT}}/tools/claude-telegram-bot-new/bots/keep-awake.sh`

**Behavior:**
- Auto-starts when any bot launches
- Uses `caffeinate` to prevent system sleep
- Display can still sleep
- Shared across all bots (single daemon)

### 9. MCP Integration ✅

**Built-in MCP servers:**
- `ask_user` - Interactive inline buttons

**Configuration:** `tools/claude-telegram-bot-new/mcp-config.local.ts`

**Pattern:** Each bot can define custom MCP servers in main config

### 10. Security Standards ✅

**Multi-layer protection (all bots):**
1. User allowlist (`TELEGRAM_ALLOWED_USERS` in bot env)
2. Rate limiting (token bucket algorithm)
3. Path validation (`ALLOWED_PATHS`)
4. Command safety checks
5. System prompt constraints
6. Audit logging (`/tmp/claude-telegram-audit.log`)

## Migration Checklist

### For Each Capsule

- [x] **{{ORCHESTRATOR_NAME}} (BuilderOS Core)**
  - [x] Bot config created: `bots/{{ORCHESTRATOR_NAME_LOWER}}.env`
  - [x] Bot running on TypeScript architecture
  - [x] Old Python implementation stopped
  - [x] Documentation updated

- [ ] **Mobile (BuilderOS Mobile)**
  - [x] Bot config exists: `bots/mobile.env`
  - [ ] Start bot: `./bot-launcher.sh mobile start`
  - [ ] Remove old API server code
  - [ ] Update capsule CLAUDE.md

- [x] **Example Partners**
  - [x] Bot config exists: `bots/mid.env`
  - [x] Bot running
  - [x] Session file verified

- [ ] **Merchant CRM**
  - [x] Bot config exists: `bots/merchant.env`
  - [ ] Start bot if needed: `./bot-launcher.sh merchant start`
  - [ ] Update capsule CLAUDE.md

- [ ] **Family Room**
  - [x] Bot config exists: `bots/family.env`
  - [ ] Start bot if needed: `./bot-launcher.sh family start`
  - [ ] Update capsule CLAUDE.md

- [ ] **Protect The Asset**
  - [x] Bot config exists: `bots/protect.env`
  - [ ] Start bot if needed: `./bot-launcher.sh protect start`
  - [ ] Update capsule CLAUDE.md

- [ ] **Finu**
  - [x] Bot config exists: `bots/finu.env`
  - [ ] Start bot if needed: `./bot-launcher.sh finu start`
  - [ ] Update capsule CLAUDE.md

- [ ] **Big Sky Tags**
  - [x] Bot config exists: `bots/exampleteamtags.env`
  - [ ] Start bot if needed: `./bot-launcher.sh exampleteamtags start`
  - [ ] Update capsule CLAUDE.md

### System-Wide Cleanup

- [x] Stop all Python-based telegram bots
- [ ] Archive old Python implementations
  - [ ] Move `{{CATALYST_ROOT}}/tools/telegram/` to `tools/telegram.archive/`
  - [ ] Document deprecation in archive README
- [ ] Remove builderos-mobile API server
  - [ ] Archive `capsules/builderos-mobile/api/` code
  - [ ] Update mobile capsule docs
- [ ] Update global documentation
  - [x] Create `global/integrations/telegram/README.md`
  - [x] Create `global/integrations/telegram/QUICK_START.md`
  - [x] Create this standardization plan
- [ ] Update CLAUDE.md in each capsule
  - [ ] Reference telegram integration docs
  - [ ] Remove old bot implementation details

## New Bot Creation Process

When creating a new capsule with Telegram integration:

1. **Create env file:**
   ```bash
   cd {{CATALYST_ROOT}}/tools/claude-telegram-bot-new/bots
   cp {{ORCHESTRATOR_NAME_LOWER}}.env <new-bot-name>.env
   ```

2. **Configure bot:**
   - Set `TELEGRAM_BOT_TOKEN` (from @BotFather)
   - Set `TELEGRAM_ALLOWED_USERS` (comma-separated user IDs)
   - Set `CLAUDE_WORKING_DIR` (capsule directory)
   - Set `ALLOWED_PATHS` (directories Claude can access)

3. **Start bot:**
   ```bash
   ./bot-launcher.sh <new-bot-name> start
   ```

4. **Verify:**
   ```bash
   ./bot-launcher.sh <new-bot-name> status
   tail -f /tmp/claude-telegram-<new-bot-name>.log
   ```

5. **Update documentation:**
   - Add bot to `global/integrations/telegram/README.md`
   - Update capsule CLAUDE.md with bot details

## LaunchAgent Auto-Start (Future)

**Goal:** Auto-start essential bots on system boot

**Implementation:** LaunchAgent templates exist in `tools/claude-telegram-bot-new/launchagent/`

**Priority bots for auto-start:**
1. `{{ORCHESTRATOR_NAME_LOWER}}` - Main BuilderOS bot
2. Capsule-specific bots as needed

**Status:** 🟡 Available but not yet configured

## Monitoring & Health Checks (Future)

**Goal:** Automated health monitoring and restart

**Potential implementation:**
- Watchdog service that monitors bot processes
- Automatic restart on crash
- Health endpoint checks
- Slack/Telegram notifications on failures

**Status:** 🔴 Not yet implemented

## Success Criteria

- [x] All active Telegram bots use TypeScript architecture
- [x] No Python-based telegram bots running
- [x] Centralized documentation in `global/integrations/telegram/`
- [ ] All capsule CLAUDE.md files reference standard bot setup
- [ ] Legacy implementations archived with deprecation notices
- [ ] Bot management is consistent across all capsules

## Timeline

- **Phase 1 (Completed):** Core architecture migration
  - {{ORCHESTRATOR_NAME}} bot migrated to TypeScript ✅
  - Documentation centralized ✅
  - Standardization plan created ✅

- **Phase 2 (Current):** Capsule bot verification
  - Verify all bot configs exist ✅
  - Start essential capsule bots
  - Test functionality across all bots

- **Phase 3 (Next):** Legacy cleanup
  - Archive old Python implementations
  - Remove deprecated code
  - Update capsule documentation

- **Phase 4 (Future):** Automation
  - LaunchAgent setup for auto-start
  - Health monitoring system
  - Automated testing

## References

- **Bot implementation:** https://github.com/linuz90/claude-telegram-bot
- **Documentation:** `{{CATALYST_ROOT}}/global/integrations/telegram/`
- **Bot configs:** `{{CATALYST_ROOT}}/tools/claude-telegram-bot-new/bots/`
