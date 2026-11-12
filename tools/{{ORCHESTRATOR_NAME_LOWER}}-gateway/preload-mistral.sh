#!/bin/bash
# Preload Mistral-Fast model to reduce cold-start latency
# This keeps the model in memory with a 24h keepalive

echo "🚀 Preloading mistral-fast model..."

# Send empty prompt to load model into memory
ollama run mistral-fast "" --keepalive 24h > /dev/null 2>&1 &

# Wait a moment for model to load
sleep 2

# Verify model is loaded
if ollama ps | grep -q "mistral-fast"; then
    echo "✅ mistral-fast loaded and ready (24h keepalive)"
    echo ""
    ollama ps
else
    echo "⚠️  Warning: Model may not be loaded. Check with: ollama ps"
fi
