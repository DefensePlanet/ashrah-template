#!/usr/bin/env python3
"""
Talk to {{ORCHESTRATOR_NAME}} - Full Conversational AI Test Client
Voice input → {{ORCHESTRATOR_NAME}} → Voice output
"""

import asyncio
import json
import base64
import tempfile
import subprocess
import os
import websockets
import speech_recognition as sr

GATEWAY_URL = "ws://localhost:18800"


class {{ORCHESTRATOR_NAME}}Client:
    def __init__(self):
        self.recognizer = sr.Recognizer()
        self.microphone = sr.Microphone()
        self.running = True

        # Adjust for ambient noise on startup
        print("🎙️ Calibrating microphone for ambient noise...")
        with self.microphone as source:
            self.recognizer.adjust_for_ambient_noise(source, duration=1)
        print("✅ Ready!")

    def listen(self) -> str | None:
        """Listen for voice input and return transcribed text."""
        print("\n🎤 Listening... (speak now)")

        try:
            with self.microphone as source:
                # Listen with timeout
                audio = self.recognizer.listen(source, timeout=10, phrase_time_limit=15)

            print("🔄 Transcribing...")

            # Use macOS speech recognition (or Google as fallback)
            try:
                # Try macOS first (faster, no internet needed)
                text = self.recognizer.recognize_whisper(audio, model="base")
            except Exception:
                # Fallback to Google
                text = self.recognizer.recognize_google(audio)

            return text.strip()

        except sr.WaitTimeoutError:
            print("⏰ No speech detected")
            return None
        except sr.UnknownValueError:
            print("❓ Could not understand audio")
            return None
        except Exception as e:
            print(f"❌ Error: {e}")
            return None

    async def send_to_{{ORCHESTRATOR_NAME_LOWER}}(self, text: str) -> bool:
        """Send text to {{ORCHESTRATOR_NAME}} and play response."""
        print(f"\n💬 You said: {text}")
        print("⏳ {{ORCHESTRATOR_NAME}} is thinking...")

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
                            task = data.get("task", "")[:50]
                            print(f"📤 Dispatching to Claude Code: {task}...")

                    except asyncio.TimeoutError:
                        print("⚠️ Timeout")
                        break

                # Play audio
                if audio_chunks:
                    audio_data = b"".join(audio_chunks)

                    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                        f.write(audio_data)
                        temp_path = f.name

                    # Play with afplay (macOS)
                    subprocess.run(["afplay", temp_path], check=True)
                    os.unlink(temp_path)

                return True

        except ConnectionRefusedError:
            print("❌ Cannot connect to {{ORCHESTRATOR_NAME}} Gateway")
            print("   Run: cd tools/{{ORCHESTRATOR_NAME_LOWER}}-gateway && docker compose up -d")
            return False
        except Exception as e:
            print(f"❌ Error: {e}")
            return False

    async def conversation_loop(self):
        """Main conversation loop - listen, respond, repeat."""
        print("\n" + "=" * 55)
        print("  🎭 {{ORCHESTRATOR_NAME_UPPER}} CONVERSATIONAL AI - VOICE MODE")
        print("  Speak naturally. Say 'goodbye' or 'exit' to quit.")
        print("  Press Ctrl+C to stop.")
        print("=" * 55)

        while self.running:
            # Listen for input
            text = self.listen()

            if text is None:
                continue

            # Check for exit commands
            if any(word in text.lower() for word in ["goodbye", "exit", "quit", "stop listening"]):
                print("\n👋 {{ORCHESTRATOR_NAME}}: Goodbye, sir.")
                # Play goodbye
                await self.send_to_{{ORCHESTRATOR_NAME_LOWER}}("Say a brief goodbye")
                break

            # Send to {{ORCHESTRATOR_NAME}}
            success = await self.send_to_{{ORCHESTRATOR_NAME_LOWER}}(text)
            if not success:
                print("Retrying in 2 seconds...")
                await asyncio.sleep(2)

    def run(self):
        """Start the conversation."""
        try:
            asyncio.run(self.conversation_loop())
        except KeyboardInterrupt:
            print("\n\n👋 Goodbye!")


def main():
    print("🚀 Starting {{ORCHESTRATOR_NAME}} Conversational AI...")
    client = {{ORCHESTRATOR_NAME}}Client()
    client.run()


if __name__ == "__main__":
    main()
