Toggle Text-to-Speech functionality in Claude Code.

```bash
# Check current TTS status and toggle it
current_status=$(grep -q '"Stop":' ~/.claude/settings.json && echo "ON" || echo "OFF")

if [ "$current_status" = "ON" ]; then
    # Turn OFF
    sed -i '' 's/"Stop":/"_Stop_disabled":/g' ~/.claude/settings.json
    echo "🔇 TTS disabled - restart Claude Code to take effect"
else
    # Turn ON  
    sed -i '' 's/"_Stop_disabled":/"Stop":/g' ~/.claude/settings.json
    echo "🔊 TTS enabled - restart Claude Code to take effect"
fi
```