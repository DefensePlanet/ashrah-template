# Catalyst Voice Bridge

**Version:** 0.2.0 (Phase 2)
**Created:** February 1, 2026
**Updated:** February 1, 2026

## Overview

Conversational AI voice interface for Catalyst that provides true real-time voice conversations using:

- **LLM:** Mistral Large (streaming responses)
- **STT:** faster-whisper (local, CPU-based, privacy-first)
- **TTS:** Kokoro (local, port 8880, streaming playback)
- **VAD:** Silero VAD (accurate voice activity detection)

## Phase 2 Features

- **Streaming LLM responses** - See text as it generates, reducing perceived latency
- **Silero VAD** - Accurate voice activity detection replaces simple volume thresholds
- **Interruption support** - Barge-in capability (stop TTS when user speaks)
- **Conversation history** - Multi-turn conversations with context
- **Pipecat-style architecture** - Frame-based pipeline design for extensibility

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                  Catalyst Voice Bridge (Phase 2)                 │
│                                                                  │
│  ┌──────────┐  ┌───────────┐  ┌──────────┐  ┌───────────────┐  │
│  │   Mic    │─▶│ Silero    │─▶│ Whisper  │─▶│   Mistral     │  │
│  │  Input   │  │   VAD     │  │   STT    │  │   Streaming   │  │
│  └──────────┘  └───────────┘  └──────────┘  └───────┬───────┘  │
│                                                      │          │
│  ┌──────────┐  ┌───────────┐                        ▼          │
│  │ Speaker  │◀─│  Kokoro   │◀───────────────────────┘          │
│  │  Output  │  │   TTS     │                                    │
│  └──────────┘  └───────────┘                                    │
└─────────────────────────────────────────────────────────────────┘
```

## Quick Start

### Prerequisites

1. **Mistral API Key:**
   ```bash
   export MISTRAL_API_KEY='your-api-key'
   ```

2. **Kokoro TTS** must be running on port 8880:
   ```bash
   voicemode service status kokoro
   voicemode service start kokoro
   ```

3. **Microphone permissions** for iTerm/Terminal in System Settings

### Running

```bash
# Using the run script
cd {{CATALYST_ROOT}}/tools/voice-bridge
./run.sh

# Or manually with uv
uv run python voice_bridge.py

# Or activate venv and run
source .venv/bin/activate
python voice_bridge.py
```

## Configuration

The `VoiceBridgeConfig` dataclass in `voice_bridge.py` provides all configurable parameters:

### Audio Settings
| Parameter | Default | Description |
|-----------|---------|-------------|
| `sample_rate` | 16000 | Audio sample rate in Hz |
| `channels` | 1 | Audio channels (mono) |
| `chunk_size` | 512 | Samples per chunk (32ms at 16kHz) |

### VAD Settings (Silero)
| Parameter | Default | Description |
|-----------|---------|-------------|
| `vad_threshold` | 0.5 | Speech detection threshold (0-1) |
| `vad_min_silence_ms` | 300 | Silence to end utterance |
| `vad_speech_pad_ms` | 100 | Padding around speech |

### LLM Settings (Mistral)
| Parameter | Default | Description |
|-----------|---------|-------------|
| `mistral_model` | mistral-large-latest | Model to use |
| `mistral_max_tokens` | 1024 | Max response tokens |
| `mistral_temperature` | 0.7 | Creativity (0-1) |

### TTS Settings (Kokoro)
| Parameter | Default | Description |
|-----------|---------|-------------|
| `kokoro_url` | localhost:8880 | Kokoro API endpoint |
| `kokoro_voice` | af_sky | Voice to use |
| `tts_max_chars` | 500 | Max characters to speak |

## Components

### SileroVAD
Voice activity detection using the Silero VAD model. Provides:
- Real-time speech probability for each audio chunk
- Start/end speech event detection
- Better accuracy than volume thresholds

### MistralLLMService
Mistral AI integration with:
- Async streaming responses
- Conversation history management
- Both SDK and httpx fallback implementations

### KokoroTTSService
Text-to-speech with:
- Async audio generation
- Chunked playback for interruption support
- Integration with Kokoro OpenAI-compatible API

### AudioInputHandler
Audio capture with:
- Real-time VAD feedback
- Configurable speech/silence detection
- Async queue-based processing

### VoiceBridge
Main orchestrator implementing the pipeline:
```
Audio Input -> VAD -> STT -> LLM (streaming) -> TTS -> Audio Output
```

## Dependencies

Managed by `uv`:
- `silero-vad` - Voice activity detection
- `mistralai` - Mistral AI SDK
- `faster-whisper` - Local speech-to-text
- `torch` - PyTorch for Silero VAD
- `sounddevice` - Audio I/O
- `httpx` - Async HTTP client
- `pipecat-ai[silero,openai]` - Pipeline framework (for future extensions)

## Voice Commands

- Say **"exit"**, **"quit"**, **"goodbye"**, or **"bye"** to end the session
- Press **Ctrl+C** to force quit

## Known Issues

1. **VoiceMode Whisper** has Metal compatibility issues on macOS 26 - using faster-whisper instead
2. **No concurrent barge-in yet** - interruption stops TTS but doesn't immediately restart listening

## Roadmap

### Phase 3: iOS Client
- WebRTC transport via LiveKit
- iOS app connects to Mac server
- Same {{ORCHESTRATOR_NAME}} context from anywhere

### Phase 4: Full Pipecat Integration
- Complete pipeline architecture
- Multiple transport options
- Advanced turn management

## Related Documentation

- Implementation plan: `capsules/catalyst-mobile/docs/CONVERSATIONAL_AI_IMPLEMENTATION_PLAN.md`
- Voice AI research: `docs/voice-ai-integration-plan.md`
- VoiceMode (alternative): https://github.com/mbailey/voicemode
- Pipecat framework: https://github.com/pipecat-ai/pipecat
- Silero VAD: https://github.com/snakers4/silero-vad

## Session Notes

**2026-02-01 (Phase 2):**
- Upgraded to Mistral LLM with streaming responses
- Replaced volume thresholds with Silero VAD
- Added interruption/barge-in support
- Implemented conversation history
- Pipecat-style frame architecture

**2026-02-01 (Phase 1):**
- Initial PoC created
- VoiceMode tested but Whisper had Metal issues on macOS 26
- Built hybrid approach with faster-whisper + Claude CLI + Kokoro
- Basic flow working, needs threshold tuning for different mics
