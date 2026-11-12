#!/usr/bin/env python3
"""PostToolUse hook — Accumulates code file changes for automatic review.

Fires after Edit/Write/NotebookEdit. Appends changed file paths to a
session-scoped queue file. The review_stop_hook.py reads this queue
when Claude is about to stop and triggers a lightweight code review.

Non-blocking, fast (~20ms). Pure filesystem operations.
"""

import json
import os
import sys
import time
import fcntl
from pathlib import Path

# Extensions that warrant code review
REVIEWABLE_EXTENSIONS = {
    '.py', '.js', '.ts', '.tsx', '.jsx', '.mjs', '.cjs',
    '.swift', '.kt', '.java',
    '.go', '.rs', '.c', '.cpp', '.h', '.hpp',
    '.sh', '.bash', '.zsh',
    '.sql',
    '.css', '.scss', '.less',
    '.html', '.vue', '.svelte',
    '.rb', '.php', '.ex', '.exs',
}

# Paths to always skip regardless of extension
SKIP_PATH_PATTERNS = (
    '/archive/',
    '/logs/',
    '/.claude/',
    '/memory/',
    '/node_modules/',
    '/__pycache__/',
    '/dist/',
    '/build/',
    '/.git/',
    'CLAUDE.md',
    'MEMORY.md',
    'session_log.md',
)

QUEUE_DIR = Path("/tmp/catalyst-review-queues")


def should_review(file_path: str) -> bool:
    """Determine if a file change warrants code review."""
    if not file_path:
        return False

    # Skip certain paths
    for pattern in SKIP_PATH_PATTERNS:
        if pattern in file_path:
            return False

    # Check extension
    ext = Path(file_path).suffix.lower()
    return ext in REVIEWABLE_EXTENSIONS


def append_to_queue(session_id: str, file_path: str, tool_name: str) -> None:
    """Atomically append a file entry to the session's review queue."""
    QUEUE_DIR.mkdir(parents=True, exist_ok=True)
    queue_file = QUEUE_DIR / f"{session_id}.json"

    # Read existing queue with file lock
    fd = None
    try:
        fd = os.open(str(queue_file), os.O_RDWR | os.O_CREAT)
        fcntl.flock(fd, fcntl.LOCK_EX)

        # Read current content
        with os.fdopen(os.dup(fd), 'r') as f:
            content = f.read()

        if content.strip():
            queue = json.loads(content)
        else:
            queue = {"session_id": session_id, "files": [], "last_review_timestamp": 0}

        # Stale check: reset if older than 24 hours
        if queue["files"] and queue["files"][0].get("timestamp", 0) < time.time() - 86400:
            queue = {"session_id": session_id, "files": [], "last_review_timestamp": 0}

        # Deduplicate: if same file already unreviewed, update timestamp
        existing = None
        for entry in queue["files"]:
            if entry["path"] == file_path and not entry.get("reviewed", False):
                existing = entry
                break

        if existing:
            existing["timestamp"] = time.time()
            existing["tool"] = tool_name
        else:
            queue["files"].append({
                "path": file_path,
                "tool": tool_name,
                "timestamp": time.time(),
                "reviewed": False,
            })

        # Write back atomically
        new_content = json.dumps(queue, indent=2)
        os.lseek(fd, 0, os.SEEK_SET)
        os.ftruncate(fd, 0)
        os.write(fd, new_content.encode())

        fcntl.flock(fd, fcntl.LOCK_UN)
    except Exception:
        # Non-blocking: if anything fails, skip silently
        pass
    finally:
        if fd is not None:
            try:
                os.close(fd)
            except Exception:
                pass


def main() -> int:
    try:
        raw = sys.stdin.read()
    except Exception:
        return 0

    if not raw.strip():
        return 0

    try:
        payload = json.loads(raw)
    except Exception:
        return 0

    tool_name = payload.get("tool_name", "")
    if tool_name not in ("Edit", "Write", "NotebookEdit"):
        return 0

    session_id = payload.get("session_id", "unknown")

    # Extract file path from tool input
    tool_input = payload.get("tool_input", {})
    file_path = tool_input.get("file_path", "")

    if not file_path:
        # Try tool_response for filePath
        tool_response = payload.get("tool_response", {})
        file_path = tool_response.get("filePath", "")

    if not should_review(file_path):
        return 0

    append_to_queue(session_id, file_path, tool_name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
