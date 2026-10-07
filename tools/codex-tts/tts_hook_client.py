#!/usr/bin/env python3
"""
TTS Hook Client - Claude Code Stop hook for Kokoro TTS summaries

Fires after each Claude Code response. Extracts the <tts-summary> tag,
sends it to the persistent Kokoro TTS server, and plays the audio.

The server (tts_server.py) keeps the Kokoro-82M model loaded in memory
for fast generation. If the server isn't running, this client auto-starts it.

Setup: Run tools/codex-tts/setup.sh to install dependencies.
Toggle: Use /voice in Claude Code to enable/disable this hook.
"""

import hashlib
import json
import os
import re
import socket
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

# Server configuration — paths computed from this file's location
SERVER_HOST = "127.0.0.1"
SERVER_PORT = 9876
SERVER_SCRIPT = Path(__file__).resolve().parent / "tts_server.py"
PID_FILE = Path.home() / '.claude' / 'tts_server.pid'
LOG_FILE = Path.home() / '.claude' / 'tts_client.log'
LOCK_FILE = Path.home() / '.claude' / 'tts_hook.lock'
LAST_HASH_FILE = Path.home() / '.claude' / 'tts_last_hash.txt'


def _find_python() -> str:
    """Find a suitable Python 3.11+ interpreter with mlx_audio installed."""
    # 1. If we're already running under a good interpreter, use it
    if sys.version_info >= (3, 11):
        return sys.executable
    # 2. Check Kokoro TTS venv first (has all deps pre-installed).
    #    Require it to be executable, not merely present — a broken/non-exec
    #    venv interpreter must not be chosen over known-good system Pythons.
    venv_python = str(Path.home() / ".kokoro-tts-venv" / "bin" / "python3.12")
    if Path(venv_python).exists() and os.access(venv_python, os.X_OK):
        return venv_python
    # 3. Check common macOS locations
    candidates = [
        "/Library/Frameworks/Python.framework/Versions/3.11/bin/python3",
        "/Library/Frameworks/Python.framework/Versions/3.12/bin/python3",
        "/Library/Frameworks/Python.framework/Versions/3.13/bin/python3",
        "/opt/homebrew/opt/python@3.12/bin/python3.12",
        "/opt/homebrew/bin/python3",
        "/usr/local/bin/python3",
    ]
    for c in candidates:
        # Require executable, not merely present — match the venv check above so a
        # broken/non-exec interpreter is never returned over a working one.
        if Path(c).exists() and os.access(c, os.X_OK):
            return c
    # 4. Fall back to PATH
    return "python3"


def log_debug(message: str) -> None:
    """Log debug information."""
    try:
        LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(LOG_FILE, 'a') as f:
            f.write(f"[{datetime.now().isoformat()}] {message}\n")
    except Exception:
        pass


def acquire_lock() -> bool:
    """Acquire lock file using atomic operations with PID tracking."""
    try:
        fd = os.open(
            str(LOCK_FILE),
            os.O_CREAT | os.O_EXCL | os.O_WRONLY,
            0o644
        )
        os.write(fd, f"{os.getpid()}\n".encode())
        os.close(fd)
        log_debug(f"Lock acquired (PID {os.getpid()})")
        return True

    except FileExistsError:
        try:
            with open(LOCK_FILE, 'r') as f:
                pid_str = f.read().strip()
                if not pid_str:
                    log_debug("Empty lock file, removing")
                    LOCK_FILE.unlink()
                    return acquire_lock()

                holder_pid = int(pid_str)
                try:
                    os.kill(holder_pid, 0)
                    log_debug(f"Lock held by active process {holder_pid}")
                    return False
                except OSError:
                    log_debug(f"Stale lock from dead process {holder_pid}, removing")
                    LOCK_FILE.unlink()
                    return acquire_lock()

        except (ValueError, FileNotFoundError) as e:
            log_debug(f"Lock file issue: {e}")
            return False

    except Exception as e:
        log_debug(f"Lock acquisition failed: {e}")
        return False


