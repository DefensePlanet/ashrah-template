#!/usr/bin/env bash
# GitNexus re-index wrapper for Catalyst
# Usage: tools/gitnexus-reindex.sh [--force]
#
# Why this wrapper exists:
# `gitnexus analyze` always regenerates AGENTS.md and expands the
# <!-- gitnexus:start/end --> block in CLAUDE.md to ~60 lines.
# Catalyst keeps a compact 8-line version instead, and AGENTS.md
# is not used. This wrapper runs the index then restores the files.

set -euo pipefail
cd "$(git rev-parse --show-toplevel)"

# Verify gitnexus markers exist before proceeding
if ! grep -q '<!-- gitnexus:start -->' CLAUDE.md || ! grep -q '<!-- gitnexus:end -->' CLAUDE.md; then
    echo "ERROR: gitnexus start/end markers not found in CLAUDE.md — aborting to prevent bloat" >&2
    exit 1
fi

# Save compact CLAUDE.md gitnexus block
COMPACT_BLOCK=$(sed -n '/<!-- gitnexus:start -->/,/<!-- gitnexus:end -->/p' CLAUDE.md)

# Run gitnexus analyze (pass through any flags like --force)
gitnexus analyze . "$@"

# Restore compact CLAUDE.md block (gitnexus re-expands it)
# Pass via env var to avoid shell injection in python -c string
if [ -n "$COMPACT_BLOCK" ]; then
    COMPACT_BLOCK="$COMPACT_BLOCK" python3 -c "
import re, os
with open('CLAUDE.md', 'r') as f:
    content = f.read()
compact = os.environ['COMPACT_BLOCK']
content = re.sub(
    r'<!-- gitnexus:start -->.*?<!-- gitnexus:end -->',
    lambda m: compact,
    content,
    flags=re.DOTALL
)
with open('CLAUDE.md', 'w') as f:
    f.write(content)
"
    echo "CLAUDE.md: compact GitNexus block restored"
fi

# Remove AGENTS.md (GitNexus creates it, Catalyst doesn't use it)
if [ -f AGENTS.md ]; then
    rm AGENTS.md
    echo "AGENTS.md: removed (not used by Catalyst)"
fi

echo "GitNexus re-index complete"
