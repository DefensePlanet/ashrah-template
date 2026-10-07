# GPT-5 Codex Endpoint Fix

**Date:** 2025-11-12
**Issue:** Claude Code CLI throwing 400 error: "Input is required for responses"

## Problem Analysis

The `bifrost-responses` provider was configured to use the `/v1/responses` endpoint which expects an "input" field. However, Claude Code CLI sends standard OpenAI chat completion format with "messages" array.

**Error:**
```
Error from provider(bifrost-responses,openai/gpt-5-codex: 400):
"Input is required for responses"
```

## Solution

**Changed all router paths from `bifrost-responses` to `bifrost-chat`:**

### Before:
```json
"Router": {
  "default": "bifrost-responses,openai/gpt-5-codex",
  "think": "bifrost-responses,openai/gpt-5-codex",
  "longContext": "bifrost-responses,openai/gpt-5-codex",
  "background": "bifrost-responses,openai/gpt-5-codex",
  "webSearch": "bifrost-responses,openai/gpt-5-codex",
  ...
}
```

### After:
```json
"Router": {
  "default": "bifrost-chat,openai/gpt-5-codex",
  "think": "bifrost-chat,openai/gpt-5-codex",
  "longContext": "bifrost-chat,openai/gpt-5-codex",
  "background": "bifrost-chat,openai/gpt-5-codex",
  "webSearch": "bifrost-chat,openai/gpt-5-codex",
  ...
}
```

## Why This Works

The `bifrost-chat` provider:
- Uses correct endpoint: `http://127.0.0.1:8083/v1/chat/completions`
- Already includes `openai/gpt-5-codex` in its models list
- Uses `bifrost-chat-endpoint` transformer (appropriate for chat completions)
- Compatible with Claude Code CLI's message format

## Technical Details

**Provider Configuration (`bifrost-chat`):**
```json
{
  "name": "bifrost-chat",
  "api_base_url": "http://127.0.0.1:8083/v1/chat/completions",
  "models": [
    "openai/gpt-4o-mini",
    "openai/gpt-4o",
    "openai/gpt-5-codex",
    "openai/gpt-4-turbo",
    "openai/gpt-4"
  ],
  "transformer": {
    "use": ["bifrost-chat-endpoint"]
  }
}
```

**Endpoint Differences:**
- `/v1/responses` - Expects "input" field (for simple text completion)
- `/v1/chat/completions` - Expects "messages" array (standard OpenAI format)

## Results

✅ Router successfully restarted (PID 85847)
✅ Listening on port 3456
✅ Configuration applied
✅ Claude Code CLI can now communicate with GPT-5 Codex via Bifrost gateway

## Status

**Router Process:** Running (PID 85847)
**Port:** 3456 (listening)
**Bifrost Gateway:** Port 8083 (active)
**Configuration File:** `{{HOME_DIR}}/.claude-code-router/config.json`
**Log File:** `{{HOME_DIR}}/.claude-code-router/logs/ccr-20251112005838.log`
