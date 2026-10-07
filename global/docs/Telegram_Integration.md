# Telegram Integration

**This documentation has moved.**

See: [global/integrations/telegram/README.md]({{CATALYST_ROOT}}/global/integrations/telegram/README.md)

The TypeScript-based Telegram bot implementation lives at:
`{{CATALYST_ROOT}}/tools/bots/claude-telegram-bot-new/`

## Quick Reference

**Start {{ORCHESTRATOR_NAME}} bot:**
```bash
cd {{CATALYST_ROOT}}/tools/bots/claude-telegram-bot-new/bots
./bot-launcher.sh {{ORCHESTRATOR_NAME_LOWER}} start
```

**Check status:**
```bash
./bot-launcher.sh {{ORCHESTRATOR_NAME_LOWER}} status
```

**View logs:**
```bash
tail -f /tmp/claude-telegram-{{ORCHESTRATOR_NAME_LOWER}}.log
```
