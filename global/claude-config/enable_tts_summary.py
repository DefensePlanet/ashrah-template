#!/usr/bin/env python3
"""
Enable TTS Summary Hook for Claude Code
Adds intelligent summary-based TTS to Claude Code responses
"""

import json
import sys
import os
from pathlib import Path

def main():
    settings_file = Path.home() / ".claude" / "settings.local.json"
    
    # Load current settings
    try:
        with open(settings_file, 'r') as f:
            settings = json.load(f)
    except FileNotFoundError:
        settings = {}
    except json.JSONDecodeError as e:
        print(f"❌ Error reading settings file: {e}")
        return False
    
    # Initialize hooks structure
    if "hooks" not in settings:
        settings["hooks"] = {}
    
    if "Stop" not in settings["hooks"]:
        settings["hooks"]["Stop"] = []
    
    # Check if summary TTS hook is already enabled
    for hook_group in settings["hooks"]["Stop"]:
        for hook in hook_group.get("hooks", []):
            if "tts_summary_hook.py" in hook.get("command", ""):
                print("🔊 TTS Summary hook is already enabled")
                return True
    
    # Add TTS Summary hook
    tts_hook_config = {
        "matcher": "*",
        "hooks": [
            {
                "type": "command",
                "command": f"python3 {Path.home() / 'Catalyst' / 'global' / 'claude-config' / 'tts_summary_hook.py'}"
            }
        ]
    }
    
    settings["hooks"]["Stop"].append(tts_hook_config)
    
    # Save updated settings
    try:
        with open(settings_file, 'w') as f:
            json.dump(settings, f, indent=2)
        
        print("✅ TTS Summary hook enabled successfully")
        print("🔊 Claude responses will now be summarized and spoken using OpenAI Onyx voice")
        print("📝 Summary format: Key action + outcome + next steps (when applicable)")
        return True
        
    except Exception as e:
        print(f"❌ Error saving settings: {e}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)