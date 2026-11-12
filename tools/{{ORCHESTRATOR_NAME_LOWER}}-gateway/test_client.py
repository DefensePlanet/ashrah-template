#!/usr/bin/env python3
"""
{{ORCHESTRATOR_NAME}} Gateway Test Client - macOS
Simple client to test voice interaction with {{ORCHESTRATOR_NAME}}
"""

import asyncio
import json
import base64
import sys
import tempfile
import subprocess
import websockets

GATEWAY_URL = "ws://localhost:18800"


async def send_message(text: str):
    """Send a message to {{ORCHESTRATOR_NAME}} and play the response."""
    print(f"\n🎤 You: {text}")
    print("⏳ Waiting for {{ORCHESTRATOR_NAME}}...")

    try:
        async with websockets.connect(GATEWAY_URL) as ws:
            # Send transcript
            await ws.send(json.dumps({
                "type": "transcript",
                "text": text
            }))

            # Collect response
            audio_chunks = []
            response_text = ""

            while True:
                try:
                    msg = await asyncio.wait_for(ws.recv(), timeout=30.0)
                    data = json.loads(msg)

                    if data.get("type") == "text":
                        response_text = data.get("content", "")
                        print(f"\n🤖 {{ORCHESTRATOR_NAME}}: {response_text}")

                    elif data.get("type") == "audio":
                        audio_data = base64.b64decode(data.get("data", ""))
                        audio_chunks.append(audio_data)

                    elif data.get("type") == "done":
                        break

                    elif data.get("type") == "dispatch":
                        print(f"📤 Dispatching to Claude Code: {data.get('task', '')[:50]}...")

                except asyncio.TimeoutError:
                    print("⚠️ Timeout waiting for response")
                    break

            # Play audio if we got any
            if audio_chunks:
                audio_data = b"".join(audio_chunks)
                print(f"\n🔊 Playing audio ({len(audio_data) // 1024}KB)...")

                # Save to temp file and play with afplay
                with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                    f.write(audio_data)
                    temp_path = f.name

                # Play audio using macOS afplay
                subprocess.run(["afplay", temp_path], check=True)

                # Cleanup
                import os
                os.unlink(temp_path)
                print("✅ Done")
            else:
                print("⚠️ No audio received")

    except ConnectionRefusedError:
        print("❌ Could not connect to {{ORCHESTRATOR_NAME}} Gateway")
        print("   Make sure the gateway is running: docker compose up -d")
    except Exception as e:
        print(f"❌ Error: {e}")


async def interactive_mode():
    """Interactive chat mode."""
    print("=" * 50)
    print("  {{ORCHESTRATOR_NAME_UPPER}} VOICE TEST CLIENT")
    print("  Type messages to talk to {{ORCHESTRATOR_NAME}}")
    print("  Type 'quit' or 'exit' to stop")
    print("=" * 50)

    while True:
        try:
            text = input("\n💬 Enter message: ").strip()
            if text.lower() in ("quit", "exit", "q"):
                print("👋 Goodbye!")
                break
            if not text:
                continue
            await send_message(text)
        except KeyboardInterrupt:
            print("\n👋 Goodbye!")
            break
        except EOFError:
            break


def main():
    if len(sys.argv) > 1:
        # Single message mode
        message = " ".join(sys.argv[1:])
        asyncio.run(send_message(message))
    else:
        # Interactive mode
        asyncio.run(interactive_mode())


if __name__ == "__main__":
    main()
