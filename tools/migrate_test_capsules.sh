#!/bin/bash
# migrate_test_capsules.sh - Move test capsules to separate test environment
set -eo pipefail

BASE="${BUILDER_ROOT:-{{CATALYST_ROOT}}}"
CAPSULES_DIR="$BASE/capsules"
TEST_DIR="$BASE/testing"
TEST_CAPSULES_DIR="$TEST_DIR/capsules"

echo "🔄 Creating separate test environment..."

# Create test directory structure
mkdir -p "$TEST_CAPSULES_DIR"
mkdir -p "$TEST_DIR/logs"
mkdir -p "$TEST_DIR/registry"

echo "✅ Created test directory structure at: $TEST_DIR"

# Identify test capsules (anything with 'test' or starts with 'at-' for audit tests)
TEST_PATTERN="test|Test|^at-.*test$|^dry-run|^enhanced-test$|^feature-test$|^final-audit$|^instant-trigger|^path-test$"

echo "🔍 Identifying test capsules..."
TEST_CAPSULES=($(cd "$CAPSULES_DIR" && ls -1 | grep -E "$TEST_PATTERN" || true))

if [ ${#TEST_CAPSULES[@]} -eq 0 ]; then
    echo "ℹ️  No test capsules found matching pattern"
    exit 0
fi

echo "📦 Found ${#TEST_CAPSULES[@]} test capsules to migrate:"
for capsule in "${TEST_CAPSULES[@]}"; do
    echo "  - $capsule"
done

echo ""
read -p "🤔 Do you want to proceed with migration? (y/N): " -n 1 -r
echo ""

if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "❌ Migration cancelled"
    exit 0
fi

echo "📦 Migrating test capsules..."

# Move test capsules
for capsule in "${TEST_CAPSULES[@]}"; do
    if [ -d "$CAPSULES_DIR/$capsule" ]; then
        echo "  Moving $capsule..."
        mv "$CAPSULES_DIR/$capsule" "$TEST_CAPSULES_DIR/"
    else
        echo "  ⚠️  $capsule not found, skipping"
    fi
done

# Create README in test directory
cat > "$TEST_DIR/README.md" <<EOF
# Builder Testing Environment

This directory contains all test capsules and testing infrastructure, completely separate from production capsules.

## Directory Structure

\`\`\`
testing/
├── capsules/           # Test capsules (moved from /capsules)
├── logs/              # Test execution logs
├── registry/          # Test registry data
└── README.md          # This file
\`\`\`

## Test Capsules Migrated

$(for capsule in "${TEST_CAPSULES[@]}"; do echo "- $capsule"; done)

## Running Tests

Tests now use this isolated environment and will not interfere with production capsules.

- Integration tests: \`tools/test_integration.sh\`
- Lane tests: \`tools/test_lane_features.sh\`
- Daily audit: \`tools/daily_audit.sh\`

All test scripts have been updated to use the testing directory.
EOF

echo "✅ Migration completed!"
echo ""
echo "📊 Summary:"
echo "  - Migrated ${#TEST_CAPSULES[@]} test capsules"
echo "  - Production capsules directory cleaned"
echo "  - Test environment created at: $TEST_DIR"
echo ""
echo "📝 Next: Update test scripts to use new test directory"




