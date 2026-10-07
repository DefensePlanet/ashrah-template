#!/usr/bin/env python3
import argparse, json, os, shutil, subprocess, sys, time
from pathlib import Path

ROOT = Path.home() / "Documents" / "Builder"
CAPSULES = ROOT / "capsules"
REG = ROOT / "registry" / "projects.json"
GEN = ROOT / "tools" / "gen-config.sh"
MERGER = ROOT / "tools" / "merge_mcp.py"

def kebab(s): return "-".join("".join(c if c.isalnum() else " " for c in s).split()).lower()

def classify(p: Path):
    # umbrella guard
try:
    files = [f for f in p.iterdir() if f.is_file()]
    dirs  = [d for d in p.iterdir() if d.is_dir()]
except Exception:
    return ("skip", [], ("", ""))
if not files and len(dirs) >= 3:
    pats = (".swift",".m",".mm",".xib",".storyboard",".ts",".tsx",".js",".jsx",".py",".rb",".sh",".json",".yaml",".yml")
    code_deep = 0
    for f in p.rglob('*'):
        if f.is_file() and f.suffix in pats:
            code_deep += 1
            if code_deep >= 3:
                break
    if code_deep == 0:
        return ("skip", [], ("", ""))
        return ("web", ["site"], ("src/web/site", kebab(p.name)))
    # n8n
    if any(p.glob("**/*n8n*.json")) or "n8n" in p.name.lower():
        return ("automation", ["n8n"], ("src/automation/n8n", kebab(p.name)))
    # Shortcuts
    if any(p.glob("**/*.shortcut")) or "shortcut" in p.name.lower():
        return ("automation", ["shortcuts"], ("src/automation/shortcuts", kebab(p.name)))
    # AppleScript
    if any(p.glob("**/*.scpt")) or any(p.glob("**/*.applescript")):
        return ("automation", ["macos"], ("src/automation/macos/applescript", kebab(p.name)))
    # Python default → macOS automation
    if any(p.glob("**/*.py")):
        return ("automation", ["macos"], ("src/automation/macos/python", kebab(p.name)))
    # Fallback: treat as web app container
    return ("web", ["web_app"], ("src/web/app", kebab(p.name)))

def ensure_capsule(slug):
    cap = CAPSULES / slug
    if not cap.exists():
        subprocess.run([str(ROOT / "tools" / "new-capsule.sh"), slug], check=True)
    return cap

def write_spec(cap: Path, name, slug, branch, targets):
    sp = cap/"spec"/"requirements.yaml"
    if sp.exists() and sp.read_text().strip(): return
    sp.parent.mkdir(parents=True, exist_ok=True)
    yaml = f"""project:
  name: "{name}"
  slug: "{slug}"
  branch: "{branch}"
  targets: {json.dumps(targets)}
objectives: ["Migrated from development root"]
constraints: {{ budget_tokens: 150000, runtime_envs: ["macOS_15"], secrets: [] }}
inputs: {{ data_sources: [] }}
outputs: {{ deliverables: ["Project migrated into capsule"] }}
definition_of_done: ["Build runs and passes smoke tests"]
handoff: {{ base_path: "{cap}", notify: [] }}
notes: {{ labels: [], risks: [], assumptions: [] }}
runtime:
  macos_python: {{ required: {str("macos" in targets or "macos_app" in targets).lower()}, python_version: "3.11", packaging: "uv", entrypoint: "" }}
cms: {{ type: null, models: [], roles: [], deploy: null, webhooks: [] }}
"""
    sp.write_text(yaml)

def gen_config(cap: Path):
    if GEN.exists() and os.access(GEN, os.X_OK):
        subprocess.run([str(GEN), str(cap)], check=True)
    else:
        print("WARN: gen-config.sh missing", file=sys.stderr)

