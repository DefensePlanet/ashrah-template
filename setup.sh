#!/bin/bash
# ---------------------------------------------------------------------------
# Ashrah Template: first-time setup
#
# The template ships with double-curly placeholder tokens in place of every
# name, path and handle. This script asks for your values, writes them into
# every text file (and every file or folder name) that carries a token, and
# records your answers in .catalyst-config.
#
#   ./setup.sh           interactive, first run
#   ./setup.sh --apply   re-apply the saved answers without prompting
#                        (use after pulling template updates that bring new
#                        placeholder tokens)
#
# Works with the bash 3.2 that ships with macOS. Safe to re-run.
# ---------------------------------------------------------------------------
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
CONFIG_FILE="$ROOT/.catalyst-config"
SELF="$ROOT/setup.sh"

if [[ -t 1 ]]; then
    RED=$'\033[0;31m'; GREEN=$'\033[0;32m'; BLUE=$'\033[0;34m'; YELLOW=$'\033[1;33m'; NC=$'\033[0m'
else
    RED=""; GREEN=""; BLUE=""; YELLOW=""; NC=""
fi
say()  { printf '%s\n' "$*"; }
ok()   { printf '%s%s%s\n' "$GREEN" "$*" "$NC"; }
note() { printf '%s%s%s\n' "$YELLOW" "$*" "$NC"; }
err()  { printf '%s%s%s\n' "$RED" "$*" "$NC" >&2; }

MODE="interactive"
case "${1:-}" in
    "")        ;;
    --apply)   MODE="apply" ;;
    -h|--help) sed -n '2,16p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *)         err "Unknown option: $1 (try --help)"; exit 1 ;;
esac

# --- validation rules ---------------------------------------------------------
# Answers land verbatim in JSON, YAML, Python, shell and Markdown, so quotes,
# backslashes, braces and control characters are refused at the prompt.
NAME_RE='^[A-Za-z][A-Za-z0-9 ._-]{0,39}$'
NAME_HINT="start with a letter; then letters, digits, space, period, hyphen or underscore (max 40)"
ORCH_RE='^[A-Za-z][A-Za-z0-9 _-]{0,29}$'
ORCH_HINT="start with a letter; then letters, digits, space, hyphen or underscore (max 30)"
EMAIL_RE='^[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,24}$'
EMAIL_HINT="an address like you@example.com"
GH_RE='^[A-Za-z0-9]([A-Za-z0-9-]{0,37}[A-Za-z0-9])?$'
GH_HINT="1-39 letters, digits or hyphens, not starting or ending with a hyphen"
BOT_RE='^[A-Za-z0-9_]{1,64}$'
BOT_HINT="letters, digits and underscores, without the @"
CHAT_RE='^-?[0-9]{1,20}$'
CHAT_HINT="digits, optionally with a leading minus"

USER_NAME=""; ORCHESTRATOR_NAME=""; USER_EMAIL=""; GITHUB_USER=""
TELEGRAM_BOT=""; TELEGRAM_CHAT_ID=""

# ask VAR "prompt" REGEX HINT required|optional
ask() {
    local var="$1" prompt="$2" re="$3" hint="$4" mode="$5" ans
    while :; do
        if ! IFS= read -r -p "$prompt" ans; then
            say ""
            err "Input ended before this question was answered. Nothing was changed."
            exit 1
        fi
        # trim surrounding whitespace
        ans="$(printf '%s' "$ans" | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//')"
        if [[ -z "$ans" ]]; then
            if [[ "$mode" == "optional" ]]; then
                eval "$var=''"
                return 0
            fi
            err "  This answer is required."
            continue
        fi
        if [[ "$ans" =~ $re ]]; then
            printf -v "$var" '%s' "$ans"
            return 0
        fi
        err "  Not accepted: use $hint."
    done
}

valid() {  # valid VALUE REGEX required|optional
    [[ -z "$1" && "$3" == "optional" ]] && return 0
    [[ -n "$1" && "$1" =~ $2 ]]
}

