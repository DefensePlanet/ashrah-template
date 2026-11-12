#!/usr/bin/env python3
"""
Watch Codex CLI session logs and speak assistant replies (Codex-only TTS).

Monitors ~/.codex/sessions/**/**.jsonl for the most recently modified file,
tails new lines, and whenever an assistant message appears, pipes text into
codex_summary_tts.py for alloy TTS playback.
"""

import json
import os
import sys
import time
import glob
from pathlib import Path
import subprocess
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
            parts = []
            for block in content:
                if isinstance(block, dict):
                    if block.get('type') in ('output_text', 'text') and block.get('text'):
                        parts.append(block['text'])
            # Join with spaces to avoid word collisions
            return ' '.join(parts)
    return ''


def speak(text: str) -> None:
    if not text or len(text.strip()) < 8:
        return
    hook = Path(__file__).resolve().parent / 'codex_summary_tts.py'
    try:
        payload = json.dumps({"assistant_message": text}).encode('utf-8')
        subprocess.Popen(['python3', str(hook)], stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).communicate(payload, timeout=60)
    except Exception as e:
        log(f"speak error: {e}")


def tail_file(path: Path, start_at_end: bool = True) -> None:
    """Tail session log, aggregate assistant turn text, and speak once per turn.

    Aggregates consecutive assistant message blocks; flushes when a user message
    appears or after a short idle timeout to avoid mid-turn playback.
    """
    current = path
    log(f"tailing: {current}")
    f = current.open('r')
    if start_at_end:
        f.seek(0, os.SEEK_END)

    buffer_parts: List[str] = []
    last_assistant_ts = 0.0
    IDLE_FLUSH_SEC = 1.2

    def flush_buffer():
        nonlocal buffer_parts
        if buffer_parts:
            text = ' '.join(buffer_parts).strip()
            log(f"assistant text len={len(text)} (flush)")
            speak(text)
            buffer_parts = []

    try:
        while True:
            # Detect newer session file
            try:
                latest = latest_session_file()
                if latest and latest != current:
                    # Before switching, flush any buffered text
                    flush_buffer()
                    log(f"switching to newer session: {latest}")
                    f.close()
                    current = latest
                    f = current.open('r')
                    f.seek(0, os.SEEK_END)
            except Exception:
                pass

            line = f.readline()
            if not line:
                # Idle flush if we've buffered text and no new assistant lines
                if buffer_parts and (time.time() - last_assistant_ts) > IDLE_FLUSH_SEC:
                    flush_buffer()
                time.sleep(0.25)
                continue
            try:
                entry = json.loads(line)
            except Exception:
                continue

            etype = entry.get('type')
            role = entry.get('role')

            # Collect assistant text if present
            text = extract_text_from_entry(entry)
            if text:
                buffer_parts.append(text)
                last_assistant_ts = time.time()
                continue

            # If we see a non-assistant message and have buffered content, flush
            if etype == 'message' and role and role != 'assistant' and buffer_parts:
                flush_buffer()

    finally:
        try:
            f.close()
        except Exception:
            pass


def main() -> int:
    path = latest_session_file()
    if not path:
        log('no session files found; waiting...')
        # poll for up to 60s for a session to appear
        until = time.time() + 60
        while time.time() < until and not path:
            time.sleep(1)
            path = latest_session_file()
        if not path:
            log('no session file; exiting')
            return 0
    tail_file(path, start_at_end=True)
    return 0


if __name__ == '__main__':
    sys.exit(main())
