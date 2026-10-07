#!/bin/bash
# export-template/export.sh
# ---------------------------------------------------------------------------
# Build the public, genericized template repo from this (private) repo.
#
#   rsync git-visible files -> temp staging dir
#   -> delete excluded paths -> transforms -> mojibake repair -> substitutions
#   -> overlay template-files/ -> verification (patterns, gitleaks, paths,
#      agent frontmatter, mojibake) -> move to --out  [-> optional --push]
#
# All policy lives in export.yaml next to this script. The live tree is only
# ever read.
#
# Usage:
#   scripts/export-template/export.sh [--out DIR] [--dry-run]
#                                     [--allow-findings] [--version VER]
#                                     [--push REMOTE_URL] [--src DIR]
#                                     [--config FILE]
#
# Exit codes: 0 clean, 1 usage/runtime error, 2 verification findings.
# ---------------------------------------------------------------------------
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENGINE="$SCRIPT_DIR/lib/export_engine.py"
CONFIG="$SCRIPT_DIR/export.yaml"
TEMPLATE_FILES="$SCRIPT_DIR/template-files"
GITLEAKS_CONFIG="$SCRIPT_DIR/gitleaks.toml"
SRC="$(cd "$SCRIPT_DIR/../.." && pwd)"

OUT=""
DRY_RUN=0
ALLOW_FINDINGS=0
PUSH_URL=""
VERSION=""

# Placeholder keys setup.sh fills. Anything else in {{...}} is reported as a
# downstream (capsule/template) token and left alone.
SETUP_KEYS="CATALYST_ROOT,HOME_DIR,CLAUDE_PROJECT_SLUG,USER_NAME,USER_EMAIL,USER_LOGIN,GITHUB_USER,ORCHESTRATOR_NAME,ORCHESTRATOR_NAME_LOWER,ORCHESTRATOR_NAME_UPPER,ASSISTANT_NAME,TELEGRAM_BOT,TELEGRAM_CHAT_ID"

usage() { sed -n '2,22p' "$0" | sed 's/^# \{0,1\}//'; }
log()   { printf '\033[0;34m==>\033[0m %s\n' "$*"; }
warn()  { printf '\033[1;33m!! \033[0m %s\n' "$*" >&2; }
fail()  { printf '\033[0;31mxx \033[0m %s\n' "$*" >&2; exit 1; }

while [[ $# -gt 0 ]]; do
    case "$1" in
        --out)            OUT="${2:?--out needs a directory}"; shift 2 ;;
        --dry-run)        DRY_RUN=1; shift ;;
        --allow-findings) ALLOW_FINDINGS=1; shift ;;
        --push)           PUSH_URL="${2:?--push needs a remote URL}"; shift 2 ;;
        --version)        VERSION="${2:?--version needs a value}"; shift 2 ;;
        --src)            SRC="$(cd "${2:?--src needs a directory}" && pwd)"; shift 2 ;;
        --config)         CONFIG="${2:?--config needs a file}"; shift 2 ;;
        -h|--help)        usage; exit 0 ;;
        *)                usage >&2; fail "unknown argument: $1" ;;
    esac
done

# --- preflight ---------------------------------------------------------------
command -v python3 >/dev/null || fail "python3 is required"
command -v rsync   >/dev/null || fail "rsync is required"
command -v git     >/dev/null || fail "git is required"
[[ -f "$ENGINE" ]] || fail "missing $ENGINE"
[[ -f "$CONFIG" ]] || fail "missing $CONFIG"
git -C "$SRC" rev-parse --is-inside-work-tree >/dev/null 2>&1 || fail "$SRC is not a git work tree"
if [[ $DRY_RUN -eq 1 && -n "$PUSH_URL" ]]; then
    fail "--dry-run and --push are mutually exclusive"
fi

cfg() { python3 -I "$ENGINE" config-get --config "$CONFIG" "$1" 2>/dev/null || true; }
TEMPLATE_NAME="$(cfg template.name)";        TEMPLATE_NAME="${TEMPLATE_NAME:-Template}"
[[ -n "$VERSION" ]] || VERSION="$(cfg template.version)"; VERSION="${VERSION:-0.0.0}"
BRANCH="$(cfg template.default_branch)";      BRANCH="${BRANCH:-main}"
AUTHOR_NAME="$(cfg template.commit_author_name)"
AUTHOR_EMAIL="$(cfg template.commit_author_email)"
SOURCE_MODE="$(cfg source.mode)";             SOURCE_MODE="${SOURCE_MODE:-git-visible}"

SHORT_SHA="$(git -C "$SRC" rev-parse --short HEAD)"
BUILD_DATE="$(date -u +%Y-%m-%d)"
if [[ -n "$(git -C "$SRC" status --porcelain 2>/dev/null | head -1)" ]]; then
    DIRTY="+dirty"
else
    DIRTY=""
fi

WORK="$(mktemp -d "${TMPDIR:-/tmp}/export-template.XXXXXX")"
STAGE="$WORK/tree"
mkdir -p "$STAGE"
KEEP_WORK=0
cleanup() { [[ $KEEP_WORK -eq 1 ]] || rm -rf "$WORK"; }
trap cleanup EXIT

if [[ -z "$OUT" ]]; then
    OUT="${TMPDIR:-/tmp}"
    OUT="${OUT%/}/template-export"
