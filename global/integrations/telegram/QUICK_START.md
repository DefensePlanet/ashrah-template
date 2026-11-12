# Telegram Bots - Quick Reference

## TL;DR

**Start {{ORCHESTRATOR_NAME}} bot:**
```bash
cd {{CATALYST_ROOT}}/tools/claude-telegram-bot-new/bots
./bot-launcher.sh {{ORCHESTRATOR_NAME_LOWER}} start
```

**Stop {{ORCHESTRATOR_NAME}} bot:**
```bash
./bot-launcher.sh {{ORCHESTRATOR_NAME_LOWER}} stop
```

**View logs:**
```bash
tail -f /tmp/claude-telegram-{{ORCHESTRATOR_NAME_LOWER}}.log
```

## Telegram Commands

| Command | Description |
|---------|-------------|
| `/start` | Show bot info |
| `/new` | Start fresh conversation |
| `/resume` | Resume last session |
| `/stop` | Interrupt current message |
| `/status` | Show session info |
| `/restart` | Kill and restart session |

## Quick Troubleshooting

**Bot not responding?**
```bash
cd {{CATALYST_ROOT}}/tools/claude-telegram-bot-new/bots
./bot-launcher.sh {{ORCHESTRATOR_NAME_LOWER}} restart
```

**Check if bot is running:**
```bash
./bot-launcher.sh {{ORCHESTRATOR_NAME_LOWER}} status
```

**View errors:**
```bash
tail -50 /tmp/claude-telegram-{{ORCHESTRATOR_NAME_LOWER}}.err
```

## All Bots Management

**Start all bots:**
```bash
./all-bots.sh start
```

**Stop all bots:**
```bash
./all-bots.sh stop
```

**Check all bots:**
```bash
for bot in {{ORCHESTRATOR_NAME_LOWER}} mobile mid merchant family protect finu exampleteamtags; do
    echo "=== $bot ==="
    ./bot-launcher.sh $bot status
    echo ""
done
```

## Architecture

- **Implementation:** TypeScript + Bun + grammY + Anthropic Agent SDK V2
- **Location:** `{{CATALYST_ROOT}}/tools/claude-telegram-bot-new/`
- **Configs:** `bots/*.env`
- **Logs:** `/tmp/claude-telegram-*.log`

Full documentation: `README.md`
