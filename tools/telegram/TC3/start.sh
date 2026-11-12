#!/bin/bash
# TC3 {{ORCHESTRATOR_NAME}} Bot — Startup Wrapper
# Reads secrets from macOS Keychain, then starts the bot.
# Keeps secrets out of .env files per Catalyst credential policy.

export HOME={{HOME_DIR}}
export PATH="{{HOME_DIR}}/.local/bin:{{HOME_DIR}}/.bun/bin:/opt/homebrew/bin:/opt/homebrew/sbin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"

# Prefer IPv4 first (avoids flaky/broken IPv6 paths to Telegram Bot API on some networks)
export NODE_OPTIONS="--dns-result-order=ipv4first"

cd {{CATALYST_ROOT}}/tools/telegram/TC3

# Debug: log start attempt
echo "[$(date '+%Y-%m-%d %H:%M:%S')] start.sh invoked (pid $$)" >> /tmp/tc3-start-debug.log

# Load Telegram bot token from Keychain
# During gym lockout (screen locked), login.keychain-db is inaccessible to background
# processes — security returns empty. Exit 0 (clean exit) to avoid crash loop.
# KeepAlive has SuccessfulExit: false, so exit 0 suppresses restart until manually
# kickstarted or the post-unlock hook triggers it.
TELEGRAM_BOT_TOKEN=$(security find-generic-password -s "tc3-telegram-bot-token" -a "catalyst" -w 2>/dev/null)
if [ -z "$TELEGRAM_BOT_TOKEN" ]; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Keychain locked (screen locked?) — tc3-telegram-bot-token unavailable. Exiting cleanly to avoid crash loop." >&2
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] KEYCHAIN EMPTY - exiting 0" >> /tmp/tc3-start-debug.log
    exit 0
fi
export TELEGRAM_BOT_TOKEN
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Token loaded, launching bun" >> /tmp/tc3-start-debug.log

# Load OpenAI API key from Keychain (for voice transcription)
OPENAI_API_KEY=$(security find-generic-password -s "openai-api-key" -a "catalyst" -w 2>/dev/null)
if [ -n "$OPENAI_API_KEY" ]; then
    export OPENAI_API_KEY
fi

exec {{HOME_DIR}}/.bun/bin/bun run src/index.ts
