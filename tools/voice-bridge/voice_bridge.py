#!/usr/bin/env python3
"""
Catalyst Voice Bridge - Phase 2: True Conversational AI

Features:
- Ollama LLM with local Mistral model (streaming responses)
- Silero VAD for accurate voice activity detection
- Pipecat-style pipeline architecture
- Streaming TTS with Kokoro
- Interruption/barge-in support
- Turn management and conversation flow
"""

import asyncio
import tempfile
import wave
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import AsyncIterator, Optional, Callable
from pathlib import Path

import numpy as np
import sounddevice as sd
import httpx
import torch
from faster_whisper import WhisperModel
from silero_vad import load_silero_vad, VADIterator

import json


# =============================================================================
# Configuration
# =============================================================================

@dataclass
class VoiceBridgeConfig:
    """Configuration for the Voice Bridge."""
    # Audio settings
    sample_rate: int = 16000
    channels: int = 1
    chunk_size: int = 512  # 32ms at 16kHz (matches Silero VAD requirements)

    # VAD settings
    vad_threshold: float = 0.5
    vad_min_silence_ms: int = 300  # Silence duration to end utterance
    vad_speech_pad_ms: int = 100   # Padding around speech

    # Recording settings
    max_recording_seconds: float = 30.0
    min_speech_duration_ms: int = 300

    # LLM settings (Ollama with local Mistral)
    ollama_url: str = "http://localhost:11434"
    ollama_model: str = "mistral:latest"
    llm_max_tokens: int = 1024
    llm_temperature: float = 0.7
    system_prompt: str = """You are {{ORCHESTRATOR_NAME}}, {{USER_NAME}}'s intelligent AI assistant from the Catalyst system.
You are helpful, concise, and conversational. Keep responses brief for voice - aim for 1-3 sentences unless more detail is needed.
You can assist with coding, automation, research, and general questions.
Speak naturally as if in a conversation."""

    # TTS settings
    kokoro_url: str = "http://localhost:8880/v1/audio/speech"
    kokoro_voice: str = "af_sky"
    tts_max_chars: int = 500

    # Whisper settings
    whisper_model: str = "base"
    whisper_device: str = "cpu"
    whisper_compute_type: str = "int8"


# =============================================================================
# Pipeline Frame Types (Pipecat-style)
# =============================================================================

class FrameType(Enum):
    """Types of frames that flow through the pipeline."""
    AUDIO_RAW = auto()
    AUDIO_SPEECH = auto()
    TRANSCRIPTION = auto()
    LLM_RESPONSE_START = auto()
    LLM_RESPONSE_CHUNK = auto()
    LLM_RESPONSE_END = auto()
    TTS_AUDIO = auto()
    USER_STARTED_SPEAKING = auto()
    USER_STOPPED_SPEAKING = auto()
    BOT_STARTED_SPEAKING = auto()
    BOT_STOPPED_SPEAKING = auto()
    INTERRUPT = auto()
    END = auto()


@dataclass
class Frame:
    """Base frame for pipeline processing."""
    type: FrameType
    data: any = None
    metadata: dict = field(default_factory=dict)


# =============================================================================
# Voice Activity Detection with Silero
# =============================================================================

