#!/usr/bin/env python3
"""List all Catalyst capsules — compact one-liner view.

Reads from global/config/capsule-registry.yaml and cross-references
with the capsules/ directory.

Usage: python3 tools/list-capsules.py
"""

import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(SCRIPT_DIR)
REGISTRY = os.path.join(ROOT, "global", "config", "capsule-registry.yaml")
REGISTRY_EXAMPLE = os.path.join(ROOT, "global", "config", "capsule-registry.example.yaml")
CAPSULES_DIR = os.path.join(ROOT, "capsules")


def load_registry():
    """Load capsule registry YAML (minimal parser, no PyYAML dependency)."""
    capsules = {}
    current = None

    registry_path = REGISTRY if os.path.exists(REGISTRY) else REGISTRY_EXAMPLE
    with open(registry_path, "r", encoding="utf-8") as f:
        for line in f:
            stripped = line.rstrip()
            if not stripped or stripped.lstrip().startswith("#"):
                continue

            if line.startswith("  ") and not line.startswith("    ") and stripped.endswith(":"):
                key = stripped.strip().rstrip(":")
                if key != "capsules":
                    current = key
                    capsules[current] = {}
                continue

            if line.startswith("    ") and current and ":" in stripped:
                prop, _, val = stripped.partition(":")
                prop = prop.strip()
                val = val.strip().strip('"').strip("'")
                if val == "null":
                    val = None
                capsules[current][prop] = val

    return capsules


STATUS_ORDER = {"active": 0, "planning": 1, "dormant": 2}


def main():
    registry = load_registry()

    print(f"Catalyst capsules ({CAPSULES_DIR})")

    # Sort by status group (active → planning → dormant), then alphabetical
    entries = sorted(registry.items(), key=lambda x: (STATUS_ORDER.get(x[1].get("status", "active"), 9), x[0]))

    current_status = None
    for slug, meta in entries:
        status = meta.get("status", "active")

        # Print group header on status change
        if status != current_status:
            if current_status is not None:
                print()
            current_status = status

        emoji = meta.get("emoji", " ")
        name = meta.get("name", slug)
        shortcut = meta.get("shortcut")

        shortcut_str = f" ({shortcut})" if shortcut else ""
        suffix = "" if status == "active" else f" [{status}]"

        print(f"  {emoji}  {name}{shortcut_str}{suffix}")


if __name__ == "__main__":
    main()