fi
case "$OUT" in /*) ;; *) OUT="$(pwd)/$OUT" ;; esac
case "$OUT/" in
    "$SRC"/*) fail "--out must be outside the source repo ($SRC)" ;;
esac

log "source      $SRC @ $SHORT_SHA$DIRTY"
log "config      $CONFIG"
log "staging     $STAGE"
[[ $DRY_RUN -eq 1 ]] && log "mode        DRY RUN (nothing is written to --out, nothing is pushed)"

# --- 1. copy -----------------------------------------------------------------
LIST="$WORK/files.lst"
case "$SOURCE_MODE" in
    git-visible)
        # tracked + untracked-not-ignored; keep only paths that exist right now
        # (a tree mid-merge can list deleted files).
        git -C "$SRC" ls-files -z -co --exclude-standard \
            | python3 -I -c '
import os, sys
root = sys.argv[1]
items = [p for p in sys.stdin.buffer.read().split(b"\0") if p]
seen = set()
for p in items:
    if p in seen:
        continue
    seen.add(p)
    if os.path.lexists(os.path.join(root.encode(), p)):
        sys.stdout.buffer.write(p + b"\0")
' "$SRC" > "$LIST"
        ;;
    *) fail "unknown source.mode: $SOURCE_MODE" ;;
esac
log "copying $(tr -cd '\0' < "$LIST" | wc -c | tr -d ' ') git-visible files"
rsync -a --from0 --files-from="$LIST" "$SRC/" "$STAGE/"

# --- 2-5. prune, transform, substitute, overlay -------------------------------
BUILD_REPORT="$WORK/build.json"
log "pruning, transforming, substituting"
python3 -I "$ENGINE" build --config "$CONFIG" --tree "$STAGE" \
    --template-files "$TEMPLATE_FILES" --report "$BUILD_REPORT"

# Build stamp (no host paths, no names).
printf '{\n  "template": "%s",\n  "version": "%s",\n  "built_from": "%s%s",\n  "built_at": "%s"\n}\n' \
    "$TEMPLATE_NAME" "$VERSION" "$SHORT_SHA" "$DIRTY" "$BUILD_DATE" > "$STAGE/.template-build.json"

# --- 6. verification ----------------------------------------------------------
GL_REPORT="$WORK/gitleaks.json"
if command -v gitleaks >/dev/null 2>&1; then
    log "gitleaks detect --no-git"
    set +e
    gitleaks detect --no-git --redact --no-banner --log-level error \
        --config "$GITLEAKS_CONFIG" --source "$STAGE" \
        --report-format json --report-path "$GL_REPORT" >/dev/null 2>"$WORK/gitleaks.err"
    GL_RC=$?
    set -e
    if [[ $GL_RC -ne 0 && $GL_RC -ne 1 ]]; then
        cat "$WORK/gitleaks.err" >&2
        fail "gitleaks failed to run (exit $GL_RC)"
    fi
    [[ -s "$GL_REPORT" ]] || echo "[]" > "$GL_REPORT"
else
    warn "gitleaks not installed (brew install gitleaks) - counted as a finding"
    GL_REPORT="SKIPPED"
fi

set +e
python3 -I "$ENGINE" verify --config "$CONFIG" --tree "$STAGE" \
    --build-report "$BUILD_REPORT" --gitleaks-report "$GL_REPORT" \
    --known-tokens "$SETUP_KEYS" --out-json "$WORK/verify.json"
VERIFY_RC=$?
set -e
[[ $VERIFY_RC -eq 0 || $VERIFY_RC -eq 2 ]] || fail "verification crashed (exit $VERIFY_RC)"

if [[ $DRY_RUN -eq 1 ]]; then
    log "dry run complete; staging discarded"
    exit $(( VERIFY_RC == 0 ? 0 : (ALLOW_FINDINGS ? 0 : 2) ))
fi

if [[ $VERIFY_RC -ne 0 && $ALLOW_FINDINGS -eq 0 ]]; then
    KEEP_WORK=1
    warn "verification found problems; nothing written to $OUT"
    warn "inspect the staged tree at: $STAGE"
    warn "re-run with --allow-findings to write it anyway (push is never allowed with findings)"
    exit 2
fi

# --- 7. place output -----------------------------------------------------------
if [[ -e "$OUT" ]]; then
    if [[ -n "$(ls -A "$OUT" 2>/dev/null)" && ! -f "$OUT/.template-build.json" ]]; then
        fail "$OUT exists, is not empty and is not a previous export - refusing to overwrite"
    fi
    rm -rf "$OUT"
fi
mkdir -p "$(dirname "$OUT")"
mv "$STAGE" "$OUT"
log "template written to $OUT"

# --- 8. optional push ------------------------------------------------------------
if [[ -n "$PUSH_URL" ]]; then
    if [[ $VERIFY_RC -ne 0 ]]; then
        fail "refusing to push: verification is not clean (--allow-findings never applies to --push)"
    fi
    MSG="$TEMPLATE_NAME v$VERSION (built from $SHORT_SHA$DIRTY, $BUILD_DATE)"
    log "creating single-commit history: $MSG"
    rm -rf "$OUT/.git"
    git -C "$OUT" init -q -b "$BRANCH"
    git -C "$OUT" add -A
    git -C "$OUT" \
        -c user.name="${AUTHOR_NAME:-Template Builder}" \
        -c user.email="${AUTHOR_EMAIL:-noreply@example.com}" \
        -c commit.gpgsign=false \
        commit -q -m "$MSG"
    # The template ships one commit per release; every release replaces the
    # previous history, hence the force push.
    log "pushing $BRANCH to $PUSH_URL (force: history is replaced each release)"
    git -C "$OUT" push --force "$PUSH_URL" "$BRANCH:$BRANCH"
    git -C "$OUT" tag -a "v$VERSION" -m "$MSG"
    git -C "$OUT" push --force "$PUSH_URL" "refs/tags/v$VERSION"
    log "pushed"
fi

exit 0
