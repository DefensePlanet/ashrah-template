#!/usr/bin/env python3
"""
Toggle automatic TTS for Claude Code
Usage: tts (toggles on/off)
       tts on
       tts off
       tts status
"""

import json
import os
import sys

SETTINGS_PATH = os.path.expanduser('~/.claude/settings.json')
TTS_HOOK_COMMAND = "python3 ~/.claude/simple_tts_hook.py"
TTS_HOOK_COMMAND_ALT = "nohup python3 ~/.claude/simple_tts_hook.py >/dev/null 2>&1 &"

def load_settings():
    """Load Claude Code settings"""
    try:
        with open(SETTINGS_PATH, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading settings: {e}")
        sys.exit(1)

def save_settings(settings):
    """Save Claude Code settings"""
    try:
        with open(SETTINGS_PATH, 'w') as f:
            json.dump(settings, f, indent=2)
        return True
    except Exception as e:
        print(f"Error saving settings: {e}")
        return False

def is_tts_enabled(settings):
    """Check if TTS hook is enabled"""
    stop_hooks = settings.get('hooks', {}).get('Stop', [])
    for hook_group in stop_hooks:
        hooks = hook_group.get('hooks', [])
        for hook in hooks:
            cmd = hook.get('command', '')
            if cmd == TTS_HOOK_COMMAND or cmd == TTS_HOOK_COMMAND_ALT or 'simple_tts_hook.py' in cmd:
                return True
    return False

def enable_tts(settings):
    """Enable TTS hook"""
    if 'hooks' not in settings:
        settings['hooks'] = {}
    
    if 'Stop' not in settings['hooks']:
        settings['hooks']['Stop'] = []
    
    # Check if already enabled
    if is_tts_enabled(settings):
        return False, "TTS is already enabled"
    
    # Add TTS hook
    settings['hooks']['Stop'].append({
        "matcher": "*",
        "hooks": [
            {
                "type": "command",
                "command": TTS_HOOK_COMMAND
            }
        ]
    })
    
    return True, "TTS enabled"

def disable_tts(settings):
    """Disable TTS hook"""
    if 'hooks' not in settings or 'Stop' not in settings['hooks']:
        return False, "TTS is already disabled"
    
    # Remove TTS hook
    stop_hooks = settings['hooks']['Stop']
    original_length = len(stop_hooks)
    
    settings['hooks']['Stop'] = [
        hook_group for hook_group in stop_hooks
        if not any(
            'simple_tts_hook.py' in hook.get('command', '')
            for hook in hook_group.get('hooks', [])
        )
    ]
    
    if len(settings['hooks']['Stop']) < original_length:
        return True, "TTS disabled"
    else:
        return False, "TTS is already disabled"

def main():
    # Load current settings
    settings = load_settings()
    
    # Get command
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
    else:
        # Toggle if no argument
        command = 'toggle'
    
    # Execute command
    if command == 'on':
        changed, message = enable_tts(settings)
        if changed and save_settings(settings):
            print(f"✅ {message}")
        else:
            print(f"ℹ️  {message}")
    
    elif command == 'off':
        changed, message = disable_tts(settings)
        if changed and save_settings(settings):
            print(f"🔇 {message}")
        else:
            print(f"ℹ️  {message}")
    
    elif command == 'status':
        if is_tts_enabled(settings):
            print("🔊 TTS is currently ENABLED (voice: onyx)")
        else:
            print("🔇 TTS is currently DISABLED")
    
    elif command == 'toggle':
        if is_tts_enabled(settings):
            changed, message = disable_tts(settings)
            if changed and save_settings(settings):
                print(f"🔇 {message}")
        else:
            changed, message = enable_tts(settings)
            if changed and save_settings(settings):
                print(f"✅ {message}")
    
    else:
        print("Usage: tts [on|off|status]")
        print("       tts (toggles current state)")
        sys.exit(1)

if __name__ == "__main__":
    main()