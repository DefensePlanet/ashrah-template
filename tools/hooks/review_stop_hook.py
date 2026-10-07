#!/usr/bin/env python3
"""Stop hook — Triggers automatic lightweight code review when code files were changed.

Checks the review queue accumulated by review_accumulator.py. If unreviewed
code files exist, blocks Claude from stopping and injects review instructions
via the decision/reason JSON protocol.

Quad-guard loop prevention:
1. stop_hook_active flag (built-in) — exit immediately if true
2. File state tracking — files marked reviewed after block output
3. 30-second cooldown — skip if reviewed recently
4. last_assistant_message check — detect if review already ran
"""

from __future__ import annotations

import json
import os
import sys
import time
import fcntl
from pathlib import Path
from typing import Optional

QUEUE_DIR = Path("/tmp/catalyst-review-queues")
DISABLED_FLAG = Path("/tmp/catalyst-auto-review-disabled")
COOLDOWN_SECONDS = 30
MAX_FILES_IN_REASON = 20


def read_queue(session_id: str) -> Optional[dict]:
    """Read the review queue for this session."""
    queue_file = QUEUE_DIR / f"{session_id}.json"
    if not queue_file.exists():
        return None

    try:
        with open(queue_file, 'r') as f:
            return json.loads(f.read())
    except Exception:
        return None


def mark_reviewed(session_id: str) -> None:
    """Mark all files as reviewed and set cooldown timestamp."""
    queue_file = QUEUE_DIR / f"{session_id}.json"
    if not queue_file.exists():
        return

    fd = None
    try:
        fd = os.open(str(queue_file), os.O_RDWR)
        fcntl.flock(fd, fcntl.LOCK_EX)

        with os.fdopen(os.dup(fd), 'r') as f:
            queue = json.loads(f.read())

        for entry in queue.get("files", []):
            entry["reviewed"] = True

        queue["last_review_timestamp"] = time.time()

        new_content = json.dumps(queue, indent=2)
        os.lseek(fd, 0, os.SEEK_SET)
        os.ftruncate(fd, 0)
        os.write(fd, new_content.encode())

        fcntl.flock(fd, fcntl.LOCK_UN)
    except Exception:
        pass
    finally:
        if fd is not None:
            try:
                os.close(fd)
            except Exception:
                pass


def build_review_reason(unreviewed_files: list[dict]) -> str:
    """Build the reason string that Claude will see as review instructions."""
    file_paths = [f["path"] for f in unreviewed_files]

    # Cap the list for token efficiency
    display_paths = file_paths[:MAX_FILES_IN_REASON]
    overflow = len(file_paths) - MAX_FILES_IN_REASON

    file_list = "\n".join(f"- {p}" for p in display_paths)
    if overflow > 0:
        file_list += f"\n- ... and {overflow} more files"

    space_separated = " ".join(f'"{p}"' for p in file_paths)

    return f"""AUTOMATIC_TURN_REVIEW: {len(file_paths)} code file(s) were modified during this turn. Run a lightweight code review before responding.

Files changed:
{file_list}

Instructions:
1. Get the diff: run `git diff HEAD -- {space_separated}` (for untracked files, read content directly)
2. Invoke Code Reviewer via Task tool with subagent_type="\U0001f9d0 Code Reviewer" and model="sonnet"
   - Pass: context_level="lightweight", files_changed={json.dumps(file_paths)}, and the git diff
   - IMPORTANT: Use model="sonnet" on the Task call for speed. Opus is reserved for manual/intentional reviews.
3. Present a brief summary of findings to the user (severity breakdown + key items)
4. Log review to quality.db: echo '{{"context_level":"lightweight","findings":{{"critical":[],"major":[],"minor":[]}},"file_path":"multi-file","session_id":"auto"}}' | python3 {{CATALYST_ROOT}}/monitoring/log_code_review.py
   - Replace the empty arrays with actual finding descriptions from the review
5. This is INFORMATIONAL ONLY — do not block any user operations
6. After presenting findings, respond normally to complete your original task"""


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

    # GUARD 0: Disabled via /auto-review toggle
    if DISABLED_FLAG.exists():
        return 0

    # GUARD 1: Loop prevention — if stop_hook_active, exit immediately
    if payload.get("stop_hook_active", False):
        return 0

    session_id = payload.get("session_id", "unknown")

    # Read the queue
    queue = read_queue(session_id)
    if not queue:
        return 0

    # GUARD 2: Check for unreviewed files
    unreviewed = [f for f in queue.get("files", []) if not f.get("reviewed", False)]
    if not unreviewed:
        return 0

    # GUARD 3: Cooldown — skip if reviewed recently
    last_review = queue.get("last_review_timestamp", 0)
    if time.time() - last_review < COOLDOWN_SECONDS:
        return 0

    # GUARD 4: Check last_assistant_message for evidence review already happened
    last_msg = payload.get("last_assistant_message", "")
    if "AUTOMATIC_TURN_REVIEW" in last_msg or "Review Results" in last_msg:
        # Review was already done this cycle, mark files and exit
        mark_reviewed(session_id)
        return 0

    # Write detailed instructions to file ({{ORCHESTRATOR_NAME}} reads this), keep terminal output minimal
    reason = build_review_reason(unreviewed)
    context_file = QUEUE_DIR / f"{session_id}_review_context.txt"
    try:
        context_file.write_text(reason)
    except Exception:
        pass

    file_count = len(unreviewed)
    decision = {
        "decision": "block",
        "reason": f"AUTOMATIC_TURN_REVIEW: {file_count} file(s). Details: {context_file}",
    }

    print(json.dumps(decision))

    # Mark files as reviewed AFTER outputting block decision
    # Guard 1 (stop_hook_active) and Guard 4 (last_assistant_message)
    # prevent re-triggering on the next Stop cycle
    mark_reviewed(session_id)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
