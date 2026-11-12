#!/bin/bash
#
# Telegram {{ORCHESTRATOR_NAME}} Bot - Uninstallation Script
#
# Removes the bot LaunchAgent and optionally cleans logs
#

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
PLIST_DEST="$HOME/Library/LaunchAgents/com.catalyst.telegram-{{ORCHESTRATOR_NAME_LOWER}}-bot.plist"
LOGS_DIR="$PROJECT_DIR/logs"

# Parse arguments
CLEAN_LOGS=false
if [ "$1" == "--clean-logs" ]; then
    CLEAN_LOGS=true
fi

echo "=================================================="
echo "  Telegram {{ORCHESTRATOR_NAME}} Bot - Uninstallation"
echo "=================================================="
echo

# Step 1: Check if installed
echo -e "${BLUE}[1/4]${NC} Checking installation..."

if [ ! -f "$PLIST_DEST" ]; then
    echo -e "${YELLOW}⚠️  LaunchAgent not found (already uninstalled?)${NC}"
else
    echo -e "${GREEN}✅${NC} LaunchAgent found"
fi

echo

# Step 2: Stop and unload LaunchAgent
echo -e "${BLUE}[2/4]${NC} Stopping bot..."

if launchctl list | grep -q "com.catalyst.telegram-{{ORCHESTRATOR_NAME_LOWER}}-bot"; then
    echo "   Unloading LaunchAgent..."
    launchctl unload "$PLIST_DEST" 2>/dev/null || true
    sleep 2

    # Verify stopped
    if launchctl list | grep -q "com.catalyst.telegram-{{ORCHESTRATOR_NAME_LOWER}}-bot"; then
        echo -e "${RED}❌ Warning: Bot may still be running${NC}"
        echo "   Try manually: launchctl kill SIGTERM gui/\$(id -u)/com.catalyst.telegram-{{ORCHESTRATOR_NAME_LOWER}}-bot"
    else
        echo -e "${GREEN}✅${NC} Bot stopped"
    fi
else
    echo -e "${GREEN}✅${NC} Bot not running"
fi

echo

# Step 3: Remove plist
echo -e "${BLUE}[3/4]${NC} Removing LaunchAgent..."

if [ -f "$PLIST_DEST" ]; then
    rm "$PLIST_DEST"
    echo -e "${GREEN}✅${NC} Removed $PLIST_DEST"
else
    echo -e "${YELLOW}⚠️  Plist already removed${NC}"
fi

echo

# Step 4: Clean logs (optional)
echo -e "${BLUE}[4/4]${NC} Cleaning logs..."

if [ "$CLEAN_LOGS" = true ]; then
    if [ -d "$LOGS_DIR" ]; then
        rm -rf "$LOGS_DIR"
        echo -e "${GREEN}✅${NC} Removed logs directory"
    else
        echo -e "${YELLOW}⚠️  Logs directory not found${NC}"
    fi
else
    echo -e "${YELLOW}⚠️  Logs not removed (use --clean-logs to remove)${NC}"
fi

echo
echo "=================================================="
echo -e "${GREEN}✅ Uninstallation Complete!${NC}"
echo "=================================================="
echo

if [ "$CLEAN_LOGS" = false ]; then
    echo "Note: Logs preserved in $LOGS_DIR"
    echo "      To remove: ./uninstall.sh --clean-logs"
    echo
fi

echo "To reinstall:"
echo "  $ ./install.sh"
echo
