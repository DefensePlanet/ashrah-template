#!/usr/bin/env python3
"""
Claude Code TTS Hook Toggle Script
Usage: python3 ~/.claude/toggle_tts.py [on|off|status]
"""

import json
import sys
import os
from pathlib import Path

SETTINGS_FILE = Path.home() / ".claude" / "settings.json"

TTS_HOOK_CONFIG = {
    "matcher": "*",
    "hooks": [
        {
            "type": "command",
            "command": "python3 ~/.claude/simple_tts_hook.py"
        }
    ]
}

def load_settings():
    """Load Claude settings file"""
    try:
        with open(SETTINGS_FILE, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"❌ Settings file not found: {SETTINGS_FILE}")
        sys.exit(1)
    except json.JSONDecodeError:
        print(f"❌ Invalid JSON in settings file: {SETTINGS_FILE}")
        sys.exit(1)

def save_settings(settings):
    """Save Claude settings file"""
    try:
        with open(SETTINGS_FILE, 'w') as f:
            json.dump(settings, f, indent=2)
        return True
    except Exception as e:
        print(f"❌ Error saving settings: {e}")
        return False

def is_tts_enabled(settings):
    """Check if TTS hook is currently enabled"""
    hooks = settings.get("hooks", {})
    stop_hooks = hooks.get("Stop", [])
    
    for hook_group in stop_hooks:
        for hook in hook_group.get("hooks", []):
            if "tts_hook.py" in hook.get("command", ""):
                return True
    return False

def enable_tts(settings):
    """Enable TTS hook"""
    if "hooks" not in settings:
        settings["hooks"] = {}
    
    if "Stop" not in settings["hooks"]:
        settings["hooks"]["Stop"] = []
    
    # Check if already enabled
    if is_tts_enabled(settings):
        print("🔊 TTS hook is already enabled")
        return settings
    
    # Add TTS hook
    settings["hooks"]["Stop"].append(TTS_HOOK_CONFIG)
    print("✅ TTS hook enabled")
    return settings

def disable_tts(settings):
    """Disable TTS hook"""
    if not is_tts_enabled(settings):
        print("🔇 TTS hook is already disabled")
        return settings
    
    # Remove TTS hooks
    hooks = settings.get("hooks", {})
    stop_hooks = hooks.get("Stop", [])
    
    # Filter out TTS hooks
    filtered_hooks = []
    for hook_group in stop_hooks:
        filtered_group_hooks = []
        for hook in hook_group.get("hooks", []):
            if "tts_hook.py" not in hook.get("command", ""):
                filtered_group_hooks.append(hook)
        
        if filtered_group_hooks:
            hook_group["hooks"] = filtered_group_hooks
            filtered_hooks.append(hook_group)
    
    settings["hooks"]["Stop"] = filtered_hooks
    print("✅ TTS hook disabled")
    return settings

def show_status(settings):
    """Show current TTS hook status"""
    enabled = is_tts_enabled(settings)
    status_icon = "🔊" if enabled else "🔇"
    status_text = "ENABLED" if enabled else "DISABLED"
    print(f"{status_icon} TTS Hook Status: {status_text}")
    return enabled

def main():
    """Main function"""
    if len(sys.argv) > 2:
        print("Usage: python3 ~/.claude/toggle_tts.py [on|off|status]")
        sys.exit(1)
    
    action = sys.argv[1] if len(sys.argv) == 2 else "toggle"
    
    # Load current settings
    settings = load_settings()
    
    if action in ["status", "s"]:
        show_status(settings)
        return
    
    current_enabled = is_tts_enabled(settings)
    
    if action in ["on", "enable", "1"]:
        settings = enable_tts(settings)
    elif action in ["off", "disable", "0"]:
        settings = disable_tts(settings)
    elif action in ["toggle", "t"]:
        if current_enabled:
            settings = disable_tts(settings)
        else:
            settings = enable_tts(settings)
    else:
        print("❌ Invalid action. Use: on, off, toggle, or status")
        sys.exit(1)
    
    # Save settings
    if save_settings(settings):
        print("💾 Settings saved successfully")
    else:
        sys.exit(1)

if __name__ == "__main__":
    main()