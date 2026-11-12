"""
Telegram notification sender for watch alerts.

Reads the bot token from ~/.openclaw/openclaw.json (the shared OpenClaw
Telegram bot). Sends messages to the wardrobe-shopper group chat.

Uses stdlib-only networking (urllib.request) so this module has zero
external dependencies beyond Python 3.9+.
"""

import json
import logging
import urllib.request
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

OPENCLAW_CONFIG = Path.home() / ".openclaw" / "openclaw.json"
WARDROBE_GROUP_ID = "-1003527973716"


def _get_bot_token() -> Optional[str]:
    """Read bot token from OpenClaw config.

    The token lives at config["channels"]["telegram"]["botToken"].
    Returns None if the file or key is missing (notifications disabled
    gracefully).
    """
    if not OPENCLAW_CONFIG.exists():
        logger.debug("OpenClaw config not found at %s", OPENCLAW_CONFIG)
        return None

    try:
        with open(OPENCLAW_CONFIG) as f:
            config = json.load(f)
        token = config.get("channels", {}).get("telegram", {}).get("botToken")
        if not token:
            logger.debug("No botToken found in OpenClaw config")
        return token
    except (json.JSONDecodeError, IOError) as e:
        logger.warning("Failed to read OpenClaw config: %s", e)
        return None


def send_telegram_message(
    text: str,
    chat_id: str = WARDROBE_GROUP_ID,
) -> bool:
    """Send a message via Telegram Bot API.

    Returns True on success, False on failure.  Never raises; all errors
    are logged and swallowed so callers can fire-and-forget.
    """
    token = _get_bot_token()
    if not token:
        logger.warning(
            "No bot token found in OpenClaw config, skipping notification"
        )
        return False

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    data = {
        "chat_id": chat_id,
        "text": text,
        "disable_web_page_preview": True,
    }

    req = urllib.request.Request(
        url,
        data=json.dumps(data).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )

    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            result = json.loads(response.read().decode("utf-8"))
            if result.get("ok"):
                logger.debug("Telegram notification sent to %s", chat_id)
                return True
            logger.error(
                "Telegram API returned ok=false: %s",
                result.get("description", "unknown error"),
            )
            return False
    except Exception as e:
        logger.error("Failed to send Telegram notification: %s", e)
        return False
