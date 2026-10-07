#!/usr/bin/env python3.12
"""
Full conversation test with the {{ORCHESTRATOR_NAME}} bot.
"""

import asyncio
import sys

sys.path.insert(0, '{{CATALYST_ROOT}}/tools/bots/telegram')

from telethon import TelegramClient
from config import API_ID, API_HASH

SESSION_PATH = '{{CATALYST_ROOT}}/tools/builder_session'


async def test_conversation():
    client = TelegramClient(SESSION_PATH, API_ID, API_HASH)
    await client.connect()

    if not await client.is_user_authorized():
        print("❌ Not authorized")
        await client.disconnect()
        return

    bot = await client.get_entity('@TyCatalyst{{ORCHESTRATOR_NAME}}Bot')
    print(f"✅ Connected to: {bot.username}\n")

    # Start new session
    print("1️⃣ Starting new session...")
    await client.send_message(bot, '/new')
    await asyncio.sleep(3)

    messages = await client.get_messages(bot, limit=1)
    print(f"📥 Response:\n{messages[0].text[:200]}...\n")

    # Send actual message
    print("2️⃣ Sending test question...")
    await client.send_message(bot, "Hello {{ORCHESTRATOR_NAME}}! Quick test - what's 2+2? Keep it brief.")

    print("⏳ Waiting for response (15 seconds)...")
    await asyncio.sleep(15)

    messages = await client.get_messages(bot, limit=1)
    print(f"\n📥 Bot response:\n{messages[0].text}\n")

    await client.disconnect()
    print("✅ Test complete!")


if __name__ == '__main__':
    asyncio.run(test_conversation())
