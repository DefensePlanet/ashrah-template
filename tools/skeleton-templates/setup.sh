#!/bin/bash
# Catalyst Skeleton — First-Time Setup
# Replaces {{PLACEHOLDER}} tokens with your personal values

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
CATALYST_ROOT="$SCRIPT_DIR"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

CONFIG_FILE="$CATALYST_ROOT/.catalyst-config"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  Catalyst Framework — First-Time Setup ${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Check for --apply mode (re-apply saved config)
if [[ "${1:-}" == "--apply" ]]; then
    if [[ -f "$CONFIG_FILE" ]]; then
        echo -e "${GREEN}Re-applying saved configuration from .catalyst-config${NC}"
        source "$CONFIG_FILE"
    else
        echo -e "${RED}No .catalyst-config found. Run setup.sh without --apply first.${NC}"
        exit 1
    fi
else
    # Interactive prompts
    echo -e "${YELLOW}This script will personalize your Catalyst installation.${NC}"
    echo -e "${YELLOW}Your choices are saved to .catalyst-config for future updates.${NC}"
    echo ""

    read -p "Your name (e.g., Josh): " USER_NAME
    if [[ -z "$USER_NAME" ]]; then
        echo -e "${RED}Name is required.${NC}"
        exit 1
    fi

    read -p "Orchestrator name (default: {{ORCHESTRATOR_NAME}}): " ORCHESTRATOR_NAME
    ORCHESTRATOR_NAME="${ORCHESTRATOR_NAME:-{{ORCHESTRATOR_NAME}}}"

    read -p "Assistant name for SOUL.md (default: Atlas): " ASSISTANT_NAME
    ASSISTANT_NAME="${ASSISTANT_NAME:-Atlas}"

    read -p "Your email (optional, for tool configs): " USER_EMAIL
    USER_EMAIL="${USER_EMAIL:-}"

    echo ""
    echo -e "${BLUE}Telegram Integration (optional — press Enter to skip)${NC}"
    echo "If your orchestrator has a Telegram bot, enter its username."
    echo "This is used to auto-create capsule supergroups."
    read -p "Bot username (e.g. HuxBot, without @): " BOT_USERNAME
    BOT_USERNAME="${BOT_USERNAME:-}"

    # Save config
    cat > "$CONFIG_FILE" <<CONF
USER_NAME="$USER_NAME"
ORCHESTRATOR_NAME="$ORCHESTRATOR_NAME"
ASSISTANT_NAME="$ASSISTANT_NAME"
USER_EMAIL="$USER_EMAIL"
BOT_USERNAME="$BOT_USERNAME"
CONF
    echo -e "${GREEN}Configuration saved to .catalyst-config${NC}"
fi

echo ""
echo -e "${BLUE}Applying personalization...${NC}"

# Count replacements
COUNT=0

# Find all text files and replace placeholders
find "$CATALYST_ROOT" \
    -type f \
    \( -name "*.md" -o -name "*.py" -o -name "*.sh" -o -name "*.yaml" \
       -o -name "*.yml" -o -name "*.json" -o -name "*.ts" -o -name "*.toml" \
       -o -name "*.txt" \) \
    -not -path "*/.git/*" \
    -not -path "*/node_modules/*" \
    -not -name "setup.sh" \
    | while read -r file; do

    # Check if file contains any placeholders
    if grep -q '{{CATALYST_ROOT}}\|{{HOME_DIR}}\|{{USER_NAME}}\|{{ORCHESTRATOR_NAME}}\|{{ASSISTANT_NAME}}\|{{USER_EMAIL}}' "$file" 2>/dev/null; then
        sed -i '' \
            -e "s|{{CATALYST_ROOT}}|$CATALYST_ROOT|g" \
            -e "s|{{HOME_DIR}}|$HOME|g" \
            -e "s|{{USER_NAME}}|$USER_NAME|g" \
            -e "s|{{ORCHESTRATOR_NAME}}|$ORCHESTRATOR_NAME|g" \
            -e "s|{{ASSISTANT_NAME}}|$ASSISTANT_NAME|g" \
            -e "s|{{USER_EMAIL}}|$USER_EMAIL|g" \
            "$file"
        COUNT=$((COUNT + 1))
        echo "  Updated: ${file#$CATALYST_ROOT/}"
    fi
done

# Create .env from .env.example if it doesn't exist
if [[ ! -f "$CATALYST_ROOT/.env" ]] && [[ -f "$CATALYST_ROOT/.env.example" ]]; then
    cp "$CATALYST_ROOT/.env.example" "$CATALYST_ROOT/.env"
    echo -e "${GREEN}Created .env from .env.example — fill in your API keys${NC}"
fi

# Create memory directory
mkdir -p "$CATALYST_ROOT/memory"

# Create capsules directory if empty
mkdir -p "$CATALYST_ROOT/capsules"

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  Setup complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "Next steps:"
echo "  1. Fill in API keys in .env"
echo "  2. (Optional) Run ./setup-skills.sh to install community skills"
echo "  3. Open Claude Code: claude"
echo ""
echo -e "Your orchestrator is named ${BLUE}$ORCHESTRATOR_NAME${NC}."
echo -e "Welcome to Catalyst, ${BLUE}$USER_NAME${NC}."
