#!/usr/bin/env python3.12
"""
Set Telegram Bot Menu Commands via Telethon API.

Configures the / command menu that appears in Telegram conversations
with the {{ORCHESTRATOR_NAME}} bot. Authenticates as the bot itself via bot token.

Usage:
    python3 set-bot-menu.py          # Set all commands
    python3 set-bot-menu.py --reset  # Clear all commands
    python3 set-bot-menu.py --show   # Show current command list
"""

import argparse
import asyncio
import os
import sys

sys.path.insert(0, '{{CATALYST_ROOT}}/tools/bots/telegram')

from telethon import TelegramClient
from telethon.tl.functions.bots import SetBotCommandsRequest, ResetBotCommandsRequest, GetBotCommandsRequest
from telethon.tl.types import (
    BotCommand,
    BotCommandScopeDefault,
    BotCommandScopeChats,
    BotCommandScopeChatAdmins,
    BotCommandScopePeer,
    BotCommandScopeUsers,
)
from telethon.tl.functions.messages import GetDialogsRequest
from telethon.tl.types import InputPeerEmpty
from config import API_ID, API_HASH

ENV_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')
SESSION_PATH = '/tmp/{{ORCHESTRATOR_NAME_LOWER}}-bot-menu-session'

# ── Command definitions (matches TC3 Grammy handlers) ──────────────────

COMMANDS = [
    BotCommand(command='start',      description='Show welcome message and help'),
    BotCommand(command='new',        description='Start a fresh session'),
    BotCommand(command='stop',       description='Stop current query'),
    BotCommand(command='status',     description='Show detailed bot status'),
    BotCommand(command='mode',       description='Toggle PI (fast) / CLI (full) mode'),
    BotCommand(command='fast',       description='Switch to Fast (PI) mode'),
    BotCommand(command='cli',        description='Switch to CLI mode'),
    BotCommand(command='resume',     description='Resume a saved session'),
    BotCommand(command='retry',      description='Retry the last message'),
    BotCommand(command='restart',    description='Restart the bot process'),
    BotCommand(command='capsule',    description='Manage capsule bindings'),
    BotCommand(command='sync',       description='Reload agents and skills'),
    BotCommand(command='context',    description='View session context'),
    BotCommand(command='specialist', description='Manage active specialist'),
    BotCommand(command='skills',     description='Manage loaded skills'),
]


def load_bot_token() -> str:
    """Load bot token from macOS Keychain (primary) or .env (fallback)."""
    import subprocess

    # Try Keychain first
    try:
        result = subprocess.run(
            ['security', 'find-generic-password', '-s', 'tc3-telegram-bot-token', '-w'],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode == 0 and result.stdout.strip():
            token = result.stdout.strip()
            if not token.startswith('123456'):
                print("🔑 Token loaded from macOS Keychain")
                return token
    except Exception:
        pass

    # Fallback to .env
    if os.path.exists(ENV_PATH):
        with open(ENV_PATH) as f:
            for line in f:
                line = line.strip()
                if line.startswith('TELEGRAM_BOT_TOKEN=') and not line.startswith('#'):
                    token = line.split('=', 1)[1].strip().strip('"\'')
                    if token and not token.startswith('123456'):
                        print("🔑 Token loaded from .env")
                        return token

    print("❌ Bot token not found in Keychain (tc3-telegram-bot-token) or .env")
    sys.exit(1)


def cleanup_session():
    """Remove temporary session files."""
    for suffix in ('', '.session', '.session-journal'):
        path = SESSION_PATH + suffix
        if os.path.exists(path):
            os.remove(path)


async def set_commands(client: TelegramClient):
    """Set bot commands for ALL scopes: default, private chats, groups, and group admins."""
    print(f"📋 Setting {len(COMMANDS)} bot commands across all scopes...\n")

    scopes = [
        ("Default (fallback)", BotCommandScopeDefault()),
        ("Private chats", BotCommandScopeUsers()),
        ("All group chats", BotCommandScopeChats()),
        ("Group admins", BotCommandScopeChatAdmins()),
    ]

    for label, scope in scopes:
        try:
            await client(SetBotCommandsRequest(
                scope=scope,
                lang_code='',
                commands=COMMANDS,
            ))
            print(f"  ✅ {label}")
        except Exception as e:
            print(f"  ⚠️  {label}: {e}")

    print(f"\n📋 Commands registered:")
    for cmd in COMMANDS:
        print(f"  /{cmd.command} — {cmd.description}")


async def reset_commands(client: TelegramClient):
    """Clear all bot commands across all scopes."""
    print("🗑️  Clearing all bot commands...")

    scopes = [
        ("Default", BotCommandScopeDefault()),
        ("Private chats", BotCommandScopeUsers()),
        ("All group chats", BotCommandScopeChats()),
        ("Group admins", BotCommandScopeChatAdmins()),
    ]

    for label, scope in scopes:
        try:
            await client(ResetBotCommandsRequest(
                scope=scope,
                lang_code='',
            ))
            print(f"  ✅ {label} cleared")
        except Exception as e:
            print(f"  ⚠️  {label}: {e}")

    print("✅ Bot menu cleared.")


async def show_commands(client: TelegramClient):
    """Show currently registered bot commands."""
    print("📋 Current bot commands:\n")

    result = await client(GetBotCommandsRequest(
        scope=BotCommandScopeDefault(),
        lang_code='',
    ))

    if not result:
        print("  (none)")
        return

    for cmd in result:
        print(f"  /{cmd.command} — {cmd.description}")


async def main():
    parser = argparse.ArgumentParser(description='Configure {{ORCHESTRATOR_NAME}} bot menu via Telethon')
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--reset', action='store_true', help='Clear all commands')
    group.add_argument('--show', action='store_true', help='Show current commands')
    args = parser.parse_args()

    bot_token = load_bot_token()

    print("🔗 Connecting to Telegram as bot...")
    client = TelegramClient(SESSION_PATH, API_ID, API_HASH)
    try:
        await client.start(bot_token=bot_token)
    except Exception as e:
        print(f"❌ Failed to connect: {e}")
        cleanup_session()
        sys.exit(1)
    print("✅ Connected\n")

    try:
        if args.reset:
            await reset_commands(client)
        elif args.show:
            await show_commands(client)
        else:
            await set_commands(client)
    finally:
        await client.disconnect()
        cleanup_session()

    print("\n🎉 Done!")


if __name__ == '__main__':
    asyncio.run(main())
