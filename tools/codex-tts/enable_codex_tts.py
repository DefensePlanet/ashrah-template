#!/usr/bin/env python3
"""
Enable Codex TTS (toggle + guidance)

This sets a simple toggle for Codex voice and prints integration guidance for
hooking Codex CLI to run the post-response TTS hook.
"""

import os
from pathlib import Path


def main() -> int:
    state_file = Path.home() / ".codex_tts_state"
    try:
        state_file.write_text("on\n")
        print("✅ Codex TTS enabled (toggle set to 'on')")
    except Exception as e:
        print(f"⚠️ Could not write toggle file: {e}")

    repo_root = Path(__file__).resolve().parents[2]
    hook_sh = repo_root / "tools" / "codex-tts" / "post_response_tts.sh"

    print("\nHow to integrate with Codex CLI (choose one):\n")
    print("1) Post-response hook (preferred, if supported):")
    print(f"   Configure Codex to run: {hook_sh}")
    print("   and pipe the assistant's reply to stdin (full text).\n")

    print("2) Manual test:")
    print(f"   echo 'Hello from Codex' | {hook_sh}")
    print("   (expects OPENAI_API_KEY in environment)\n")

    print("3) Env toggles:")
    print("   - CODEX_TTS=off (disable) | CODEX_TTS=on (enable)")
    print("   - Or edit ~/.codex_tts_state (on/off)\n")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

