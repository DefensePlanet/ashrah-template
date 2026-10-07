#!/usr/bin/env python3
"""
General-purpose Telegram notification sender for Catalyst.

Reads bot token from ~/.openclaw/openclaw.json. Uses stdlib-only
(urllib.request) -- zero external dependencies. Fire-and-forget:
all errors logged to stderr, never raises.

Usage:
    python3 tools/notify_telegram.py --chat-id CHAT_ID --message "text"
    python3 tools/notify_telegram.py --chat-id CHAT_ID --message "text" --parse-mode HTML
    echo "message" | python3 tools/notify_telegram.py --chat-id CHAT_ID
"""

import argparse
import json
import logging
import sys
import urllib.request
from pathlib import Path
from typing import Optional

OPENCLAW_CONFIG = Path.home() / ".openclaw" / "openclaw.json"

logger = logging.getLogger(__name__)


def get_bot_token() -> Optional[str]:
    """Read bot token from OpenClaw config at channels.telegram.botToken."""
    if not OPENCLAW_CONFIG.exists():
        logger.warning("OpenClaw config not found: %s", OPENCLAW_CONFIG)
        return None
    try:
        with open(OPENCLAW_CONFIG) as f:
            config = json.load(f)
        token = config.get("channels", {}).get("telegram", {}).get("botToken")
        if not token:
            logger.warning("No botToken found in OpenClaw config")
        return token
    except (json.JSONDecodeError, IOError) as exc:
        logger.warning("Failed to read OpenClaw config: %s", exc)
        return None


def send(
    text: str,
    chat_id: str,
    parse_mode: Optional[str] = None,
    disable_preview: bool = True,
) -> bool:
    """Send a Telegram message. Returns True on success, False on failure."""
    token = get_bot_token()
    if not token:
        logger.error("No bot token available -- notification skipped")
        return False

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "disable_web_page_preview": disable_preview,
    }
    if parse_mode:
        payload["parse_mode"] = parse_mode

    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            if result.get("ok"):
                return True
            logger.error("Telegram API error: %s", result.get("description"))
            return False
    except Exception as exc:
        logger.error("Failed to send Telegram notification: %s", exc)
        return False


def main() -> int:
    logging.basicConfig(level=logging.WARNING, format="%(levelname)s: %(message)s")

    parser = argparse.ArgumentParser(description="Send Telegram notification")
    parser.add_argument("--chat-id", required=True, help="Telegram chat ID")
    parser.add_argument("--message", "-m", help="Message text (or pipe via stdin)")
    parser.add_argument(
        "--parse-mode", choices=["HTML", "MarkdownV2"], default=None
    )
    args = parser.parse_args()

    text = args.message or sys.stdin.read().strip()
    if not text:
        print("Error: no message provided", file=sys.stderr)
        return 1

    ok = send(text, args.chat_id, parse_mode=args.parse_mode)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
