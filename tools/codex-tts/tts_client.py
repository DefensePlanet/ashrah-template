#!/usr/bin/env python3
"""
TTS Client - Sends requests to persistent TTS server

Fast TTS hook that communicates with the pre-loaded model server.
Falls back to direct generation if server is unavailable.
"""

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

# Server configuration
SERVER_HOST = "127.0.0.1"
SERVER_PORT = 9876
SERVER_SCRIPT = Path(__file__).parent / "tts_server.py"
PID_FILE = Path.home() / '.claude' / 'tts_server.pid'
LOG_FILE = Path.home() / '.claude' / 'tts_client.log'


def _find_python() -> str:
    """Find a suitable Python 3.11+ interpreter."""
    if sys.version_info >= (3, 11):
        return sys.executable
    candidates = [
        "/Library/Frameworks/Python.framework/Versions/3.11/bin/python3",
        "/Library/Frameworks/Python.framework/Versions/3.12/bin/python3",
        "/Library/Frameworks/Python.framework/Versions/3.13/bin/python3",
        "/opt/homebrew/bin/python3",
        "/usr/local/bin/python3",
    ]
    for c in candidates:
        if Path(c).exists():
            return c
    return "python3"


def log_debug(message: str) -> None:
    """Log debug information."""
    try:
        LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(LOG_FILE, 'a') as f:
            f.write(f"[{datetime.now().isoformat()}] {message}\n")
    except Exception:
        pass


def is_server_running() -> bool:
    """Check if TTS server is running."""
    if not PID_FILE.exists():
        return False

    try:
        with open(PID_FILE, 'r') as f:
            pid = int(f.read().strip())

        # Check if process exists
        os.kill(pid, 0)
        return True
    except (OSError, ValueError):
        # Process doesn't exist, clean up PID file
        if PID_FILE.exists():
            PID_FILE.unlink()
        return False


def start_server() -> bool:
    """Start the TTS server in background."""
    log_debug("Starting TTS server...")

    try:
        python_path = _find_python()

        # Start server as background daemon
        subprocess.Popen(
            [python_path, str(SERVER_SCRIPT)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True
        )

        # Wait for server to start
        for _ in range(30):  # 3 seconds max
            time.sleep(0.1)
            if is_server_running():
                log_debug("Server started successfully")
                return True

        log_debug("Server start timeout")
        return False

    except Exception as e:
        log_debug(f"Failed to start server: {e}")
        return False


def send_tts_request(text: str, timeout: float = 10.0) -> Optional[Path]:
    """Send TTS request to server and get audio path."""
    try:
        # Create socket
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_socket.settimeout(timeout)

        # Connect to server
        client_socket.connect((SERVER_HOST, SERVER_PORT))

        # Send request
        request = {"text": text}
        request_data = json.dumps(request).encode('utf-8') + b"\n\n"
        client_socket.sendall(request_data)

        # Receive response
        response_data = b""
        while True:
            chunk = client_socket.recv(4096)
            if not chunk:
                break
            response_data += chunk

        client_socket.close()

        # Parse response
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
    """Play audio file."""
    try:
        subprocess.run(
            ['afplay', str(audio_path)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=90
        )
        # Cleanup
        try:
            audio_path.unlink()
        except Exception:
            pass
    except Exception as e:
        log_debug(f"Playback error: {e}")


def create_conceptual_summary(text: str) -> str:
    """Create concise summary of text for TTS."""
    # Normalize/clean
    t = re.sub(r'<[^>]+>', '', text)
    t = re.sub(r'```[\s\S]*?```', ' ', t)
    t = re.sub(r'`([^`]+)`', r'\1', t)
    t = re.sub(r'\*\*(.*?)\*\*', r'\1', t)
    t = re.sub(r'\*(.*?)\*', r'\1', t)
    t = re.sub(r'https?://\S+', ' ', t)
    t = t.replace('•', ' ').replace('–', ' ').replace('- ', ' ')
    t = re.sub(r'\n+', ' ', t)
    t = re.sub(r'\s+', ' ', t).strip()

    # Pattern extraction
    def cap(s: str) -> str:
        s = s.strip().strip('.;,:- ')
        return s[0].upper() + s[1:] if s else s

    actions = re.findall(r'(?:I will|I\'m going to|Let me|I\'ll|I am|We will|Next I|Proceed to)\s+([^.!?]*[.!?])', t, re.IGNORECASE)
    findings = re.findall(r'(?:I found|I discovered|I identified|The issue is|The problem is|It appears|We observed)\s+([^.!?]*[.!?])', t, re.IGNORECASE)
    file_ops = re.findall(r'(?:created|updated|modified|edited|wrote|read|added|removed)\s+([^.!?]*[.!?])', t, re.IGNORECASE)
    nexts = re.findall(r'(?:You should|I recommend|Next steps?|To fix|To resolve|Consider)\s+([^.!?]*[.!?])', t, re.IGNORECASE)

    parts = []
    if actions:
        parts.append(f"Actions: {cap(actions[0])}")
    if findings:
        parts.append(f"Findings: {cap(findings[0])}")
    if file_ops:
        parts.append(f"Files: {cap(file_ops[0])}")
    if nexts:
        parts.append(f"Next: {cap(nexts[0])}")

    if not parts:
        sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', t) if 8 < len(s.strip()) < 160]
        summary = sentences[0] if sentences else t[:140]
    else:
        summary = ' '.join(parts)

    # Clean and truncate
    summary = re.sub(r'[!]+', '.', summary)
    summary = re.sub(r'[🙂😀😄🚀🔥✨✅🟢🔧💡⭐️📦📊⚠️🥳🙌👍👋🧠🎙️]', '', summary)
    summary = re.sub(r'\s+', ' ', summary).strip()

    if len(summary) > 260:
        cut = summary[:260].rstrip()
        m = re.search(r'[.!?](?=[^.!?]*$)', cut)
        summary = (cut[:m.end()] if m else cut)

    if summary and summary[-1] not in '.!?':
        summary += '.'

    return summary


def main():
    """Main entry point."""
    log_debug("TTS client started")

    # Read input
    try:
        input_data = sys.stdin.read()
        if not input_data or len(input_data.strip()) < 20:
            log_debug("Input too short")
            return

        # Parse input
        try:
            data = json.loads(input_data)
            text = data.get("assistant_message", data.get("message", data.get("text", "")))
            if not text:
                text = str(data)
        except:
            text = input_data

        # Create summary
        summary = create_conceptual_summary(text)
        log_debug(f"Summary: {len(summary)} chars")

        if not summary or len(summary) < 10:
            log_debug("Summary too short")
            return

        # Ensure server is running
        if not is_server_running():
            log_debug("Server not running, starting...")
            if not start_server():
                log_debug("Failed to start server, aborting")
                return
            # Give server time to load model (first start only)
            time.sleep(2)

        # Send TTS request
        audio_path = send_tts_request(summary)

        if audio_path and audio_path.exists():
            play_audio(audio_path)
            log_debug("TTS completed successfully")
        else:
            log_debug("TTS request failed")

    except Exception as e:
        log_debug(f"Client error: {e}")


if __name__ == "__main__":
    main()
