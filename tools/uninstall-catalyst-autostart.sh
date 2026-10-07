#!/bin/bash
# Catalyst Core Services Auto-Start Uninstallation Script
set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log() {
    echo -e "${BLUE}[Uninstall]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[Uninstall]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[Uninstall]${NC} $1"
}

log_error() {
    echo -e "${RED}[Uninstall]${NC} $1"
}

LAUNCH_AGENTS_DIR="$HOME/Library/LaunchAgents"
PLIST_NAME="com.catalyst.core.plist"
PLIST_PATH="$LAUNCH_AGENTS_DIR/$PLIST_NAME"

log "Catalyst Core Services Auto-Start Uninstallation"
log "================================================"

# 1. Check if service is loaded
if launchctl list | grep -q "com.catalyst.core"; then
    log "Unloading launch agent..."
    if launchctl unload "$PLIST_PATH" 2>/dev/null; then
        log_success "Launch agent unloaded"
    else
        log_warning "Failed to unload launch agent (may not be loaded)"
    fi
    sleep 2
else
    log_warning "Launch agent not currently loaded"
fi

# 2. Stop all services
log "Stopping Catalyst core services..."

stop_service() {
    local port=$1
    local name=$2

    if lsof -i :$port -sTCP:LISTEN >/dev/null 2>&1; then
        local pid=$(lsof -ti :$port -sTCP:LISTEN)
        log "Stopping $name (PID: $pid)..."
        kill $pid 2>/dev/null || true
        sleep 1

        # Force kill if still running
        if lsof -i :$port -sTCP:LISTEN >/dev/null 2>&1; then
            log_warning "Force stopping $name..."
            kill -9 $pid 2>/dev/null || true
        fi

        log_success "$name stopped"
    else
        log_warning "$name not running on port $port"
    fi
}

stop_service 443 "Caddy"
stop_service 8080 "Agent API"
stop_service 8083 "Bifrost Gateway"
stop_service 3456 "Claude Router"

# 3. Verify plist file exists before trying to remove
if [ -f "$PLIST_PATH" ]; then
    log "Removing plist file: $PLIST_PATH"
    rm -f "$PLIST_PATH"
    log_success "Plist file removed"
else
    log_warning "Plist file not found at $PLIST_PATH"
fi

log "================================================"
log_success "Uninstallation complete!"
log ""
log "Catalyst core services will no longer:"
log "  • Start automatically on login"
log "  • Restart automatically on crash"
log ""
log "You can manually start services with:"
log "  ./tools/catalyst-core-services.sh"
log ""
log "To reinstall auto-start, run:"
log "  ./tools/install-catalyst-autostart.sh"
