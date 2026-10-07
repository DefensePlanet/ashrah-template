#!/usr/bin/env python3
"""
Check TTS Summary Hook Status
"""

import json
from pathlib import Path

def main():
    settings_file = Path.home() / ".claude" / "settings.local.json"
    
    try:
        with open(settings_file, 'r') as f:
            settings = json.load(f)
    except FileNotFoundError:
        print("🔇 No settings file - TTS disabled")
        return
    except json.JSONDecodeError:
        print("❌ Invalid settings file")
        return
    
    # Check for TTS hooks
    if "hooks" not in settings or "Stop" not in settings["hooks"]:
        print("🔇 TTS Summary: DISABLED")
        return
    
    for hook_group in settings["hooks"]["Stop"]:
        for hook in hook_group.get("hooks", []):
            if "tts_summary_hook.py" in hook.get("command", ""):
                print("🔊 TTS Summary: ENABLED")
                print("📝 Mode: Intelligent summaries with OpenAI Onyx voice")
                return
    
    print("🔇 TTS Summary: DISABLED")

if __name__ == "__main__":
    main()