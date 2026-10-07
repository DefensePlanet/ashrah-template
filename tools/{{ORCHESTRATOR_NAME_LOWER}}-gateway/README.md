# {{ORCHESTRATOR_NAME}} Gateway

Conversational AI gateway for the Catalyst system, enabling voice and text interaction with {{ORCHESTRATOR_NAME}} anywhere.

## Overview

{{ORCHESTRATOR_NAME}} Gateway provides real-time voice conversation with {{ORCHESTRATOR_NAME}} using:
- **Local LLM** (Mistral via Ollama) for fast responses
- **Kokoro TTS** for natural voice synthesis
- **Pipecat** for conversational AI pipeline orchestration
- **WebSocket** for real-time communication
- **Claude Code** integration for complex task dispatch

## Architecture

```
┌─────────────┐
│ iOS/Watch   │ ──┐
│   Client    │   │
└─────────────┘   │
                  │  WebSocket
┌─────────────┐   │  ws://localhost:18800
│   Mac       │   │
│  Terminal   │ ──┤
└─────────────┘   │
                  │
                  ▼
        ┌──────────────────┐
        │ {{ORCHESTRATOR_NAME}} Gateway   │
        │  (Pipecat)       │
        └──────────────────┘
                │
        ┌───────┴───────┐
        │               │
        ▼               ▼
   ┌─────────┐    ┌──────────┐
   │ Mistral │    │  Kokoro  │
   │(Ollama) │    │   TTS    │
   └─────────┘    └──────────┘
        │
        ▼
   ┌─────────────┐
   │ Claude Code │ (for dispatch)
   └─────────────┘
```

## Performance Optimizations

**Target: <500ms latency for conversational AI**

See [MISTRAL-OPTIMIZATION.md](./MISTRAL-OPTIMIZATION.md) for full details.

### Key Optimizations

1. **Custom `mistral-fast` model**
   - Reduced context window (4096 tokens)
   - Optimized sampling parameters
   - GPU acceleration enabled

2. **Streaming at every layer**
   - LLM token streaming (faster TTFT)
   - Sentence-level TTS generation
   - Audio chunk streaming

3. **Context management**
   - Limited history (8-10 messages)
   - Concise prompt engineering
   - Token budget tracking

4. **Model preloading**
   - 24h keepalive to prevent cold starts
   - `preload-mistral.sh` for initialization

### Performance Benchmarks

| Metric | Baseline (mistral) | Optimized (mistral-fast) | Improvement |
|--------|-------------------|-------------------------|-------------|
| Total latency | 9.7s | ~5s | 2x faster |
| TTFT | 2.8s | <500ms | 5x faster |
| Token rate | 20 tok/s | 25-30 tok/s | 25-50% faster |

## Quick Start

### Prerequisites

1. **Ollama** with Mistral model
```bash
brew install ollama
ollama pull mistral
```

2. **Kokoro TTS** (running on port 8880)
```bash
# See Kokoro setup instructions
```

3. **Python dependencies**
```bash
pip install -r requirements.txt
```

### Setup

1. **Create optimized model**
```bash
./setup.sh  # Creates mistral-fast model
```

2. **Preload model (optional, recommended)**
```bash
./preload-mistral.sh  # Keeps model in memory
```

3. **Start gateway**
```bash
python3 pipecat_gateway.py
```

Or for development:
```bash
./run.sh
```

## Usage

### Environment Variables

```bash
# Ollama configuration
export OLLAMA_URL="http://localhost:11434"
export OLLAMA_MODEL="mistral-fast"  # or "mistral"

# Kokoro TTS
export KOKORO_URL="http://localhost:8880/v1"
export KOKORO_VOICE="am_onyx"  # {{ORCHESTRATOR_NAME}} voice
export KOKORO_MODEL="kokoro"

# Gateway
export GATEWAY_HOST="0.0.0.0"
export GATEWAY_PORT="18800"
```

### Testing

```bash
# Test latency
./test-latency.sh

# Test conversation
python3 test_client.py  # (if available)

# Manual Ollama test
ollama run mistral-fast "Hello {{ORCHESTRATOR_NAME}}" --verbose
```

## Components

### `pipecat_gateway.py`
Main gateway using Pipecat for conversational AI pipeline.

