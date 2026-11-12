#!/bin/bash
# Performance testing script for Mistral optimization
# Compares baseline vs optimized model latency

set -e

echo "🧪 Mistral Speed Optimization Test"
echo "======================================"
echo ""

# Test queries
QUERIES=(
    "What time is it?"
    "Set a reminder for tomorrow"
    "How's the weather?"
    "Tell me a joke"
)

echo "Testing models:"
echo "1. mistral:latest (baseline)"
echo "2. mistral-fast (optimized)"
echo ""

# Function to test a model
test_model() {
    local model=$1
    local query=$2

    echo "Testing: $model"
    echo "Query: $query"

    # Run with timing and extract metrics
    result=$(time (ollama run "$model" "$query" --verbose 2>&1) 2>&1)

    # Extract timing info
    total_time=$(echo "$result" | grep "total duration" | awk '{print $3}')
    load_time=$(echo "$result" | grep "load duration" | awk '{print $3}')
    eval_rate=$(echo "$result" | grep "^eval rate" | awk '{print $3}')

    echo "  Total: $total_time"
    echo "  Load:  $load_time"
    echo "  Rate:  $eval_rate tokens/s"
    echo ""
}

# Check if models exist
if ! ollama list | grep -q "mistral:latest"; then
    echo "❌ mistral:latest not found. Please run: ollama pull mistral"
    exit 1
fi

if ! ollama list | grep -q "mistral-fast"; then
    echo "❌ mistral-fast not found. Creating now..."
    cd "$(dirname "$0")"
    ollama create mistral-fast -f Modelfile.mistral-fast
    echo "✅ mistral-fast created"
    echo ""
fi

# Run tests
for query in "${QUERIES[@]}"; do
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "Query: \"$query\""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

    test_model "mistral:latest" "$query"
    test_model "mistral-fast" "$query"

    echo ""
done

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Test complete"
echo ""
echo "Expected improvements with mistral-fast:"
echo "  • 30-50% faster total time"
echo "  • Lower load time (smaller context)"
echo "  • Higher token/s rate"
echo ""
echo "For streaming tests, see voice_agent_v2.py"
