#!/usr/bin/env python3
import json
import os
from datetime import datetime
from pathlib import Path

ROOT = Path.home() / "Documents" / "Builder"
REGISTRY = ROOT / "registry"
DAILY = REGISTRY / "daily"
EVENTS_JSONL = REGISTRY / "events.jsonl"

def safe_read_jsonl_tail(path: Path, n: int = 200):
    items = []
    if not path.exists():
        return items
    try:
        lines = path.read_text().splitlines()[-n:]
        for line in lines:
            line = line.strip()
            if not line:
                continue
            try:
                items.append(json.loads(line))
            except Exception:
                # skip malformed
                continue
    except Exception:
        pass
    return items

def rollup():
    DAILY.mkdir(parents=True, exist_ok=True)

    # Basic counts
    capsules = list((ROOT / "capsules").glob("*/")) if (ROOT / "capsules").exists() else []
    fast = 0
    deep = 0
    for c in capsules:
        lane = "standard"
        cj = c / "capsule.json"
        if cj.exists():
            try:
            except Exception:
                pass
        if lane == "standard":
            fast += 1
        else:
            deep += 1

    events = safe_read_jsonl_tail(EVENTS_JSONL, 500)

    summary = {
        "date": datetime.utcnow().strftime("%Y-%m-%d"),
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "capsules_total": len(capsules),
        "capsules_standard": fast,
        "capsules_standard": deep,
        "events_count": len(events),
        "events_tail": events[-20:],
    }

    out = DAILY / f"{summary['date']}.summary.json"
    out.write_text(json.dumps(summary, indent=2))
    print(f"Wrote daily summary: {out}")

if __name__ == "__main__":
    rollup()

