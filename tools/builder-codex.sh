#!/usr/bin/env bash
set -euo pipefail

# Minimal Codex launcher for Catalyst
# Reads current context directly from source files at launch.

ROOT_DIR="${BUILDER_ROOT:-$(cd "$(dirname "$0")/.." && pwd)}"

# Refresh Codex context bundle before launching
python3 "$ROOT_DIR/tools/compose_codex_context.py" >/dev/null 2>&1 || true

prompt() {
  local codex_context triggers_output
  codex_context="$(python3 "$ROOT_DIR/tools/load_codex_context.py" --core)"
  if [[ -n "${CODEX_CONTEXT_TRIGGERS:-}" ]]; then
    triggers_output="$(python3 "$ROOT_DIR/tools/load_codex_context.py" --triggers "${CODEX_CONTEXT_TRIGGERS}")"
  fi

  echo "# Catalyst – Codex Warmup"
  echo "You are Codex operating inside $ROOT_DIR."
  echo
  echo "## Codex Core Context"
  echo "${codex_context}"

  if [[ -n "${triggers_output:-}" ]]; then
    echo
    echo "## Dynamic Context (triggered)"
    echo "${triggers_output}"
  fi

  if [[ -f "$ROOT_DIR/PROJECT_COMPASS_Builder_System.md" ]]; then
    echo
    echo "## Project Compass (Authoritative)"
    cat "$ROOT_DIR/PROJECT_COMPASS_Builder_System.md"
  fi

  if [[ -f "$HOME/.codex/context/builder_context.md" ]]; then
    echo
    echo "## Latest Codex Context Bundle"
    cat "$HOME/.codex/context/builder_context.md"
  fi
}

PROMPT_CONTENT="$(prompt)"

# Ensure Codex runs with a safe default heap unless caller overrides NODE_OPTIONS.
if [[ -z "${NODE_OPTIONS:-}" ]]; then
  export NODE_OPTIONS="--max-old-space-size=8192"
fi

exec codex -C "$ROOT_DIR" "$PROMPT_CONTENT" "$@"
