#!/bin/bash
#
# Telegram {{ORCHESTRATOR_NAME}} Bot - Installation Script
#
# Installs the bot as a LaunchAgent for automatic startup
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
PLIST_TEMPLATE="$PROJECT_DIR/com.catalyst.telegram-{{ORCHESTRATOR_NAME_LOWER}}-bot.plist"
PLIST_DEST="$HOME/Library/LaunchAgents/com.catalyst.telegram-{{ORCHESTRATOR_NAME_LOWER}}-bot.plist"
LOGS_DIR="$PROJECT_DIR/logs"
ENV_FILE="$PROJECT_DIR/.env"
ENV_EXAMPLE="$PROJECT_DIR/.env.example"

echo "=================================================="
echo "  Telegram {{ORCHESTRATOR_NAME}} Bot - Installation"
echo "=================================================="
echo

# Step 1: Check dependencies
echo -e "${BLUE}[1/8]${NC} Checking dependencies..."

# Check Bun
if ! command -v bun &> /dev/null; then
    echo -e "${RED}❌ Error: Bun is not installed${NC}"
    echo "   Install it from: https://bun.sh"
    exit 1
fi
echo -e "${GREEN}✅${NC} Bun: $(bun --version)"

# Check Node (for some MCPs)
if command -v node &> /dev/null; then
    echo -e "${GREEN}✅${NC} Node: $(node --version)"
else
    echo -e "${YELLOW}⚠️  Node not found (some MCPs may not work)${NC}"
fi

echo

# Step 2: Check .env file
echo -e "${BLUE}[2/8]${NC} Checking environment configuration..."

if [ ! -f "$ENV_FILE" ]; then
    echo -e "${RED}❌ Error: .env file not found${NC}"
    echo
    echo "   Please create .env file from template:"
    echo "   $ cp .env.example .env"
    echo "   $ nano .env  # Edit with your values"
    echo
    exit 1
fi

# Validate required environment variables
source "$ENV_FILE"

if [ -z "$TELEGRAM_BOT_TOKEN" ]; then
    echo -e "${RED}❌ Error: TELEGRAM_BOT_TOKEN not set in .env${NC}"
    exit 1
fi
echo -e "${GREEN}✅${NC} TELEGRAM_BOT_TOKEN: configured"

if [ -z "$TELEGRAM_ALLOWED_USERS" ]; then
    echo -e "${RED}❌ Error: TELEGRAM_ALLOWED_USERS not set in .env${NC}"
    exit 1
fi
echo -e "${GREEN}✅${NC} TELEGRAM_ALLOWED_USERS: configured"

# Check optional variables
if [ -z "$OPENAI_API_KEY" ]; then
    echo -e "${YELLOW}⚠️  OPENAI_API_KEY not set (voice transcription disabled)${NC}"
fi

echo

# Step 3: Install dependencies
echo -e "${BLUE}[3/8]${NC} Installing dependencies..."
cd "$PROJECT_DIR"
bun install > /dev/null 2>&1
echo -e "${GREEN}✅${NC} Dependencies installed"
echo

# Step 4: Create logs directory
echo -e "${BLUE}[4/8]${NC} Creating logs directory..."
mkdir -p "$LOGS_DIR"
echo -e "${GREEN}✅${NC} Logs directory: $LOGS_DIR"
echo

# Step 5: Test bot (dry run)
echo -e "${BLUE}[5/8]${NC} Testing bot configuration..."

# Use gtimeout if available (brew install coreutils), otherwise skip test
if command -v gtimeout &> /dev/null; then
    gtimeout 5 bun run src/index.ts > /tmp/telegram-{{ORCHESTRATOR_NAME_LOWER}}-test.log 2>&1 || true

    if grep -q "Bot started:" /tmp/telegram-{{ORCHESTRATOR_NAME_LOWER}}-test.log; then
        echo -e "${GREEN}✅${NC} Bot configuration valid"
    else
        echo -e "${RED}❌ Error: Bot failed to start${NC}"
        echo
        echo "   Check test output:"
        cat /tmp/telegram-{{ORCHESTRATOR_NAME_LOWER}}-test.log
        rm -f /tmp/telegram-{{ORCHESTRATOR_NAME_LOWER}}-test.log
        exit 1
    fi
    rm -f /tmp/telegram-{{ORCHESTRATOR_NAME_LOWER}}-test.log
else
    echo -e "${YELLOW}⚠️  Skipping bot test (gtimeout not available)${NC}"
    echo "   Install with: brew install coreutils"
fi
echo

# Step 6: Check if already installed
echo -e "${BLUE}[6/8]${NC} Checking existing installation..."
if launchctl list | grep -q "com.catalyst.telegram-{{ORCHESTRATOR_NAME_LOWER}}-bot"; then
    echo -e "${YELLOW}⚠️  Bot is already running${NC}"
    echo "   Unloading existing installation..."
    launchctl unload "$PLIST_DEST" 2>/dev/null || true
    sleep 2
fi

# Step 7: Install LaunchAgent
echo -e "${BLUE}[7/8]${NC} Installing LaunchAgent..."

# Ensure LaunchAgents directory exists
mkdir -p "$HOME/Library/LaunchAgents"

# Copy plist to LaunchAgents
cp "$PLIST_TEMPLATE" "$PLIST_DEST"
echo -e "${GREEN}✅${NC} Copied plist to ~/Library/LaunchAgents/"

# Set correct permissions
chmod 644 "$PLIST_DEST"

# Load LaunchAgent
launchctl load "$PLIST_DEST"
echo -e "${GREEN}✅${NC} LaunchAgent loaded"

echo

# Step 8: Verify installation
echo -e "${BLUE}[8/8]${NC} Verifying installation..."
sleep 3  # Give bot time to start

if launchctl list | grep -q "com.catalyst.telegram-{{ORCHESTRATOR_NAME_LOWER}}-bot"; then
    echo -e "${GREEN}✅${NC} Bot is running!"

    # Get PID
    PID=$(launchctl list | grep "com.catalyst.telegram-{{ORCHESTRATOR_NAME_LOWER}}-bot" | awk '{print $1}')
    if [ "$PID" != "-" ]; then
        echo -e "${GREEN}✅${NC} Process ID: $PID"
    fi
else
    echo -e "${RED}❌ Error: Bot failed to start${NC}"
    echo
    echo "   Check logs for errors:"
    echo "   $ tail -f $LOGS_DIR/stderr.log"
    exit 1
fi

echo
echo "=================================================="
echo -e "${GREEN}✅ Installation Complete!${NC}"
echo "=================================================="
echo
echo "Next steps:"
echo "  1. Test bot by messaging it on Telegram"
echo "  2. Check logs: tail -f $LOGS_DIR/stdout.log"
echo "  3. View status: launchctl list | grep telegram-{{ORCHESTRATOR_NAME_LOWER}}"
echo
echo "Useful commands:"
echo "  • Stop:    launchctl unload $PLIST_DEST"
echo "  • Start:   launchctl load $PLIST_DEST"
echo "  • Restart: launchctl kickstart -k gui/\$(id -u)/com.catalyst.telegram-{{ORCHESTRATOR_NAME_LOWER}}-bot"
echo "  • Logs:    tail -f $LOGS_DIR/*.log"
echo
echo "To uninstall:"
echo "  $ ./uninstall.sh"
echo
