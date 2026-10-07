#!/usr/bin/env bash
set -euo pipefail
ROOT="${CATALYST_ROOT:-$(cd "$(dirname "$0")/.." && pwd)}"
cd "$ROOT"

echo "Scanning for potential secrets (single-pass)..."

grep -RInE \
  --exclude-dir=.git \
  --exclude-dir=node_modules \
  --exclude-dir=.venv \
  --exclude-dir=__pycache__ \
  --exclude-dir='.cache' \
  --exclude='*.tar.gz' \
  --exclude='*.zip' \
  --exclude='*.db' \
  --exclude='*.pyc' \
  --exclude='*.woff2' \
  --exclude='*.woff' \
  -e 'AKIA[0-9A-Z]{16}' \
  -e 'AIza[0-9A-Za-z\-_]{35}' \
  -e 'xox[baprs]-[0-9A-Za-z-]{10,48}' \
  -e '-----BEGIN (RSA|DSA|EC) PRIVATE KEY-----' \
  -e 'sk-[A-Za-z0-9]{20,}' \
  -e 'ghp_[A-Za-z0-9]{36}' \
  -e 'gho_[A-Za-z0-9]{36}' \
  . 2>/dev/null \
  | sed 's/\(.\{0,80\}\).*/\1 [REDACTED]/' \
  | head -n 50 \
  || echo "No obvious secrets matched common patterns."
