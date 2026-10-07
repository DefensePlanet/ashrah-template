#!/usr/bin/env python3
"""
Sharp Edges Loader Utility

Loads and filters sharp-edges patterns for code review integration.
"""

import os
import fnmatch
import json
from pathlib import Path
from typing import List, Dict, Any, Optional

try:
    import yaml
except ImportError:
    yaml = None


SHARP_EDGES_DIR = Path(__file__).parent
CATALYST_ROOT = Path(os.environ.get('CATALYST_ROOT', '{{CATALYST_ROOT}}'))


def load_yaml_file(filepath: Path) -> List[Dict[str, Any]]:
    """Load a YAML file and return its contents."""
    if yaml is None:
        # Fallback: try to parse simple YAML manually or return empty
        return []

    if not filepath.exists():
        return []

    with open(filepath, 'r') as f:
        content = yaml.safe_load(f)

    # Handle files with 'edges' key or direct list
    if isinstance(content, dict):
        return content.get('edges', [])
    elif isinstance(content, list):
        return content
    return []


def load_all_sharp_edges() -> List[Dict[str, Any]]:
    """Load all sharp-edges from YAML files in the directory."""
    all_edges = []

    for filepath in SHARP_EDGES_DIR.glob('*.yaml'):
        # Skip schema and internal files
        if filepath.name.startswith('_'):
            continue

        edges = load_yaml_file(filepath)
        for edge in edges:
            edge['_source_file'] = filepath.name
        all_edges.extend(edges)

    return all_edges


def filter_for_files(
    edges: List[Dict[str, Any]],
    file_paths: List[str]
) -> List[Dict[str, Any]]:
    """Filter sharp-edges to those applicable to the given file paths."""
    applicable = []

    for edge in edges:
        detection = edge.get('detection', [])

        # If no detection rules, include based on source file type match
        if not detection:
            applicable.append(edge)
            continue

        for rule in detection:
            file_patterns = rule.get('files', ['*'])

            for file_path in file_paths:
                for pattern in file_patterns:
                    if fnmatch.fnmatch(file_path, pattern) or fnmatch.fnmatch(os.path.basename(file_path), pattern):
                        applicable.append(edge)
                        break
                else:
                    continue
                break
            else:
                continue
            break

    # Deduplicate by id
    seen = set()
    unique = []
    for edge in applicable:
        if edge.get('id') not in seen:
            seen.add(edge.get('id'))
            unique.append(edge)

    return unique


def filter_by_severity(
    edges: List[Dict[str, Any]],
    min_severity: str = 'info'
) -> List[Dict[str, Any]]:
    """Filter edges by minimum severity level."""
    severity_order = {'critical': 1, 'warning': 2, 'info': 3}
    min_level = severity_order.get(min_severity, 3)

    return [
        edge for edge in edges
        if severity_order.get(edge.get('severity', 'info'), 3) <= min_level
    ]


def filter_by_category(
    edges: List[Dict[str, Any]],
    categories: List[str]
) -> List[Dict[str, Any]]:
    """Filter edges by category."""
    return [
        edge for edge in edges
        if edge.get('category') in categories
    ]


def get_detection_regex(edge: Dict[str, Any]) -> List[str]:
    """Extract regex patterns from an edge's detection rules."""
    patterns = []
    for rule in edge.get('detection', []):
        if rule.get('type') == 'regex' and rule.get('value'):
            patterns.append(rule['value'])
    return patterns


def format_edge_for_review(edge: Dict[str, Any]) -> str:
    """Format a sharp-edge for inclusion in code review output."""
    severity_emoji = {
        'critical': '\U0001F6A8',  # rotating light
        'warning': '\u26A0\uFE0F',  # warning
        'info': '\U0001F4A1'  # bulb
    }

    emoji = severity_emoji.get(edge.get('severity', 'info'), '\U0001F4A1')

    output = [
        f"{emoji} **{edge.get('severity', 'info').upper()}**: {edge.get('pattern')}",
        f"   Category: {edge.get('category', 'unknown')}",
        f"   Why: {edge.get('why', 'No explanation provided')}",
        f"   Fix: {edge.get('fix', 'No fix provided')}",
    ]

    if edge.get('examples', {}).get('bad'):
        output.append(f"   Bad example: `{edge['examples']['bad'].strip()[:80]}...`")

    return '\n'.join(output)


def to_json(edges: List[Dict[str, Any]]) -> str:
    """Convert edges to JSON for integration with other tools."""
    return json.dumps(edges, indent=2)


# CLI interface
if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Sharp Edges Loader')
    parser.add_argument('--files', nargs='+', help='Filter for specific files')
    parser.add_argument('--severity', choices=['critical', 'warning', 'info'],
                        default='info', help='Minimum severity level')
    parser.add_argument('--category', nargs='+', help='Filter by categories')
    parser.add_argument('--json', action='store_true', help='Output as JSON')
    parser.add_argument('--stats', action='store_true', help='Show statistics only')

    args = parser.parse_args()

    # Load all edges
    edges = load_all_sharp_edges()

    # Apply filters
    if args.files:
        edges = filter_for_files(edges, args.files)

    edges = filter_by_severity(edges, args.severity)

    if args.category:
        edges = filter_by_category(edges, args.category)

    # Output
    if args.stats:
        by_severity = {}
        by_category = {}
        for e in edges:
            sev = e.get('severity', 'info')
            cat = e.get('category', 'unknown')
            by_severity[sev] = by_severity.get(sev, 0) + 1
            by_category[cat] = by_category.get(cat, 0) + 1

        print(f"Total: {len(edges)} sharp edges")
        print(f"By severity: {by_severity}")
        print(f"By category: {by_category}")
    elif args.json:
        print(to_json(edges))
    else:
        for edge in edges:
            print(format_edge_for_review(edge))
            print()
