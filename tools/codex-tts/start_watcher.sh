#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG=/tmp/codex_watch_tts.log
nohup python3 "$SCRIPT_DIR/watch_sessions_tts.py" >>"$LOG" 2>&1 &
echo "Started Codex TTS watcher (PID $!)"
