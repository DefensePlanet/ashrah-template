#!/bin/bash
# ${BUILDER_ROOT:-{{CATALYST_ROOT}}}/tools/weekly_system_audit.sh
# Weekly Builder system comprehensive audit with System Ops Advisor integration

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

# Environment setup with validation
readonly HOME="{{HOME_DIR}}"
readonly BASE="${BUILDER_ROOT:-{{CATALYST_ROOT}}}"
readonly REGISTRY="$BASE/registry"
readonly WEEKLY_DIR="$REGISTRY/weekly"
readonly TOOLS_DIR="$BASE/tools"

# Verify directories exist
if [[ ! -d "$BASE" ]] || [[ ! -d "$REGISTRY" ]] || [[ ! -d "$TOOLS_DIR" ]]; then
    echo "ERROR: Required Builder directories not found" >&2
    exit 1
fi

# Timestamps
ISO_TS=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
DATE_STAMP=$(date +"%Y%m%d")
WEEK_STAMP=$(date +"%Y_w%U")  # Year_weekNN format
STATUS_FILE="$WEEKLY_DIR/weekly_status-$WEEK_STAMP.json"
LOG_FILE="$WEEKLY_DIR/weekly_audit.log"

# Ensure directories exist
mkdir -p "$WEEKLY_DIR"

# Logging helper
log_step() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" >> "$LOG_FILE"
    echo "$*"
}

log_step "=== Starting Builder weekly comprehensive audit ==="

# Initialize status tracking
OVERALL_RC=0
NOTES="weekly comprehensive analysis completed"
ERROR_SUMMARY=""

# STEP 1: System Integration Evidence Collection
log_step "STEP 1: Running comprehensive system integration"
INTEGRATION_RC=0

if [[ -f "$TOOLS_DIR/system_ops_integration.py" ]]; then
    log_step "   Running system ops integration: python3 $TOOLS_DIR/system_ops_integration.py --days 7"
    if python3 "$TOOLS_DIR/system_ops_integration.py" --days 7 >> "$LOG_FILE" 2>&1; then
        log_step "   ✅ System ops integration completed successfully"
    else
        INTEGRATION_RC=$?
        log_step "   ❌ System ops integration failed (exit $INTEGRATION_RC)"
        OVERALL_RC=$INTEGRATION_RC
        ERROR_SUMMARY="System ops integration failed"
    fi
else
    log_step "   ⚠️ System ops integration script not found"
    INTEGRATION_RC=1
    ERROR_SUMMARY="System ops integration script missing"
fi

# STEP 2: Complete Dependency Graph Rebuild
log_step "STEP 2: Rebuilding complete dependency graph"
DEPENDENCY_RC=0

if [[ -f "$TOOLS_DIR/dependency_mapper.py" ]]; then
    log_step "   Running dependency mapper: python3 $TOOLS_DIR/dependency_mapper.py"
    if python3 "$TOOLS_DIR/dependency_mapper.py" >> "$LOG_FILE" 2>&1; then
        log_step "   ✅ Dependency graph rebuilt successfully"
    else
        DEPENDENCY_RC=$?
        log_step "   ❌ Dependency graph rebuild failed (exit $DEPENDENCY_RC)"
        if [[ $OVERALL_RC -eq 0 ]]; then
            OVERALL_RC=$DEPENDENCY_RC
            ERROR_SUMMARY="Dependency graph rebuild failed"
        fi
    fi
else
    log_step "   ⚠️ Dependency mapper script not found"
fi

# STEP 3: RAG System Health Check and Optimization
log_step "STEP 3: Checking RAG system health and performance"
RAG_RC=0

# Check if RAG service is running and healthy
if curl -s "http://localhost:8000/health" > /dev/null 2>&1; then
    log_step "   ✅ RAG service is responsive"
    
    # Run performance check and optimization
    if [[ -f "$BASE/global/rag/service/ingest_internal_metrics.py" ]]; then
        log_step "   Running comprehensive internal metrics ingestion: python3 $BASE/global/rag/service/ingest_internal_metrics.py --hours 168"
        if python3 "$BASE/global/rag/service/ingest_internal_metrics.py" --hours 168 >> "$LOG_FILE" 2>&1; then
            log_step "   ✅ Weekly internal metrics ingested successfully"
        else
            RAG_RC=$?
            log_step "   ❌ Internal metrics ingestion failed (exit $RAG_RC)"
        fi
    fi