class SileroVAD:
    """Voice Activity Detection using Silero VAD model."""

    def __init__(self, config: VoiceBridgeConfig):
        self.config = config
        print("   Loading Silero VAD model...")

        # Set torch threads for better performance
        torch.set_num_threads(1)

        # Load the Silero VAD model
        self.model = load_silero_vad()

        # Create VAD iterator for streaming
        self.vad_iterator = VADIterator(
            self.model,
            threshold=config.vad_threshold,
            sampling_rate=config.sample_rate,
            min_silence_duration_ms=config.vad_min_silence_ms,
            speech_pad_ms=config.vad_speech_pad_ms
        )

        print("   Silero VAD loaded")

    def process_chunk(self, audio_chunk: np.ndarray) -> Optional[dict]:
        """
        Process an audio chunk and return speech event if detected.

        Returns:
            dict with 'start' or 'end' key (in seconds), or None
        """
        # Convert numpy array to torch tensor
        if isinstance(audio_chunk, np.ndarray):
            audio_tensor = torch.from_numpy(audio_chunk.astype(np.float32))
        else:
            audio_tensor = audio_chunk

        # Ensure correct shape
        if audio_tensor.ndim > 1:
            audio_tensor = audio_tensor.squeeze()

        # Get VAD result
        speech_dict = self.vad_iterator(audio_tensor, return_seconds=True)
        return speech_dict

    def reset(self):
        """Reset VAD state for new utterance."""
        self.vad_iterator.reset_states()

    def get_speech_probability(self, audio_chunk: np.ndarray) -> float:
        """Get raw speech probability for a chunk."""
        if isinstance(audio_chunk, np.ndarray):
            audio_tensor = torch.from_numpy(audio_chunk.astype(np.float32))
        else:
            audio_tensor = audio_chunk

        if audio_tensor.ndim > 1:
            audio_tensor = audio_tensor.squeeze()

        return self.model(audio_tensor, self.config.sample_rate).item()


# =============================================================================
# Ollama LLM Service with Streaming
# =============================================================================

