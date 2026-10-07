#!/bin/bash
# Shared-core drift detection — checks if agent files have changed since last sync.
# Exit codes: 0 = in sync, 1 = drift detected, 2 = no manifest (needs initial generate)

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SHARED_CORE_DIR="$(dirname "$SCRIPT_DIR")"
BUN="${HOME}/.bun/bin/bun"

if [ ! -f "$BUN" ]; then
  echo "bun not found at $BUN"
  exit 2
fi

if [ ! -f "$SHARED_CORE_DIR/output/sync-manifest.json" ]; then
  echo "No sync manifest found. Run: $BUN run $SHARED_CORE_DIR/src/cli.ts generate"
  exit 2
fi

# Run the check-drift CLI command and capture output
OUTPUT=$("$BUN" run "$SHARED_CORE_DIR/src/cli.ts" check-drift 2>&1)
EXIT_CODE=$?

echo "$OUTPUT"

# If bun/tsc crashed, report infrastructure error
if [ $EXIT_CODE -ne 0 ]; then
  echo "Error running check-drift (exit code: $EXIT_CODE)"
  exit 2
fi

# Check if drift was detected (look for warning indicators)
if echo "$OUTPUT" | grep -q "agents have changed\|new agents\|removed agents"; then
  exit 1
fi

exit 0
