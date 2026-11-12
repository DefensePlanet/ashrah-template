#!/bin/bash
# Catalyst — Upgrade Script
# Pulls upstream updates while preserving your personalization and custom edits.
#
# Usage:
#   ./upgrade.sh              # Pull latest and re-personalize
#   ./upgrade.sh --check      # Preview what's new (no changes)
#   ./upgrade.sh --dry-run    # Simulate full upgrade (test for conflicts, no changes)
#   ./upgrade.sh --force      # Overwrite local changes with upstream + re-personalize

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
CATALYST_ROOT="$SCRIPT_DIR"
CONFIG_FILE="$CATALYST_ROOT/.catalyst-config"
STASHED=false
DRY_RUN=false
DRY_STASHED=false
BEHIND=0

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

log_info()  { echo -e "${BLUE}[info]${NC} $1"; }
log_ok()    { echo -e "${GREEN}[ok]${NC} $1"; }
log_warn()  { echo -e "${YELLOW}[warn]${NC} $1"; }
log_error() { echo -e "${RED}[error]${NC} $1"; }
log_step()  { echo -e "${CYAN}[$1/$TOTAL_STEPS]${NC} $2"; }

TOTAL_STEPS=6

# ─── Cleanup on exit ──────────────────────────────────────────────────────────

cleanup() {
    cd "$CATALYST_ROOT"
    if [[ "$DRY_RUN" == "true" ]]; then
        git merge --abort 2>/dev/null || true
        if [[ "$DRY_STASHED" == "true" ]]; then
            git stash pop --quiet 2>/dev/null || true
            DRY_STASHED=false
            # Only re-personalize in trap if the main path didn't already do it
            "$CATALYST_ROOT/setup.sh" --apply >/dev/null 2>&1 || true
        fi
    fi
    if [[ "$STASHED" == "true" ]]; then
        log_warn "Restoring stashed changes due to error..."
        git stash pop --quiet 2>/dev/null || log_warn "Could not auto-restore stash. Run 'git stash pop' manually."
        STASHED=false
    fi
}
trap cleanup EXIT

# ─── Prerequisites ─────────────────────────────────────────────────────────────

if [[ ! -f "$CONFIG_FILE" ]]; then
    if [[ -f "$CATALYST_ROOT/setup.sh" ]]; then
        log_warn "No .catalyst-config found — running first-time setup..."
        echo ""
        "$CATALYST_ROOT/setup.sh"
        echo ""
        if [[ ! -f "$CONFIG_FILE" ]]; then
            log_error "Setup did not complete. Run ./setup.sh manually."
            exit 1
        fi
    else
        log_error "No .catalyst-config found. Run ./setup.sh first."
        exit 1
    fi
fi

# shellcheck source=/dev/null
source "$CONFIG_FILE"

cd "$CATALYST_ROOT"

if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    log_error "Not a git repository."
    exit 1
fi

CURRENT_BRANCH=$(git branch --show-current 2>/dev/null || echo "main")
REMOTE_BRANCH="origin/${CURRENT_BRANCH}"

# ─── Parse flags ───────────────────────────────────────────────────────────────

CHECK_ONLY=false
FORCE_MODE=false

while [[ $# -gt 0 ]]; do
    case "$1" in
        --check) CHECK_ONLY=true; shift ;;
        --dry-run) DRY_RUN=true; shift ;;
        --force) FORCE_MODE=true; shift ;;
        *) log_error "Unknown option: $1"; echo "Usage: ./upgrade.sh [--check|--dry-run|--force]"; exit 1 ;;
    esac
done

# ─── Step 1: Fetch ─────────────────────────────────────────────────────────────

