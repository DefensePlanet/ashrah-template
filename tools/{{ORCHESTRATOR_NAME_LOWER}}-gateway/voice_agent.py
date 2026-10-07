#!/usr/bin/env python3
"""
{{ORCHESTRATOR_NAME}} Voice Agent - Fast LLM for conversational responses
Uses Mistral via Ollama (local) for <500ms latency + Kokoro TTS
"""

import asyncio
import os
import random
from typing import AsyncGenerator
from loguru import logger
import httpx

from {{ORCHESTRATOR_NAME_LOWER}}_identity import {{ORCHESTRATOR_NAME_UPPER}}_SYSTEM_PROMPT, DISPATCH_KEYWORDS


class {{ORCHESTRATOR_NAME}}VoiceAgent:
    """Voice agent using Mistral (Ollama) for fast local responses."""

    def __init__(self):
        self.ollama_url = os.getenv("OLLAMA_URL", "http://localhost:11434")
        self.model = os.getenv("OLLAMA_MODEL", "mistral-fast")  # Use optimized model by default
        self.kokoro_url = os.getenv("KOKORO_URL", "http://localhost:8880/v1/audio/speech")
        self.kokoro_voice = os.getenv("KOKORO_VOICE", "am_onyx")  # {{ORCHESTRATOR_NAME}} voice
        self.kokoro_model = os.getenv("KOKORO_MODEL", "kokoro")  # OpenAI-compatible endpoint model
        self.kokoro_speed = 1.2  # {{ORCHESTRATOR_NAME}} speech speed
        self.conversation_history = []
        self.is_speaking = False
        self.interrupt_flag = False
        self.ollama_available = False
        self.max_history_tokens = 2048  # Limit context to reduce latency

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
                        logger.info(f"Ollama connected - using {self.model} (local)")
                        self.ollama_available = True
                    else:
                        logger.warning(f"Model {self.model} not found. Available: {model_names}")
                else:
                    logger.warning(f"Ollama health check returned: {response.status_code}")
        except Exception as e:
            logger.warning(f"Ollama not reachable: {e}")

        # Test Kokoro connection
        # Derive health URL from kokoro_url (e.g., http://host:8880/v1/audio/speech -> http://host:8880/health)
        kokoro_base = self.kokoro_url.rsplit("/v1", 1)[0] if "/v1" in self.kokoro_url else self.kokoro_url.rsplit("/", 1)[0]
        kokoro_health_url = f"{kokoro_base}/health"
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(kokoro_health_url, timeout=5.0)
                if response.status_code == 200:
                    logger.info(f"Kokoro TTS connected (voice: {self.kokoro_voice}, speed: {self.kokoro_speed}x)")
                else:
                    logger.warning(f"Kokoro health check returned: {response.status_code}")
        except Exception as e:
            logger.warning(f"Kokoro not reachable: {e}")

    async def process(self, text: str) -> AsyncGenerator[dict, None]:
        """
        Process user input and generate response.
        Yields events: text, audio, dispatch, done
        """
        self.interrupt_flag = False
        self.is_speaking = True

        try:
            # Check if this needs Claude Code dispatch
            needs_dispatch = self._should_dispatch(text)

            if needs_dispatch:
                # Quick acknowledgment + dispatch
                ack_text = self._get_acknowledgment(text)
                async for event in self._generate_response(ack_text):
                    yield event

                # Signal dispatch to Claude Code
                yield {"type": "dispatch", "task": text}
            else:
                # Direct response from Mistral
                response_text = await self._get_llm_response(text)
                async for event in self._generate_response(response_text):
                    if self.interrupt_flag:
                        break
                    yield event

            yield {"type": "done"}

        finally:
            self.is_speaking = False

    async def speak(self, text: str) -> AsyncGenerator[dict, None]:
        """Generate speech for proactive messages."""
        async for event in self._generate_response(text):
            yield event

    async def interrupt(self):
        """Handle interruption from user."""
        self.interrupt_flag = True
        logger.info("Voice agent interrupted")

    def _should_dispatch(self, text: str) -> bool:
        """Determine if request needs Claude Code."""
        text_lower = text.lower()
        return any(keyword in text_lower for keyword in DISPATCH_KEYWORDS)

    def _get_acknowledgment(self, text: str) -> str:
        """Generate quick acknowledgment for dispatch tasks."""
        acks = [
            "On it. I'll start working on that now.",
            "Got it. Let me handle that for you.",
            "Understood. I'm on it.",
            "Right away. I'll take care of that.",
        ]
        return random.choice(acks)

    async def _get_llm_response(self, text: str) -> str:
        """Get response from Mistral via Ollama (local).

        Note: Using non-streaming mode because Docker networking causes streaming
        to buffer and delay first tokens significantly (30-60s). Non-streaming
        returns the full response faster for short voice responses.
        """
        if not self.ollama_available:
            # Mock response for testing
            return f"I heard you say: {text}. Ollama is not available."

        # Add to conversation history
        self.conversation_history.append({"role": "user", "content": text})

        # Keep history manageable - limit by message count
        if len(self.conversation_history) > 10:
            self.conversation_history = self.conversation_history[-10:]

        try:
            # Use longer timeout and non-streaming for Docker networking reliability
            # Streaming from Docker to host has buffering issues causing 30-60s delays
            timeout = httpx.Timeout(connect=10.0, read=90.0, write=10.0, pool=10.0)

            async with httpx.AsyncClient(timeout=timeout) as client:
                logger.info(f"Sending to Ollama ({self.model})...")
                response = await client.post(
                    f"{self.ollama_url}/api/chat",
                    json={
                        "model": self.model,
                        "messages": [
                            {"role": "system", "content": {{ORCHESTRATOR_NAME_UPPER}}_SYSTEM_PROMPT},
                            *self.conversation_history
                        ],
                        "stream": False,  # Non-streaming is faster from Docker
                        "options": {
                            "num_predict": 150,  # Keep responses concise for voice
                            "temperature": 0.7,
                            "num_ctx": 4096,  # Reduced context window
                            "top_p": 0.9,
                            "top_k": 40,
                        }
                    }
                )

                if response.status_code == 200:
                    data = response.json()
                    full_response = data.get("message", {}).get("content", "")
                    logger.info(f"Ollama responded: {full_response[:50]}...")
                    self.conversation_history.append({"role": "assistant", "content": full_response})
                    return full_response
                else:
                    logger.error(f"Ollama API error: HTTP {response.status_code}")
                    return "I apologize, I encountered an error processing that request."

        except httpx.TimeoutException as e:
            logger.error(f"Ollama timeout after 90s: {e}")
            return "I apologize, the request timed out. Please try again."
        except Exception as e:
            logger.error(f"Ollama API error: {type(e).__name__}: {e}")
            return "I apologize, I encountered an error processing that request."

    async def _generate_response(self, text: str) -> AsyncGenerator[dict, None]:
        """Generate text and audio response."""
        # Emit text
        yield {"type": "text", "content": text}

        # Generate TTS audio via Kokoro
        try:
            # Increased timeout for Docker networking delays
            timeout = httpx.Timeout(connect=10.0, read=60.0, write=10.0, pool=10.0)
            async with httpx.AsyncClient(timeout=timeout) as client:
                logger.info(f"Generating TTS for {len(text)} chars...")
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
                    chunk_size = 8192
                    audio_data = response.content
                    logger.info(f"TTS generated {len(audio_data)} bytes, sending {len(audio_data) // chunk_size + 1} chunks")
                    for i in range(0, len(audio_data), chunk_size):
                        if self.interrupt_flag:
                            break
                        chunk = audio_data[i:i + chunk_size]
                        yield {"type": "audio", "data": chunk}
                else:
                    logger.error(f"Kokoro TTS error: {response.status_code} - {response.text[:100]}")

        except httpx.TimeoutException as e:
            logger.error(f"TTS timeout after 60s: {e}")
        except Exception as e:
            logger.error(f"TTS generation failed: {type(e).__name__}: {e}")
