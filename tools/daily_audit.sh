#!/bin/bash
# ${BUILDER_ROOT:-{{CATALYST_ROOT}}}/tools/daily_audit.sh
# Daily Builder system audit: smoke tests + metrics + dashboard + notifications

# Strict error handling and security
set -euo pipefail
IFS=$'\n\t'

# Security: Restrict PATH to known safe directories
export PATH="/usr/bin:/bin:/usr/local/bin"

# Security: Set secure umask
umask 077

# Security: Validate environment
if [[ "${EUID:-$(id -u)}" -eq 0 ]]; then
    echo "ERROR: This script should not be run as root" >&2
    exit 1
fi

# Input validation function
validate_path() {
    local path="$1"
    local description="$2"
    
    # Check path is absolute
    if [[ ! "$path" =~ ^/ ]]; then
        echo "ERROR: $description must be absolute path: $path" >&2
        return 1
    fi
    
    # Check path doesn't contain dangerous characters
    if [[ "$path" =~ [';''\&''\|''\`''\$''\(''\)''><'] ]]; then
        echo "ERROR: $description contains unsafe characters: $path" >&2
        return 1
    fi
    
    # Ensure path is within Builder directory
    if [[ ! "$path" =~ ^${BUILDER_ROOT:-{{CATALYST_ROOT}}} ]]; then
        echo "ERROR: $description outside Builder directory: $path" >&2
        return 1
    fi
    
    return 0
}

# Environment setup with validation
readonly HOME="{{HOME_DIR}}"
readonly BASE="${BUILDER_ROOT:-{{CATALYST_ROOT}}}"

# Validate core directories exist and are secure
validate_path "$BASE" "BASE directory" || exit 1
validate_path "$BASE/registry" "Registry directory" || exit 1
validate_path "$BASE/tools" "Tools directory" || exit 1

# Set validated paths as readonly
readonly REGISTRY="$BASE/registry"
readonly DAILY_DIR="$REGISTRY/daily"
readonly TOOLS_DIR="$BASE/tools"

# Verify directories exist
if [[ ! -d "$BASE" ]] || [[ ! -d "$REGISTRY" ]] || [[ ! -d "$TOOLS_DIR" ]]; then
    echo "ERROR: Required Builder directories not found" >&2
    exit 1
fi

# Secure script execution function
safe_execute() {
    local script_path="$1"
    local description="$2"
    
    # Validate script path
    validate_path "$script_path" "$description script" || return 1
    
    # Verify script exists and is readable
    if [[ ! -f "$script_path" ]]; then
        echo "WARNING: $description script not found: $script_path" >&2
        return 1
    fi
    
    if [[ ! -r "$script_path" ]]; then
        echo "WARNING: $description script not readable: $script_path" >&2
        return 1
    fi
    
    # Execute with timeout and resource limits
    timeout 120s python3 "$script_path" 2>/dev/null || {
        echo "WARNING: $description execution failed or timed out" >&2
        return 1
    }
}

# Refresh Codex context (secured execution)
safe_execute "$TOOLS_DIR/compose_codex_context.py" "Codex context refresh" || true

# Load testing directory from config or use default
TEST_ROOT="$BASE/testing"
CONFIG_FILE="$BASE/global/config/config.json"
if [[ -f "$CONFIG_FILE" ]]; then
    if command -v jq >/dev/null 2>&1; then
        TESTING_DIR=$(jq -r '.paths.testing_dir // empty' "$CONFIG_FILE" 2>/dev/null)
        if [[ -n "$TESTING_DIR" && "$TESTING_DIR" != "null" ]]; then
            TEST_ROOT="$TESTING_DIR"
            echo "CONFIG loaded: testing_dir=$TEST_ROOT" >&2
        fi
    fi
fi

# Timestamps
ISO_TS=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
DATE_STAMP=$(date +"%Y%m%d")
STATUS_FILE="$DAILY_DIR/status-$DATE_STAMP.json"
LOG_FILE="$DAILY_DIR/daily_audit.log"

# Ensure directories exist
mkdir -p "$DAILY_DIR" "$REGISTRY/dashboard"

# Initialize status tracking
SMOKE_RC=0
NOTES="dashboard refreshed"
ERROR_HINT=""

# Logging helper
log_step() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" >> "$LOG_FILE"
    echo "$*"
}

log_step "=== Starting Builder daily audit ==="

# STEP 0: Fix permissions, normalize files, and validate test environment
log_step "STEP 0: Fixing permissions, line endings, and test environment setup"
if [[ -x "$TOOLS_DIR/fix_perms.sh" ]]; then
    "$TOOLS_DIR/fix_perms.sh" >> "$LOG_FILE" 2>&1 || log_step "⚠️ fix_perms.sh had issues"
else
    log_step "⚠️ fix_perms.sh not found, skipping normalization"
fi

# STEP 1: Determine test entrypoint  
log_step "STEP 1: Resolving test entrypoint with absolute paths"
log_step "   Test root: $TEST_ROOT"

