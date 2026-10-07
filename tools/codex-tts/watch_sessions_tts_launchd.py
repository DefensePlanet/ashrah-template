#!/usr/bin/env python3
import json, os, sys, time, glob, subprocess
from pathlib import Path
from typing import Optional, List

LOG = Path('/tmp/codex_watch_tts.log')

def log(msg: str) -> None:
    try:
        LOG.parent.mkdir(parents=True, exist_ok=True)
        with LOG.open('a') as f:
            f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} {msg}\n")
    except Exception:
        pass

def latest_session_file() -> Optional[Path]:
    base = Path.home() / '.codex' / 'sessions'
    pats = glob.glob(str(base / '**' / '*.jsonl'), recursive=True)
    if not pats:
        return None
    pats.sort(key=lambda p: os.path.getmtime(p), reverse=True)
    return Path(pats[0])

def extract_text_from_entry(entry: dict) -> str:
    if entry.get('type') == 'message' and entry.get('role') == 'assistant':
        content = entry.get('content')
        if isinstance(content, list):
            parts: List[str] = []
            for block in content:
                if isinstance(block, dict) and block.get('type') in ('output_text','text') and block.get('text'):
                    parts.append(block['text'])
            return ' '.join(parts)
    return ''

def speak(text: str) -> None:
    if not text or len(text.strip()) < 8:
        return
    hook = Path(__file__).resolve().parent / 'codex_summary_tts.py'
    try:
        payload = json.dumps({"assistant_message": text}).encode('utf-8')
        subprocess.Popen(['python3', str(hook)], stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).communicate(payload, timeout=90)
    except Exception as e:
        log(f"speak error: {e}")

def tail_file(path: Path, start_at_end: bool = True) -> None:
    current = path
    log(f"tailing: {current}")
    f = current.open('r')
    if start_at_end:
        f.seek(0, os.SEEK_END)
    buffer_parts: List[str] = []
    last_assistant_ts = 0.0
    IDLE_FLUSH_SEC = 1.2

    def flush():
        nonlocal buffer_parts
        if buffer_parts:
            text = ' '.join(buffer_parts).strip()
            log(f"assistant text len={len(text)} (flush)")
            speak(text)
            buffer_parts = []

    try:
        while True:
            try:
                latest = latest_session_file()
                if latest and latest != current:
                    flush()
                    log(f"switching to newer session: {latest}")
                    f.close()
                    current = latest
                    f = current.open('r')
                    f.seek(0, os.SEEK_END)
            except Exception:
                pass

            line = f.readline()
            if not line:
                if buffer_parts and (time.time() - last_assistant_ts) > IDLE_FLUSH_SEC:
                    flush()
                time.sleep(0.25)
                continue
            try:
                entry = json.loads(line)
            except Exception:
                continue
            text = extract_text_from_entry(entry)
            if text:
                buffer_parts.append(text)
                last_assistant_ts = time.time()
                continue
            if entry.get('type') == 'message' and entry.get('role') and entry.get('role') != 'assistant' and buffer_parts:
                flush()
    finally:
        try:
            f.close()
        except Exception:
            pass

def main() -> int:
    p = latest_session_file()
    if not p:
        log('no session files found; waiting...')
        until = time.time() + 60
        while time.time() < until and not p:
            time.sleep(1)
            p = latest_session_file()
        if not p:
            log('no session file; exiting')
            return 0
    tail_file(p, start_at_end=True)
    return 0

if __name__ == '__main__':
    sys.exit(main())

