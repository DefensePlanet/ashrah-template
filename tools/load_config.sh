#!/bin/bash
# load_config.sh - Centralized configuration loader
# Source this file to load merged configuration

BUILDER_ROOT="${BUILDER_ROOT:-$HOME/Catalyst}"
GLOBAL_CONFIG="$BUILDER_ROOT/global/config/config.json"

# Load configuration with priority: env vars > script config > global config > defaults
load_builder_config() {
    local script_config="${1:-}"  # Optional script-specific config path
    
    # Defaults
    export BUILDER_QUALITY_MODE="standard"
    export BUILDER_DEFAULT_LANE="${BUILDER_DEFAULT_LANE:-standard}"
    export BUILDER_PREP_BUDGET_MS="${BUILDER_PREP_BUDGET_MS:-2000}"
    export BUILDER_PLANNER_BUDGET_MS="${BUILDER_PLANNER_BUDGET_MS:-5000}"
    export BUILDER_EXEC_BUDGET_MS="${BUILDER_EXEC_BUDGET_MS:-10000}"
    export BUILDER_KEYCHAIN_SERVICE="${BUILDER_KEYCHAIN_SERVICE:-Builder-System}"
    export BUILDER_DASHBOARD_ENABLED="${BUILDER_DASHBOARD_ENABLED:-true}"
    export BUILDER_BACKUP_ENABLED="${BUILDER_BACKUP_ENABLED:-true}"
    export BUILDER_LOG_LEVEL="${BUILDER_LOG_LEVEL:-INFO}"
    
    # Load from global config if available
    if [ -f "$GLOBAL_CONFIG" ] && command -v python3 >/dev/null 2>&1; then
        local config_values
        config_values=$(python3 -c "
import json, sys, os
try:
    with open('$GLOBAL_CONFIG') as f:
        config = json.load(f)
    
    # Extract values with fallbacks
    lanes = ','.join(config.get('lanes', {}).get('valid_lanes', ['standard', 'standard']))
    default_lane = config.get('lanes', {}).get('default_lane', 'standard')
    prep_budget = config.get('perf_budgets', {}).get('prep_ms', 2000)
    planner_budget = config.get('perf_budgets', {}).get('planner_ms', 5000)
    exec_budget = config.get('perf_budgets', {}).get('exec_ms', 10000)
    keychain_service = config.get('secrets', {}).get('keychain_service', 'Builder-System')
    dashboard_enabled = str(config.get('dashboard', {}).get('enabled', True)).lower()
    backup_enabled = str(config.get('backup', {}).get('enabled', True)).lower()
    log_level = config.get('logging', {}).get('level', 'INFO')
    
    print(f'BUILDER_QUALITY_MODE="standard"
    print(f'BUILDER_DEFAULT_LANE={default_lane}')
    print(f'BUILDER_PREP_BUDGET_MS={prep_budget}')
    print(f'BUILDER_PLANNER_BUDGET_MS={planner_budget}')
    print(f'BUILDER_EXEC_BUDGET_MS={exec_budget}')
    print(f'BUILDER_KEYCHAIN_SERVICE={keychain_service}')
    print(f'BUILDER_DASHBOARD_ENABLED={dashboard_enabled}')
    print(f'BUILDER_BACKUP_ENABLED={backup_enabled}')
    print(f'BUILDER_LOG_LEVEL={log_level}')
    
except Exception as e:
    sys.stderr.write(f'Config load warning: {e}\n')
" 2>/dev/null) || true
        
        if [ -n "$config_values" ]; then
            # Only override if not already set by environment
            while IFS='=' read -r key value; do
                if [ -n "$key" ] && [ -z "${!key}" ]; then
                    export "$key"="$value"
                fi
            done <<< "$config_values"
        fi
    fi
    
    # Load script-specific config if provided
    if [ -n "$script_config" ] && [ -f "$script_config" ]; then
        # Script configs can override global but not env vars
        # Implementation depends on script config format
        : # Placeholder for script-specific config loading
    fi
}

# Validate configuration
validate_builder_config() {
    local valid_lanes
    IFS=',' read -ra valid_lanes <<< "$BUILDER_LANES"
    
    # Check if default lane is in valid lanes
    local lane_valid=false
    for lane in "${valid_lanes[@]}"; do
        if [ "$lane" = "$BUILDER_DEFAULT_LANE" ]; then
            lane_valid=true
            break
        fi
    done
    
    if [ "$lane_valid" = "false" ]; then
        echo "⚠️  Warning: Default lane '$BUILDER_DEFAULT_LANE' not in valid lanes: $BUILDER_LANES" >&2
    fi
    
    # Validate numeric budgets
    if ! [[ "$BUILDER_PREP_BUDGET_MS" =~ ^[0-9]+$ ]] || [ "$BUILDER_PREP_BUDGET_MS" -le 0 ]; then
        echo "⚠️  Warning: Invalid prep budget: $BUILDER_PREP_BUDGET_MS" >&2
    fi
    
    if ! [[ "$BUILDER_PLANNER_BUDGET_MS" =~ ^[0-9]+$ ]] || [ "$BUILDER_PLANNER_BUDGET_MS" -le 0 ]; then
        echo "⚠️  Warning: Invalid planner budget: $BUILDER_PLANNER_BUDGET_MS" >&2
    fi
    
    if ! [[ "$BUILDER_EXEC_BUDGET_MS" =~ ^[0-9]+$ ]] || [ "$BUILDER_EXEC_BUDGET_MS" -le 0 ]; then
        echo "⚠️  Warning: Invalid exec budget: $BUILDER_EXEC_BUDGET_MS" >&2
    fi
}

# Print current configuration (for debugging)
print_builder_config() {
    echo "Builder Configuration:"
    echo "  BUILDER_QUALITY_MODE="standard"
    echo "  BUILDER_DEFAULT_LANE=$BUILDER_DEFAULT_LANE"
    echo "  BUILDER_PREP_BUDGET_MS=$BUILDER_PREP_BUDGET_MS"
    echo "  BUILDER_PLANNER_BUDGET_MS=$BUILDER_PLANNER_BUDGET_MS"
    echo "  BUILDER_EXEC_BUDGET_MS=$BUILDER_EXEC_BUDGET_MS"
    echo "  BUILDER_KEYCHAIN_SERVICE=$BUILDER_KEYCHAIN_SERVICE"
    echo "  BUILDER_DASHBOARD_ENABLED=$BUILDER_DASHBOARD_ENABLED"
    echo "  BUILDER_BACKUP_ENABLED=$BUILDER_BACKUP_ENABLED"
    echo "  BUILDER_LOG_LEVEL=$BUILDER_LOG_LEVEL"
}

# Auto-load configuration when sourced
if [ "${BASH_SOURCE[0]}" != "${0}" ]; then
    # Being sourced, load config automatically
    load_builder_config
fi




