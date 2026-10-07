# Catalyst Telegram Connections

Two Telegram bot architectures for integrating Catalyst with Telegram.

> **Naming convention:** "TC" = Telegram Connection. TC1 was the original gateway (now deprecated and removed). TC2 and TC3 are the active architectures.

## Quick Reference

| TC | Name | What It Is | Bot(s) | Status |
|----|------|-----------|--------|--------|
| **TC2** | OpenClaw | Telegram bot configs for Catalyst via [OpenClaw](https://github.com/nicholasgriffintn/openclaw) framework | @iamspartacusbot | Production |
| **TC3** | {{ORCHESTRATOR_NAME}} Hybrid | CLI-based Telegram bot with full Catalyst agent integration | @TyCatalyst{{ORCHESTRATOR_NAME}}Bot | Production |

---

## TC2: OpenClaw (`TC2-openclaw/`)

**What:** Telegram bot configuration for Catalyst using the OpenClaw multi-channel bot framework. This is the simpler option — you install OpenClaw separately and point it at these configs.

**Architecture:** OpenClaw v2026.2.9 multi-channel platform with multi-agent routing

**Bot:** @iamspartacusbot (one bot, multiple agents)

**Agents:**
| Agent | Group | Workspace |
|-------|-------|-----------|
| `main` | DMs (default) | Catalyst root |
| `exampleteam` | Big Sky Team | `capsules/example-team-tags` |
| `mid` | exampleco Lead Gen | `capsules/example-partners` |
| `brotobot` | Bro to Bot | Catalyst root |
| `wardrobe` | Wardrobe Shopper | `capsules/wardrobe-shopper` |

**How it works:**
- OpenClaw framework with 417+ skills
- Multi-agent routing: `bindings[]` maps group ID to agent, each with its own capsule context
- Multi-channel support (Telegram, Discord, Signal, etc.)
- Gateway-based architecture with LaunchAgent
- DMs locked to owner only (`allowlist`), groups allowlisted with `requireMention: true`

**Config:** `~/.openclaw/openclaw.json`

**Start:**
```bash
openclaw gateway start
```

**LaunchAgent:** `~/Library/LaunchAgents/ai.openclaw.gateway.plist`

**Context loading:** OpenClaw injects 9 bootstrap files from the workspace (AGENTS.md, SOUL.md, IDENTITY.md, etc.). **CLAUDE.md is NOT loaded** — project context goes in AGENTS.md's `## Project Context` section.

**Adding new agents:** See `.claude/skills/openclaw-connect/SKILL.md` for the full runbook.

**Details:** See `TC2-openclaw/README.md` for full agent setup, bootstrap files, security config, and member lists.

---

## TC3: {{ORCHESTRATOR_NAME}} Hybrid (`TC3/`)

**What:** A standalone Telegram bot built in TypeScript (Bun + grammY) that gives you full Catalyst agent access from Telegram. This is the more powerful option — it loads the entire Catalyst context and can delegate to specialist agents.

**Architecture:** Full Catalyst integration with 28+ agents, 323 skills, 17 MCP servers

**Bot:** @TyCatalyst{{ORCHESTRATOR_NAME}}Bot

**How it works:**
- Loads entire Catalyst context on startup
- Can delegate to specialist agents (Backend Dev, Frontend Dev, etc.)
- Session context optimization (30K→2K chars)
- Hot reload capability (500ms)
- Full MCP integration (Supabase, Context7, OBS, etc.)

**Config:** `TC3/.env`

**Start:**
```bash
cd TC3 && bun run start
```

**LaunchAgent:** `TC3/com.catalyst.telegram-{{ORCHESTRATOR_NAME_LOWER}}-bot.plist`

---

## Shared Resources

**`shared-core/`** — Shared utilities used by both TC2 and TC3 (trigger classification, specialist routing, etc.)

**Global docs:** `../../global/integrations/telegram/README.md`

---

## Which to Use?

| Scenario | Recommended |
|----------|-------------|
| Quick Telegram bot with multi-channel support (Discord, Signal, etc.) | **TC2** (OpenClaw) |
| Full Catalyst agent access from Telegram | **TC3** ({{ORCHESTRATOR_NAME}} Hybrid) |
| Both — OpenClaw for casual, TC3 for power use | **TC2 + TC3** |
