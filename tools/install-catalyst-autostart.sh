#!/bin/bash
# Catalyst Core Services Auto-Start Installation Script
set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log() {
    echo -e "${BLUE}[Install]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[Install]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[Install]${NC} $1"
}

log_error() {
    echo -e "${RED}[Install]${NC} $1"
}

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
CATALYST_ROOT="$(dirname "$SCRIPT_DIR")"
LAUNCH_AGENTS_DIR="$HOME/Library/LaunchAgents"
PLIST_NAME="com.catalyst.core.plist"
PLIST_SOURCE="$LAUNCH_AGENTS_DIR/$PLIST_NAME"
STARTUP_SCRIPT="$SCRIPT_DIR/catalyst-core-services.sh"

log "Catalyst Core Services Auto-Start Installation"
log "================================================"

# 1. Verify startup script exists and is executable
log "Checking startup script..."
if [ ! -f "$STARTUP_SCRIPT" ]; then
    log_error "Startup script not found at $STARTUP_SCRIPT"
    exit 1
fi

if [ ! -x "$STARTUP_SCRIPT" ]; then
    log "Making startup script executable..."
    chmod +x "$STARTUP_SCRIPT"
fi

log_success "Startup script verified: $STARTUP_SCRIPT"

# 2. Create log directory
LOG_DIR="/tmp/catalyst"
log "Creating log directory: $LOG_DIR"
mkdir -p "$LOG_DIR"
log_success "Log directory ready"

# 3. Verify plist file exists
log "Checking plist file..."
if [ ! -f "$PLIST_SOURCE" ]; then
    log_error "Plist file not found at $PLIST_SOURCE"
    log_error "Expected location: $LAUNCH_AGENTS_DIR/$PLIST_NAME"
    exit 1
fi

log_success "Plist file found: $PLIST_SOURCE"

# 4. Set correct permissions
log "Setting permissions..."
chmod 644 "$PLIST_SOURCE"
log_success "Permissions set to 644"

# 5. Unload existing service if running
if launchctl list | grep -q "com.catalyst.core"; then
    log_warning "Existing service found, unloading..."
    launchctl unload "$PLIST_SOURCE" 2>/dev/null || true
    sleep 2
fi

# 6. Load the launch agent
log "Loading launch agent..."
if launchctl load "$PLIST_SOURCE"; then
    log_success "Launch agent loaded successfully"
else
    log_error "Failed to load launch agent"
    exit 1
fi

# 7. Wait for services to start
log "Waiting for services to start (30 seconds)..."
sleep 30

# 8. Verify services are running
log "Verifying services..."
log "================================================"

check_service() {
    local port=$1
    local name=$2

    if lsof -i :$port -sTCP:LISTEN >/dev/null 2>&1; then
        log_success "✓ $name (port $port) - RUNNING"
        return 0
    else
        log_error "✗ $name (port $port) - NOT RUNNING"
        return 1
    fi
}

SUCCESS=0
check_service 443 "Caddy" || SUCCESS=1
check_service 8080 "Agent API" || SUCCESS=1
check_service 8083 "Bifrost Gateway" || SUCCESS=1
check_service 3456 "Claude Router" || SUCCESS=1

log "================================================"

if [ $SUCCESS -eq 0 ]; then
    log_success "Installation complete! All services are running."
    log ""
    log "Service URLs:"
    log "  • Caddy:           https://localhost"
    log "  • Agent API:       http://localhost:8080"
    log "  • Bifrost Gateway: http://localhost:8083"
    log "  • Claude Router:   http://localhost:3456"
    log ""
    log "Services will now start automatically:"
    log "  • On Mac login"
    log "  • After service crashes (auto-restart)"
    log ""
    log "Logs are available in: $LOG_DIR/"
    log ""
    log "To uninstall, run: ./tools/uninstall-catalyst-autostart.sh"
else
    log_error "Installation completed but some services failed to start."
    log_warning "Check logs in $LOG_DIR/ for details:"
    log "  • $LOG_DIR/launch-agent.out.log"
    log "  • $LOG_DIR/launch-agent.err.log"
    log "  • $LOG_DIR/caddy.log"
    log "  • $LOG_DIR/agent-api.log"
    log "  • $LOG_DIR/bifrost.log"
    log "  • $LOG_DIR/claude-router.log"
    exit 1
fi