echo ""
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  Catalyst — Upgrade                    ${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

log_step 1 "Fetching upstream changes..."
git fetch origin --quiet 2>/dev/null

BEHIND=$(git rev-list HEAD.."$REMOTE_BRANCH" --count 2>/dev/null || echo "0")

if [[ "$BEHIND" -eq 0 ]]; then
    log_ok "Already up to date."
    exit 0
fi

echo ""
log_info "$BEHIND new commit(s) from upstream:"
echo ""
git log HEAD.."$REMOTE_BRANCH" --oneline --no-decorate | head -20
if [[ "$BEHIND" -gt 20 ]]; then
    echo "  ... and $((BEHIND - 20)) more"
fi
echo ""

if [[ "$CHECK_ONLY" == "true" ]]; then
    log_info "Run ./upgrade.sh (without --check) to apply these updates."
    exit 0
fi

# ─── Step 2: De-personalize ───────────────────────────────────────────────────

log_step 2 "Reversing personalization (temporary)..."

depersonalize_file() {
    local file="$1"
    local sed_args=()

    # Build reverse substitutions — most specific (longest) first to avoid partial matches
    # CATALYST_ROOT before HOME (CATALYST_ROOT contains HOME)
    sed_args+=(-e "s|${CATALYST_ROOT}|{{CATALYST_ROOT}}|g")
    sed_args+=(-e "s|${HOME}|{{HOME_DIR}}|g")

    # Only reverse non-empty, non-default values
    if [[ -n "${USER_NAME:-}" ]]; then
        sed_args+=(-e "s|${USER_NAME}|{{USER_NAME}}|g")
    fi
    if [[ -n "${ORCHESTRATOR_NAME:-}" && "${ORCHESTRATOR_NAME}" != "{{ORCHESTRATOR_NAME}}" ]]; then
        sed_args+=(-e "s|${ORCHESTRATOR_NAME}|{{ORCHESTRATOR_NAME}}|g")
    fi
    if [[ -n "${ASSISTANT_NAME:-}" && "${ASSISTANT_NAME}" != "Atlas" ]]; then
        sed_args+=(-e "s|${ASSISTANT_NAME}|{{ASSISTANT_NAME}}|g")
    fi
    if [[ -n "${USER_EMAIL:-}" ]]; then
        sed_args+=(-e "s|${USER_EMAIL}||g")
    fi

    sed -i '' "${sed_args[@]}" "$file" 2>/dev/null || true
}

DEPERSO_COUNT=0
while IFS= read -r file; do
    # Only process files that actually contain personalized values
    if grep -qF "${USER_NAME:-__NONE__}" "$file" 2>/dev/null || \
       grep -qF "${CATALYST_ROOT}" "$file" 2>/dev/null || \
       grep -qF "${ORCHESTRATOR_NAME:-__NONE__}" "$file" 2>/dev/null; then
        depersonalize_file "$file"
        DEPERSO_COUNT=$((DEPERSO_COUNT + 1))
    fi
done < <(
    find "$CATALYST_ROOT" \
        -type f \
        \( -name "*.md" -o -name "*.py" -o -name "*.sh" -o -name "*.yaml" \
           -o -name "*.yml" -o -name "*.json" -o -name "*.ts" -o -name "*.toml" \
           -o -name "*.txt" \) \
        -not -path "*/.git/*" \
        -not -path "*/node_modules/*" \
        -not -path "*/community/*" \
        -not -name "setup.sh" \
        -not -name "upgrade.sh" \
        -not -name ".catalyst-config"
)

log_ok "De-personalized $DEPERSO_COUNT file(s)"

# ─── Dry-run simulation ─────────────────────────────────────────────────────

if [[ "$DRY_RUN" == "true" ]]; then
    echo ""
    log_step 3 "Stashing local changes (temporary)..."

    if ! git diff --quiet 2>/dev/null || ! git diff --cached --quiet 2>/dev/null; then
        git stash push -m "catalyst-dry-run-$(date +%Y%m%d-%H%M%S)" --quiet
        DRY_STASHED=true
        log_ok "Changes stashed for simulation"
    else
        log_ok "Working tree clean"
    fi

    log_step 4 "Testing merge against upstream (simulation only)..."

    MERGE_RESULT=0
    git merge --no-commit --no-ff "$REMOTE_BRANCH" 2>/dev/null || MERGE_RESULT=$?

    if [[ "$MERGE_RESULT" -eq 0 ]]; then
        echo ""
        log_ok "Merge would succeed — no conflicts!"
        echo ""
        log_info "Files that would change:"
        git diff --cached --stat 2>/dev/null
        echo ""
    else
        echo ""
        log_warn "Merge would have conflicts in these files:"
        echo ""
        git diff --name-only --diff-filter=U 2>/dev/null | while read -r f; do
            echo "  ✗ $f"
        done
        echo ""
        log_info "If this happens during a real upgrade, you can:"
        echo "    1. Resolve conflicts manually"
        echo "    2. Run ./upgrade.sh --force to accept all upstream changes"
        echo ""
    fi

    # Clean up — restore everything exactly as it was
    log_step 5 "Restoring your files..."
    git merge --abort 2>/dev/null || true

    if [[ "$DRY_STASHED" == "true" ]]; then
        git stash pop --quiet 2>/dev/null || true
        DRY_STASHED=false
    fi

    # Re-personalize (let failures surface so user knows if restore failed)
    "$CATALYST_ROOT/setup.sh" --apply >/dev/null

    echo ""
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}  Dry run complete!                     ${NC}"
    echo -e "${GREEN}========================================${NC}"
    echo ""
    log_ok "Your files are exactly as they were — nothing changed."
    log_info "Run ./upgrade.sh to apply the upgrade for real."
    echo ""
    exit 0