TEST_ENTRY=""
TEST_ARGS=""

# Robust test entrypoint resolution with absolute paths
if [[ -x "$TOOLS_DIR/test_integration.sh" ]]; then
    TEST_ENTRY="$TOOLS_DIR/test_integration.sh"
    log_step "✅ Found test_integration.sh"
elif [[ -x "$TOOLS_DIR/test_builder.sh" ]]; then
    TEST_ENTRY="$TOOLS_DIR/test_builder.sh"
    TEST_ARGS="--integration-only"
    log_step "✅ Found test_builder.sh, will use with --integration-only"
else
    log_step "⚠️ No test scripts found (test_integration.sh or test_builder.sh)"
    log_step "   Skipping smoke tests - audit will still refresh dashboard"
    SMOKE_RC=0
    NOTES="no test scripts found, dashboard refreshed"
fi

# STEP 2: Run smoke tests
if [[ -n "$TEST_ENTRY" ]]; then
    log_step "STEP 2: Running smoke tests in isolated environment"
    log_step "   Command: $TEST_ENTRY $TEST_ARGS"
    log_step "   Test capsules: $TEST_ROOT/capsules"
    
    # Create a temp log for this test run
    TEST_LOG="$DAILY_DIR/test_output.tmp"
    
    # Use gtimeout if available, otherwise run without timeout on macOS
    if command -v gtimeout >/dev/null 2>&1; then
        TIMEOUT_CMD="gtimeout 120s"
    elif command -v timeout >/dev/null 2>&1; then
        TIMEOUT_CMD="timeout 120s"
    else
        TIMEOUT_CMD=""
    fi
    
    if [ -n "$TIMEOUT_CMD" ]; then
        TEST_CMD="$TIMEOUT_CMD $TEST_ENTRY $TEST_ARGS"
    else
        TEST_CMD="$TEST_ENTRY $TEST_ARGS"
    fi
    
    if $TEST_CMD >> "$TEST_LOG" 2>&1; then
        SMOKE_RC=0
        log_step "✅ Smoke tests PASSED"
        NOTES="smoke tests passed, dashboard refreshed"
    else
        SMOKE_RC=$?
        log_step "❌ Smoke tests FAILED (exit $SMOKE_RC)"
        
        # Extract first error line for hint
        if [ -f "$TEST_LOG" ]; then
            FIRST_ERROR=$(grep -E "(error|Error|ERROR|fail|Fail|FAIL)" "$TEST_LOG" | head -1 || echo "")
            if [ -n "$FIRST_ERROR" ]; then
                ERROR_HINT="$FIRST_ERROR"
            else
                ERROR_HINT="Test failed with exit $SMOKE_RC"
            fi
        else
            ERROR_HINT="Test command failed with exit $SMOKE_RC"
        fi
        
        NOTES="smoke tests failed"
    fi
    
    # Append test output to main log and cleanup
    if [ -f "$TEST_LOG" ]; then
        echo "--- Test Output ---" >> "$LOG_FILE"
        cat "$TEST_LOG" >> "$LOG_FILE"
        echo "--- End Test Output ---" >> "$LOG_FILE"
        rm -f "$TEST_LOG"
    fi
else
    log_step "STEP 2: Skipping smoke tests (no test entrypoint found)"
fi

# STEP 3: Refresh metrics and advanced system analysis
log_step "STEP 3: Refreshing metrics and advanced system analysis"

# Metrics rollup
if [[ -f "$TOOLS_DIR/metrics_rollup.py" ]]; then
    log_step "   Running metrics rollup: python3 $TOOLS_DIR/metrics_rollup.py"
    python3 "$TOOLS_DIR/metrics_rollup.py" >> "$LOG_FILE" 2>&1 || log_step "⚠️ Metrics rollup had issues"
else
    log_step "   Metrics rollup not found: $TOOLS_DIR/metrics_rollup.py"
fi

# Dependency monitoring (daily)
if [[ -f "$TOOLS_DIR/daily_dependency_check.py" ]]; then
    log_step "   Running dependency check: python3 $TOOLS_DIR/daily_dependency_check.py"
    python3 "$TOOLS_DIR/daily_dependency_check.py" --quiet >> "$LOG_FILE" 2>&1 || log_step "⚠️ Dependency check had issues"
else
    log_step "   Dependency check not found: $TOOLS_DIR/daily_dependency_check.py"
fi

# Internal metrics ingestion for Scout opportunities  
if [[ -f "$BASE/global/rag/service/ingest_internal_metrics.py" ]]; then
    log_step "   Running internal metrics ingestion: python3 $BASE/global/rag/service/ingest_internal_metrics.py"
    python3 "$BASE/global/rag/service/ingest_internal_metrics.py" --hours 24 >> "$LOG_FILE" 2>&1 || log_step "⚠️ Internal metrics ingestion had issues"
else
    log_step "   Internal metrics ingestion not found: $BASE/global/rag/service/ingest_internal_metrics.py"
fi

