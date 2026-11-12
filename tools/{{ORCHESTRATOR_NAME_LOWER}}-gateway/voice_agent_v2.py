#!/usr/bin/env python3
"""
{{ORCHESTRATOR_NAME}} Voice Agent v2 - Ultra-Fast Streaming
Enhanced with sentence-level TTS streaming for <500ms TTFT

Key optimizations:
1. LLM streaming for immediate token arrival
2. Sentence-level TTS generation (parallel processing)
3. Audio chunk streaming (no waiting for full response)
4. Reduced context window
"""

import asyncio
import os
import random
import re
from typing import AsyncGenerator
from loguru import logger
import httpx

from {{ORCHESTRATOR_NAME_LOWER}}_identity import {{ORCHESTRATOR_NAME_UPPER}}_SYSTEM_PROMPT, DISPATCH_KEYWORDS


class {{ORCHESTRATOR_NAME}}VoiceAgentV2:
    """Ultra-fast voice agent with streaming at every layer."""

    def __init__(self):
        self.ollama_url = os.getenv("OLLAMA_URL", "http://localhost:11434")
        self.model = os.getenv("OLLAMA_MODEL", "mistral-fast")
        self.kokoro_url = os.getenv("KOKORO_URL", "http://localhost:8880/v1/audio/speech")
        self.kokoro_voice = os.getenv("KOKORO_VOICE", "am_onyx")
        self.kokoro_model = os.getenv("KOKORO_MODEL", "kokoro")
        self.kokoro_speed = 1.2
        self.conversation_history = []
        self.is_speaking = False
        self.interrupt_flag = False
        self.ollama_available = False
        self.max_history_messages = 8  # Further reduced for speed

    async def initialize(self):
        """Initialize the voice agent."""
        # Test Ollama connection
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.ollama_url}/api/tags", timeout=5.0)
                if response.status_code == 200:
                    models = response.json().get("models", [])
                    model_names = [m.get("name", "").split(":")[0] for m in models]
                    if self.model in model_names or f"{self.model}:latest" in [m.get("name") for m in models]:
                        logger.info(f"Ollama connected - using {self.model} (optimized)")
                        self.ollama_available = True
                    else:
                        logger.warning(f"Model {self.model} not found. Available: {model_names}")
                else:
                    logger.warning(f"Ollama health check returned: {response.status_code}")
        except Exception as e:
            logger.warning(f"Ollama not reachable: {e}")

        # Test Kokoro
        kokoro_base = self.kokoro_url.rsplit("/v1", 1)[0] if "/v1" in self.kokoro_url else self.kokoro_url.rsplit("/", 1)[0]
        kokoro_health_url = f"{kokoro_base}/health"
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(kokoro_health_url, timeout=5.0)
                if response.status_code == 200:
                    logger.info(f"Kokoro TTS connected (voice: {self.kokoro_voice}, speed: {self.kokoro_speed}x)")
        except Exception as e:
            logger.warning(f"Kokoro not reachable: {e}")

    async def process(self, text: str) -> AsyncGenerator[dict, None]:
        """
        Process user input with ULTRA-FAST streaming.
        Streams: LLM tokens → sentences → TTS → audio chunks
        """
        self.interrupt_flag = False
        self.is_speaking = True

        try:
            # Check dispatch need
            needs_dispatch = self._should_dispatch(text)

            if needs_dispatch:
                # Quick acknowledgment
                ack_text = self._get_acknowledgment(text)
                async for event in self._stream_response_with_tts(ack_text):
                    yield event
                yield {"type": "dispatch", "task": text}
            else:
                # Stream LLM → TTS in parallel
                async for event in self._stream_llm_with_tts(text):
                    if self.interrupt_flag:
                        break
                    yield event

            yield {"type": "done"}

        finally:
            self.is_speaking = False

    async def _stream_llm_with_tts(self, text: str) -> AsyncGenerator[dict, None]:
        """
        Stream LLM response and generate TTS per sentence in parallel.
        This is the KEY optimization for perceived latency.
        """
        if not self.ollama_available:
            async for event in self._stream_response_with_tts(f"I heard: {text}. Ollama unavailable."):
                yield event
            return

        # Add to history
        self.conversation_history.append({"role": "user", "content": text})
        if len(self.conversation_history) > self.max_history_messages:
            self.conversation_history = self.conversation_history[-self.max_history_messages:]

        sentence_buffer = ""
        full_response = ""

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                async with client.stream(
                    "POST",
                    f"{self.ollama_url}/api/chat",
                    json={
                        "model": self.model,
                        "messages": [
                            {"role": "system", "content": {{ORCHESTRATOR_NAME_UPPER}}_SYSTEM_PROMPT},
                            *self.conversation_history
                        ],
                        "stream": True,
                        "options": {
                            "num_predict": 150,
                            "temperature": 0.7,
                            "num_ctx": 4096,
                            "top_p": 0.9,
                            "top_k": 40,
                        }
                    }
                ) as response:
                    if response.status_code != 200:
                        logger.error(f"Ollama error: {response.status_code}")
                        return

                    import json
                    async for line in response.aiter_lines():
                        if not line.strip():
                            continue

                        try:
                            chunk = json.loads(line)
                            if "message" in chunk:
                                content = chunk["message"].get("content", "")
                                sentence_buffer += content
                                full_response += content

                                # Emit text token immediately
                                yield {"type": "text_token", "content": content}

                                # Check for sentence boundary
                                if self._is_sentence_complete(sentence_buffer):
                                    sentence = sentence_buffer.strip()
                                    sentence_buffer = ""

                                    # Generate TTS for this sentence immediately
                                    async for audio_event in self._generate_tts_stream(sentence):
                                        yield audio_event

                            if chunk.get("done", False):
                                break

                        except json.JSONDecodeError:
                            continue

                    # Handle any remaining text
                    if sentence_buffer.strip():
                        async for audio_event in self._generate_tts_stream(sentence_buffer.strip()):
                            yield audio_event

            # Save to history
            self.conversation_history.append({"role": "assistant", "content": full_response})

        except Exception as e:
            logger.error(f"Streaming LLM error: {e}")

    def _is_sentence_complete(self, text: str) -> bool:
        """Detect sentence boundaries for streaming TTS."""
        # Simple heuristic: ends with punctuation + space, or multiple punctuation
        return bool(re.search(r'[.!?]\s', text)) or bool(re.search(r'[.!?]{2,}', text))

    async def _generate_tts_stream(self, text: str) -> AsyncGenerator[dict, None]:
        """Generate TTS audio for a text segment."""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    self.kokoro_url,
                    json={
                        "model": self.kokoro_model,
                        "input": text,
                        "voice": self.kokoro_voice,
                        "speed": self.kokoro_speed,
                        "response_format": "wav"
                    }
                )

                if response.status_code == 200:
                    # Stream audio in chunks
                    chunk_size = 4096  # Smaller chunks for lower latency
                    audio_data = response.content
                    for i in range(0, len(audio_data), chunk_size):
                        if self.interrupt_flag:
                            break
                        chunk = audio_data[i:i + chunk_size]
                        yield {"type": "audio", "data": chunk}
                else:
                    logger.error(f"Kokoro TTS error: {response.status_code}")

        except Exception as e:
            logger.error(f"TTS generation failed: {e}")

    async def _stream_response_with_tts(self, text: str) -> AsyncGenerator[dict, None]:
        """Stream pre-composed text with TTS (for acknowledgments)."""
        yield {"type": "text", "content": text}
        async for event in self._generate_tts_stream(text):
            yield event

    def _should_dispatch(self, text: str) -> bool:
        """Determine if request needs Claude Code."""
        text_lower = text.lower()
        return any(keyword in text_lower for keyword in DISPATCH_KEYWORDS)

    def _get_acknowledgment(self, text: str) -> str:
        """Quick acknowledgment for dispatch tasks."""
        acks = [
            "On it.",
            "Got it. Handling that now.",
            "Understood. I'm on it.",
            "Right away.",
        ]
        return random.choice(acks)

    async def interrupt(self):
        """Handle interruption."""
        self.interrupt_flag = True
        logger.info("Voice agent interrupted")
