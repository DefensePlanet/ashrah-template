#!/usr/bin/env python3.12
"""
Create Telegram {{ORCHESTRATOR_NAME}} Bot - Standalone Version

Creates a Telegram bot for the standalone {{ORCHESTRATOR_NAME}} bot (not capsule-specific).
"""

import asyncio
import json
import os
import re
import sys

sys.path.insert(0, '{{CATALYST_ROOT}}/tools/bots/telegram')

from telethon import TelegramClient
from config import API_ID, API_HASH

# Constants
SESSION_PATH = '{{CATALYST_ROOT}}/tools/builder_session'
ENV_PATH = '{{CATALYST_ROOT}}/tools/telegram-{{ORCHESTRATOR_NAME_LOWER}}-bot/.env'


async def create_bot_via_botfather(client, display_name: str, bot_username: str) -> dict:
    """Create a new bot by messaging @BotFather."""
    botfather = await client.get_entity('@BotFather')

    print(f"📱 Creating bot: {display_name} (@{bot_username})")

    # Send /newbot
    await client.send_message(botfather, '/newbot')
    await asyncio.sleep(2)

    # Send display name
    await client.send_message(botfather, display_name)
    await asyncio.sleep(2)

    # Send username
    await client.send_message(botfather, bot_username)
    await asyncio.sleep(3)

    # Get response with token
    messages = await client.get_messages(botfather, limit=1)
    response = messages[0].text

    # Check for errors
    if 'Sorry' in response or 'already' in response.lower():
        return {'error': response}

    # Extract token
    token_match = re.search(r'(\d+:[A-Za-z0-9_-]+)', response)
    if not token_match:
        return {'error': 'Could not extract token from response', 'response': response}

    token = token_match.group(1)

    return {
        'token': token,
        'username': bot_username,
        'display_name': display_name,
    }


async def configure_bot_profile(client, bot_username: str, description: str, about: str):
    """Set bot description and about text via BotFather."""
    botfather = await client.get_entity('@BotFather')

    # Set description
    print(f"📝 Setting description...")
    await client.send_message(botfather, '/setdescription')
    await asyncio.sleep(1.5)
    await client.send_message(botfather, f'@{bot_username}')
    await asyncio.sleep(1.5)
    await client.send_message(botfather, description)
    await asyncio.sleep(1.5)

    # Set about
    print(f"📝 Setting about...")
    await client.send_message(botfather, '/setabouttext')
    await asyncio.sleep(1.5)
    await client.send_message(botfather, f'@{bot_username}')
    await asyncio.sleep(1.5)
    await client.send_message(botfather, about)
    await asyncio.sleep(1.5)


def update_env_file(token: str, bot_username: str) -> None:
    """Update the .env file with the new bot token."""
    if not os.path.exists(ENV_PATH):
        print(f"❌ .env file not found: {ENV_PATH}")
        sys.exit(1)

    with open(ENV_PATH, 'r') as f:
        content = f.read()

    # Replace the token
    content = re.sub(
        r'TELEGRAM_BOT_TOKEN=.*',
        f'TELEGRAM_BOT_TOKEN={token}',
        content
    )

    with open(ENV_PATH, 'w') as f:
        f.write(content)

    print(f"✅ Updated {ENV_PATH}")


async def start_conversation(client, bot_username: str):
    """Start a conversation with the bot by sending /start."""
    print(f"💬 Starting conversation with @{bot_username}...")

    bot = await client.get_entity(f'@{bot_username}')
    await client.send_message(bot, '/start')

    # Wait for response
    await asyncio.sleep(3)

    messages = await client.get_messages(bot, limit=1)
    return messages[0].text if messages else None


async def main():
    display_name = "{{ORCHESTRATOR_NAME}}"
    bot_username = "TyCatalyst{{ORCHESTRATOR_NAME}}Bot"
    description = "{{USER_NAME}}'s {{ORCHESTRATOR_NAME}} - Full Catalyst system with 28 agents and 323 skills"
    about = "{{ORCHESTRATOR_NAME}} assistant powered by Claude - Your Number-2 for the Catalyst System"

    # Connect to Telegram
    print("🔗 Connecting to Telegram...")
    client = TelegramClient(SESSION_PATH, API_ID, API_HASH)
    await client.connect()

    if not await client.is_user_authorized():
        print("❌ Telethon session not authorized. Run authenticate_telethon.py first.")
        await client.disconnect()
        sys.exit(1)

    print("✅ Connected")

    # Create bot
    bot_result = await create_bot_via_botfather(client, display_name, bot_username)

    if 'error' in bot_result:
        print(f"❌ Failed to create bot: {bot_result['error']}")
        await client.disconnect()
        sys.exit(1)

    token = bot_result['token']
    print(f"✅ Bot created: @{bot_username}")
    print(f"🔑 Token: {token}")

    # Configure profile
    await configure_bot_profile(client, bot_username, description, about)
    print("✅ Bot profile configured")

    # Update .env file
    update_env_file(token, bot_username)

    # Start conversation
    await asyncio.sleep(2)
    response = await start_conversation(client, bot_username)
    if response:
        print(f"✅ Conversation started")
        print(f"📱 First response: {response[:100]}...")

    await client.disconnect()

    print("\n" + "=" * 60)
    print(f"✅ {{ORCHESTRATOR_NAME}} Bot Created Successfully!")
    print("=" * 60)
    print(f"📱 Bot: @{bot_username}")
    print(f"🔑 Token: {token}")
    print(f"🔧 Config updated: {ENV_PATH}")
    print(f"\n💬 Next step: Restart the bot service")
    print("   Run: launchctl unload ~/Library/LaunchAgents/com.catalyst.telegram-{{ORCHESTRATOR_NAME_LOWER}}-bot.plist")
    print("   Then: launchctl load ~/Library/LaunchAgents/com.catalyst.telegram-{{ORCHESTRATOR_NAME_LOWER}}-bot.plist")


if __name__ == '__main__':
    asyncio.run(main())
