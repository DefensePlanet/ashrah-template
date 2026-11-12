# TTS Performance Fix - Configuration Verification

## ✅ Verified for Claude Code (NOT Codex)

**Date:** 2025-10-13
**Issue:** TTS hook delay (3-8 seconds per response)
**Root Cause:** Kokoro model loading from disk on every TTS call
**Solution:** Persistent server with pre-loaded model

---

## Configuration Chain (All Verified ✅)

### 1. Claude Code Hook Registration
**File:** `~/.claude/settings.json`
**Hook Event:** `Stop` (fires after Claude finishes responding)
**Line 43:**
```json
"command": "/Library/Frameworks/Python.framework/Versions/3.11/bin/python3 ~/.claude/simple_tts_hook_fast.py"
```

### 2. Fast TTS Client
**File:** `~/.claude/simple_tts_hook_fast.py`
**Function:** Sends TTS requests to persistent server
**Server Path:** `{{CATALYST_ROOT}}/tools/codex-tts/tts_server.py` (absolute path, correctly configured)
**Auto-Start:** Yes, launches server on first use
**Syntax:** ✅ Validated

### 3. Persistent TTS Server
**File:** `{{CATALYST_ROOT}}/tools/codex-tts/tts_server.py`
**Function:** Keeps Kokoro-82M model loaded in memory
**Socket:** `127.0.0.1:9876`
**Model:** `prince-canuma/Kokoro-82M` (loaded once at startup)
**Syntax:** ✅ Validated

### 4. Server Control Script
**File:** `{{CATALYST_ROOT}}/tools/codex-tts/tts-server-ctl.sh`
**Commands:** start, stop, restart, status, logs

---

## Expected Performance

| Metric | Before | After |
|--------|--------|-------|
| Model Load | 1-3s | 0s (already loaded) |
| TTS Generation | 1-2s | 0.5-1s |
| **Total Delay** | **3-8s** | **<1s** |

---

## Testing

The server will auto-start when you get your next Claude Code response.

### Manual Testing:
```bash
# Check if server is running
{{CATALYST_ROOT}}/tools/codex-tts/tts-server-ctl.sh status

# Start server manually (optional)
{{CATALYST_ROOT}}/tools/codex-tts/tts-server-ctl.sh start

# Monitor logs
{{CATALYST_ROOT}}/tools/codex-tts/tts-server-ctl.sh logs
```

### Monitoring:
- **Client Log:** `~/.claude/tts_client.log`
- **Server Log:** `~/.claude/tts_server.log`
- **Server PID:** `~/.claude/tts_server.pid`

---

## Architecture Flow

```
Claude Code Response
    ↓
Stop Hook Fires
    ↓
simple_tts_hook_fast.py (client)
    ↓
Creates Summary (regex-based)
    ↓
Checks: Is server running?
    ├─ No  → Start server (auto-start)
    └─ Yes → Continue
    ↓
Send summary to 127.0.0.1:9876 (socket)
    ↓
tts_server.py (already has model loaded)
    ↓
Generate audio (fast - no model load)
    ↓
Return audio file path
    ↓
Client plays audio with afplay
    ↓
Done (<1 second total)
```

---

## Files Modified/Created

### Modified:
- `~/.claude/settings.json` - Updated hook to use fast client

### Created:
- `~/.claude/simple_tts_hook_fast.py` - Fast TTS client
- `{{CATALYST_ROOT}}/tools/codex-tts/tts_server.py` - Persistent server
- `{{CATALYST_ROOT}}/tools/codex-tts/tts-server-ctl.sh` - Management script
- `{{CATALYST_ROOT}}/tools/codex-tts/tts_client.py` - Original client (source)

### Preserved (not modified):
- `{{CATALYST_ROOT}}/global/claude-config/simple_tts_hook.py` - Original hook (backup)
- `{{CATALYST_ROOT}}/tools/codex-tts/codex_summary_tts.py` - Codex TTS (separate)

---

## Rollback Instructions

If you need to revert to the old system:

```bash
# Edit ~/.claude/settings.json, change line 43 to:
"command": "/Library/Frameworks/Python.framework/Versions/3.11/bin/python3 {{CATALYST_ROOT}}/global/claude-config/simple_tts_hook.py"

# Stop the server
{{CATALYST_ROOT}}/tools/codex-tts/tts-server-ctl.sh stop
```

---

**Status:** ✅ Ready to test - Next Claude Code response will use the fast path
