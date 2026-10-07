#!/usr/bin/env python3.12
"""
Test the {{ORCHESTRATOR_NAME}} bot by sending a message and checking response.
"""

import asyncio
import sys

sys.path.insert(0, '{{CATALYST_ROOT}}/tools/bots/telegram')

from telethon import TelegramClient
from config import API_ID, API_HASH

SESSION_PATH = '{{CATALYST_ROOT}}/tools/builder_session'


async def test_bot():
    client = TelegramClient(SESSION_PATH, API_ID, API_HASH)
    await client.connect()

    if not await client.is_user_authorized():
        print("❌ Not authorized")
        await client.disconnect()
        return

    # Get the bot
    bot = await client.get_entity('@TyCatalyst{{ORCHESTRATOR_NAME}}Bot')
    print(f"✅ Found bot: {bot.username}")

    # Send test message
    print("📤 Sending test message...")
    await client.send_message(bot, "Hello {{ORCHESTRATOR_NAME}}! Quick test - what's 2+2?")

    # Wait for response
    await asyncio.sleep(5)

    # Get latest message
    messages = await client.get_messages(bot, limit=1)
    if messages:
        response = messages[0].text
        print(f"📥 Bot response:\n{response}")
    else:
        print("⚠️  No response yet")

    await client.disconnect()


if __name__ == '__main__':
    asyncio.run(test_bot())