**Features:**
- WebSocket server for client connections
- VAD (Voice Activity Detection) for interruption
- LLM → TTS pipeline orchestration
- Real-time audio streaming

### `voice_agent.py`
Original voice agent implementation.

**Features:**
- Direct Ollama integration
- Kokoro TTS generation
- Conversation history management
- Dispatch keyword detection

### `voice_agent_v2.py`
**Next-gen ultra-fast streaming implementation.**

**Enhancements:**
- Sentence-level TTS streaming
- Token-by-token LLM streaming
- Parallel processing pipeline
- <500ms TTFT target

### `Modelfile.mistral-fast`
Ollama Modelfile for speed-optimized Mistral variant.

**Optimizations:**
- Reduced context window (4096)
- Limited output tokens (150)
- GPU acceleration
- Optimized sampling

## Performance Tuning

### For Speed
```bash
export OLLAMA_MODEL="mistral-fast"
# Or even faster (lower quality):
ollama pull phi3:mini
export OLLAMA_MODEL="phi3:mini"
```

### For Quality
```bash
export OLLAMA_MODEL="mistral:latest"
# Larger context if needed:
ollama run mistral "..." --num_ctx 8192
```

### For Balance
```bash
# Current default: mistral-fast
# Good balance of speed + quality
```

## Troubleshooting

### Gateway won't start
```bash
# Check Ollama
ollama list
ollama ps

# Check Kokoro
curl http://localhost:8880/health

# Check port availability
lsof -i :18800
```

### Slow responses
```bash
# Verify GPU usage
ollama ps

# Preload model
./preload-mistral.sh

# Check system resources
top -o cpu
```

### Quality issues
```bash
# Increase output length
# Edit Modelfile.mistral-fast: num_predict 150 → 200

# Use standard model
export OLLAMA_MODEL="mistral"
```

## Integration

### iOS/Watch Clients
Connect via WebSocket to `ws://localhost:18800` (or Cloudflare Tunnel for remote access).

### Claude Code Dispatch
For complex tasks, gateway detects dispatch keywords and invokes Claude Code CLI:
```bash
claude-code --prompt "User request here"
```

### Voice Pipeline
```
User speech → STT (on-device) → Gateway → LLM → TTS → Audio stream
```

## Development

### File Structure
```
{{ORCHESTRATOR_NAME_LOWER}}-gateway/
├── pipecat_gateway.py      # Main Pipecat gateway
├── voice_agent.py           # Voice agent v1
├── voice_agent_v2.py        # Voice agent v2 (streaming)
├── {{ORCHESTRATOR_NAME_LOWER}}_identity.py       # Identity & prompts
├── Modelfile.mistral-fast   # Optimized model config
├── preload-mistral.sh       # Model preloader
├── test-latency.sh          # Performance tests
├── requirements.txt         # Python dependencies
├── README.md                # This file
└── MISTRAL-OPTIMIZATION.md  # Detailed optimization guide
```

### Testing Changes

1. **Test model changes:**
```bash
ollama create mistral-fast -f Modelfile.mistral-fast
./test-latency.sh
```

2. **Test gateway changes:**
```bash
python3 pipecat_gateway.py
# Connect with test client
```

3. **Benchmark performance:**
```bash
time ollama run mistral-fast "test query" --verbose
```

## Roadmap

- [ ] **v2 Integration** - Switch to `voice_agent_v2.py` with sentence streaming
- [ ] **Response Caching** - Cache common queries for instant responses
- [ ] **Model Quantization** - Test Q4 quantized models for speed
- [ ] **Hybrid Routing** - Fast model for simple, powerful for complex
- [ ] **Metrics Dashboard** - Real-time latency/quality monitoring

## Related Documentation

- [MISTRAL-OPTIMIZATION.md](./MISTRAL-OPTIMIZATION.md) - Detailed optimization guide
- [Pipecat Docs](https://docs.pipecat.ai/) - Pipeline framework
- [Ollama Docs](https://ollama.ai/) - Local LLM runtime
- [Kokoro TTS](https://github.com/thewh1teagle/kokoro-onnx) - TTS engine

---

**Last Updated:** 2026-02-01
**Status:** Production-ready, actively optimized
