#!/usr/bin/env python3
"""
Format a catalyst-os sync changelog for Telegram notification.

Takes file paths from stdin and optional commit messages to produce
clean, domain-grouped bullet points with emojis.

Usage:
    git diff --name-only HEAD~1 | python3 tools/format_sync_changelog.py
    git diff --name-only HEAD~1 | python3 tools/format_sync_changelog.py \
        --commits "feat(tc3): add fast mode\nfix: scrub pipeline"
"""

import sys
import re
import argparse
from collections import defaultdict


# Domain groups: (path_prefix, group_key)
PATH_GROUPS = [
    (".claude/agents/", "agents"),
    (".claude/skills/", "skills"),
    (".claude/commands/", "commands"),
    (".claude/output-styles/", "config"),
    (".claude/sharp-edges/", "config"),
    (".claude-context/", "docs"),
    ("tools/telegram/", "telegram"),
    ("global/integrations/telegram/", "telegram"),
    ("tools/media-engine/", "media"),
    ("tools/product-sourcing/", "sourcing"),
    ("tools/youtube-intel/", "intel"),
    ("tools/tiktok", "intel"),
    ("tools/voice-pipeline/", "tools"),
    ("tools/", "tools"),
    ("global/config/", "config"),
    ("global/governance/", "config"),
    ("global/navigation/", "config"),
    ("global/lib/", "config"),
    ("global/docs/", "docs"),
    ("global/security/", "security"),
    ("global/mcp/", "config"),
    ("global/integrations/", "integrations"),
    ("global/rag/", "tools"),
    ("global/", "config"),
    ("catalyst-design-system/", "design"),
    ("templates/", "templates"),
    ("scripts/", "scripts"),
    ("docs/", "docs"),
    ("monitoring/", "config"),
]

# Display config per group
GROUP_DISPLAY = {
    "agents":       ("🤖", "Agents"),
    "skills":       ("⚡", "Skills"),
    "tools":        ("🔧", "Tools"),
    "telegram":     ("📱", "TC3 Bot"),
    "media":        ("🎬", "Media Engine"),
    "sourcing":     ("🛍️", "Sourcer"),
    "intel":        ("📊", "Intel Tools"),
    "docs":         ("📝", "Docs"),
    "config":       ("⚙️", "System"),
    "security":     ("🔒", "Security"),
    "design":       ("🎨", "Design System"),
    "templates":    ("🏗️", "Templates"),
    "scripts":      ("🔧", "Scripts"),
    "integrations": ("🔌", "Integrations"),
    "commands":     ("⌨️", "Commands"),
}

# Priority order for display
GROUP_PRIORITY = [
    "agents", "tools", "skills", "telegram", "media", "sourcing",
    "intel", "security", "docs", "design", "integrations",
    "commands", "config", "templates", "scripts",
]

MAX_LINES = 8


def classify_file(path: str) -> str:
    """Map a file path to a group key."""
    for prefix, group in PATH_GROUPS:
        if path.startswith(prefix):
            return group
    return "config"


def item_name(path: str) -> str:
    """Extract a clean item name from a file path."""
    from pathlib import PurePosixPath
    p = PurePosixPath(path)

    # Agents: use stem
    if path.startswith(".claude/agents/"):
        name = p.stem
        # Strip emoji prefixes (e.g., "backend-developer" from agent files)
        return name.replace("-", " ").title()

    # Skills: use directory name
    if path.startswith(".claude/skills/"):
        parts = path[len(".claude/skills/"):].split("/")
        return parts[0].replace("-", " ").title()

    # Telegram: use subdirectory after telegram/ (e.g., TC3)
    if "telegram/" in path:
        parts = path.split("telegram/")[-1].split("/")
        name = parts[0] if parts[0] else "config"
        return name.replace("_", " ").replace("-", " ")

    # Tools: use directory or file name
    if path.startswith("tools/"):
        parts = path[len("tools/"):].split("/")
        name = parts[0]
        if "." in name and len(parts) == 1:
            name = PurePosixPath(name).stem
        return name.replace("_", " ").replace("-", " ").title()

    # Root dotfiles: strip leading dot
    name = p.stem.replace("_", " ").replace("-", " ")
    if name.startswith("."):
        name = name[1:]
    return name.title() if name else p.name


def parse_commit_scopes(commits: str) -> dict:
    """Extract scope -> descriptions from conventional commits."""
    scope_map = defaultdict(list)
    if not commits:
        return scope_map

    for line in commits.strip().split("\n"):
        line = line.strip()
        if not line:
            continue
        # Match: type(scope): description  or  type: description
        m = re.match(r"(?:\w+)\(([^)]+)\):\s*(.+)", line)
        if m:
            scope, desc = m.group(1).lower(), m.group(2).strip()
            scope_map[scope].append(desc)
        else:
            m2 = re.match(r"\w+:\s*(.+)", line)
            if m2:
                scope_map["general"].append(m2.group(1).strip())

    return scope_map


def format_group_line(group: str, items: set, count: int) -> str:
    """Format a single group line."""
    emoji, label = GROUP_DISPLAY.get(group, ("📦", group.title()))
    # Filter out items that repeat or are part of the group label
    label_lower = label.lower()
    filtered = sorted(i for i in items if i.lower() != label_lower
                       and i.lower() != label_lower.rstrip("s")
                       and i.lower() not in label_lower)
    total = count

    if not filtered:
        # All items match the group name — just show file count
        detail = f"{total} file{'s' if total != 1 else ''} updated"
    elif len(filtered) == 1 and total == 1:
        detail = filtered[0]
    elif len(filtered) <= 3:
        detail = ", ".join(filtered)
        if total > len(filtered):
            detail += f" + {total - len(filtered)} more"
    else:
        shown = ", ".join(filtered[:2])
        detail = f"{shown} + {total - 2} more"

    return f"  - {emoji} <b>{label}</b> — {detail}"


def format_changelog(files: list, commits: str = "") -> str:
    """Produce a clean changelog from file paths and optional commits."""
    groups = defaultdict(set)
    group_counts = defaultdict(int)

    for f in files:
        f = f.strip()
        if not f:
            continue
        group = classify_file(f)
        name = item_name(f)
        groups[group].add(name)
        group_counts[group] += 1

    if not groups:
        return "Minor internal updates"

    # Sort by priority
    sorted_groups = sorted(
        groups.items(),
        key=lambda x: GROUP_PRIORITY.index(x[0]) if x[0] in GROUP_PRIORITY else 999,
    )

    lines = []
    for group, items in sorted_groups:
        if len(lines) >= MAX_LINES:
            remaining = len(sorted_groups) - len(lines)
            if remaining > 0:
                lines.append(f"  - 📦 <b>Other</b> — {remaining} more area(s) updated")
            break
        lines.append(format_group_line(group, items, group_counts[group]))

    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--commits", default="", help="Newline-separated commit messages")
    args = parser.parse_args()

    files = sys.stdin.read().strip().split("\n")
    print(format_changelog(files, args.commits))


if __name__ == "__main__":
    main()
