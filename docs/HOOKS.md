# Hook System Guide

Hooks are extension points that let you run custom code at key moments during a Claude Code session. They are the primary mechanism for adding behavior like memory retrieval, task logging, notification, and quality gates -- without modifying Claude Code itself.

## What Are Hooks

A hook is a script (Python or shell) that Claude Code executes at a specific lifecycle event. Hooks can:

- **Observe** -- Log events, record metrics, store memories
- **Enrich** -- Inject context before a tool executes (e.g., retrieve relevant past patterns)
- **Gate** -- Block a tool from executing by returning a non-zero exit code (PreToolUse only)
- **Notify** -- Send notifications when events occur (TTS, push notifications, etc.)

Hooks are configured in `.claude/settings.json` and run as subprocesses. They receive event context on stdin as JSON and communicate back through their exit code and stdout/stderr.

## Hook Types

Claude Code supports these hook events:

| Event | When It Fires | Can Block? | Use Cases |
|---|---|---|---|
| `PreToolUse` | Before any tool executes | Yes (exit non-zero) | Memory retrieval, routing checks, governance gates |
| `PostToolUse` | After any tool completes | No | Task logging, outcome tracking, memory storage |
| `Stop` | When the agent finishes responding | No | TTS notifications, session summaries |
| `SubagentStart` | When a subagent is spawned | No | Lifecycle tracking |
| `SubagentStop` | When a subagent terminates | No | Outcome capture, cleanup |
| `SessionEnd` | When the Claude Code session ends | No | State persistence, cleanup |

### Event Matchers

Hooks can be scoped to specific tools using the `matcher` field:

```json
{
  "matcher": "Edit|Write",
  "hooks": [{ "type": "command", "command": "python3 /path/to/hook.py" }]
}
```

The `matcher` is a regex pattern matched against the tool name. Common patterns:

- `"Edit|Write"` -- Fires only for file edit/write operations
- `"Task"` -- Fires only for agent delegation
- `"Bash"` -- Fires only for shell commands
- (no matcher) -- Fires for all tools / every occurrence of the event

## How Hooks Work

### Input

Hooks receive a JSON payload on stdin with information about the event. The payload structure varies by event type but typically includes:

```json
{
  "hook_event_name": "PostToolUse",
  "tool_name": "Edit",
  "tool_input": { ... },
  "tool_output": { ... }
}
```

### Output

- **Exit code 0** -- Success. For `PreToolUse`, this means "allow the tool to proceed."
- **Exit code non-zero** -- For `PreToolUse`, this blocks the tool from executing. For other events, the exit code is logged but does not affect execution.
- **Stdout** -- Printed to the Claude Code session as context (visible to the agent).
- **Stderr** -- Used for logging and debugging (not injected into the session).

### Execution

Hooks run as subprocesses of Claude Code. They have access to:
- The filesystem
- Environment variables (including `CLAUDE_HOOKS_LOG_DIR` for log output)
- Network (for calling services like the Agent Memory MCP server)

Hooks should be fast. Long-running hooks delay tool execution. Use timeouts where possible.

## Built-in Hooks

Catalyst ships with these hooks configured in `.claude/settings.json`:

### Post-Tool-Use: File Tracking

**Matcher:** `Edit|Write`
**Script:** `tools/hooks/post_tool_use.py`

Runs after every file edit or write operation. Tracks which files were modified during the session for later review and capsule state updates.

### Post-Tool-Use: Delegation Validation

**Matcher:** `Task`
**Script:** `tools/{{ORCHESTRATOR_NAME_LOWER}}-validation-hook.py`

Runs after every agent delegation. Validates the agent's output and logs the task outcome (agent name, task summary, duration, success/failure) to `quality.db` for performance tracking.

### Stop: TTS Notification

**Script:** `simple_tts_hook_fast.py`

Runs when the orchestrator finishes responding. Extracts a `<tts-summary>` tag from the response and speaks it aloud using the system text-to-speech engine. This provides audio feedback so {{USER_NAME}} knows when a task is complete without watching the terminal.