else
    log_step "   ⚠️ RAG service not responsive at http://localhost:8000"
    RAG_RC=1
fi

# STEP 4: Capsule Health and Performance Analysis
log_step "STEP 4: Analyzing capsule health and performance trends"
CAPSULE_RC=0

# Run autopsy on all capsules with recent activity
if [[ -f "$TOOLS_DIR/capsule_autopsy.py" ]]; then
    log_step "   Running comprehensive capsule analysis"
    
    # Find capsules with activity in the last week
    WEEK_AGO=$(date -d '7 days ago' '+%s')
    ACTIVE_CAPSULES=0
    
    if [[ -d "$BASE/capsules" ]]; then
        for capsule_dir in "$BASE/capsules"/*; do
            if [[ -d "$capsule_dir" ]] && [[ ! "$(basename "$capsule_dir")" =~ ^[.] ]]; then
                capsule_name=$(basename "$capsule_dir")
                runs_dir="$capsule_dir/runs"
                
                if [[ -d "$runs_dir" ]]; then
                    # Check for recent activity
                    recent_activity=false
                    for run_dir in "$runs_dir"/*; do
                        if [[ -d "$run_dir" ]]; then
                            manifest_file="$run_dir/manifest.json"
                            if [[ -f "$manifest_file" ]]; then
                                # Get the modification time of the manifest
                                if [[ $(stat -f "%m" "$manifest_file" 2>/dev/null || stat -c "%Y" "$manifest_file" 2>/dev/null || echo "0") -gt $WEEK_AGO ]]; then
                                    recent_activity=true
                                    break
                                fi
                            fi
                        fi
                    done
                    
                    if [[ "$recent_activity" = true ]]; then
                        log_step "     Analyzing capsule: $capsule_name"
                        python3 "$TOOLS_DIR/capsule_autopsy.py" "$capsule_name" >> "$LOG_FILE" 2>&1 || true
                        ((ACTIVE_CAPSULES++))
                    fi
                fi
            fi
        done
    fi
    
    log_step "   ✅ Analyzed $ACTIVE_CAPSULES active capsules"
else
    log_step "   ⚠️ Capsule autopsy script not found"
fi

# STEP 5: System Health Summary Generation
log_step "STEP 5: Generating comprehensive system health report"

# Calculate overall health score
HEALTH_SCORE=100
if [[ $INTEGRATION_RC -ne 0 ]]; then
    ((HEALTH_SCORE -= 30))
fi
if [[ $DEPENDENCY_RC -ne 0 ]]; then
    ((HEALTH_SCORE -= 20))
fi
if [[ $RAG_RC -ne 0 ]]; then
    ((HEALTH_SCORE -= 15))
fi
if [[ $CAPSULE_RC -ne 0 ]]; then
    ((HEALTH_SCORE -= 10))
fi

STATUS="HEALTHY"
if [[ $HEALTH_SCORE -lt 80 ]]; then
    STATUS="DEGRADED"
fi
if [[ $HEALTH_SCORE -lt 60 ]]; then
    STATUS="UNHEALTHY"
fi

# Write comprehensive status JSON
cat > "$STATUS_FILE" <<EOF
{
  "ts": "$ISO_TS",
  "week": "$WEEK_STAMP",
  "overall_status": "$STATUS",
  "health_score": $HEALTH_SCORE,
  "system_integration_rc": $INTEGRATION_RC,
  "dependency_analysis_rc": $DEPENDENCY_RC,
  "rag_system_rc": $RAG_RC,
  "capsule_analysis_rc": $CAPSULE_RC,
  "active_capsules_analyzed": ${ACTIVE_CAPSULES:-0},
  "notes": "$NOTES",
  "error_summary": "$ERROR_SUMMARY",
  "reports": {
    "weekly_evidence": "$BASE/global/weekly_evidence_*.json",
    "dependency_graph": "$BASE/global/dependency-graph.json",
    "dependency_reports": "$BASE/docs/dependency-reports/",
    "mermaid_diagram": "$BASE/docs/dependency-graph.md"
  }
}
EOF

log_step "   Weekly status recorded: $STATUS (health: $HEALTH_SCORE%)"

# STEP 6: Cleanup and Maintenance
log_step "STEP 6: Performing weekly cleanup and maintenance"

# Clean up old weekly reports (keep last 4 weeks)
find "$WEEKLY_DIR" -name "weekly_status-*.json" -mtime +28 -delete 2>/dev/null || true
find "$BASE/global" -name "weekly_evidence_*.json" -mtime +28 -delete 2>/dev/null || true

# Rotate logs (keep last 1000 lines)
if [[ -f "$LOG_FILE" ]] && [[ $(wc -l < "$LOG_FILE") -gt 1000 ]]; then
    tail -1000 "$LOG_FILE" > "$LOG_FILE.tmp" && mv "$LOG_FILE.tmp" "$LOG_FILE"
fi

log_step "   ✅ Cleanup completed"

# STEP 7: Notification and Summary
log_step "STEP 7: Sending weekly summary notification"

# Create summary message
SUMMARY_MESSAGE="Weekly Builder audit completed"
if [[ "$STATUS" = "HEALTHY" ]]; then
    SUMMARY_MESSAGE="$SUMMARY_MESSAGE ✅ System health: $HEALTH_SCORE%"
    NOTIF_SOUND="Glass"
elif [[ "$STATUS" = "DEGRADED" ]]; then
    SUMMARY_MESSAGE="$SUMMARY_MESSAGE ⚠️ System degraded: $HEALTH_SCORE%"
    NOTIF_SOUND="Tink"
else
    SUMMARY_MESSAGE="$SUMMARY_MESSAGE ❌ System unhealthy: $HEALTH_SCORE%"
    NOTIF_SOUND="Basso"
fi

# macOS notification
if osascript -e "display notification \"$SUMMARY_MESSAGE\" with title \"Builder Weekly Audit\" sound name \"$NOTIF_SOUND\"" 2>/dev/null; then
    log_step "   ✅ Desktop notification sent"
else
    log_step "   ⚠️ Desktop notification failed"
fi

# Log final event if available
if [[ -f "$TOOLS_DIR/log_event.py" ]]; then
    EVENT_LEVEL="INFO"
    if [[ "$STATUS" != "HEALTHY" ]]; then
        EVENT_LEVEL="WARNING"
    fi
    
    python3 "$TOOLS_DIR/log_event.py" \
        --stage weekly_audit \
        --level "$EVENT_LEVEL" \
        --message "Weekly comprehensive audit completed: $STATUS ($HEALTH_SCORE%)" \
        --data "{\"health_score\": $HEALTH_SCORE, \"status\": \"$STATUS\", \"active_capsules\": ${ACTIVE_CAPSULES:-0}}" \
        >> "$LOG_FILE" 2>&1 || true
fi

log_step "=== Weekly comprehensive audit completed ==="
log_step "   OVERALL STATUS: $STATUS"
log_step "   HEALTH SCORE: $HEALTH_SCORE%"
log_step "   STATUS_FILE: $STATUS_FILE"

# Print summary to stdout for cron/automation
echo ""
echo "🔄 Builder Weekly Comprehensive Audit Summary"
echo "=============================================="
echo "Status: $STATUS ($HEALTH_SCORE% health)"
echo "Integration: $([ $INTEGRATION_RC -eq 0 ] && echo "✅" || echo "❌")"
echo "Dependencies: $([ $DEPENDENCY_RC -eq 0 ] && echo "✅" || echo "❌")"
echo "RAG System: $([ $RAG_RC -eq 0 ] && echo "✅" || echo "❌")"
echo "Capsule Analysis: $([ $CAPSULE_RC -eq 0 ] && echo "✅" || echo "❌")"
echo "Active Capsules: ${ACTIVE_CAPSULES:-0}"
echo ""

# Exit with appropriate code
if [[ "$STATUS" = "HEALTHY" ]]; then
    exit 0
elif [[ "$STATUS" = "DEGRADED" ]]; then
    exit 1
else
    exit 2
fi

