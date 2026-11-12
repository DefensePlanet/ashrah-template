#!/bin/bash
set -euo pipefail

# diagnose_builder.sh - Comprehensive Builder system diagnostics
# Usage: diagnose_builder.sh [--strict] [--capsule /abs/path] [--verbose]

BUILDER_ROOT="$HOME/Catalyst"
STRICT_MODE=false
VERBOSE=false
TEST_CAPSULE=""
WARNINGS=0
FAILURES=0

usage() {
    cat << 'EOF'
diagnose_builder.sh - Catalyst Diagnostics

Usage: diagnose_builder.sh [options]

Options:
  --strict           Exit non-zero on any failures (default: warnings only)
  --capsule PATH     Test config merging for specific capsule
  --verbose          Show detailed output for all checks
  --help             Show this help message

Examples:
  diagnose_builder.sh                                    # Basic health check
  diagnose_builder.sh --strict                           # Fail on any issues
  diagnose_builder.sh --capsule ~/Catalyst/capsules/my-app
  diagnose_builder.sh --verbose --strict
EOF
}

log_check() {
    local status="$1"
    local message="$2"
    case "$status" in
        "PASS") echo "✅ $message" ;;
        "WARN") 
            echo "⚠️  $message"
            ((WARNINGS++))
            ;;
        "FAIL")
            echo "❌ $message"
            ((FAILURES++))
            ;;
        "INFO") [ "$VERBOSE" = true ] && echo "ℹ️  $message" ;;
    esac
}

check_file_permissions() {
    local file="$1"
    local expected_perm="$2"
    local description="$3"
    
    if [ ! -f "$file" ]; then
        log_check "FAIL" "$description: File missing ($file)"
        return 1
    fi
    
    if [ "$expected_perm" = "executable" ] && [ ! -x "$file" ]; then
        log_check "WARN" "$description: Not executable ($file)"
        return 1
    fi
    
    if [ "$expected_perm" = "readable" ] && [ ! -r "$file" ]; then
        log_check "FAIL" "$description: Not readable ($file)"
        return 1
    fi
    
    log_check "PASS" "$description"
    return 0
}

check_directory() {
    local dir="$1"
    local description="$2"
    
    if [ ! -d "$dir" ]; then
        log_check "FAIL" "$description: Directory missing ($dir)"
        return 1
    fi
    
    if [ ! -w "$dir" ]; then
        log_check "WARN" "$description: Directory not writable ($dir)"
        return 1
    fi
    
    log_check "PASS" "$description"
    return 0
}

merge_capsule_config() {
    local capsule_path="$1"
    local global_config="$BUILDER_ROOT/tools/planner_config.json"
    local capsule_config="$capsule_path/ops/planner.json"
    
    python3 - <<PY
import json
import sys

try:
    # Read global config
    with open('$global_config', 'r') as f:
        global_cfg = json.load(f)
    
    # Read capsule config if it exists
    capsule_cfg = {}
    try:
        with open('$capsule_config', 'r') as f:
            capsule_cfg = json.load(f)
    except FileNotFoundError:
        pass
    
    # Merge: capsule overrides global
    merged = global_cfg.copy()
    for key, value in capsule_cfg.items():
        if key == 'env' and isinstance(value, dict) and key in merged:
            merged_env = merged[key].copy()
            merged_env.update(value)
            merged[key] = merged_env
        else:
            merged[key] = value
    
    print(json.dumps(merged, indent=2))
    
except Exception as e:
    print(f'ERROR: Config merge failed: {e}')
    sys.exit(1)
PY
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --strict)
            STRICT_MODE=true
            shift
            ;;
        --verbose)
            VERBOSE=true
            shift
            ;;
        --capsule)
            TEST_CAPSULE="$2"
            shift 2
            ;;
        --help)
            usage
            exit 0
            ;;
        *)
            echo "Unknown option: $1" >&2
            usage >&2
            exit 1
            ;;
    esac
done

echo "=== Catalyst Diagnostics ==="
echo "$(date)"
[ "$STRICT_MODE" = true ] && echo "Mode: STRICT (will exit non-zero on failures)"
[ "$VERBOSE" = true ] && echo "Mode: VERBOSE"
echo

echo "📁 DIRECTORY STRUCTURE"
echo "====================="
check_directory "$BUILDER_ROOT" "Builder root"
check_directory "$BUILDER_ROOT/tools" "Tools directory" 
check_directory "$BUILDER_ROOT/registry" "Registry/logs directory"
check_directory "$BUILDER_ROOT/capsules" "Capsules directory"
check_directory "$BUILDER_ROOT/recipes" "Recipes directory"
check_directory "$BUILDER_ROOT/sandbox" "Sandbox directory"

