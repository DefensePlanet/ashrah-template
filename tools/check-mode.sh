#!/bin/bash
# Check current Catalyst LLM mode

GATEWAY_STATE_FILE="$HOME/.claude/gateway-mode"

echo "🔍 Catalyst LLM Mode Status"
echo "=============================="
echo

# Check state file
if [ -f "$GATEWAY_STATE_FILE" ]; then
    MODE=$(cat "$GATEWAY_STATE_FILE")
    echo "📁 Configured Mode: $MODE"
else
    echo "📁 Configured Mode: subscription (default)"
    MODE="subscription"
fi

echo

# Check current session environment
if [ -n "$ANTHROPIC_BASE_URL" ]; then
    echo "🔗 Current Session: GATEWAY MODE"
    echo "   ANTHROPIC_BASE_URL=$ANTHROPIC_BASE_URL"
    echo "   ANTHROPIC_AUTH_TOKEN=sk-litellm-***"

    # Check proxy health
    if curl -s http://localhost:4000/health > /dev/null 2>&1; then
        echo "   ✅ LiteLLM proxy: Running"
    else
        echo "   ❌ LiteLLM proxy: Not running"
    fi
else
    echo "🏢 Current Session: SUBSCRIPTION MODE"
    echo "   Using Anthropic subscription credits"
fi

echo

# Show guidance
if [ "$MODE" = "gateway" ] && [ -z "$ANTHROPIC_BASE_URL" ]; then
    echo "⚠️  Gateway mode configured but not active in this session"
    echo "   Start new terminal to activate"
elif [ "$MODE" = "subscription" ] && [ -n "$ANTHROPIC_BASE_URL" ]; then
    echo "⚠️  Subscription mode configured but gateway still active"
    echo "   Start new terminal to activate"
else
    echo "✅ Configuration matches current session"
fi

echo