def release_lock() -> None:
    """Release lock file."""
    try:
        if LOCK_FILE.exists():
            try:
                with open(LOCK_FILE, 'r') as f:
                    holder_pid = int(f.read().strip())
                    if holder_pid == os.getpid():
                        LOCK_FILE.unlink()
                        log_debug("Lock released")
                    else:
                        log_debug(f"Not releasing lock owned by PID {holder_pid}")
            except (ValueError, FileNotFoundError):
                LOCK_FILE.unlink(missing_ok=True)
    except Exception as e:
        log_debug(f"Lock release failed: {e}")


def is_server_running() -> bool:
    """Check if TTS server process is alive (PID check only)."""
    if not PID_FILE.exists():
        return False

    try:
        with open(PID_FILE, 'r') as f:
            pid = int(f.read().strip())
        os.kill(pid, 0)
        return True
    except (OSError, ValueError):
        if PID_FILE.exists():
            PID_FILE.unlink()
        return False


def is_server_ready() -> bool:
    """Check if TTS server is actually accepting connections (socket probe)."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(1.0)
        s.connect((SERVER_HOST, SERVER_PORT))
        s.close()
        return True
    except (ConnectionRefusedError, socket.timeout, OSError):
        return False


def start_server() -> bool:
    """Start the TTS server in background and wait until it accepts connections."""
    log_debug("Starting TTS server...")

    try:
        python_path = _find_python()

        subprocess.Popen(
            [python_path, str(SERVER_SCRIPT)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True
        )

        # Kokoro model cold-start can take 5-12s on first load
        for i in range(30):  # 15 seconds max
            time.sleep(0.5)
            if is_server_ready():
                log_debug(f"Server ready after {(i+1)*0.5:.1f}s")
                return True
            if i % 4 == 3:
                log_debug(f"Still waiting for server... ({(i+1)*0.5:.1f}s)")

        log_debug("Server start timeout after 15s")
        return False

    except Exception as e:
        log_debug(f"Failed to start server: {e}")
        return False


def send_tts_request(text: str, timeout: float = 10.0) -> Optional[Path]:
    """Send TTS request to server and get audio path."""
    try:
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_socket.settimeout(timeout)
        client_socket.connect((SERVER_HOST, SERVER_PORT))

        request = {"text": text}
        request_data = json.dumps(request).encode('utf-8') + b"\n\n"
        client_socket.sendall(request_data)

        response_data = b""
        while True:
            chunk = client_socket.recv(4096)
            if not chunk:
                break
            response_data += chunk

        client_socket.close()

        response = json.loads(response_data.decode('utf-8'))

        if response.get("status") == "success":
            audio_path = Path(response["audio_path"])
            log_debug(f"Received audio: {audio_path}")
            return audio_path
        else:
            log_debug(f"Server error: {response.get('message')}")
            return None

    except Exception as e:
        log_debug(f"Request failed: {e}")
        return None


def play_audio(audio_path: Path) -> None:
    """Play audio file in non-blocking detached process."""
    try:
        # Kill any existing afplay to prevent overlapping audio
        try:
            subprocess.run(
                ['pkill', '-9', 'afplay'],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=1
            )
            log_debug("Killed existing afplay processes")
        except Exception as e:
            log_debug(f"No afplay processes to kill: {e}")

        subprocess.Popen(
            ['afplay', str(audio_path)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True
        )
        log_debug(f"Started non-blocking playback of {audio_path}")

    except Exception as e:
        log_debug(f"Playback error: {e}")


def _flatten_content(content):
    """Normalize Claude content payloads into plain text."""
    if isinstance(content, str):
        return content

    if isinstance(content, dict):
        if "text" in content:
            return _flatten_content(content.get("text"))
        if "content" in content:
            return _flatten_content(content.get("content"))
        return ""

    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                parts.append(item.get("text", ""))
            elif isinstance(item, str):
                parts.append(item)
        return " ".join(p for p in parts if p)

    return ""


def _read_transcript_once(transcript_path: str) -> str:
    """Read the last assistant message from a transcript file (single pass)."""
    try:
        with open(transcript_path, "r") as fh:
            lines = fh.readlines()
    except Exception as exc:
        log_debug(f"Failed to read transcript {transcript_path}: {exc}")
        return ""

    for line in reversed(lines):
        line = line.strip()
        if not line:
            continue
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue

        if entry.get("type") != "assistant":
            continue

        message = entry.get("message", {})
        text = _flatten_content(message.get("content"))
        if text:
            return text

    return ""


def _message_hash(text: str) -> str:
    """Quick hash of message text for dedup."""
    return hashlib.sha256(text.encode()).hexdigest()[:16]


def _load_last_hash() -> str:
    try:
        return LAST_HASH_FILE.read_text().strip()
    except Exception:
        return ""


def _save_last_hash(h: str) -> None:
    try:
        LAST_HASH_FILE.write_text(h + "\n")
    except Exception:
        pass


def _read_transcript(transcript_path: str) -> str:
    """Read the last assistant message, retrying if transcript is stale.

    The Stop hook can fire before Claude Code finishes writing the current
    response to the transcript file. When that happens the last assistant
    entry still belongs to the *previous* turn. Retry with hash comparison.
    """
    last_hash = _load_last_hash()
    start_time = time.monotonic()

    text = _read_transcript_once(transcript_path)
    if text:
        h = _message_hash(text)
        if h != last_hash:
            log_debug(f"Fresh message on first read (hash {h[:8]})")
            _save_last_hash(h)
            return text

    delays = [0.3, 0.5, 0.5, 0.75, 1.0, 1.0, 1.0, 1.25, 1.25, 1.5, 1.5, 2.0]
    max_wait = 20.0  # absolute ceiling for total wait (fixed ~12.5s + bonus ~7.5s)
    last_mtime_change: float = 0.0  # monotonic timestamp of last mtime advance
    retry_num = 0
    try:
        prev_mtime = os.path.getmtime(transcript_path)
    except OSError:
        prev_mtime = 0.0
    for delay in delays:
        retry_num += 1
        log_debug(f"Stale transcript (same hash as last TTS), retry {retry_num}/{len(delays)} after {delay}s")
        time.sleep(delay)

        try:
            cur_mtime = os.path.getmtime(transcript_path)
            if cur_mtime > prev_mtime:
                log_debug("Transcript still being written (mtime changed)")
                last_mtime_change = time.monotonic()
            prev_mtime = cur_mtime
        except OSError:
            pass

        text = _read_transcript_once(transcript_path)
        if text:
            h = _message_hash(text)
            if h != last_hash:
                elapsed = time.monotonic() - start_time
                log_debug(f"Fresh message on retry {retry_num} after {elapsed:.1f}s (hash {h[:8]})")
                _save_last_hash(h)
                return text

    # If the file was recently changing (within 3s), keep polling beyond the
    # fixed delay list — Claude is still flushing a long response.
    while True:
        now = time.monotonic()
        if not last_mtime_change or (now - last_mtime_change) >= 3.0 or (now - start_time) >= max_wait:
            break
        retry_num += 1
        log_debug(f"File recently changed, bonus retry {retry_num} (elapsed {now - start_time:.1f}s)")
        time.sleep(1.5)

        try:
            cur_mtime = os.path.getmtime(transcript_path)
            if cur_mtime > prev_mtime:
                last_mtime_change = time.monotonic()
            prev_mtime = cur_mtime
        except OSError:
            pass

        text = _read_transcript_once(transcript_path)
        if text:
            h = _message_hash(text)
            if h != last_hash:
                elapsed = time.monotonic() - start_time
                log_debug(f"Fresh message on bonus retry {retry_num} after {elapsed:.1f}s (hash {h[:8]})")
                _save_last_hash(h)
                return text

    elapsed = time.monotonic() - start_time
    log_debug(f"Exhausted retries after {elapsed:.1f}s -- transcript still stale, skipping TTS this turn")
    # CRITICAL: Do NOT save the hash here. The text is from the PREVIOUS turn.
    # Saving it would cause the NEXT turn to detect the (finally-written) current
    # message as "fresh" — but that message is already one turn old by then,
    # creating a persistent one-turn lag. By not saving, the next turn's hash
    # comparison will still correctly detect its own fresh content.
    return ""


def _project_transcript_dir() -> Optional[Path]:
    """~/.claude/projects/<cwd-with-slashes-as-dashes>/ — where Claude Code
    stores this workspace's transcripts (hooks run with cwd = workspace root)."""
    try:
        sanitized = str(Path.cwd()).replace('/', '-')
        proj_dir = Path.home() / '.claude' / 'projects' / sanitized
        return proj_dir if proj_dir.is_dir() else None
    except Exception as e:
        log_debug(f"project transcript dir lookup failed: {e}")
        return None


