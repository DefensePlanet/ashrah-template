#!/bin/bash

# TTS Toggle Script for Claude Code
# Usage: ~/.claude/tts-toggle.sh [on|off|status]

SETTINGS_FILE="$HOME/.claude/settings.json"

show_status() {
    if grep -q '"Stop":' "$SETTINGS_FILE"; then
        echo "TTS is ON"
    elif grep -q '"_Stop_disabled":' "$SETTINGS_FILE"; then
        echo "TTS is OFF"
    else
        echo "TTS hook not found in settings"
    fi
}

toggle_on() {
    if grep -q '"_Stop_disabled":' "$SETTINGS_FILE"; then
        sed -i '' 's/"_Stop_disabled":/"Stop":/g' "$SETTINGS_FILE"
        echo "TTS enabled - restart Claude Code to take effect"
    else
        echo "TTS is already enabled"
    fi
}

toggle_off() {
    if grep -q '"Stop":' "$SETTINGS_FILE"; then
        sed -i '' 's/"Stop":/"_Stop_disabled":/g' "$SETTINGS_FILE"
        echo "TTS disabled - restart Claude Code to take effect"
    else
        echo "TTS is already disabled"
    fi
}

case "$1" in
    on)
        toggle_on
        ;;
    off)
        toggle_off
        ;;
    status)
        show_status
        ;;
    *)
        echo "Usage: tts-toggle.sh [on|off|status]"
        echo "Current status:"
        show_status
        ;;
esac