### Session End: Cleanup

**Script:** `tools/hooks/on_session_end.py`

Runs when the Claude Code session ends. Performs cleanup tasks like persisting session state.

### Session End: Capsule Update

**Script:** `tools/hooks/simple_capsule_update.py`

Runs when the session ends. Updates capsule metadata based on work performed during the session.

## Creating Custom Hooks

### Step 1: Write the script

Create a Python script that reads JSON from stdin and does something useful:

```python
#!/usr/bin/env python3
"""Example: Log all Bash commands to a file."""

import json
import sys
from datetime import datetime

def main():
    # Read the event payload from stdin
    raw = sys.stdin.read()
    if not raw.strip():
        return 0

    payload = json.loads(raw)

    tool_name = payload.get("tool_name", "")
    tool_input = payload.get("tool_input", {})

    # Only care about Bash commands
    if tool_name != "Bash":
        return 0

    command = tool_input.get("command", "")

    # Log to file
    with open("/tmp/catalyst-bash-log.jsonl", "a") as f:
        f.write(json.dumps({
            "timestamp": datetime.utcnow().isoformat(),
            "command": command
        }) + "\n")

    return 0

if __name__ == "__main__":
    raise SystemExit(main())
```

### Step 2: Make it executable

```bash
chmod +x /path/to/my_hook.py
```

### Step 3: Test it standalone

```bash
echo '{"hook_event_name":"PostToolUse","tool_name":"Bash","tool_input":{"command":"ls"}}' | python3 /path/to/my_hook.py
```

### Step 4: Register in settings.json

Add your hook to `.claude/settings.json`:

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": "python3 /path/to/my_hook.py"
          }
        ]
      }
    ]
  }
}
```

### Step 5: Verify

Start a new Claude Code session and trigger the relevant tool. Check your hook's output to confirm it is running.

## Configuration

Hooks are configured in `.claude/settings.json` under the `hooks` key. The structure is:

```json
{
  "hooks": {
    "<EventName>": [
      {
        "matcher": "<regex pattern>",  // Optional: filter by tool name
        "hooks": [
          {
            "type": "command",
            "command": "<shell command to execute>",
            "timeout": 30  // Optional: timeout in seconds
          }
        ]
      }
    ]
  }
}
```

### Configuration Rules

- **Multiple hooks per event**: You can register multiple hook entries for the same event. They all run.
- **Multiple matchers**: Different matchers can trigger different scripts for the same event type.
- **No matcher**: Omitting `matcher` means the hook fires for every occurrence of that event.
- **Timeout**: Optional. Defaults to Claude Code's built-in timeout. Set explicit timeouts for hooks that call external services.
- **Ordering**: Hooks within the same event fire in the order they appear in the array.

### Full Example

Here is the Catalyst hook configuration:

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Edit|Write",
        "hooks": [
          {
            "type": "command",
            "command": "python3 /absolute/path/to/post_tool_use.py"
          }
        ]
      },
      {
        "matcher": "Task",
        "hooks": [
          {
            "type": "command",
            "command": "python3 /absolute/path/to/validation-hook.py"
          }
        ]
      }
    ],
    "Stop": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "python3 /absolute/path/to/tts_hook.py"
          }
        ]
      }
    ],
    "SessionEnd": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "python3 /absolute/path/to/on_session_end.py",
            "timeout": 30
          },
          {
            "type": "command",
            "command": "python3 /absolute/path/to/capsule_update.py",
            "timeout": 30
          }
        ]
      }
    ]
  }
}
```

### Settings File Priority

Claude Code loads settings from multiple locations (highest priority first):

1. Enterprise managed settings
2. Command line arguments
3. `.claude/settings.local.json` (project-local, gitignored)
4. `.claude/settings.json` (project-shared, committed)
5. `~/.claude/settings.json` (user-level)

Hook configurations merge across levels. Put project-specific hooks in `.claude/settings.json` and personal hooks in `~/.claude/settings.json`.
```

---