# .catalyst-config is KEY=<printf %q value>. Only known keys are read back,
# line by line, never sourced, so a hand-edited file cannot execute anything.
load_config() {
    local line key val
    while IFS= read -r line || [[ -n "$line" ]]; do
        [[ -z "$line" || "$line" == \#* ]] && continue
        key="${line%%=*}"; val="${line#*=}"
        case "$key" in
            USER_NAME|ORCHESTRATOR_NAME|USER_EMAIL|GITHUB_USER|TELEGRAM_BOT|TELEGRAM_CHAT_ID) ;;
            *) continue ;;
        esac
        # undo printf %q escaping for the restricted charset (backslash-space etc.)
        val="$(printf '%s' "$val" | sed -e "s/^'//" -e "s/'$//" -e 's/\\\(.\)/\1/g')"
        printf -v "$key" '%s' "$val"
    done < "$CONFIG_FILE"
}

# --- 1. answers ---------------------------------------------------------------------
if [[ "$MODE" == "apply" ]]; then
    [[ -f "$CONFIG_FILE" ]] || { err "No .catalyst-config yet. Run ./setup.sh first."; exit 1; }
    load_config
    ok "Re-applying saved answers from .catalyst-config"
else
    if [[ -f "$CONFIG_FILE" ]]; then
        load_config
        ok "This copy is already personalized (user: $USER_NAME, orchestrator: $ORCHESTRATOR_NAME)."
        say "Nothing to do. After pulling template updates run:  ./setup.sh --apply"
        say "To start over with different names, re-clone the template."
        exit 0
    fi
    say "${BLUE}========================================${NC}"
    say "${BLUE}  Ashrah Template: first-time setup${NC}"
    say "${BLUE}========================================${NC}"
    say ""
    say "Answers are written into config and source files across the tree."
    say ""
    ask USER_NAME         "Your name (e.g. Alex): "                                   "$NAME_RE"  "$NAME_HINT" required
    ask ORCHESTRATOR_NAME "Name your orchestrator, the agent you talk to (e.g. Atlas): " "$ORCH_RE" "$ORCH_HINT" required
    ask USER_EMAIL        "Your email (optional, Enter to skip): "                    "$EMAIL_RE" "$EMAIL_HINT" optional
    ask GITHUB_USER       "GitHub username (optional): "                              "$GH_RE"    "$GH_HINT"    optional
    say ""
    say "Telegram (optional): only used by tools that post status to a chat."
    ask TELEGRAM_BOT      "Telegram bot username, without @ (optional): "             "$BOT_RE"   "$BOT_HINT"   optional
    ask TELEGRAM_CHAT_ID  "Telegram chat ID (optional): "                             "$CHAT_RE"  "$CHAT_HINT"  optional
fi

# Re-check everything (the --apply path reads a file that may have been edited).
BAD=0
valid "$USER_NAME"         "$NAME_RE"  required || { err "USER_NAME is missing or invalid";         BAD=1; }
valid "$ORCHESTRATOR_NAME" "$ORCH_RE"  required || { err "ORCHESTRATOR_NAME is missing or invalid"; BAD=1; }
valid "$USER_EMAIL"        "$EMAIL_RE" optional || { err "USER_EMAIL is invalid";                   BAD=1; }
valid "$GITHUB_USER"       "$GH_RE"    optional || { err "GITHUB_USER is invalid";                  BAD=1; }
valid "$TELEGRAM_BOT"      "$BOT_RE"   optional || { err "TELEGRAM_BOT is invalid";                 BAD=1; }
valid "$TELEGRAM_CHAT_ID"  "$CHAT_RE"  optional || { err "TELEGRAM_CHAT_ID is invalid";             BAD=1; }
[[ $BAD -eq 0 ]] || { err "Nothing was changed."; exit 1; }

