# TTS Hook Toggle

Toggle the Claude Code TTS (Text-to-Speech) hook on/off.

## Task
You need to toggle the TTS hook in Claude Code settings. 

## Steps
1. Read `{{HOME_DIR}}/.claude/settings.json`
2. Check if TTS hook exists in "hooks" > "Stop" array
3. If enabled: Remove the hook containing `tts_hook.py`
4. If disabled: Add the TTS hook configuration
5. Save the file and report status

## TTS Hook Configuration
```json
{
  "matcher": "*",
  "hooks": [
    {
      "type": "command",
      "command": "python3 ~/.claude/tts_hook.py"
    }
  ]
}
```

## Response
- "🔊 TTS enabled" or "🔇 TTS disabled"