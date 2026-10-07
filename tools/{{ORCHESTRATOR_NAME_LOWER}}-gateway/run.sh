#!/bin/bash
# {{ORCHESTRATOR_NAME}} Gateway - Start Script

cd "$(dirname "$0")"

# Source project .env if exists
if [ -f "../../.env" ]; then
    set -a
    source "../../.env"
    set +a
fi

echo "=========================================="
echo "  {{ORCHESTRATOR_NAME_UPPER}} GATEWAY - Conversational AI"
echo "  Local LLM: Mistral 7B via Ollama"
echo "=========================================="

# Check for Ollama
echo "Checking Ollama..."
if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo "✅ Ollama is running on :11434"
    # Check if mistral model is available
    if ollama list 2>/dev/null | grep -q "mistral"; then
        echo "✅ Mistral model loaded"
    else
        echo "⚠️  Mistral model not found"
        echo "   Run: ollama pull mistral"
    fi
else
    echo "⚠️  Ollama not detected on :11434"
    echo "   Start it with: brew services start ollama"
fi

# Check for Kokoro
echo "Checking Kokoro TTS..."
if curl -s http://localhost:8880/health > /dev/null 2>&1; then
    echo "✅ Kokoro TTS is running on :8880"
else
    echo "⚠️  Kokoro TTS not detected on :8880"
    echo "   Start it with: voicemode service start kokoro"
fi

echo ""
echo "Starting {{ORCHESTRATOR_NAME}} Gateway on ws://0.0.0.0:18800..."
echo ""

# Activate venv and run
if [ -d ".venv" ]; then
    source .venv/bin/activate
fi

python3 gateway.py