def merge_mcp(cap: Path, src: Path):
    local = None
    for cand in [src/".mcp.json", src/".mcp.json.template"]:
        if cand.exists(): local = cand; break
    gen = cap/".mcp.json"
    if local and gen.exists() and MERGER.exists():
        subprocess.run([str(MERGER), str(gen), str(local), str(gen), str(src)], check=True)

def load_reg():
    REG.parent.mkdir(parents=True, exist_ok=True)
    if not REG.exists() or not REG.read_text().strip(): REG.write_text("[]\n")
    try: return json.loads(REG.read_text())
    except: REG.write_text("[]\n"); return []
def save_reg(rows): REG.write_text(json.dumps(rows, indent=2)+"\n")
def in_reg(reg, slug): return any(r.get("slug")==slug for r in reg)


SKIP_NAMES = {n.lower() for n in [
    "__pycache__", "pycache", "logs", "log", "tmp", "temp", "debug", "output", "outputs",
    "cache", ".git", "dist", "build", "node_modules", ".idea", ".vscode"
]}
JUNK_DIRS = {"node_modules","dist","build",".next",".nuxt",".vercel",".expo",".idea",".vscode"}
MIN_CODE_FILES = 5  # require at least this many code-ish files to count as a project
def looks_junky(src):
    import os
    from pathlib import Path
    src = Path(src)
    if not src.exists(): return True
    # Count code files
    pats = (".py",".ts",".tsx",".js",".jsx",".swift",".m",".mm",".rb",".go",".rs",".sh",".json",".yaml",".yml")
    code = sum(1 for f in src.rglob("*") if f.is_file() and f.suffix in pats)
    if code < MIN_CODE_FILES: return True
    # Only junk top-level?
    top = [d.name for d in src.iterdir() if d.is_dir()]
    if top and all(n in JUNK_DIRS for n in top): return True
    return False

def main():
    ap = argparse.ArgumentParser(description="Migrate all immediate subfolders from one root into capsules (COPY).")
    ap.add_argument("--root", default=str(Path.home()/ "Development"), help="Root folder to scan (default: ~/Development)")
    ap.add_argument("--yes", action="store_true", help="No prompts; migrate everything possible.")
    ap.add_argument("--dry-run", action="store_true", help="Preview only.")
    args = ap.parse_args()

    root = Path(args.root).expanduser()
    if not root.exists(): sys.exit(f"Root not found: {root}")
    reg = load_reg()

    projects = [p for p in sorted(root.iterdir()) if p.is_dir()]
    if not projects:
        print("No projects found under", root); return

    migrated = 0; skipped = 0
    for src in projects:
        name = src.name
        slug = kebab(name)
        if in_reg(reg, slug) or slug.lower() in SKIP_NAMES:
            skipped += 1; continue
        branch, targets, (rel_base, leaf) = classify(src)
        cap = ensure_capsule(slug)
        dest = cap / rel_base / leaf
        action = f"{'COPY' if not args.dry_run else 'DRY-COPY'} {src} -> {dest}"

        if not args.yes:
            print(f"{name}: {branch} {targets} :: {action}")
            ans = input("Migrate? [y/N] ").strip().lower()
            if ans != "y": skipped += 1; continue
        else:
            print(f"[AUTO] {name}: {branch} {targets} :: {action}")

        # materialize
        if args.dry_run:
            migrated += 1; continue
        if dest.exists():
            print(f"SKIP (dest exists): {dest}")
            skipped += 1; continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(src, dest)
        # spec, config, mcp merge, registry
        write_spec(cap, name, slug, branch, targets)
        gen_config(cap)
        merge_mcp(cap, src)
        # registry entry
        row = {"slug": slug, "name": name, "branch": branch, "targets": targets, "labels": [], "source_path": str(dest)}
        reg.append(row); save_reg(reg)
        migrated += 1

    print(f"\nDone. Migrated: {migrated}, Skipped: {skipped}. Root: {root}")

if __name__=="__main__": main()