#!/bin/bash
# Catalyst Core Services Startup Script
# Starts Caddy, Agent API, Bifrost Gateway, and Claude Router
set -euo pipefail

# Ensure proper PATH for Homebrew
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:$PATH"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "${BLUE}[Catalyst]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[Catalyst]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[Catalyst]${NC} $1"
}

log_error() {
    echo -e "${RED}[Catalyst]${NC} $1"
}

# Check if service is already running
is_running() {
    local port=$1
    lsof -i :$port -sTCP:LISTEN >/dev/null 2>&1
}

# Wait for service to be ready
wait_for_service() {
    local port=$1
    local service_name=$2
    local max_attempts=30
    local attempt=1

    log "Waiting for $service_name (port $port) to be ready..."

    while [ $attempt -le $max_attempts ]; do
        if is_running $port; then
            log_success "$service_name is ready on port $port"
            return 0
        fi
        sleep 1
        attempt=$((attempt + 1))
    done

    log_error "$service_name failed to start within 30 seconds"
    return 1
}

# Load environment variables
ENV_FILE="{{CATALYST_ROOT}}/.env"
if [ -f "$ENV_FILE" ]; then
    set -a
    source "$ENV_FILE"
    set +a
    log "Loaded environment variables from $ENV_FILE"
fi

# Service directories
CATALYST_ROOT="{{CATALYST_ROOT}}"
CADDY_DIR="$CATALYST_ROOT/catalyst-design-system"
API_DIR="$CATALYST_ROOT/api"
BIFROST_DIR="$CATALYST_ROOT/tools/bifrost-cli"
BIFROST_DATA="$CATALYST_ROOT/tools/bifrost-data"
ROUTER_DIR="$CATALYST_ROOT/tools/claude-router"

# Log directory
LOG_DIR="/tmp/catalyst"
mkdir -p "$LOG_DIR"

log "Starting Catalyst Core Services..."
log "========================================="

# 1. Start Caddy (port 443)
log "Checking Caddy (port 443)..."
if is_running 443; then
    log_warning "Caddy already running on port 443"
else
    log "Starting Caddy..."
    cd "$CADDY_DIR"
    nohup /opt/homebrew/bin/caddy run --config Caddyfile --adapter caddyfile \
        > "$LOG_DIR/caddy.log" 2>&1 &

    if wait_for_service 443 "Caddy"; then
        log_success "Caddy started successfully"
    else
        log_error "Caddy failed to start - check $LOG_DIR/caddy.log"
        exit 1
    fi
fi

# 2. Start Agent API (port 8080)
log "Checking Agent API (port 8080)..."
if is_running 8080; then
    log_warning "Agent API already running on port 8080"
else
    log "Starting Agent API..."
    cd "$API_DIR"

    # Activate virtual environment if it exists
    if [ -d "venv_312" ]; then
        source venv_312/bin/activate
    fi

    nohup python3 server.py > "$LOG_DIR/agent-api.log" 2>&1 &

    if wait_for_service 8080 "Agent API"; then
        log_success "Agent API started successfully"
    else
        log_error "Agent API failed to start - check $LOG_DIR/agent-api.log"
        exit 1
    fi
fi

# 3. Start Bifrost Gateway (port 8083)
log "Checking Bifrost Gateway (port 8083)..."
if is_running 8083; then
    log_warning "Bifrost Gateway already running on port 8083"
else
    log "Starting Bifrost Gateway..."

    # Set required environment variables for Bifrost
    export OTEL_EXPORTER_OTLP_ENDPOINT="http://localhost:4318"
    export OTEL_EXPORTER_OTLP_PROTOCOL="http/protobuf"
    export OTEL_TRACES_EXPORTER="otlp"
    export BIFROST_OTEL_ENABLED="true"

    cd "$BIFROST_DIR"
    nohup node_modules/@maximhq/bifrost/bifrost-http \
        -port 8083 \
        -app-dir "$BIFROST_DATA" \
        > "$LOG_DIR/bifrost.log" 2>&1 &

    if wait_for_service 8083 "Bifrost Gateway"; then
        log_success "Bifrost Gateway started successfully"
    else
        log_error "Bifrost Gateway failed to start - check $LOG_DIR/bifrost.log"
        exit 1
    fi
fi

# 4. Start Claude Router (port 3456)
log "Checking Claude Router (port 3456)..."
if is_running 3456; then
    log_warning "Claude Router already running on port 3456"
else
    log "Starting Claude Router..."
    cd "$ROUTER_DIR"

    # Run the router start script
    bash start_router.sh > "$LOG_DIR/claude-router.log" 2>&1

    if wait_for_service 3456 "Claude Router"; then
        log_success "Claude Router started successfully"
    else
        log_error "Claude Router failed to start - check $LOG_DIR/claude-router.log"
        exit 1
    fi
fi

log "========================================="
log_success "All Catalyst Core Services are running!"
log ""
log "Service Status:"
log "  ✓ Caddy:           https://localhost (port 443)"
log "  ✓ Agent API:       http://localhost:8080"
log "  ✓ Bifrost Gateway: http://localhost:8083"
log "  ✓ Claude Router:   http://localhost:3456"
log ""
log "Logs are available in: $LOG_DIR/"
log "========================================="

exit 0