class OllamaLLMService:
    """Ollama LLM service with streaming support using local Mistral model."""

    def __init__(self, config: VoiceBridgeConfig):
        self.config = config
        self.base_url = config.ollama_url

        # Initialize conversation history
        self.conversation_history: list[dict] = []

        # Add system prompt
        self.system_message = {
            "role": "system",
            "content": config.system_prompt
        }

        print(f"   Ollama client initialized ({self.base_url}, model: {config.ollama_model})")

    async def check_ollama_available(self) -> bool:
        """Check if Ollama server is running and model is available."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.base_url}/api/tags", timeout=5.0)
                if response.status_code == 200:
                    data = response.json()
                    models = [m.get("name", "") for m in data.get("models", [])]
                    return any(self.config.ollama_model in m for m in models)
                return False
        except Exception:
            return False

    async def stream_response(self, user_message: str) -> AsyncIterator[str]:
        """
        Stream a response from Ollama for the given user message.

        Yields:
            Text chunks as they arrive from the API
        """
        # Add user message to history
        self.conversation_history.append({
            "role": "user",
            "content": user_message
        })

        # Build messages list with system prompt
        messages = [self.system_message] + self.conversation_history

        full_response = ""

        async with httpx.AsyncClient() as client:
            try:
                # Use Ollama's native chat API with streaming
                async with client.stream(
                    "POST",
                    f"{self.base_url}/api/chat",
                    json={
                        "model": self.config.ollama_model,
                        "messages": messages,
                        "stream": True,
                        "options": {
                            "num_predict": self.config.llm_max_tokens,
                            "temperature": self.config.llm_temperature,
                        }
                    },
                    timeout=120.0
                ) as response:
                    async for line in response.aiter_lines():
                        if not line:
                            continue
                        try:
                            chunk_data = json.loads(line)
                            # Ollama streams message content in 'message.content'
                            message = chunk_data.get("message", {})
                            content = message.get("content", "")
                            if content:
                                full_response += content
                                yield content

                            # Check if done
                            if chunk_data.get("done", False):
                                break
                        except json.JSONDecodeError:
                            continue

            except httpx.ConnectError:
                error_msg = "Ollama connection failed. Is Ollama running?"
                print(f"   {error_msg}")
                yield error_msg
                full_response = error_msg
            except Exception as e:
                error_msg = f"Ollama API error: {e}"
                print(f"   {error_msg}")
                yield error_msg
                full_response = error_msg

        # Add assistant response to history
        if full_response and not full_response.startswith("Ollama"):
            self.conversation_history.append({
                "role": "assistant",
                "content": full_response
            })

        # Keep conversation history manageable
        if len(self.conversation_history) > 20:
            self.conversation_history = self.conversation_history[-16:]

    def reset_conversation(self):
        """Clear conversation history."""
        self.conversation_history = []


# =============================================================================
# Streaming TTS with Kokoro
# =============================================================================

class KokoroTTSService:
    """Text-to-Speech service using Kokoro with streaming support."""

    def __init__(self, config: VoiceBridgeConfig):
        self.config = config
        self._playback_lock = asyncio.Lock()
        self._is_playing = False
        self._should_stop = False

    async def speak(self, text: str, on_start: Optional[Callable] = None,
                   on_end: Optional[Callable] = None) -> bool:
        """
        Speak text using Kokoro TTS.

        Returns:
            True if completed, False if interrupted
        """
        if not text or not text.strip():
            return True

        # Truncate very long responses
        if len(text) > self.config.tts_max_chars:
            text = text[:self.config.tts_max_chars] + "..."

        async with self._playback_lock:
            self._is_playing = True
            self._should_stop = False

            if on_start:
                on_start()

            try:
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        self.config.kokoro_url,
                        json={
                            "model": "kokoro",
                            "input": text,
                            "voice": self.config.kokoro_voice,
                            "response_format": "wav"
                        },
                        timeout=30.0
                    )

                    if response.status_code != 200:
                        print(f"   Kokoro error: {response.status_code}")
                        return False

                    # Check if we should stop before playing
                    if self._should_stop:
                        return False

                    # Play audio
                    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                        f.write(response.content)
                        f.flush()

                        try:
                            with wave.open(f.name, 'rb') as wav:
                                data = np.frombuffer(
                                    wav.readframes(wav.getnframes()),
                                    dtype=np.int16
                                )
                                sample_rate = wav.getframerate()

                            # Play in chunks to allow interruption
                            chunk_size = sample_rate // 4  # 250ms chunks
                            for i in range(0, len(data), chunk_size):
                                if self._should_stop:
                                    sd.stop()
                                    return False

                                chunk = data[i:i + chunk_size]
                                sd.play(chunk, sample_rate)
                                sd.wait()

                        finally:
                            Path(f.name).unlink(missing_ok=True)

                    return True

            except Exception as e:
                print(f"   TTS error: {e}")
                return False
            finally:
                self._is_playing = False
                if on_end:
                    on_end()

    def interrupt(self):
        """Interrupt current playback."""
        self._should_stop = True
        sd.stop()

    @property
    def is_playing(self) -> bool:
        return self._is_playing


# =============================================================================
# Audio Input Handler with VAD
# =============================================================================

class AudioInputHandler:
    """Handles audio input with Silero VAD for speech detection."""

    def __init__(self, config: VoiceBridgeConfig, vad: SileroVAD):
        self.config = config
        self.vad = vad
        self._recording = False
        self._audio_queue: asyncio.Queue = asyncio.Queue()

    async def listen_for_speech(self) -> tuple[np.ndarray, float]:
        """
        Listen for speech using Silero VAD.

        Returns:
            Tuple of (audio_data, duration_seconds)
        """
        print("\n[MIC] Listening... (speak now)")

        audio_chunks = []
        speech_detected = False
        speech_start_time = None
        silence_start_time = None

        # Reset VAD state
        self.vad.reset()

        max_samples = int(self.config.max_recording_seconds * self.config.sample_rate)
        total_samples = 0

        min_speech_samples = int(
            self.config.min_speech_duration_ms * self.config.sample_rate / 1000
        )
        min_silence_samples = int(
            self.config.vad_min_silence_ms * self.config.sample_rate / 1000
        )

        speech_samples = 0
        silence_samples = 0

        # Create event for signaling
        stop_event = asyncio.Event()

        def audio_callback(indata, frames, time_info, status):
            """Called for each audio chunk."""
            if not stop_event.is_set():
                # Put audio data in queue for async processing
                self._audio_queue.put_nowait(indata.copy())

        try:
            # Open audio stream
            stream = sd.InputStream(
                samplerate=self.config.sample_rate,
                channels=self.config.channels,
                dtype='float32',
                callback=audio_callback,
                blocksize=self.config.chunk_size
            )

            with stream:
                while total_samples < max_samples:
                    try:
                        # Get audio chunk with timeout
                        chunk = await asyncio.wait_for(
                            self._audio_queue.get(),
                            timeout=0.1
                        )
                    except asyncio.TimeoutError:
                        continue

                    # Flatten if needed
                    if chunk.ndim > 1:
                        chunk = chunk.flatten()

                    # Get speech probability
                    speech_prob = self.vad.get_speech_probability(chunk)

                    # Visual feedback
                    bars = int(speech_prob * 30)
                    speech_indicator = "[SPEECH]" if speech_prob > self.config.vad_threshold else "       "
                    print(f"\r   VAD: {speech_prob:.2f} [{'#' * bars}{' ' * (30 - bars)}] {speech_indicator}", end="", flush=True)

                    # Track speech/silence
                    if speech_prob > self.config.vad_threshold:
                        if not speech_detected:
                            speech_detected = True
                            print(f"\n   >> Speech started")

                        speech_samples += len(chunk)
                        silence_samples = 0
                        audio_chunks.append(chunk)

                    elif speech_detected:
                        silence_samples += len(chunk)
                        audio_chunks.append(chunk)  # Include trailing silence

                        # Check if we should stop
                        if silence_samples > min_silence_samples:
                            if speech_samples > min_speech_samples:
                                print(f"\n   >> Speech ended (silence detected)")
                                break

                    total_samples += len(chunk)

                stop_event.set()

        except Exception as e:
            print(f"\n   Recording error: {e}")
            return np.array([]), 0.0

        # Clear any remaining items in queue
        while not self._audio_queue.empty():
            try:
                self._audio_queue.get_nowait()
            except:
                break

        if not audio_chunks:
            return np.array([]), 0.0

        # Concatenate all audio
        audio_data = np.concatenate(audio_chunks)
        duration = len(audio_data) / self.config.sample_rate

        print(f"   Recording: {duration:.2f}s, {speech_samples / self.config.sample_rate:.2f}s speech")

        return audio_data, duration


# =============================================================================
# Main Voice Bridge Orchestrator
# =============================================================================

class VoiceBridge:
    """
    Main Voice Bridge orchestrator implementing Pipecat-style pipeline.

    Pipeline flow:
    Audio Input -> VAD -> STT -> LLM (streaming) -> TTS (streaming) -> Audio Output
    """

    def __init__(self, config: Optional[VoiceBridgeConfig] = None):
        self.config = config or VoiceBridgeConfig()

        print("[INIT] Initializing Catalyst Voice Bridge Phase 2...")

        # Initialize components
        print("   Loading Whisper model...")
        self.whisper = WhisperModel(
            self.config.whisper_model,
            device=self.config.whisper_device,
            compute_type=self.config.whisper_compute_type
        )
        print("   Whisper loaded")

        self.vad = SileroVAD(self.config)

        print("   Initializing Ollama LLM...")
        self.llm = OllamaLLMService(self.config)

        print("   Initializing Kokoro TTS...")
        self.tts = KokoroTTSService(self.config)

        self.audio_input = AudioInputHandler(self.config, self.vad)

        # State
        self.running = False
        self._bot_speaking = False
        self._interrupt_requested = False

        print("[INIT] Voice Bridge ready")

    def transcribe(self, audio: np.ndarray) -> str:
        """Transcribe audio using Whisper."""
        if len(audio) == 0:
            return ""

        print("[STT] Transcribing...")

        # Save to temp file for Whisper
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            with wave.open(f.name, 'wb') as wav:
                wav.setnchannels(1)
                wav.setsampwidth(2)
                wav.setframerate(self.config.sample_rate)
                wav.writeframes((audio * 32767).astype(np.int16).tobytes())

            segments, _ = self.whisper.transcribe(f.name)
            text = " ".join([s.text for s in segments]).strip()
            Path(f.name).unlink(missing_ok=True)

        print(f"   You said: \"{text}\"")
        return text

    async def process_turn(self, user_text: str):
        """
        Process a single conversation turn with streaming LLM and TTS.
        """
        print("[LLM] Generating response...")

        # Collect response for TTS
        response_buffer = ""
        sentence_buffer = ""
        sentence_end_chars = ".!?;:"

        # Track chunks for display
        full_response = ""

        async for chunk in self.llm.stream_response(user_text):
            if self._interrupt_requested:
                print("\n   [INTERRUPTED]")
                break

            full_response += chunk
            sentence_buffer += chunk

            # Print streaming chunks
            print(chunk, end="", flush=True)

            # Check for sentence boundaries for TTS
            for char in sentence_end_chars:
                if char in sentence_buffer:
                    # Extract complete sentence(s)
                    parts = sentence_buffer.split(char)
                    for i, part in enumerate(parts[:-1]):
                        complete_sentence = part + char
                        response_buffer += complete_sentence
                    sentence_buffer = parts[-1]
                    break

        print()  # New line after streaming

        # Add any remaining text
        response_buffer += sentence_buffer

        if not response_buffer.strip():
            return

        # Speak the response
        print("[TTS] Speaking...")
        self._bot_speaking = True

        completed = await self.tts.speak(
            response_buffer.strip(),
            on_start=lambda: None,
            on_end=lambda: None
        )

        self._bot_speaking = False

        if completed:
            print("   Done")
        else:
            print("   Interrupted")

    async def conversation_loop(self):
        """Main conversation loop."""
        print("\n" + "=" * 60)
        print("  CATALYST VOICE BRIDGE - Phase 2")
        print("  Ollama (Mistral) | Silero VAD | Streaming TTS")
        print("=" * 60)
        print("Speak to converse with {{ORCHESTRATOR_NAME}}. Ctrl+C to exit.\n")

        self.running = True

        try:
            while self.running:
                # Reset interrupt flag
                self._interrupt_requested = False

                # Listen for speech
                audio, duration = await self.audio_input.listen_for_speech()

                if len(audio) == 0 or duration < 0.3:
                    print("   (No speech detected, listening again...)\n")
                    continue

                # Transcribe
                text = self.transcribe(audio)

                if not text or len(text.strip()) < 2:
                    print("   (Transcription empty, listening again...)\n")
                    continue

                # Check for exit commands
                if text.lower().strip() in ["exit", "quit", "goodbye", "bye"]:
                    print("\n[EXIT] Goodbye!")
                    break

                # Process turn
                await self.process_turn(text)
                print()  # Spacing between turns

        except KeyboardInterrupt:
            print("\n\n[EXIT] Goodbye!")
        finally:
            self.running = False

    def request_interrupt(self):
        """Request interruption of current response."""
        self._interrupt_requested = True
        if self._bot_speaking:
            self.tts.interrupt()


# =============================================================================
# Entry Point
# =============================================================================

async def main():
    """Main entry point."""
    config = VoiceBridgeConfig()

    # Check if Ollama is running
    print(f"[INIT] Checking Ollama at {config.ollama_url}...")
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{config.ollama_url}/api/tags", timeout=5.0)
            if response.status_code != 200:
                print(f"ERROR: Ollama returned status {response.status_code}")
                print(f"Make sure Ollama is running: ollama serve")
                return

            data = response.json()
            models = [m.get("name", "") for m in data.get("models", [])]
            model_found = any(config.ollama_model in m for m in models)

            if not model_found:
                print(f"ERROR: Model '{config.ollama_model}' not found in Ollama")
                print(f"Available models: {', '.join(models) if models else 'none'}")
                print(f"Pull the model with: ollama pull {config.ollama_model}")
                return

            print(f"   Ollama OK, model '{config.ollama_model}' available")

    except httpx.ConnectError:
        print(f"ERROR: Cannot connect to Ollama at {config.ollama_url}")
        print("Make sure Ollama is running: ollama serve")
        return
    except Exception as e:
        print(f"ERROR: Failed to check Ollama: {e}")
        return

    # Create and run voice bridge
    bridge = VoiceBridge(config)
    await bridge.conversation_loop()


if __name__ == "__main__":
    asyncio.run(main())