def _find_session_transcript(session_id: Optional[str]) -> Optional[str]:
    """Resolve the EXACT transcript for this session by id (<session_id>.jsonl).

    Precise even with multiple concurrent Claude sessions — avoids the
    'newest .jsonl might be another conversation' hazard.
    """
    if not session_id:
        return None
    proj_dir = _project_transcript_dir()
    if not proj_dir:
        return None
    candidate = proj_dir / f"{session_id}.jsonl"
    return str(candidate) if candidate.exists() else None


def _find_latest_transcript() -> Optional[str]:
    """Last-resort fallback: newest .jsonl for the current project directory.

    Only used when neither a payload transcript_path nor a session-id match is
    available. With concurrent sessions this can pick the wrong conversation, so
    it is intentionally the lowest-priority path.
    """
    proj_dir = _project_transcript_dir()
    if not proj_dir:
        return None
    try:
        jsonls = sorted(
            proj_dir.glob('*.jsonl'),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        return str(jsonls[0]) if jsonls else None
    except Exception as e:
        log_debug(f"latest-transcript fallback failed: {e}")
        return None


def extract_hook_text(data):
    """Best-effort extraction of Claude's latest assistant text."""
    session_id = data.get("session_id")
    log_debug(
        f"hook payload keys: {list(data.keys())}; "
        f"transcript_path={data.get('transcript_path')!r}; session_id={session_id!r}"
    )

    # PRIMARY: Claude Code hands the finished assistant message directly in the
    # Stop payload. Using it avoids transcript flush-timing races (the "stale,
    # skipping TTS" failures), wrong-session reads, and stale-line repeats.
    direct = _flatten_content(data.get("last_assistant_message"))
    if direct and direct.strip():
        log_debug(f"Using last_assistant_message from payload ({len(direct)} chars)")
        return direct

    transcript_path = data.get("transcript_path")
    if transcript_path:
        transcript_path = os.path.expanduser(str(transcript_path))

    if not transcript_path or not os.path.exists(transcript_path):
        # 1) Exact session match (safe with concurrent sessions)
        session_match = _find_session_transcript(session_id)
        if session_match:
            log_debug(
                f"transcript_path missing/invalid ({data.get('transcript_path')!r}); "
                f"resolved exact session transcript {session_match}"
            )
            transcript_path = session_match
        else:
            # 2) Last resort: newest transcript (may be another session)
            fallback = _find_latest_transcript()
            if fallback:
                log_debug(
                    f"transcript_path + session match both unavailable "
                    f"(session_id={session_id!r}); using newest project transcript "
                    f"{fallback} (may be another session)"
                )
                transcript_path = fallback

    if transcript_path and os.path.exists(transcript_path):
        text = _read_transcript(transcript_path)
        if text:
            log_debug(f"Extracted text from transcript ({len(text)} chars)")
            return text

    for key in (
        "assistant_message",
        "message",
        "final_response",
        "response",
        "content",
        "text",
    ):
        if key in data:
            candidate = _flatten_content(data[key])
            if candidate:
                log_debug(f"Extracted text from key '{key}' ({len(candidate)} chars)")
                return candidate

    return ""


def create_conceptual_summary(text: str) -> str:
    """Extract TTS notification from Claude's response.

    Priority:
    1. Extract <tts-summary> tag if present (Claude's explicit notification)
    2. Fallback to first 1-2 sentences if no tag found
    """
    text_without_code = re.sub(r'```[\s\S]*?```', '', text)

    tts_match = re.search(r'<tts-summary>(.*?)</tts-summary>', text_without_code, re.DOTALL | re.IGNORECASE)
    if tts_match:
        summary = tts_match.group(1).strip()
        summary = re.sub(r'\s+', ' ', summary).strip()
        summary = re.sub(r'\U0001f399\ufe0f\s*', '', summary)
        log_debug(f"Extracted <tts-summary> tag: {summary}")
        return summary

    log_debug("No <tts-summary> tag found, using first sentences as fallback")

    t = re.sub(r'<[^>]+>', '', text)
    t = re.sub(r'```[\s\S]*?```', '', t)
    t = re.sub(r'[*`]', '', t)
    t = re.sub(r'\n+', ' ', t)
    t = re.sub(r'\s+', ' ', t).strip()

    sentences = re.split(r'(?<=[.!?])\s+', t)

    if not sentences or not sentences[0]:
        return ""

    notification = sentences[0]
    if len(notification) < 100 and len(sentences) > 1:
        notification += " " + sentences[1]

    notification = notification.strip()
    if notification and notification[-1] not in '.!?':
        notification += '.'

    return notification


def main():
    """Main entry point."""
    log_debug("TTS client started")

    # Skip TTS for mobile sessions
    if os.environ.get("CATALYST_MOBILE_SESSION") == "true" or os.environ.get("BUILDEROS_MOBILE_SESSION") == "true":
        log_debug("Mobile session detected, skipping TTS (playing on iOS)")
        return

    # Skip TTS for Telegram sessions
    if os.environ.get("CATALYST_TELEGRAM_SESSION") == "true" or os.environ.get("BUILDEROS_TELEGRAM_SESSION") == "true":
        log_debug("Telegram session detected, skipping TTS (user is remote)")
        return

    if not acquire_lock():
        log_debug("Another instance running, exiting")
        return

    try:
        input_data = sys.stdin.read()
        if not input_data or len(input_data.strip()) < 20:
            log_debug("Input too short")
            return

        try:
            data = json.loads(input_data)
            text = extract_hook_text(data)
            if not text:
                log_debug("No text extracted from hook payload, skipping TTS")
                return
        except Exception as e:
            log_debug(f"JSON parsing failed: {e}, skipping TTS")
            return

        summary = create_conceptual_summary(text)
        log_debug(f"Summary: {len(summary)} chars")

        if not summary or len(summary) < 10:
            log_debug("Summary too short")
            return

        if not is_server_ready():
            if is_server_running():
                log_debug("Server process alive but not ready, waiting...")
                for _ in range(20):
                    time.sleep(0.5)
                    if is_server_ready():
                        break
            else:
                log_debug("Server not running, starting...")
                if not start_server():
                    log_debug("Failed to start server, skipping TTS")
                    return

        if not is_server_ready():
            log_debug("Server still not ready after waiting, skipping TTS")
            return

        audio_path = send_tts_request(summary)

        if audio_path and audio_path.exists():
            play_audio(audio_path)
            log_debug("TTS completed successfully")
        else:
            log_debug("TTS request failed")

    except Exception as e:
        log_debug(f"Client error: {e}")
    finally:
        release_lock()


if __name__ == "__main__":
    main()
