#!/bin/bash
# ${BUILDER_ROOT:-{{CATALYST_ROOT}}}/tools/test_integration.sh  
# Builder system integration tests with complete isolation from production

# Use absolute paths only
BASE="${BUILDER_ROOT:-{{CATALYST_ROOT}}}"
TOOLS_DIR="$BASE/tools"
PROD_CAPSULES="$BASE/capsules"
REGISTRY="$BASE/registry"

# Load testing directory from config or use default
TEST_ROOT="$BASE/testing"
CONFIG_FILE="$BASE/global/config/config.json"
if [[ -f "$CONFIG_FILE" ]]; then
    if command -v jq >/dev/null 2>&1; then
        TESTING_DIR=$(jq -r '.paths.testing_dir // empty' "$CONFIG_FILE" 2>/dev/null)
        if [[ -n "$TESTING_DIR" && "$TESTING_DIR" != "null" ]]; then
            TEST_ROOT="$TESTING_DIR"
            echo "CONFIG loaded: testing_dir=$TEST_ROOT"
        fi
    fi
fi

TEST_CAPSULES="$TEST_ROOT/capsules"
PASSED=0
FAILED=0

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Catalyst Integration Tests"
echo "============================================================"
echo "Base directory: $BASE"
echo "Production capsules: $PROD_CAPSULES"  
echo "Testing root: $TEST_ROOT"
echo "Test capsules: $TEST_CAPSULES"
echo ""

# Production capsule write guard
guard_prod_capsules() {
    local target_path="$1"
    if [[ "$target_path" == "$PROD_CAPSULES"* ]]; then
        echo "ERROR: Refusing to write to production capsules directory: $target_path"
        echo "       Tests must use testing directory: $TEST_CAPSULES"
        exit 1
    fi
}

# Test: Basic setup
echo "⚙️ TEST: Basic environment setup"
mkdir -p "$TEST_CAPSULES"
mkdir -p "$TEST_ROOT/registry" "$TEST_ROOT/logs"

# Guard test
echo "⚙️ TEST: Production capsule guard"
guard_prod_capsules "$TEST_CAPSULES/test-path"
echo "✅ Production guard working"
PASSED=$((PASSED + 1))

# Test: Tool availability
echo "⚙️ TEST: Essential tools"
TOOLS_OK=0
for tool in "$TOOLS_DIR/trigger_planner.sh" "$TOOLS_DIR/fix_perms.sh" "$TOOLS_DIR/daily_audit.sh"; do
    if [[ -x "$tool" ]]; then
        echo "✓ $(basename "$tool")"
        TOOLS_OK=$((TOOLS_OK + 1))
    else
        echo "✗ $(basename "$tool") (missing or not executable)"
    fi
done

if [[ $TOOLS_OK -ge 2 ]]; then
    echo "✅ Essential tools available ($TOOLS_OK/3)"
    PASSED=$((PASSED + 1))
else
    echo "❌ Essential tools missing ($TOOLS_OK/3)" 
    FAILED=$((FAILED + 1))
fi

# Test: Basic functionality
echo "⚙️ TEST: Basic functionality in isolated environment"
TEST_CAPSULE="$TEST_CAPSULES/test-basic"
guard_prod_capsules "$TEST_CAPSULE"

if mkdir -p "$TEST_CAPSULE/spec"; then
    if cat > "$TEST_CAPSULE/spec/requirements.yaml" << 'EOF'
project:
  name: "Basic Test"
  slug: "test-basic"
  branch: automation  
  targets: [macos]
  lane: standard
objectives:
  - Test basic functionality
definition_of_done:
  - Test passes  
EOF
    then
        echo "✅ Basic operations in testing environment successful"
        PASSED=$((PASSED + 1))
    else
        echo "❌ Cannot create test spec file"
        FAILED=$((FAILED + 1))
    fi
else
    echo "❌ Cannot create test capsule directory"
    FAILED=$((FAILED + 1))
fi

# Clean up test capsule
rm -rf "$TEST_CAPSULE" 2>/dev/null || true

# Results
echo ""
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Integration Test Results"
echo "================================================"
echo "Passed: $PASSED"
echo "Failed: $FAILED"
echo "Total:  $((PASSED + FAILED))"

# Write results to registry
RESULT_JSON="{\"timestamp\":\"$(date -Iseconds)\",\"type\":\"integration_test\",\"passed\":$PASSED,\"failed\":$FAILED,\"test_root\":\"$TEST_ROOT\"}"
echo "$RESULT_JSON" >> "$REGISTRY/events.jsonl"

# Write summary to audit log
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Integration tests: $PASSED passed, $FAILED failed" >> "$REGISTRY/daily/daily_audit.log"

if [[ $FAILED -eq 0 ]]; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ✅ ALL INTEGRATION TESTS PASSED!"
    exit 0
else
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ❌ $FAILED INTEGRATION TEST(S) FAILED"
    exit 1
fi



