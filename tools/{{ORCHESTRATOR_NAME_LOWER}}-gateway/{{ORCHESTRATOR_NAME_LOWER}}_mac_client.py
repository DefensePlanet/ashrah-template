#!/usr/bin/env python3
"""
{{ORCHESTRATOR_NAME}} Mac Client - Full Voice Conversational AI
Uses Pipecat with local microphone → Whisper STT → Ollama LLM → Kokoro TTS → Speaker
True conversational AI with interruption handling.
"""

import asyncio
import os

from loguru import logger

from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.audio.vad.vad_analyzer import VADParams
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineParams, PipelineTask
from pipecat.frames.frames import LLMMessagesFrame
from pipecat.processors.aggregators.llm_context import LLMContext
from pipecat.processors.aggregators.llm_response_universal import LLMContextAggregatorPair
from pipecat.services.ollama.llm import OLLamaLLMService
from pipecat.services.openai.tts import OpenAITTSService
from pipecat.services.whisper.stt import WhisperSTTService, Model as WhisperModel
from pipecat.transports.local.audio import LocalAudioTransport, LocalAudioTransportParams
from pipecat.transports.base_transport import TransportParams

# {{ORCHESTRATOR_NAME}} system prompt
{{ORCHESTRATOR_NAME_UPPER}}_SYSTEM_PROMPT = """You are {{ORCHESTRATOR_NAME}}, {{USER_NAME}}'s personal AI assistant and chief of staff for the Catalyst system.

## Voice Interaction Guidelines
- Keep responses concise and conversational (1-3 sentences for quick questions)
- Speak naturally, as if having a real conversation
- Use "sir" occasionally but not excessively
- When tasks require Claude Code, acknowledge and say you'll handle it

## Identity
- You are {{ORCHESTRATOR_NAME}} - intelligent, helpful, and proactive
- You assist with everything from scheduling to system management
- Your voice is confident and professional

## Response Style
- Direct and efficient
- Warm but professional
- Brief acknowledgments for simple requests
- More detail only when specifically asked
"""


async def main():
    """Main entry point for {{ORCHESTRATOR_NAME}} Mac Client."""

    # Configuration
    ollama_base_url = os.getenv("OLLAMA_URL", "http://localhost:11434/v1")
    ollama_model = os.getenv("OLLAMA_MODEL", "mistral")
    kokoro_base_url = os.getenv("KOKORO_URL", "http://localhost:8880/v1")
    kokoro_voice = os.getenv("KOKORO_VOICE", "onyx")

    print("=" * 60)
    print("  🎭 {{ORCHESTRATOR_NAME_UPPER}} - Conversational AI (Mac Client)")
    print("  Speak naturally. {{ORCHESTRATOR_NAME}} will respond.")
    print("  Press Ctrl+C to exit.")
    print("=" * 60)
    print(f"  LLM: Ollama ({ollama_model})")
    print(f"  TTS: Kokoro ({kokoro_voice})")
    print(f"  STT: Whisper (local)")
    print("=" * 60)

    # Local audio transport (microphone + speaker)
    transport = LocalAudioTransport(
        params=LocalAudioTransportParams(
            audio_in_enabled=True,
            audio_out_enabled=True,
            vad_analyzer=SileroVADAnalyzer(
                params=VADParams(
                    stop_secs=0.5,  # 500ms silence to detect end of speech
                )
            ),
        )
    )

    # Whisper STT (local)
    stt = WhisperSTTService(
        model=WhisperModel.BASE,  # Good balance of speed/accuracy
    )

    # Ollama LLM (local Mistral)
    llm = OLLamaLLMService(
        model=ollama_model,
        base_url=ollama_base_url,
    )

    # Kokoro TTS via OpenAI-compatible API
    tts = OpenAITTSService(
        api_key="kokoro",
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
        {
            "role": "assistant",
            "content": "Good evening, sir. {{ORCHESTRATOR_NAME}} at your service. How can I help you today?",
        },
    ]

    context = LLMContext(messages)
    user_aggregator, assistant_aggregator = LLMContextAggregatorPair(context)

    # Build the pipeline:
    # Microphone → VAD → STT → LLM Context → LLM → TTS → Speaker
    pipeline = Pipeline(
        [
            transport.input(),           # Microphone input
            stt,                          # Speech-to-text
            user_aggregator,             # Aggregate user speech
            llm,                          # LLM processing
            tts,                          # Text-to-speech
            transport.output(),          # Speaker output
            assistant_aggregator,        # Store assistant response
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

    # Play initial greeting
    print("\n🤖 {{ORCHESTRATOR_NAME}}: Good evening, sir. {{ORCHESTRATOR_NAME}} at your service.")
    print("🎤 Listening...\n")

    runner = PipelineRunner()

    try:
        await runner.run(task)
    except KeyboardInterrupt:
        print("\n\n👋 Goodbye, sir.")


if __name__ == "__main__":
    asyncio.run(main())