# --- 2. derived values ------------------------------------------------------------------
CATALYST_ROOT="$ROOT"
HOME_DIR="$HOME"
USER_LOGIN="$(id -un)"
# Claude Code keys per-project memory by the absolute path with every
# non-alphanumeric character turned into '-'.
CLAUDE_PROJECT_SLUG="$(printf '%s' "$CATALYST_ROOT" | sed 's/[^A-Za-z0-9]/-/g')"
# UPPER: env-var / constant style.  LOWER: file names, module names, slugs;
# restricted to [a-z0-9_] so it stays a valid Python module name.
ORCHESTRATOR_NAME_UPPER="$(printf '%s' "$ORCHESTRATOR_NAME" | tr '[:lower:]' '[:upper:]' | sed 's/[^A-Z0-9]/_/g')"
ORCHESTRATOR_NAME_LOWER="$(printf '%s' "$ORCHESTRATOR_NAME" | tr '[:upper:]' '[:lower:]' | sed -e 's/[^a-z0-9]/_/g' -e 's/__*/_/g' -e 's/^_//' -e 's/_$//')"
ORCHESTRATOR_NAME_LOWER="${ORCHESTRATOR_NAME_LOWER:-orchestrator}"

case "$CATALYST_ROOT" in
    *$'\n'*|*\\*|*\"*|*\'*) err "The repo path contains a quote, backslash or newline; move it and re-run."; exit 1 ;;
esac

# --- 3. substitution program ---------------------------------------------------------------
# Escape the replacement side of s|pattern|replacement|g for BSD and GNU sed:
# backslash, ampersand and the '|' delimiter are special there.
sed_escape() { printf '%s' "$1" | sed -e 's/[\\&|]/\\&/g'; }

SED_PROG="$(mktemp "${TMPDIR:-/tmp}/template-setup.XXXXXX")"
FILE_LIST="$(mktemp "${TMPDIR:-/tmp}/template-files.XXXXXX")"
trap 'rm -f "$SED_PROG" "$FILE_LIST"' EXIT

emit() { printf 's|{{%s}}|%s|g\n' "$1" "$(sed_escape "$2")" >> "$SED_PROG"; }
emit CATALYST_ROOT           "$CATALYST_ROOT"
emit HOME_DIR                "$HOME_DIR"
emit CLAUDE_PROJECT_SLUG     "$CLAUDE_PROJECT_SLUG"
emit USER_LOGIN              "$USER_LOGIN"
emit USER_NAME               "$USER_NAME"
emit USER_EMAIL              "${USER_EMAIL:-you@example.com}"
emit GITHUB_USER             "${GITHUB_USER:-your-github-user}"
emit ORCHESTRATOR_NAME_UPPER "$ORCHESTRATOR_NAME_UPPER"
emit ORCHESTRATOR_NAME_LOWER "$ORCHESTRATOR_NAME_LOWER"
emit ORCHESTRATOR_NAME       "$ORCHESTRATOR_NAME"
emit ASSISTANT_NAME          "$ORCHESTRATOR_NAME"
emit TELEGRAM_BOT            "${TELEGRAM_BOT:-YourBotUsername}"
emit TELEGRAM_CHAT_ID        "${TELEGRAM_CHAT_ID:-0}"

TOKEN_RE='\{\{(CATALYST_ROOT|HOME_DIR|CLAUDE_PROJECT_SLUG|USER_LOGIN|USER_NAME|USER_EMAIL|GITHUB_USER|ORCHESTRATOR_NAME_UPPER|ORCHESTRATOR_NAME_LOWER|ORCHESTRATOR_NAME|ASSISTANT_NAME|TELEGRAM_BOT|TELEGRAM_CHAT_ID)\}\}'

# --- 4. file contents ----------------------------------------------------------------------
# .git, dependency folders and virtualenvs are pruned; grep -I skips binaries.
# LC_ALL=C keeps BSD sed/grep from choking on non-UTF-8 bytes.
export LC_ALL=C
say ""
say "${BLUE}Applying your names...${NC}"
find "$ROOT" \( -name .git -o -name node_modules -o -name .venv -o -name venv -o -name __pycache__ \) -prune \
    -o -type f ! -path "$SELF" ! -name '.catalyst-config*' -print0 > "$FILE_LIST"

