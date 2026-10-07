#!/usr/bin/env python3
"""export-template engine.

Called by export.sh. Holds no policy of its own: every path, name, pattern and
substitution comes from the YAML config passed with --config.

Subcommands
  config-get KEY          print a dotted config value (scalars only)
  build                   prune excluded paths, apply transforms, fix mojibake,
                          substitute, overlay template files; writes a JSON report
  verify                  run every verification; merges a gitleaks JSON report;
                          prints the summary table; exit 0 clean / 2 findings
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import unicodedata
from pathlib import Path

# --------------------------------------------------------------------------
# config
# --------------------------------------------------------------------------


def die(msg: str, code: int = 1) -> None:
    print(f"export_engine: {msg}", file=sys.stderr)
    sys.exit(code)


def load_config(path: str) -> dict:
    """Load YAML with PyYAML when present, else through the system ruby."""
    try:
        import yaml  # type: ignore

        with open(path, encoding="utf-8") as fh:
            return yaml.safe_load(fh) or {}
    except ImportError:
        pass
    ruby = shutil.which("ruby")
    if not ruby:
        die("reading the config needs PyYAML (pip install pyyaml) or ruby")
    proc = subprocess.run(
        [ruby, "-ryaml", "-rjson", "-e",
         "puts JSON.generate(YAML.safe_load(File.read(ARGV[0], encoding: 'UTF-8')))", path],
        capture_output=True, text=True,
    )
    if proc.returncode != 0:
        die(f"could not parse {path}: {proc.stderr.strip()}")
    return json.loads(proc.stdout) or {}


# --------------------------------------------------------------------------
# gitignore-style globs
# --------------------------------------------------------------------------


def _glob_regex(pat: str) -> str:
    out, i = [], 0
    while i < len(pat):
        if pat.startswith("**/", i):
            out.append("(?:.*/)?")
            i += 3
        elif pat.startswith("**", i):
            out.append(".*")
            i += 2
        elif pat[i] == "*":
            out.append("[^/]*")
            i += 1
        elif pat[i] == "?":
            out.append("[^/]")
            i += 1
        else:
            out.append(re.escape(pat[i]))
            i += 1
    return "".join(out)


class Glob:
    def __init__(self, raw: str):
        self.raw = raw
        p = raw
        self.negate = p.startswith("!")
        if self.negate:
            p = p[1:]
        p = p.lstrip("/")
        self.dir_only = p.endswith("/")
        p = p.rstrip("/")
        body = _glob_regex(p)
        if "/" not in p:
            body = "(?:.*/)?" + body
        self.rx = re.compile(body + r"\Z")

    def matches(self, rel: str) -> bool:
        parts = rel.split("/")
        # ancestors (directories) first, then the path itself
        for n in range(1, len(parts)):
            if self.rx.match("/".join(parts[:n])):
                return True
        return (not self.dir_only) and bool(self.rx.match(rel))


def path_selected(rel: str, globs: list[Glob]) -> Glob | None:
    """Last-match-wins. Returns the deciding non-negated glob, else None."""
    hit = None
    for g in globs:
        if g.matches(rel):
            hit = None if g.negate else g
    return hit


def in_globs(rel: str, patterns) -> bool:
    if not patterns:
        return True
    return any(Glob(p).matches(rel) for p in patterns)


# --------------------------------------------------------------------------
# file helpers
# --------------------------------------------------------------------------


def walk_files(root: Path):
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d != ".git"]
        for fn in filenames:
            p = Path(dirpath) / fn
            yield p, p.relative_to(root).as_posix()


def is_text(path: Path) -> bool:
    if path.is_symlink() or not path.is_file():
        return False
    try:
        with open(path, "rb") as fh:
            chunk = fh.read(8192)
    except OSError:
        return False
    return b"\0" not in chunk


def read_text(path: Path) -> str | None:
    """UTF-8 text, or None for files that are not valid UTF-8 (left untouched)."""
    try:
        return path.read_bytes().decode("utf-8")
    except (UnicodeDecodeError, OSError):
        return None


def write_text(path: Path, text: str) -> None:
    mode = path.stat().st_mode
    path.write_bytes(text.encode("utf-8"))
    os.chmod(path, mode)


# --------------------------------------------------------------------------
# mojibake (cp1252 double encoding)
# --------------------------------------------------------------------------

_B2C: dict[int, str] = {}
for _b in range(256):
    try:
        _B2C[_b] = bytes([_b]).decode("cp1252")
    except UnicodeDecodeError:
        _B2C[_b] = chr(_b)
_C2B = {c: b for b, c in _B2C.items()}


def _cls(lo: int, hi: int) -> str:
    return "".join(re.escape(_B2C[b]) for b in range(lo, hi + 1))


_CONT = _cls(0x80, 0xBF)
MOJIBAKE_RX = re.compile(
    f"[{_cls(0xF0, 0xF4)}][{_CONT}]{{3}}|[{_cls(0xE0, 0xEF)}][{_CONT}]{{2}}|[{_cls(0xC2, 0xDF)}][{_CONT}]"
)
# The byte signatures the verification greps for ("ðŸ" and "â€" as UTF-8).
MOJIBAKE_SIGNATURES = [b"\xc3\xb0\xc5\xb8", b"\xc3\xa2\xe2\x80"]


def fix_mojibake(text: str) -> tuple[str, int]:
    count = 0

    def repl(mo):
        nonlocal count
        try:
            fixed = bytes(_C2B[c] for c in mo.group()).decode("utf-8")
        except (KeyError, UnicodeDecodeError):
            return mo.group()
        # A real repair yields assigned characters; unassigned / private-use
        # output means the match was ordinary Latin-1 text, so keep it.
        if any(unicodedata.category(ch) in ("Cn", "Co", "Cs") for ch in fixed):
            return mo.group()
        count += 1
        return fixed

    for _ in range(3):  # double- or triple-encoded runs
        before = count
        text = MOJIBAKE_RX.sub(repl, text)
        if count == before:
            break
    return text, count


# --------------------------------------------------------------------------
# transforms
# --------------------------------------------------------------------------


def drop_md_sections(text: str, heading_rx: re.Pattern) -> tuple[str, int]:
    lines = text.split("\n")
    out, dropped, skip_level, in_fence = [], 0, 0, False
    for line in lines:
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
        m = None if in_fence else re.match(r"^(#{1,6}) ", line)
        if skip_level:
            if m and len(m.group(1)) <= skip_level:
                skip_level = 0
            else:
                continue
        if m and heading_rx.search(line):
            skip_level = len(m.group(1))
            dropped += 1
            continue
        out.append(line)
    return "\n".join(out), dropped


def drop_lines(text: str, line_rx: re.Pattern) -> tuple[str, int]:
    kept, dropped = [], 0
    for line in text.split("\n"):
        if line_rx.search(line):
            dropped += 1
            continue
        kept.append(line)
    return "\n".join(kept), dropped


def drop_yaml_blocks(text: str, key_rx: re.Pattern) -> tuple[str, int]:
    lines = text.split("\n")
    out: list[str] = []
    dropped, i = 0, 0
    while i < len(lines):
        line = lines[i]
        if key_rx.search(line):
            indent = len(line) - len(line.lstrip(" "))
            # comment lines directly above, at the same indent
            while out and out[-1].strip().startswith("#") and (len(out[-1]) - len(out[-1].lstrip(" "))) == indent:
                out.pop()
            i += 1
            while i < len(lines):
                nxt = lines[i]
                if nxt.strip() == "":
                    i += 1
                    continue
                if len(nxt) - len(nxt.lstrip(" ")) > indent:
                    i += 1
                    continue
                break
            dropped += 1
            continue
        out.append(line)
        i += 1
    return "\n".join(out), dropped


# --------------------------------------------------------------------------
# substitutions
# --------------------------------------------------------------------------


class Rule:
    def __init__(self, d: dict):
        self.name = d["name"]
        self.find = d["find"]
        # "token: NAME" is shorthand for replace: "{{NAME}}" (lets a config that
        # is itself shipped avoid literal tokens that setup.sh would fill).
        self.replace = "{{" + d["token"] + "}}" if d.get("token") else d["replace"]
        self.is_regex = bool(d.get("regex", False))
        self.paths = d.get("paths")
        self.exclude_paths = d.get("exclude_paths")
        self.rename_paths = d.get("rename_paths", True)
        self.rx = re.compile(self.find) if self.is_regex else None

    def applies(self, rel: str) -> bool:
        if self.paths and not in_globs(rel, self.paths):
            return False
        if self.exclude_paths and in_globs(rel, self.exclude_paths):
            return False
        return True

    def apply(self, text: str) -> tuple[str, int]:
        if self.rx is not None:
            return self.rx.subn(self.replace, text)
        n = text.count(self.find)
        return (text.replace(self.find, self.replace), n) if n else (text, 0)


# --------------------------------------------------------------------------
# build
# --------------------------------------------------------------------------


def cmd_build(a) -> None:
    cfg = load_config(a.config)
    tree = Path(a.tree).resolve()
    report: dict = {"excluded": 0, "excluded_by_rule": {}, "symlinks_removed": [],
                    "transforms": [], "mojibake_fixed": 0, "mojibake_files": 0,
                    "substitutions": {}, "renamed_paths": 0, "overlay": [],
                    "source_files": 0, "shipped": 0}

    # 1. prune ------------------------------------------------------------
    globs = [Glob(p) for p in cfg.get("exclude", [])]
    all_files = list(walk_files(tree))
    report["source_files"] = len(all_files)
    for p, rel in all_files:
        g = path_selected(rel, globs)
        if g is not None:
            p.unlink()
            report["excluded"] += 1
            report["excluded_by_rule"][g.raw] = report["excluded_by_rule"].get(g.raw, 0) + 1
    git_dir = tree / ".git"
    if git_dir.exists():
        shutil.rmtree(git_dir)

    # symlinks that leave the tree would publish a host path
    for p, rel in list(walk_files(tree)):
        if p.is_symlink():
            target = os.readlink(p)
            resolved = (p.parent / target).resolve()
            if os.path.isabs(target) or not str(resolved).startswith(str(tree)):
                p.unlink()
                report["symlinks_removed"].append(rel)

    # 2. transforms -----------------------------------------------------------
    for t in cfg.get("transforms", []) or []:
        rx = re.compile(t.get("heading_regex") or t.get("key_regex") or t.get("line_regex"))
        for p, rel in walk_files(tree):
            if not in_globs(rel, t.get("paths")) or not is_text(p):
                continue
            text = read_text(p)
            if text is None:
                continue
            if t["type"] == "drop_md_sections":
                new, n = drop_md_sections(text, rx)
            elif t["type"] == "drop_yaml_blocks":
                new, n = drop_yaml_blocks(text, rx)
            elif t["type"] == "drop_lines":
                new, n = drop_lines(text, rx)
            else:
                die(f"unknown transform type {t['type']}")
            if n:
                write_text(p, new)
                report["transforms"].append({"type": t["type"], "path": rel, "dropped": n})

    # 3. mojibake + 4. substitutions (content) -----------------------------------
    mj = cfg.get("fix_mojibake") or {}
    rules = [Rule(r) for r in cfg.get("substitutions", [])]
    counts = {r.name: 0 for r in rules}
    files_touched = {r.name: 0 for r in rules}
    for p, rel in walk_files(tree):
        if not is_text(p):
            continue
        text = read_text(p)
        if text is None:
            report.setdefault("non_utf8_text_files", []).append(rel)
            continue
        new = text
        if mj.get("enabled") and in_globs(rel, mj.get("paths")):
            new, n = fix_mojibake(new)
            if n:
                report["mojibake_fixed"] += n
                report["mojibake_files"] += 1
        for r in rules:
            if not r.applies(rel):
                continue
            new, n = r.apply(new)
            if n:
                counts[r.name] += n
                files_touched[r.name] += 1
        if new != text:
            write_text(p, new)
    report["substitutions"] = {k: {"occurrences": counts[k], "files": files_touched[k]} for k in counts}

    # 4b. substitutions (path names), deepest first ----------------------------
    path_rules = [r for r in rules if r.rename_paths]
    renamed = 0
    for dirpath, dirnames, filenames in os.walk(tree, topdown=False):
        for name in filenames + dirnames:
            new = name
            for r in path_rules:
                new, _ = r.apply(new)
            if new != name:
                src = Path(dirpath) / name
                dst = Path(dirpath) / new
                if dst.exists():
                    die(f"rename collision: {src.relative_to(tree)} -> {new}")
                src.rename(dst)
                renamed += 1
    report["renamed_paths"] = renamed

    # 5. overlay template-only files (after substitution: they are hand-written) --
    tf = Path(a.template_files)
    if tf.is_dir():
        for p, rel in walk_files(tf):
            dst = tree / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(p, dst)
            report["overlay"].append(rel)

    # 6. tidy empty directories ---------------------------------------------------
    for dirpath, dirnames, filenames in os.walk(tree, topdown=False):
        d = Path(dirpath)
        if d != tree and not any(d.iterdir()):
            d.rmdir()

    report["shipped"] = sum(1 for _ in walk_files(tree))
    Path(a.report).write_text(json.dumps(report, indent=2))


# --------------------------------------------------------------------------
# verify
# --------------------------------------------------------------------------


def parse_frontmatter(text: str) -> dict | None:
    if not text.startswith("---"):
        return None
    lines = text.split("\n")
    if lines[0].strip() != "---":
        return None
    keys: dict = {}
    for line in lines[1:]:
        if line.strip() == "---":
            return keys
        m = re.match(r"^([A-Za-z_][A-Za-z0-9_-]*):\s*(.*)$", line)
        if m:
            keys[m.group(1)] = m.group(2).strip()
    return None  # unterminated


def cmd_verify(a) -> None:
    cfg = load_config(a.config)
    tree = Path(a.tree).resolve()
    build = json.loads(Path(a.build_report).read_text()) if a.build_report else {}
    findings: list[dict] = []
    checks: list[tuple[str, str, str]] = []  # (check, result, detail)

    allow = cfg.get("verify_allow", []) or []

    def allowed(pname: str, rel: str, hit: str | None = None) -> bool:
        for x in allow:
            if x.get("pattern") != pname or not in_globs(rel, x.get("paths")):
                continue
            if x.get("match") and (hit is None or not re.search(x["match"], hit)):
                continue
            return True
        return False

    # (a) forbidden patterns -------------------------------------------------
    pats = []
    for vp in cfg.get("verify_patterns", []) or []:
        flags = re.I if vp.get("ignore_case") else 0
        pats.append((vp["name"], re.compile(vp["regex"], flags), vp.get("only_ext"), vp.get("paths")))
    warns = []
    for wp in cfg.get("warn_patterns", []) or []:
        flags = re.I if wp.get("ignore_case") else 0
        warns.append((wp["name"], re.compile(wp["regex"], flags)))

    per_pattern = {n: 0 for n, _, _, _ in pats}
    warn_counts = {n: 0 for n, _ in warns}
    warn_files: dict[str, set] = {n: set() for n, _ in warns}
    moj_fatal, moj_other = 0, 0
    moj_other_files: dict[str, int] = {}
    fatal_globs = (cfg.get("verify_mojibake") or {}).get("fatal_paths", [])
    for p, rel in walk_files(tree):
        # path names are content too
        for name, rx, only_ext, vpaths in pats:
            if vpaths and not in_globs(rel, vpaths):
                continue
            if not only_ext and rx.search(rel) and not allowed(name, rel, rel):
                per_pattern[name] += 1
                findings.append({"check": "pattern", "pattern": name, "path": rel, "line": 0, "where": "path"})
        if not is_text(p):
            continue
        raw = p.read_bytes()
        text = read_text(p)
        if text is None:
            text = raw.decode("latin-1")
        ext = os.path.splitext(rel)[1].lower()
        for name, rx, only_ext, vpaths in pats:
            if only_ext and ext not in only_ext:
                continue
            if vpaths and not in_globs(rel, vpaths):
                continue
            for m in rx.finditer(text):
                if allowed(name, rel, m.group(0)):
                    continue
                line = text.count("\n", 0, m.start()) + 1
                per_pattern[name] += 1
                findings.append({"check": "pattern", "pattern": name, "path": rel, "line": line})
        for name, rx in warns:
            n = len(rx.findall(text))
            if n:
                warn_counts[name] += n
                warn_files[name].add(rel)
        mcount = sum(raw.count(sig) for sig in MOJIBAKE_SIGNATURES)
        if mcount:
            if in_globs(rel, fatal_globs):
                moj_fatal += mcount
                findings.append({"check": "mojibake", "path": rel, "count": mcount})
            else:
                moj_other += mcount
                moj_other_files[rel] = mcount
    for name, n in per_pattern.items():
        checks.append((f"pattern:{name}", "PASS" if n == 0 else "FAIL", f"{n} hit(s)"))

    # (b) gitleaks -------------------------------------------------------------
    if a.gitleaks_report == "SKIPPED":
        checks.append(("gitleaks", "SKIP", "gitleaks not installed"))
        findings.append({"check": "gitleaks", "path": "-", "detail": "gitleaks not installed"})
    elif a.gitleaks_report:
        try:
            leaks = json.loads(Path(a.gitleaks_report).read_text() or "[]")
        except (OSError, json.JSONDecodeError):
            leaks = None
        if leaks is None:
            checks.append(("gitleaks", "FAIL", "no readable report"))
            findings.append({"check": "gitleaks", "path": "-", "detail": "report unreadable"})
        else:
            for lk in leaks:
                fp = lk.get("File", "")
                try:
                    fp = Path(fp).resolve().relative_to(tree).as_posix()
                except ValueError:
                    pass
                findings.append({"check": "gitleaks", "path": fp, "line": lk.get("StartLine"),
                                 "rule": lk.get("RuleID")})
            checks.append(("gitleaks", "PASS" if not leaks else "FAIL", f"{len(leaks)} leak(s)"))

    # (c) required paths ---------------------------------------------------------
    missing = [x for x in cfg.get("verify_paths_must_exist", []) or [] if not (tree / x).exists()]
    for x in missing:
        findings.append({"check": "required-path", "path": x})
    checks.append(("required paths", "PASS" if not missing else "FAIL",
                   "all present" if not missing else "missing: " + ", ".join(missing)))

    # (d) agent frontmatter --------------------------------------------------------
    af = cfg.get("verify_agent_frontmatter") or {}
    if af:
        adir = tree / af.get("dir", ".claude/agents")
        req = af.get("required_keys", ["name", "description", "model"])
        bad, total = [], 0
        for p in sorted(adir.rglob("*")) if adir.is_dir() else []:
            if not p.is_file():
                continue
            total += 1
            fm = parse_frontmatter(read_text(p) or "")
            miss = [k for k in req if not fm or not fm.get(k)]
            if fm is None or miss:
                rel = p.relative_to(tree).as_posix()
                bad.append(rel)
                findings.append({"check": "frontmatter", "path": rel,
                                 "detail": "no frontmatter" if fm is None else "missing " + ",".join(miss)})
        checks.append(("agent frontmatter", "PASS" if not bad else "FAIL", f"{total - len(bad)}/{total} valid"))

    # (e) mojibake -----------------------------------------------------------------
    checks.append(("mojibake (CLAUDE.md, agents)", "PASS" if moj_fatal == 0 else "FAIL", f"{moj_fatal} sequence(s)"))
    checks.append(("mojibake (elsewhere, info)", "INFO", f"{moj_other} sequence(s) in {len(moj_other_files)} file(s)"))

    # unresolved placeholder tokens that setup.sh does not know about would be a
    # bug in the substitution table; report them for a human.
    known = set(a.known_tokens.split(",")) if a.known_tokens else set()
    unknown: dict[str, int] = {}
    if known:
        tok_rx = re.compile(r"\{\{([A-Z][A-Z0-9_]*)\}\}")
        for p, rel in walk_files(tree):
            if is_text(p):
                for t in tok_rx.findall(read_text(p) or ""):
                    if t not in known:
                        unknown[t] = unknown.get(t, 0) + 1

    # ---------------------------------------------------------------- output ----
    W = 64
    print()
    print("=" * W)
    print(" EXPORT SUMMARY")
    print("=" * W)
    if build:
        print(f" {'source files (git-visible)':<40}{build.get('source_files', 0):>10}")
        print(f" {'files excluded by policy':<40}{build.get('excluded', 0):>10}")
        print(f" {'template-only files overlaid':<40}{len(build.get('overlay', [])):>10}")
        print(f" {'files shipped':<40}{build.get('shipped', 0):>10}")
        print(f" {'paths renamed (placeholders)':<40}{build.get('renamed_paths', 0):>10}")
        print(f" {'mojibake sequences repaired':<40}{build.get('mojibake_fixed', 0):>10}")
        if build.get("symlinks_removed"):
            print(f" {'out-of-tree symlinks removed':<40}{len(build['symlinks_removed']):>10}")
        for t in build.get("transforms", []):
            print(f"  transform {t['type']}: {t['path']} ({t['dropped']} block(s))")
        print("-" * W)
        print(f" {'EXCLUSION RULE':<46}{'FILES':>8}")
        for k, v in sorted(build.get("excluded_by_rule", {}).items(), key=lambda kv: -kv[1]):
            print(f"  {k:<45}{v:>8}")
        print("-" * W)
        print(f" {'SUBSTITUTION RULE':<30}{'OCCURRENCES':>14}{'FILES':>10}")
        for k, v in build.get("substitutions", {}).items():
            print(f"  {k:<29}{v['occurrences']:>14}{v['files']:>10}")
    print("-" * W)
    print(f" {'VERIFICATION':<36}{'RESULT':<8}DETAIL")
    for c, r, d in checks:
        print(f"  {c:<35}{r:<8}{d}")
    if any(warn_counts.values()):
        print("-" * W)
        print(" WARN (report-only)")
        for n, c in warn_counts.items():
            if c:
                files = sorted(warn_files[n])
                print(f"  {n:<20}{c:>5} in {len(files)} file(s): {', '.join(files[:4])}{' ...' if len(files) > 4 else ''}")
    if unknown:
        print("-" * W)
        print(" placeholder tokens setup.sh will NOT fill (left for downstream templates):")
        print("  " + ", ".join(f"{k}({v})" for k, v in sorted(unknown.items())))
    if findings:
        print("-" * W)
        print(f" FINDINGS ({len(findings)}), first 60:")
        for f in findings[:60]:
            where = f"{f['path']}:{f.get('line', '')}" if f.get("line") else f["path"]
            what = f.get("pattern") or f.get("rule") or f.get("detail") or f.get("count", "")
            print(f"  [{f['check']}] {where}  {what}")
    print("=" * W)
    print(f" RESULT: {'CLEAN' if not findings else f'{len(findings)} FINDING(S)'}")
    print("=" * W)

    if a.out_json:
        Path(a.out_json).write_text(json.dumps({"checks": checks, "findings": findings,
                                                "warn": warn_counts, "mojibake_elsewhere": moj_other_files,
                                                "unknown_tokens": unknown}, indent=2))
    sys.exit(0 if not findings else 2)


def cmd_config_get(a) -> None:
    cur = load_config(a.config)
    for part in a.key.split("."):
        if not isinstance(cur, dict) or part not in cur:
            sys.exit(1)
        cur = cur[part]
    if isinstance(cur, (dict, list)):
        print(json.dumps(cur))
    else:
        print(cur)


def main() -> None:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    g = sub.add_parser("config-get")
    g.add_argument("--config", required=True)
    g.add_argument("key")
    b = sub.add_parser("build")
    b.add_argument("--config", required=True)
    b.add_argument("--tree", required=True)
    b.add_argument("--template-files", required=True)
    b.add_argument("--report", required=True)
    v = sub.add_parser("verify")
    v.add_argument("--config", required=True)
    v.add_argument("--tree", required=True)
    v.add_argument("--build-report")
    v.add_argument("--gitleaks-report")
    v.add_argument("--known-tokens", default="")
    v.add_argument("--out-json")
    a = ap.parse_args()
    {"config-get": cmd_config_get, "build": cmd_build, "verify": cmd_verify}[a.cmd](a)


if __name__ == "__main__":
    main()
