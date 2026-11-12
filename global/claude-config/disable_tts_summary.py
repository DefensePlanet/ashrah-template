#!/usr/bin/env python3
"""
Disable TTS Summary Hook for Claude Code
"""

import json
import sys
from pathlib import Path

def main():
    settings_file = Path.home() / ".claude" / "settings.local.json"
    
    # Load current settings
    try:
        with open(settings_file, 'r') as f:
            settings = json.load(f)
    except FileNotFoundError:
        print("🔇 No settings file found - TTS already disabled")
        return True
    except json.JSONDecodeError as e:
        print(f"❌ Error reading settings file: {e}")
        return False
    
    # Check for hooks
    if "hooks" not in settings or "Stop" not in settings["hooks"]:
        print("🔇 TTS Summary hook is already disabled")
        return True
    
    # Remove TTS Summary hooks
    filtered_hooks = []
    removed = False
    
    for hook_group in settings["hooks"]["Stop"]:
        filtered_group_hooks = []
        for hook in hook_group.get("hooks", []):
            if "tts_summary_hook.py" not in hook.get("command", ""):
                filtered_group_hooks.append(hook)
            else:
                removed = True
        
        if filtered_group_hooks:
            hook_group["hooks"] = filtered_group_hooks
            filtered_hooks.append(hook_group)
    
    if not removed:
        print("🔇 TTS Summary hook was already disabled")
        return True
    
    settings["hooks"]["Stop"] = filtered_hooks
    
    # Save updated settings
    try:
        with open(settings_file, 'w') as f:
            json.dump(settings, f, indent=2)
        
        print("✅ TTS Summary hook disabled successfully")
        return True
        
    except Exception as e:
        print(f"❌ Error saving settings: {e}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)