INBOX_PATH="$HOME/Library/Mobile Documents/com~apple~CloudDocs/Builder Inbox"
if check_directory "$INBOX_PATH" "iCloud Builder Inbox"; then
    check_directory "$INBOX_PATH/Processed" "Inbox processed folder"
fi

echo
echo "📄 CORE FILES"
echo "============="
check_file_permissions "$BUILDER_ROOT/tools/inbox_sync.py" "readable" "Inbox sync script"
check_file_permissions "$BUILDER_ROOT/tools/trigger_planner.sh" "executable" "Planner trigger script"
check_file_permissions "$BUILDER_ROOT/tools/on_capsule_created.sh" "executable" "Capsule hook script"
check_file_permissions "$BUILDER_ROOT/tools/planner_config.json" "readable" "Planner configuration"
check_file_permissions "$BUILDER_ROOT/README.md" "readable" "Main documentation"
check_file_permissions "$BUILDER_ROOT/README-Secrets.md" "readable" "Secrets documentation"

echo
echo "🚀 LAUNCH AGENT"
echo "==============="
PLIST_PATH="$HOME/Library/LaunchAgents/com.ty.builder.inbox-sync.plist"
if check_file_permissions "$PLIST_PATH" "readable" "Launch agent plist"; then
    if plutil -lint "$PLIST_PATH" >/dev/null 2>&1; then
        log_check "PASS" "Plist syntax valid"
        
        # Check Python path in plist
        PYTHON_PATH=$(plutil -extract ProgramArguments.0 raw "$PLIST_PATH" 2>/dev/null || echo "")
        if [ -n "$PYTHON_PATH" ] && [ -x "$PYTHON_PATH" ]; then
            log_check "PASS" "Python interpreter accessible ($PYTHON_PATH)"
        else
            log_check "WARN" "Python interpreter path issue ($PYTHON_PATH)"
        fi
        
        # Check if agent is loaded
        if launchctl list | grep -q "com.ty.builder.inbox-sync"; then
            log_check "PASS" "Launch agent loaded"
        else
            log_check "WARN" "Launch agent not loaded"
        fi
    else
        log_check "FAIL" "Plist syntax invalid"
    fi
fi

echo
echo "🐍 PYTHON ENVIRONMENT"  
echo "===================="
if command -v python3 >/dev/null 2>&1; then
    log_check "PASS" "Python3 available ($(command -v python3))"
    
    # Test python compilation
    if python3 -m py_compile "$BUILDER_ROOT/tools/inbox_sync.py" 2>/dev/null; then
        log_check "PASS" "inbox_sync.py compiles without errors"
    else
        log_check "FAIL" "inbox_sync.py has syntax errors"
    fi
    
    # Check required modules
    for module in json yaml subprocess hashlib pathlib; do
        if python3 -c "import $module" 2>/dev/null; then
            log_check "INFO" "Python module $module available"
        else
            log_check "WARN" "Python module $module missing"
        fi
    done
else
    log_check "FAIL" "Python3 not found in PATH"
fi

echo
echo "🔧 SHELL SCRIPTS"
echo "==============="
if command -v shellcheck >/dev/null 2>&1; then
    for script in "$BUILDER_ROOT/tools/trigger_planner.sh" "$BUILDER_ROOT/tools/on_capsule_created.sh"; do
        if [ -f "$script" ]; then
            if shellcheck "$script" >/dev/null 2>&1; then
                log_check "PASS" "$(basename "$script") passes shellcheck"
            else
                log_check "WARN" "$(basename "$script") has shellcheck warnings"
                [ "$VERBOSE" = true ] && shellcheck "$script" 2>&1 | head -10
            fi
        fi
    done
else
    log_check "INFO" "shellcheck not available (install with: brew install shellcheck)"
fi

echo
echo "⚙️  CONFIGURATION"
echo "================"
CONFIG_FILE="$BUILDER_ROOT/tools/planner_config.json"
if [ -f "$CONFIG_FILE" ]; then
    if jq . "$CONFIG_FILE" >/dev/null 2>&1; then
        log_check "PASS" "planner_config.json is valid JSON"
        
        # Check required keys
        for key in cmd args timeout_sec fallback_to_marker; do
            if jq -e "has(\"$key\")" "$CONFIG_FILE" >/dev/null 2>&1; then
                log_check "INFO" "Config has required key: $key"
            else
                log_check "WARN" "Config missing key: $key"
            fi
        done
        
        # Check if command exists
        CMD=$(jq -r '.cmd' "$CONFIG_FILE")
        if [ "$CMD" != "null" ] && command -v "$CMD" >/dev/null 2>&1; then
            log_check "PASS" "Planner command accessible ($CMD)"
        else
            log_check "WARN" "Planner command not found ($CMD)"
        fi
    else
        log_check "FAIL" "planner_config.json has invalid JSON syntax"
    fi
