#!/usr/bin/env python3
"""
{{ORCHESTRATOR_NAME}} Gateway - Pipecat-based Conversational AI
True conversational AI with interruption handling, VAD, and real-time streaming.
"""

import asyncio
import os
import sys

from loguru import logger

from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.audio.vad.vad_analyzer import VADParams
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineParams, PipelineTask
from pipecat.frames.frames import EndFrame, LLMMessagesFrame
from pipecat.processors.aggregators.openai_llm_context import OpenAILLMContext
from pipecat.services.ollama.llm import OLLamaLLMService
from pipecat.services.openai.tts import OpenAITTSService
from pipecat.transports.websocket.server import (
    WebsocketServerParams,
    WebsocketServerTransport,
)
from pipecat.serializers.protobuf import ProtobufFrameSerializer

# {{ORCHESTRATOR_NAME}} system prompt
{{ORCHESTRATOR_NAME_UPPER}}_SYSTEM_PROMPT = """You are {{ORCHESTRATOR_NAME}}, {{USER_NAME}}'s personal AI assistant and chief of staff for the Catalyst system.

## Voice Interaction Guidelines
- Keep responses concise and conversational (1-3 sentences for quick questions)
- Speak naturally, as if having a real conversation
- Use "sir" occasionally but not excessively
- When tasks require Claude Code, say you'll handle it and dispatch

## Identity
- You are {{ORCHESTRATOR_NAME}} - intelligent, helpful, and proactive
- You assist with everything from scheduling to system management
- You have access to Claude Code for complex tasks

## Response Style
- Direct and efficient
- Warm but professional
- Brief acknowledgments for simple requests
- More detail only when specifically asked
"""


async def main():
    """Main entry point for {{ORCHESTRATOR_NAME}} Gateway with Pipecat."""

    # Configuration from environment
    ollama_base_url = os.getenv("OLLAMA_URL", "http://localhost:11434/v1")
    ollama_model = os.getenv("OLLAMA_MODEL", "mistral-fast")  # Use optimized model
    kokoro_base_url = os.getenv("KOKORO_URL", "http://localhost:8880/v1")
    kokoro_voice = os.getenv("KOKORO_VOICE", "am_onyx")
    gateway_host = os.getenv("GATEWAY_HOST", "0.0.0.0")
    gateway_port = int(os.getenv("GATEWAY_PORT", "18800"))

    logger.info("=" * 60)
    logger.info("{{ORCHESTRATOR_NAME_UPPER}} GATEWAY - Pipecat Conversational AI")
    logger.info("=" * 60)
    logger.info(f"Ollama: {ollama_base_url} (model: {ollama_model})")
    logger.info(f"Kokoro TTS: {kokoro_base_url} (voice: {kokoro_voice})")
    logger.info(f"WebSocket: ws://{gateway_host}:{gateway_port}")
    logger.info("=" * 60)

    # WebSocket transport with VAD for interruption detection
    transport = WebsocketServerTransport(
        host=gateway_host,
        port=gateway_port,
        params=WebsocketServerParams(
            audio_in_enabled=True,
            audio_out_enabled=True,
            add_wav_header=True,
            vad_enabled=True,
            vad_analyzer=SileroVADAnalyzer(
                params=VADParams(
                    stop_secs=0.3,  # 300ms silence to detect end of speech
                )
            ),
            vad_audio_passthrough=True,
            serializer=ProtobufFrameSerializer(),
        ),
    )

    # Ollama LLM (local Mistral)
    llm = OLLamaLLMService(
        model=ollama_model,
        base_url=ollama_base_url,
    )

    # Kokoro TTS via OpenAI-compatible API
    tts = OpenAITTSService(
        api_key="kokoro",  # Kokoro doesn't need a real key
        base_url=kokoro_base_url,
        voice=kokoro_voice,
        model="kokoro",
    )

    # Conversation context
    messages = [
        {
            "role": "system",
            "content": {{ORCHESTRATOR_NAME_UPPER}}_SYSTEM_PROMPT,
        },
    ]

    context = OpenAILLMContext(messages)
    context_aggregator = llm.create_context_aggregator(context)

    # Build the pipeline
    pipeline = Pipeline(
        [
            transport.input(),           # WebSocket input (audio from client)
            context_aggregator.user(),   # Aggregate user speech
            llm,                          # LLM processing
            tts,                          # Text-to-speech
            transport.output(),          # WebSocket output (audio to client)
            context_aggregator.assistant(),  # Store assistant response
        ]
    )

    task = PipelineTask(
        pipeline,
        params=PipelineParams(
            allow_interruptions=True,     # Enable barge-in
            enable_metrics=True,
            enable_usage_metrics=True,
        ),
    )

    @transport.event_handler("on_client_connected")
    async def on_client_connected(transport, client):
        logger.info(f"Client connected: {client.remote_address}")
        # Send initial greeting
        messages.append({
            "role": "user",
            "content": "Say a brief greeting to {{USER_NAME}}, letting him know you're ready."
        })
        await task.queue_frames([LLMMessagesFrame(messages)])

    @transport.event_handler("on_client_disconnected")
    async def on_client_disconnected(transport, client):
        logger.info(f"Client disconnected: {client.remote_address}")
        await task.queue_frames([EndFrame()])

    runner = PipelineRunner()

    logger.info("{{ORCHESTRATOR_NAME}} Gateway ready - waiting for connections...")
    await runner.run(task)


if __name__ == "__main__":
    asyncio.run(main())