fi

# ─── Step 3: Stash local customizations ──────────────────────────────────────

log_step 3 "Preserving your customizations..."

if ! git diff --quiet 2>/dev/null || ! git diff --cached --quiet 2>/dev/null; then
    git stash push -m "catalyst-upgrade-$(date +%Y%m%d-%H%M%S)" --quiet
    STASHED=true
    log_ok "Local customizations stashed"
else
    log_ok "Working tree clean — no customizations to preserve"
fi

# ─── Step 4: Merge upstream ─────────────────────────────────────────────────

log_step 4 "Merging upstream changes..."

if [[ "$FORCE_MODE" == "true" ]]; then
    git reset --hard "$REMOTE_BRANCH" --quiet 2>/dev/null
    log_ok "Force-reset to upstream (--force mode)"
    # Don't pop stash in force mode — user chose to overwrite
    STASHED=false
else
    if git merge "$REMOTE_BRANCH" --no-edit --quiet 2>/dev/null; then
        log_ok "Merged $BEHIND commit(s) from upstream"
    else
        log_error "Merge conflict."
        echo ""
        echo "  Options:"
        echo "    1. Resolve conflicts manually, then run: ./setup.sh --apply"
        echo "    2. Discard local changes: ./upgrade.sh --force"
        echo ""
        if [[ "$STASHED" == "true" ]]; then
            log_info "Your customizations are saved in git stash."
            log_info "After resolving, run: git stash pop && ./setup.sh --apply"
            STASHED=false  # Don't auto-pop — user resolves manually
        fi
        exit 1
    fi
fi

# ─── Restore stashed customizations ──────────────────────────────────────────

if [[ "$STASHED" == "true" ]]; then
    STASHED=false  # Prevent double-pop in cleanup
    if git stash pop --quiet 2>/dev/null; then
        log_ok "Customizations restored"
    else
        log_warn "Some customizations conflict with upstream changes."
        echo ""
        echo "  Your customizations are partially applied. Resolve conflicts:"
        echo "    git diff --name-only --diff-filter=U    # Show conflicted files"
        echo "    # Edit files to resolve, then:"
        echo "    git checkout --theirs <file>             # Accept upstream version"
        echo "    git checkout --ours <file>               # Keep your version"
        echo "    ./setup.sh --apply                       # Re-personalize"
        echo ""
        exit 1
    fi
fi

# ─── Step 5: Re-personalize ──────────────────────────────────────────────────

log_step 5 "Re-applying personalization..."
"$CATALYST_ROOT/setup.sh" --apply

# ─── Step 6: Sync Telegram supergroups ───────────────────────────────────────

log_step 6 "Syncing Telegram supergroups for new capsules..."

PYTHON_BIN=""
if command -v python3.12 &>/dev/null; then
    PYTHON_BIN="python3.12"
elif command -v python3 &>/dev/null; then
    PYTHON_BIN="python3"
fi

if [[ -z "$PYTHON_BIN" ]]; then
    log_warn "Python not found — skipping supergroup sync"
elif [[ ! -f "$CATALYST_ROOT/tools/capsule_creator.py" ]]; then
    log_warn "capsule_creator.py not found — skipping supergroup sync"
else
    # Non-blocking: never fail the upgrade on supergroup sync issues
    # Timeout guards against expired Telethon sessions that prompt interactively
    SYNC_OUTPUT=$(timeout 90 $PYTHON_BIN "$CATALYST_ROOT/tools/capsule_creator.py" --sync-groups 2>&1) || true

    if echo "$SYNC_OUTPUT" | grep -q "\[skip\]"; then
        log_warn "Supergroup sync skipped (Telegram not configured yet)"
    elif echo "$SYNC_OUTPUT" | grep -q "\[error\]"; then
        log_warn "Supergroup sync encountered errors (non-blocking)"
        echo "$SYNC_OUTPUT" | tail -5
    else
        CREATED_COUNT=$(echo "$SYNC_OUTPUT" | sed -n 's/.*Created *: *\([0-9]*\).*/\1/p')
        if [[ "${CREATED_COUNT:-0}" -gt 0 ]]; then
            log_ok "Created ${CREATED_COUNT} new Telegram supergroup(s)"
            echo "$SYNC_OUTPUT" | grep '^\s*+' || true
        else
            log_ok "All capsules already have Telegram supergroups"
        fi
    fi
fi

# ─── Done ─────────────────────────────────────────────────────────────────────

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  Upgrade complete!                     ${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
log_ok "$BEHIND commit(s) applied. Here's what changed:"
echo ""
git log HEAD~"$BEHIND"..HEAD --oneline --no-decorate
echo ""
