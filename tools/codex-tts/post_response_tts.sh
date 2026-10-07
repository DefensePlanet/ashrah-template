#!/usr/bin/env bash
# Codex CLI Post-Response TTS Hook (shell wrapper)
#
# Reads the assistant's latest reply from stdin and invokes the shared
# summary TTS pipeline. Provide OPENAI_API_KEY in the environment for audio.

set -euo pipefail

PY=${PYTHON_BIN:-python3}
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HOOK_PY="$SCRIPT_DIR/post_response_tts.py"

# Buffer stdin fully then forward to Python
INPUT=$(cat || true)
{
  echo "[$(date)] wrapper invoked; input_len=${#INPUT}" >> /tmp/codex_tts_wrapper.log
} || true
if [ -z "${INPUT// /}" ]; then
  exit 0
fi

printf "%s" "$INPUT" | "$PY" "$HOOK_PY" >/dev/null 2>&1 || true
