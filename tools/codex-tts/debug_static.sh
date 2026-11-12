#!/bin/bash
# TTS Static Debugging Script
# Tests the entire hook pipeline vs direct playback

set -e

LOG_FILE="$HOME/.claude/tts_debug_static.log"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CLIENT="$SCRIPT_DIR/tts_client.py"

# Find Python 3.11+
if [ -x "/Library/Frameworks/Python.framework/Versions/3.11/bin/python3" ]; then
    PYTHON="/Library/Frameworks/Python.framework/Versions/3.11/bin/python3"
elif [ -x "/Library/Frameworks/Python.framework/Versions/3.12/bin/python3" ]; then
    PYTHON="/Library/Frameworks/Python.framework/Versions/3.12/bin/python3"
elif [ -x "/opt/homebrew/bin/python3" ]; then
    PYTHON="/opt/homebrew/bin/python3"
else
    PYTHON="python3"
fi
TEST_TEXT="Testing for static. This is a diagnostic message to identify audio artifacts."

echo "=== TTS Static Debugging ===" | tee -a "$LOG_FILE"
echo "Timestamp: $(date)" | tee -a "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"

# Test 1: Direct file playback
echo "TEST 1: Playing most recent audio file directly..." | tee -a "$LOG_FILE"
LATEST_FILE=$(ls -t ~/.mlx_audio/outputs/tts_server_*.wav 2>/dev/null | head -1)
if [ -n "$LATEST_FILE" ]; then
    echo "File: $LATEST_FILE" | tee -a "$LOG_FILE"
    afinfo "$LATEST_FILE" | grep -E "(sample_rate|duration)" | tee -a "$LOG_FILE"
    echo "Playing now... (listen for static)" | tee -a "$LOG_FILE"
    afplay "$LATEST_FILE"
    echo "Did you hear static? (y/n)" | tee -a "$LOG_FILE"
    read -r response
    echo "Response: $response" | tee -a "$LOG_FILE"
else
    echo "No audio files found" | tee -a "$LOG_FILE"
fi
echo "" | tee -a "$LOG_FILE"

# Test 2: Generate fresh via client (mimics hook)
echo "TEST 2: Generating via client (simulates hook path)..." | tee -a "$LOG_FILE"
echo "{\"message\": \"$TEST_TEXT\"}" | "$PYTHON" "$CLIENT" 2>&1 | tee -a "$LOG_FILE"
sleep 2
echo "Did you hear static? (y/n)" | tee -a "$LOG_FILE"
read -r response
echo "Response: $response" | tee -a "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"

# Test 3: Play the file that was just generated
echo "TEST 3: Re-playing the file that was just generated..." | tee -a "$LOG_FILE"
NEW_FILE=$(ls -t ~/.mlx_audio/outputs/tts_server_*.wav 2>/dev/null | head -1)
if [ -n "$NEW_FILE" ]; then
    echo "File: $NEW_FILE" | tee -a "$LOG_FILE"
    afinfo "$NEW_FILE" | grep -E "(sample_rate|duration)" | tee -a "$LOG_FILE"
    echo "Playing now... (listen for static)" | tee -a "$LOG_FILE"
    afplay "$NEW_FILE"
    echo "Did you hear static? (y/n)" | tee -a "$LOG_FILE"
    read -r response
    echo "Response: $response" | tee -a "$LOG_FILE"
else
    echo "No new file found" | tee -a "$LOG_FILE"
fi
echo "" | tee -a "$LOG_FILE"

# Test 4: Simulate exact hook path
echo "TEST 4: Exact hook simulation (with backgrounding)..." | tee -a "$LOG_FILE"
(
    echo "{\"message\": \"$TEST_TEXT\"}" | "$PYTHON" "$CLIENT" 2>&1 | \
    while IFS= read -r line; do
        echo "Client: $line" | tee -a "$LOG_FILE"
    done
) &
HOOK_PID=$!
echo "Backgrounded client with PID: $HOOK_PID" | tee -a "$LOG_FILE"
wait $HOOK_PID
sleep 1
echo "Did you hear static? (y/n)" | tee -a "$LOG_FILE"
read -r response
echo "Response: $response" | tee -a "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"

echo "=== Debug Summary ===" | tee -a "$LOG_FILE"
echo "Check $LOG_FILE for full results" | tee -a "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"

# Show recent server logs
echo "=== Recent Server Processing ===" | tee -a "$LOG_FILE"
tail -20 ~/.claude/tts_server.log | tee -a "$LOG_FILE"