FILES=0
while IFS= read -r -d '' f; do
    if grep -IqE "$TOKEN_RE" "$f" 2>/dev/null; then
        if sed --version >/dev/null 2>&1; then
            sed -i -f "$SED_PROG" "$f"
        else
            sed -i '' -f "$SED_PROG" "$f"
        fi
        FILES=$((FILES + 1))
    fi
done < "$FILE_LIST"
ok "  Updated $FILES file(s)"

# --- 5. file and folder names (deepest first) --------------------------------------------------
RENAMED=0
while IFS= read -r -d '' p; do
    base="$(basename "$p")"
    new="$(printf '%s' "$base" | sed -f "$SED_PROG")"
    if [[ "$new" != "$base" ]]; then
        dest="$(dirname "$p")/$new"
        if [[ -e "$dest" ]]; then
            err "  Cannot rename ${p#"$ROOT"/}: ${dest#"$ROOT"/} already exists"
            exit 1
        fi
        mv "$p" "$dest"
        RENAMED=$((RENAMED + 1))
    fi
done < <(find "$ROOT" -depth -name '*{{*}}*' \
            ! -path '*/.git/*' ! -path '*/node_modules/*' ! -path '*/.venv/*' -print0)
ok "  Renamed $RENAMED path(s)"
unset LC_ALL

# --- 6. save answers (also the "already set up" marker) -------------------------------------------
{
    printf '# Written by setup.sh. Edit only by re-cloning; read back by --apply.\n'
    printf 'USER_NAME=%q\n'         "$USER_NAME"
    printf 'ORCHESTRATOR_NAME=%q\n' "$ORCHESTRATOR_NAME"
    printf 'USER_EMAIL=%q\n'        "$USER_EMAIL"
    printf 'GITHUB_USER=%q\n'       "$GITHUB_USER"
    printf 'TELEGRAM_BOT=%q\n'      "$TELEGRAM_BOT"
    printf 'TELEGRAM_CHAT_ID=%q\n'  "$TELEGRAM_CHAT_ID"
} > "$CONFIG_FILE.tmp"
chmod 600 "$CONFIG_FILE.tmp"
mv "$CONFIG_FILE.tmp" "$CONFIG_FILE"

# --- 7. local scaffolding --------------------------------------------------------------------------
if [[ ! -f "$ROOT/.env" && -f "$ROOT/.env.example" ]]; then
    cp "$ROOT/.env.example" "$ROOT/.env"
    chmod 600 "$ROOT/.env"
    ok "  Created .env from .env.example"
fi
mkdir -p "$ROOT/memory" "$ROOT/logs" "$ROOT/capsules"

LEFT="$( { grep -rIlE --exclude-dir=.git --exclude-dir=node_modules --exclude=setup.sh "$TOKEN_RE" "$ROOT" 2>/dev/null || true; } | wc -l | tr -d ' ')"
if [[ "$LEFT" != "0" ]]; then
    note "  $LEFT file(s) still carry a setup token (unreadable or non-text?); re-run ./setup.sh --apply"
fi

say ""
ok "========================================"
ok "  Setup complete"
ok "========================================"
say ""
say "Your orchestrator is ${BLUE}${ORCHESTRATOR_NAME}${NC}. Next steps:"
say "  1. Put your API keys in .env (ANTHROPIC_API_KEY first; the rest only when a tool asks)."
say "  2. Optional: ./setup-skills.sh to link the community skills several agents reference."
say "  3. Start Claude Code here:  claude"
say "  4. Say hello to ${ORCHESTRATOR_NAME}, then try: \"have Backend Dev scaffold a FastAPI hello world in a new capsule\""
say ""
say "Answers are saved in .catalyst-config (git-ignored). See GETTING-STARTED.md for the full tour."
