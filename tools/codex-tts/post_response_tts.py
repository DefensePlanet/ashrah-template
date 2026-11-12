#!/usr/bin/env python3
"""
Codex CLI Post-Response TTS Hook

Purpose:
- Accept the assistant's latest response on stdin (raw text or simple JSON)
- Reuse Catalyst summary TTS pipeline to produce concise, spoken output

How it works:
- Checks a simple toggle (env CODEX_TTS or ~/.codex_tts_state)
- Wraps the response into a compact JSON payload
- Pipes it to global/claude-config/summary_tts_hook.py (single source of truth)

Usage:
- Configure Codex CLI to run this script after each assistant reply, with the
  full assistant message piped to stdin.

Input formats supported on stdin:
- Raw text (entire assistant message)
- JSON with one of: {"message": str}, {"assistant_message": str}, {"text": str}
"""

import json
import os
import sys
import subprocess
from pathlib import Path


def tts_enabled() -> bool:
    # Env override takes precedence
    flag = os.environ.get("CODEX_TTS", "").strip().lower()
    if flag in ("1", "true", "on", "yes"): 
        return True
    if flag in ("0", "false", "off", "no"): 
        return False

    # Fallback to state file
    state_file = Path.home() / ".codex_tts_state"
    if state_file.exists():
        try:
            return state_file.read_text().strip().lower() == "on"
        except Exception:
            return False
    return True  # default on if not specified


def read_input() -> str:
    data = sys.stdin.read()
    if not data:
        return ""
    # Try to parse as JSON; fall back to raw
    try:
        obj = json.loads(data)
        for key in ("assistant_message", "message", "text", "content"):
            if key in obj and isinstance(obj[key], str):
                return obj[key]
        # Unknown JSON shape; pass-through compacted
        return json.dumps(obj, ensure_ascii=False)
    except json.JSONDecodeError:
        return data


def main() -> int:
    if not tts_enabled():
        return 0

    text = read_input()
    if not text or len(text.strip()) < 4:
        return 0

    # Target summary TTS script (shared with Claude)
    builder_root = Path(__file__).resolve().parents[2]
    hook = builder_root / "tools" / "codex-tts" / "codex_summary_tts.py"
    if not hook.exists():
        print(f"TTS hook not found: {hook}", file=sys.stderr)
        return 1

    # Prepare a compact payload expected by the shared hook
    payload = {"message": text}

    try:
        proc = subprocess.run(
            ["python3", str(hook)],
            input=json.dumps(payload).encode("utf-8"),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        return proc.returncode
    except Exception as e:
        print(f"Codex TTS error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

