#!/usr/bin/env python3
"""Codex peer-review Stop hook (multi-capsule).

Runs after Jarvis finishes a turn. Scans every watched root for code files
touched THIS turn (mtime > marker), sends a scoped review payload to the Codex
CLI for an independent second opinion, and feeds any findings back into the
conversation so they can be relayed and fixed.

Coverage:
- Auto-discovers git repos under WATCH_ROOTS (catalyst-os + any git capsule).
- Also covers NON-git capsule dirs (e.g. ~/capsules/my-app) by reviewing the
  full contents of code files that changed.

Design notes:
- Scoped to files changed since the last run (mtime > marker) so it never
  re-reviews a pre-existing dirty tree.
- Only reviews recognised code extensions (skips docs/config churn).
- `stop_hook_active` guard prevents an infinite Stop->review->Stop loop.
- Read-only Codex sandbox: the reviewer can never modify any repo.
- Stays silent (exit 0, no block) when Codex reports "No issues found".
"""
import sys, os, json, subprocess, re

# Roots to watch. A root that is itself a git repo is reviewed directly; a root
# that is NOT a git repo has each immediate sub-directory treated as a capsule
# (git repo -> diff review, plain dir -> file-content review).
WATCH_ROOTS = [
    "{{CATALYST_ROOT}}",
    "{{HOME_DIR}}/capsules",
]

STATE_DIR = "/tmp/catalyst-codex-review"
MARKER = os.path.join(STATE_DIR, "marker")
REVIEW_OUT = os.path.join(STATE_DIR, "review.md")

PRUNE_DIRS = {
    ".git", "node_modules", ".dart_tool", "build", "dist", "out", ".next",
    ".venv", "venv", "env", "Pods", "DerivedData", "target", "__pycache__",
    ".gradle", ".idea", ".expo", ".turbo", "vendor", ".terraform",
    "coverage", ".pytest_cache", ".mypy_cache", "Carthage",
}
CODE_RE = re.compile(
    r"\.(py|js|jsx|ts|tsx|mjs|cjs|swift|sh|bash|zsh|go|rs|rb|java|kt|kts|c|cc|"
    r"cpp|h|hpp|m|mm|sql|vue|svelte|php|lua|pl|r|scala|dart|sol)$",
    re.I,
)
MAX_TOTAL_LINES = 4000
MAX_FILE_LINES = 1500

PROMPT = (
    "You are a senior peer code reviewer giving an independent second opinion on "
    "code another engineer just wrote. The stdin block contains git diffs and/or "
    "full file contents (grouped by repo/file). Review them for real bugs, "
    "security issues, and significant quality problems. Be concise. List only "
    "genuine issues, each with a severity (Critical/High/Medium/Low), file:line, "
    "and a one-line fix. If nothing is wrong, reply exactly 'No issues found.'"
)


def run(args):
    return subprocess.run(args, capture_output=True, text=True).stdout


def is_git_repo(path):
    return os.path.exists(os.path.join(path, ".git"))


def reset_marker():
    open(MARKER, "w").close()


def discover_targets():
    """Return (git_repos, plain_dirs) as absolute paths."""
    git_repos, plain_dirs = [], []
    for root in WATCH_ROOTS:
        if not os.path.isdir(root):
            continue
        if is_git_repo(root):
            git_repos.append(root)
            continue
        for name in sorted(os.listdir(root)):
            child = os.path.join(root, name)
            if not os.path.isdir(child):
                continue
            (git_repos if is_git_repo(child) else plain_dirs).append(child)
    return git_repos, plain_dirs


def git_changed(repo, marker_mtime):
    """Yield (repo, relpath, abspath, tracked) for changed code files."""
    listing = run(["git", "-C", repo, "ls-files", "-mo", "--exclude-standard"])
    for rel in listing.splitlines():
        rel = rel.strip()
        if not rel or not CODE_RE.search(rel):
            continue
        ab = os.path.join(repo, rel)
        try:
            if os.path.getmtime(ab) <= marker_mtime:
                continue
        except OSError:
            continue
        tracked = subprocess.run(
            ["git", "-C", repo, "ls-files", "--error-unmatch", rel],
            capture_output=True,
        ).returncode == 0
        yield (repo, rel, ab, tracked)


def plain_changed(d, marker_mtime):
    """Yield abspaths of changed code files inside a non-git directory."""
    for dirpath, dirnames, filenames in os.walk(d):
        dirnames[:] = [x for x in dirnames if x not in PRUNE_DIRS]
        for fn in filenames:
            if not CODE_RE.search(fn):
                continue
            ab = os.path.join(dirpath, fn)
            try:
                if os.path.getmtime(ab) > marker_mtime:
                    yield ab
            except OSError:
                continue


def main():
    try:
        data = json.load(sys.stdin)
    except Exception:
        data = {}

    # Prevent loop: if we are already inside a stop-hook continuation, allow stop.
    if data.get("stop_hook_active"):
        return 0

    if subprocess.run(["which", "codex"], capture_output=True).returncode != 0:
        return 0

    os.makedirs(STATE_DIR, exist_ok=True)

    # First run establishes the baseline; never review the pre-existing trees.
    if not os.path.exists(MARKER):
        reset_marker()
        return 0
    marker_mtime = os.path.getmtime(MARKER)

    git_repos, plain_dirs = discover_targets()

    blocks = []
    changed_files = []

    for repo in git_repos:
        for (_repo, rel, ab, tracked) in git_changed(repo, marker_mtime):
            if tracked:
                d = run(["git", "-C", repo, "diff", "--", rel])
            else:
                d = run(["git", "-C", repo, "diff", "--no-index", "--",
                         "/dev/null", ab])
            if d.strip():
                blocks.append(f"# Repo: {repo}\n# File: {rel}\n{d}")
                changed_files.append(ab)

    for d in plain_dirs:
        for ab in plain_changed(d, marker_mtime):
            try:
                content = open(ab, errors="replace").read()
            except OSError:
                continue
            if content.count("\n") > MAX_FILE_LINES:
                content = "<file too large to inline; skipped>"
            blocks.append(f"# Non-git capsule file: {ab}\n```\n{content}\n```")
            changed_files.append(ab)

    if not blocks:
        reset_marker()
        return 0

    payload = "\n\n".join(blocks)
    if payload.count("\n") > MAX_TOTAL_LINES:
        reset_marker()
        return 0

    try:
        subprocess.run(
            ["codex", "exec", "-s", "read-only", "--skip-git-repo-check",
             "-o", REVIEW_OUT, PROMPT],
            input=payload, text=True, capture_output=True, timeout=180,
        )
    except Exception:
        reset_marker()
        return 0

    reset_marker()

    if not os.path.exists(REVIEW_OUT):
        return 0
    review = open(REVIEW_OUT).read().strip()
    if not review or re.match(r"(?i)^\s*no issues found", review):
        return 0

    # Show capsule-relative paths where possible for readability.
    nice = []
    for ab in changed_files:
        shown = ab
        for root in WATCH_ROOTS:
            if ab.startswith(root.rstrip("/") + "/"):
                shown = ab[len(root.rstrip("/")) + 1:]
                break
        nice.append(shown)
    filelist = ", ".join(nice)

    reason = (
        f"\U0001f916 Codex peer review (gpt-5.5) of code changed this turn "
        f"({filelist}):\n\n{review}\n\n"
        "Relay these Codex findings to {{USER_NAME}} concisely, and fix anything "
        "Critical/High before finishing. If you disagree with a finding, say so "
        "with brief reasoning."
    )
    print(json.dumps({"decision": "block", "reason": reason}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
