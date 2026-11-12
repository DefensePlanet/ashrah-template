#!/bin/bash
# Audio Static Diagnostic Tool
# Monitors all audio-related activity during command execution

LOG_DIR="$HOME/.claude/audio_diagnostics"
mkdir -p "$LOG_DIR"

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_FILE="$LOG_DIR/diagnostic_$TIMESTAMP.log"

echo "=== Audio Static Diagnostic - $TIMESTAMP ===" | tee "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"

echo "1. Checking for running audio processes..." | tee -a "$LOG_FILE"
ps aux | grep -iE "afplay|tts|audio" | grep -v grep | tee -a "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"

echo "2. Monitoring audio device changes..." | tee -a "$LOG_FILE"
system_profiler SPAudioDataType | grep -A3 "Default" | tee -a "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"

echo "3. Checking hook configuration..." | tee -a "$LOG_FILE"
cat ~/.claude/settings.json | jq '.hooks.Stop' 2>/dev/null | tee -a "$LOG_FILE"
cat {{CATALYST_ROOT}}/.claude/settings.json | jq '.hooks.Stop' 2>/dev/null | tee -a "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"

echo "4. Recent TTS client activity..." | tee -a "$LOG_FILE"
tail -20 ~/.claude/tts_client.log 2>/dev/null | tee -a "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"

echo "5. System beep settings..." | tee -a "$LOG_FILE"
defaults read -g com.apple.sound.beep.volume 2>/dev/null | tee -a "$LOG_FILE"
defaults read com.apple.systemsound 'com.apple.sound.uiaudio.enabled' 2>/dev/null | tee -a "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"

echo "=== Diagnostic complete - Log saved to: $LOG_FILE ===" | tee -a "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"
echo "Next steps:" | tee -a "$LOG_FILE"
echo "1. Run a /mid command" | tee -a "$LOG_FILE"
echo "2. Note when static occurs" | tee -a "$LOG_FILE"
echo "3. Run: tail -50 ~/.claude/tts_client.log" | tee -a "$LOG_FILE"
echo "4. Run: log show --predicate 'subsystem == \"com.apple.audio\"' --last 1m" | tee -a "$LOG_FILE"
