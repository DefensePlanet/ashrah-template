#!/usr/bin/env python3
"""
Catalyst Capsule Navigation with Auto-Context Loading

Navigates to a capsule and returns its CLAUDE.md content for mid-session context loading.
This solves the problem that Claude Code only loads CLAUDE.md at session startup.
"""

import os
import sys
from pathlib import Path
from typing import Optional, Dict


def load_capsule_context(capsule_path: str) -> Optional[Dict[str, str]]:
    """Load capsule's CLAUDE.md and MCP configuration"""
    capsule_path_obj = Path(capsule_path)

    if not capsule_path_obj.exists():
        return None

    context = {
        "path": str(capsule_path_obj),
        "name": capsule_path_obj.name,
        "claude_md": None,
        "mcp_config": None,
        "settings": None
    }

    # Load CLAUDE.md
    claude_md = capsule_path_obj / "CLAUDE.md"
    if claude_md.exists():
        try:
            with open(claude_md, 'r') as f:
                context["claude_md"] = f.read()
        except Exception as e:
            context["claude_md_error"] = str(e)

    # Load MCP configuration
    mcp_json = capsule_path_obj / "ops" / "mcp.json"
    if mcp_json.exists():
        try:
            with open(mcp_json, 'r') as f:
                context["mcp_config"] = f.read()
        except Exception as e:
            context["mcp_config_error"] = str(e)

    # Load .claude settings
    settings_file = capsule_path_obj / ".claude" / "settings.local.json"
    if settings_file.exists():
        try:
            with open(settings_file, 'r') as f:
                context["settings"] = f.read()
        except Exception as e:
            context["settings_error"] = str(e)

    return context


def navigate_with_context(capsule_name: str, capsules_root: str = "{{CATALYST_ROOT}}/capsules") -> Dict:
    """Navigate to capsule and load its context"""
    capsules_root_path = Path(capsules_root)

    # Try to find capsule
    capsule_path = capsules_root_path / capsule_name

    if not capsule_path.exists():
        # Try fuzzy matching
        for item in capsules_root_path.iterdir():
            if item.is_dir() and capsule_name.lower() in item.name.lower():
                capsule_path = item
                break
        else:
            return {
                "success": False,
                "error": f"Capsule '{capsule_name}' not found"
            }

    # Load context
    context = load_capsule_context(str(capsule_path))

    if not context:
        return {
            "success": False,
            "error": f"Failed to load context for '{capsule_name}'"
        }

    return {
        "success": True,
        "capsule": context["name"],
        "path": context["path"],
        "has_claude_md": context["claude_md"] is not None,
        "has_mcp_config": context["mcp_config"] is not None,
        "has_settings": context["settings"] is not None,
        "claude_md_content": context["claude_md"],
        "mcp_config_content": context["mcp_config"],
        "settings_content": context["settings"]
    }


def main():
    """CLI entry point"""
    import argparse
    import json

    parser = argparse.ArgumentParser(
        description="Navigate to capsule and load context for mid-session use"
    )
    parser.add_argument("capsule", help="Capsule name to navigate to")
    parser.add_argument("--format", choices=["json", "claude"], default="claude",
                       help="Output format (json for raw data, claude for {{ORCHESTRATOR_NAME}} consumption)")

    args = parser.parse_args()

    result = navigate_with_context(args.capsule)

    if args.format == "json":
        print(json.dumps(result, indent=2))
    else:
        # Claude/{{ORCHESTRATOR_NAME}} friendly output
        if not result["success"]:
            print(f"❌ Navigation failed: {result['error']}")
            sys.exit(1)

        print(f"✅ Navigated to: {result['capsule']}")
        print(f"📂 Path: {result['path']}")
        print()

        if result["has_claude_md"]:
            print("=" * 80)
            print("CAPSULE CONTEXT (CLAUDE.md)")
            print("=" * 80)
            print(result["claude_md_content"])
            print()
        else:
            print("⚠️  No CLAUDE.md found in this capsule")

        if result["has_settings"]:
            print("=" * 80)
            print("CAPSULE SETTINGS (.claude/settings.local.json)")
            print("=" * 80)
            print(result["settings_content"])
            print()


if __name__ == "__main__":
    main()