fi

echo
echo "📊 LOGS & REGISTRY"
echo "=================="
for log_file in "inbox-sync.log" "planner-hooks.log"; do
    log_path="$BUILDER_ROOT/registry/$log_file"
    if [ -f "$log_path" ]; then
        size=$(stat -f%z "$log_path" 2>/dev/null || echo "0")
        size_mb=$((size / 1024 / 1024))
        
        if [ "$size_mb" -gt 10 ]; then
            log_check "WARN" "$log_file is large (${size_mb}MB) - consider rotation"
        else
            log_check "PASS" "$log_file present (${size_mb}MB)"
        fi
        
        # Check recent activity
        if [ "$(find "$log_path" -mtime -1 2>/dev/null)" ]; then
            log_check "INFO" "$log_file has recent activity"
        else
            log_check "INFO" "$log_file no recent activity (>24h)"
        fi
    else
        log_check "INFO" "$log_file not present (will be created on first use)"
    fi
done

# Capsule-specific diagnostics
if [ -n "$TEST_CAPSULE" ]; then
    echo
    echo "🧪 CAPSULE DIAGNOSTICS"
    echo "======================"
    
    if [ -d "$TEST_CAPSULE" ]; then
        CAPSULE_NAME=$(basename "$TEST_CAPSULE")
        log_check "PASS" "Test capsule exists ($CAPSULE_NAME)"
        
        # Check spec structure
        if [ -f "$TEST_CAPSULE/spec/requirements.yaml" ]; then
            log_check "PASS" "requirements.yaml present"
            
            # Test config merging
            echo
            echo "📋 MERGED CONFIGURATION FOR $CAPSULE_NAME:"
            if merge_capsule_config "$TEST_CAPSULE"; then
                log_check "PASS" "Config merging successful"
            else
                log_check "FAIL" "Config merging failed"
            fi
        else
            log_check "WARN" "requirements.yaml missing"
        fi
        
        # Check for prompt files
        prompt_count=0
        for role in planner executor tester; do
            for location in ops spec; do
                if [ -f "$TEST_CAPSULE/$location/agent-$role.md" ]; then
                    log_check "INFO" "Found $role prompt: $location/agent-$role.md"
                    ((prompt_count++))
                fi
            done
        done
        [ "$prompt_count" -gt 0 ] && log_check "PASS" "Found $prompt_count prompt file(s)"
        
        # Check for overrides
        if [ -f "$TEST_CAPSULE/ops/planner.json" ]; then
            if jq . "$TEST_CAPSULE/ops/planner.json" >/dev/null 2>&1; then
                log_check "PASS" "Capsule config override present and valid"
            else
                log_check "WARN" "Capsule config override has invalid JSON"
            fi
        fi
        
        # Check secrets
        if [ -f "$TEST_CAPSULE/.env.example" ]; then
            log_check "PASS" "Secrets template present"
        fi
        if [ -f "$TEST_CAPSULE/.env" ]; then
            log_check "INFO" "Secrets file present"
        fi
    else
        log_check "FAIL" "Test capsule not found ($TEST_CAPSULE)"
    fi
fi

echo
echo "📈 SUMMARY"
echo "========="
echo "Warnings: $WARNINGS"
echo "Failures: $FAILURES"

if [ "$FAILURES" -gt 0 ]; then
    echo "❌ SYSTEM HAS CRITICAL ISSUES"
    if [ "$STRICT_MODE" = true ]; then
        exit 1
    fi
elif [ "$WARNINGS" -gt 0 ]; then
    echo "⚠️  SYSTEM HAS MINOR ISSUES"
    if [ "$STRICT_MODE" = true ]; then
        exit 1
    fi
else
    echo "✅ SYSTEM HEALTHY"
fi

echo
echo "Next steps:"
[ "$FAILURES" -gt 0 ] && echo "• Fix critical failures above"
[ "$WARNINGS" -gt 0 ] && echo "• Address warnings for optimal operation"
echo "• Run 'test_builder.sh' for functional testing"
echo "• Check logs: tail -f ~/Catalyst/registry/*.log"

exit 0




