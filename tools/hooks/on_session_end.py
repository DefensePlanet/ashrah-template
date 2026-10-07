#!/usr/bin/env python3
"""OnSessionEnd hook - Runs session audit and logs activity"""

import sys
import json
import datetime
from pathlib import Path

# Add hook utilities to path
sys.path.insert(0, str(Path(__file__).parent / "lib"))
from hook_utils import HookResult, get_catalyst_root, log_hook_execution


def main():
    # Read hook input from stdin (JSON format)
    try:
        hook_input = json.load(sys.stdin)
    except Exception:
        hook_input = {}

    session_id = hook_input.get("session_id", "unknown")
    cwd = hook_input.get("cwd", str(Path.cwd()))

    # Determine capsule from cwd
    builder_root = get_catalyst_root()
    if str(cwd).startswith(str(builder_root / "capsules")):
        relative = Path(cwd).relative_to(builder_root / "capsules")
        capsule = str(relative.parts[0]) if relative.parts else "SYSTEM"
    else:
        capsule = "SYSTEM"

    timestamp = datetime.datetime.now().isoformat()

    # Collect session metrics
    session_data = {
        "timestamp": timestamp,
        "session_id": session_id,
        "capsule": capsule,
        "cwd": cwd,
    }

    # Log session end
    audit_log = builder_root / "registry" / "daily" / "session_audit.log"
    audit_log.parent.mkdir(parents=True, exist_ok=True)

    try:
        with open(audit_log, 'a') as f:
            f.write(json.dumps(session_data) + "\n")

        result = HookResult(success=True, message=f"✓ Session audit logged for {capsule}")
    except Exception as e:
        result = HookResult(success=False, message=f"⚠ Audit logging failed: {str(e)}", block=False)

    log_hook_execution("on_session_end", result)
    return result


if __name__ == "__main__":
    result = main()
    if not result.success:
        print(result.message, file=sys.stderr)
    else:
        print(result.message)
    sys.exit(result.exit_code())