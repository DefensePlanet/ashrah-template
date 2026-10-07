#!/usr/bin/env python3
"""
OpenClaw AGENTS.md Staleness Checker

Checks whether AGENTS.md is stale relative to CLAUDE.md for connected
OpenClaw agents. AGENTS.md Project Context sections are maintained by
{{ORCHESTRATOR_NAME}} (hand-curated), not auto-generated.

Usage:
    python3 tools/openclaw-sync.py --check --all     # Check all agents
    python3 tools/openclaw-sync.py --check {{brand}}  # Check one capsule
    python3 tools/openclaw-sync.py --check --all --json  # JSON output

This tool does NOT auto-generate content. It only reports drift so {{ORCHESTRATOR_NAME}}
knows when to update AGENTS.md after working on a capsule's CLAUDE.md.
"""

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path

CATALYST_ROOT = Path("{{CATALYST_ROOT}}")
OPENCLAW_CONFIG = Path.home() / ".openclaw" / "openclaw.json"


def load_openclaw_config():
    """Load openclaw.json and return agent workspace mappings."""
    if not OPENCLAW_CONFIG.exists():
        print(f"Error: OpenClaw config not found at {OPENCLAW_CONFIG}", file=sys.stderr)
        sys.exit(1)
    with open(OPENCLAW_CONFIG) as f:
        config = json.load(f)
    agents = {}
    for agent in config.get("agents", {}).get("list", []):
        workspace = agent.get("workspace")
        if workspace and agent.get("id") != "main":
            agents[agent["id"]] = {
                "workspace": Path(workspace),
                "name": agent.get("name", agent["id"]),
            }
    return agents


def check_staleness(capsule_path):
    """Check if AGENTS.md is stale relative to CLAUDE.md."""
    agents_md = capsule_path / "AGENTS.md"
    claude_md = capsule_path / "CLAUDE.md"

    result = {"capsule": str(capsule_path)}

    if not agents_md.exists():
        result["status"] = "missing_agents_md"
        result["message"] = "AGENTS.md not found — needs creation"
        return result

    if not claude_md.exists():
        result["status"] = "missing_claude_md"
        result["message"] = "CLAUDE.md not found"
        return result

    agents_mtime = agents_md.stat().st_mtime
    claude_mtime = claude_md.stat().st_mtime
    diff_hours = (claude_mtime - agents_mtime) / 3600

    # Check for staleness marker in AGENTS.md
    content = agents_md.read_text()
    updated_match = re.search(r"<!-- Updated: ([\d-]+)", content)
    last_updated = updated_match.group(1) if updated_match else "unknown"

    # Check if Project Context section exists
    has_context = "## Project Context" in content

    result["agents_modified"] = datetime.fromtimestamp(agents_mtime).strftime("%Y-%m-%d %H:%M")
    result["claude_modified"] = datetime.fromtimestamp(claude_mtime).strftime("%Y-%m-%d %H:%M")
    result["context_date"] = last_updated
    result["has_project_context"] = has_context

    if not has_context:
        result["status"] = "no_context"
        result["message"] = "AGENTS.md exists but has no Project Context section"
    elif diff_hours > 24:
        result["status"] = "stale"
        result["hours_behind"] = round(diff_hours, 1)
        result["message"] = f"STALE by {round(diff_hours, 1)}h — CLAUDE.md updated since last AGENTS.md edit"
    elif diff_hours > 0:
        result["status"] = "minor_drift"
        result["hours_behind"] = round(diff_hours, 1)
        result["message"] = f"Minor drift ({round(diff_hours, 1)}h) — may not need update"
    else:
        result["status"] = "current"
        result["message"] = "Up to date"

    return result


def resolve_capsule_path(path_arg):
    """Resolve capsule path from argument (relative or absolute)."""
    p = Path(path_arg)
    if p.is_absolute() and p.exists():
        return p
    candidate = CATALYST_ROOT / p
    if candidate.exists():
        return candidate
    candidate = CATALYST_ROOT / "capsules" / p
    if candidate.exists():
        return candidate
    print(f"Error: Could not resolve capsule path: {path_arg}", file=sys.stderr)
    sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="Check OpenClaw AGENTS.md staleness relative to capsule CLAUDE.md"
    )
    parser.add_argument("capsule", nargs="?", help="Capsule path or name")
    parser.add_argument("--all", action="store_true", help="Check all connected capsules")
    parser.add_argument("--check", action="store_true", default=True, help="Check staleness (default)")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()

    if args.all:
        agents = load_openclaw_config()
        results = {}
        for agent_id, info in agents.items():
            result = check_staleness(info["workspace"])
            result["agent_id"] = agent_id
            results[agent_id] = result
            if not args.json:
                status_icon = {
                    "current": "✅",
                    "minor_drift": "🟡",
                    "stale": "🔴",
                    "no_context": "⚠️",
                    "missing_agents_md": "❌",
                    "missing_claude_md": "❌",
                }.get(result["status"], "?")
                print(f"  {status_icon} {agent_id}: {result['message']}")
        if args.json:
            print(json.dumps(results, indent=2))
        return

    if not args.capsule:
        parser.print_help()
        print("\nConnected agents:")
        agents = load_openclaw_config()
        for agent_id, info in agents.items():
            print(f"  - {agent_id} → {info['workspace']}")
        sys.exit(1)

    capsule_path = resolve_capsule_path(args.capsule)
    result = check_staleness(capsule_path)

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(result["message"])
        if result.get("context_date"):
            print(f"  Context date: {result['context_date']}")
        if result.get("claude_modified"):
            print(f"  CLAUDE.md last modified: {result['claude_modified']}")


if __name__ == "__main__":
    main()
