#!/usr/bin/env python3
"""
Global Telegram Integration for BuilderOS

Provides centralized access to Telegram via Telethon for all capsules.
Credentials are stored in Strongbox and loaded dynamically.

Usage:
    from global.integrations.telegram import TelegramIntegration

    # Get Telethon client for user-level access
    async with TelegramIntegration.get_client() as client:
        await client.send_message("username", "Hello!")

    # Get bot token for a specific bot
    token = TelegramIntegration.get_bot_token("{{ORCHESTRATOR_NAME_LOWER}}")
"""

import os
import sys
from pathlib import Path
from typing import Optional, Dict, Any

# Add tools to path for Strongbox access
CATALYST_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(CATALYST_ROOT / "tools"))

try:
    from pykeepass import PyKeePass
except ImportError:
    PyKeePass = None

# Strongbox configuration
STRONGBOX_DB = "{{HOME_DIR}}/Library/Mobile Documents/iCloud~com~strongbox/Documents/Roth Pass.kdbx"
STRONGBOX_PASSWORD = ""  # Empty password for {{USER_NAME}}'s database

# Telethon session location
SESSION_PATH = CATALYST_ROOT / "tools" / "telegram" / "builder_session"


class TelegramIntegration:
    """Centralized Telegram access for BuilderOS."""

    _credentials_cache: Dict[str, Any] = {}

    @classmethod
    def _get_strongbox(cls) -> Optional["PyKeePass"]:
        """Get PyKeePass instance."""
        if PyKeePass is None:
            raise ImportError("PyKeePass not installed. Run: pip3 install pykeepass")
        return PyKeePass(STRONGBOX_DB, password=STRONGBOX_PASSWORD)

    @classmethod
    def _find_entry(cls, kp: "PyKeePass", title: str) -> Optional[Any]:
        """Find Strongbox entry by title, excluding Recycle Bin."""
        entries = [e for e in kp.find_entries(title=title, regex=False)
                   if 'Recycle Bin' not in str(e.path)]
        return entries[0] if entries else None

    @classmethod
    def get_telethon_credentials(cls) -> Dict[str, str]:
        """
        Get Telethon API credentials from Strongbox.

        Returns:
            Dict with keys: api_id, api_hash, session_path
        """
        if 'telethon' in cls._credentials_cache:
            return cls._credentials_cache['telethon']

        kp = cls._get_strongbox()
        entry = cls._find_entry(kp, 'Telegram - Telethon API')

        if not entry:
            raise ValueError("Telegram - Telethon API entry not found in Strongbox")

        creds = {
            'api_id': int(entry.get_custom_property('API_ID')),
            'api_hash': entry.get_custom_property('API_HASH'),
            'session_path': str(SESSION_PATH),
        }

        cls._credentials_cache['telethon'] = creds
        return creds

    @classmethod
    def get_bot_token(cls, bot_name: str = "{{ORCHESTRATOR_NAME_LOWER}}") -> str:
        """
        Get bot token from Strongbox.

        Args:
            bot_name: "{{ORCHESTRATOR_NAME_LOWER}}" or "mid_portal"

        Returns:
            Bot token string
        """
        cache_key = f'bot_{bot_name}'
        if cache_key in cls._credentials_cache:
            return cls._credentials_cache[cache_key]

        kp = cls._get_strongbox()

        title_map = {
            '{{ORCHESTRATOR_NAME_LOWER}}': 'Telegram - {{ORCHESTRATOR_NAME}} Bot',
            'mid_portal': 'Telegram - MID Portal Bot',
        }

        title = title_map.get(bot_name)
        if not title:
            raise ValueError(f"Unknown bot: {bot_name}. Use: {list(title_map.keys())}")

        entry = cls._find_entry(kp, title)
        if not entry:
            raise ValueError(f"{title} entry not found in Strongbox")

        token = entry.get_custom_property('BOT_TOKEN')
        cls._credentials_cache[cache_key] = token
        return token

    @classmethod
    def get_chat_id(cls, bot_name: str) -> Optional[int]:
        """Get configured chat ID for a bot."""
        kp = cls._get_strongbox()

        title_map = {
            'mid_portal': 'Telegram - MID Portal Bot',
        }

        title = title_map.get(bot_name)
        if not title:
            return None

        entry = cls._find_entry(kp, title)
        if not entry:
            return None

        chat_id = entry.get_custom_property('CHAT_ID')
        return int(chat_id) if chat_id else None

    @classmethod
    async def get_client(cls):
        """
        Get an async context manager for a Telethon client.

        Usage:
            async with TelegramIntegration.get_client() as client:
                await client.send_message(...)
        """
        try:
            from telethon import TelegramClient
        except ImportError:
            raise ImportError("Telethon not installed. Run: pip3 install telethon")

        creds = cls.get_telethon_credentials()
        client = TelegramClient(
            creds['session_path'],
            creds['api_id'],
            creds['api_hash']
        )
        return client

    @classmethod
    def clear_cache(cls):
        """Clear credentials cache."""
        cls._credentials_cache.clear()


# Convenience functions for direct import
def get_telethon_credentials() -> Dict[str, str]:
    """Get Telethon API credentials."""
    return TelegramIntegration.get_telethon_credentials()


def get_bot_token(bot_name: str = "{{ORCHESTRATOR_NAME_LOWER}}") -> str:
    """Get bot token by name."""
    return TelegramIntegration.get_bot_token(bot_name)


async def get_client():
    """Get Telethon client context manager."""
    return await TelegramIntegration.get_client()


# CLI for testing
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Telegram Integration CLI")
    parser.add_argument("command", choices=["creds", "bot", "test"],
                       help="Command to run")
    parser.add_argument("--bot", default="{{ORCHESTRATOR_NAME_LOWER}}", help="Bot name for 'bot' command")

    args = parser.parse_args()

    if args.command == "creds":
        creds = get_telethon_credentials()
        print(f"API ID: {creds['api_id']}")
        print(f"API Hash: {creds['api_hash'][:8]}...{creds['api_hash'][-4:]}")
        print(f"Session: {creds['session_path']}")

    elif args.command == "bot":
        token = get_bot_token(args.bot)
        print(f"Bot: {args.bot}")
        print(f"Token: {token[:12]}...{token[-4:]}")

    elif args.command == "test":
        import asyncio

        async def test():
            client = await get_client()
            await client.connect()
            me = await client.get_me()
            print(f"Connected as: {me.first_name} (@{me.username})")
            await client.disconnect()

        asyncio.run(test())
