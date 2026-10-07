#!/bin/bash
# Start {{ORCHESTRATOR_NAME}} Gateway natively (not in Docker)
# This avoids Docker networking latency issues with Ollama and Kokoro TTS

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Activate virtual environment
if [ -f .venv/bin/activate ]; then
    source .venv/bin/activate
else
    echo "Virtual environment not found. Creating..."
    python3 -m venv .venv
    source .venv/bin/activate
    pip install -r requirements.txt
fi

# Set environment variables
export OLLAMA_URL="${OLLAMA_URL:-http://localhost:11434}"
export OLLAMA_MODEL="${OLLAMA_MODEL:-mistral}"
export KOKORO_URL="${KOKORO_URL:-http://localhost:8880/v1/audio/speech}"
export KOKORO_VOICE="${KOKORO_VOICE:-am_onyx}"

echo "Starting {{ORCHESTRATOR_NAME}} Gateway (native mode)..."
echo "  Ollama: $OLLAMA_URL (model: $OLLAMA_MODEL)"
echo "  Kokoro: $KOKORO_URL (voice: $KOKORO_VOICE)"
echo ""

# Run gateway
python3 gateway.py