# Automatic autopsy for failed runs (if any recent failures detected)
if [[ -f "$TOOLS_DIR/post_run_hook.py" ]] && [[ $SMOKE_RC -ne 0 ]]; then
    log_step "   Triggering autopsy for recent failures: python3 $TOOLS_DIR/post_run_hook.py"
    # Find recent failed capsule runs and trigger autopsy
    find "$BASE/capsules" -name "manifest.json" -newer "$DAILY_DIR/status-$(date -d 'yesterday' '+%Y%m%d').json" 2>/dev/null | while read manifest; do
        if [[ -f "$manifest" ]]; then
            capsule_name=$(basename "$(dirname "$(dirname "$manifest")")")
            run_id=$(basename "$(dirname "$manifest")")
            # Check if run failed
            if jq -e '.success == false' "$manifest" >/dev/null 2>&1; then
                python3 "$TOOLS_DIR/post_run_hook.py" "$capsule_name" --run-id "$run_id" >> "$LOG_FILE" 2>&1 || true
            fi
        fi
    done
fi

# Dashboard rebuild  
if [[ -f "$TOOLS_DIR/build_dashboard.py" ]]; then
    log_step "   Building dashboard: python3 $TOOLS_DIR/build_dashboard.py"
    python3 "$TOOLS_DIR/build_dashboard.py" >> "$LOG_FILE" 2>&1 || log_step "⚠️ Dashboard build had issues"
elif [[ -x "$TOOLS_DIR/refresh_dashboard.sh" ]]; then
    log_step "   Refreshing dashboard: $TOOLS_DIR/refresh_dashboard.sh"
    "$TOOLS_DIR/refresh_dashboard.sh" >> "$LOG_FILE" 2>&1 || log_step "⚠️ Dashboard refresh had issues"
else
    log_step "   No dashboard tools found"
fi

# STEP 4: Record status
log_step "STEP 4: Recording audit status"

STATUS="PASS"
if [ $SMOKE_RC -ne 0 ]; then
    STATUS="FAIL"
fi

# Write status JSON with error hint
if [ -n "$ERROR_HINT" ]; then
    cat > "$STATUS_FILE" <<EOF
{
  "ts": "$ISO_TS",
  "status": "$STATUS",
  "smoke_exit": $SMOKE_RC,
  "notes": "$NOTES",
  "dashboard": "$REGISTRY/dashboard/index.html",
  "error_hint": "$ERROR_HINT"
}
EOF
else
    cat > "$STATUS_FILE" <<EOF
{
  "ts": "$ISO_TS",
  "status": "$STATUS",
  "smoke_exit": $SMOKE_RC,
  "notes": "$NOTES",
  "dashboard": "$REGISTRY/dashboard/index.html"
}
EOF
fi

log_step "   Status recorded: $STATUS (exit: $SMOKE_RC)"

# Log event if available
if [[ -f "$TOOLS_DIR/log_event.py" ]]; then
    if [[ "$STATUS" = "PASS" ]]; then
        python3 "$TOOLS_DIR/log_event.py" --stage daily_audit --level INFO --message "Daily audit completed successfully" >> "$LOG_FILE" 2>&1 || true
    else
        python3 "$TOOLS_DIR/log_event.py" --stage daily_audit --level ERROR --message "Daily audit failed: $NOTES" >> "$LOG_FILE" 2>&1 || true
    fi
fi

# STEP 5: Desktop notification
log_step "STEP 5: Sending desktop notification"

# macOS notification via osascript
if [[ "$STATUS" = "PASS" ]]; then
    NOTIF_BODY="Daily audit completed successfully ✅ Test root: $TEST_ROOT"
    NOTIF_SOUND="Glass"
else
    NOTIF_BODY="Daily audit failed ❌ Check logs for details"
    NOTIF_SOUND="Basso"
fi

# Primary notification
if osascript -e "display notification \"$NOTIF_BODY\" with title \"Builder Daily Audit\" sound name \"$NOTIF_SOUND\"" 2>/dev/null; then
    log_step "   ✅ Desktop notification sent"
else
    log_step "   ⚠️ Desktop notification failed"
fi

# Optional terminal-notifier backup
if command -v terminal-notifier >/dev/null 2>&1; then
    terminal-notifier -title "Builder Daily Audit" -message "$NOTIF_BODY" -sound "$NOTIF_SOUND" 2>/dev/null || \
        log_step "   ⚠️ terminal-notifier backup failed"
fi

# Keep log manageable - last 200 lines
tail -200 "$LOG_FILE" > "$LOG_FILE.tmp" && mv "$LOG_FILE.tmp" "$LOG_FILE"

log_step "=== Daily audit completed ==="
log_step "   STATUS: $STATUS"
log_step "   SMOKE_RC: $SMOKE_RC" 
log_step "   DASHBOARD: $REGISTRY/dashboard/index.html"
log_step "   STATUS_FILE: $STATUS_FILE"

# Exit with smoke test result for LaunchAgent logging
exit $SMOKE_RC




