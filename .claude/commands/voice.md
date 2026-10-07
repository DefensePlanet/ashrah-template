---
description: Toggle Kokoro TTS voice on/off
---

Toggle the Kokoro TTS voice summary. This enables/disables the Stop hook in `.claude/settings.json` that speaks response summaries via local Kokoro TTS.

**How it works:** Read `.claude/settings.json`, check if the Stop hook contains a TTS entry, and flip it.

1. **Read** the project settings file at the repo's `.claude/settings.json`

2. **Detect Python 3.11+:** Check in order:
   - `/Library/Frameworks/Python.framework/Versions/3.11/bin/python3`
   - `/Library/Frameworks/Python.framework/Versions/3.12/bin/python3`
   - `/opt/homebrew/bin/python3`
   - `python3` (PATH fallback)
   Use the first one that exists.

3. **Compute hook path:** Use the absolute path to `tools/codex-tts/tts_hook_client.py` in this repo

4. **Check** if `hooks.Stop` contains a hook with `tts_hook_client.py` OR legacy `simple_tts_hook_fast.py` in the command

5. **Toggle:**
   - If a TTS hook **IS present** → Remove the entire Stop hook entry containing `tts_hook_client.py` or `simple_tts_hook_fast.py` (preserve other Stop hooks if any)
   - If **NOT present** (or Stop array is missing/empty) → Add this entry to `hooks.Stop`:
     ```json
     {
       "hooks": [
         {
           "type": "command",
           "command": "<detected_python> <repo_root>/tools/codex-tts/tts_hook_client.py"
         }
       ]
     }
     ```

6. **Write** the updated settings back (preserve all other settings exactly)

7. **Confirm** with a short message:
   - If turned ON: "🔊 Voice ON — Kokoro TTS summaries enabled. Takes effect next response."
   - If turned OFF: "🔇 Voice OFF — Kokoro TTS summaries disabled. Takes effect next response."

Keep it brief. No extra explanation needed.
