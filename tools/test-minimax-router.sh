#!/bin/bash
# Test MiniMax routing through Claude Code Router

echo "=== Testing MiniMax Router Transformation ==="
echo ""

# Send Anthropic-format request to router
echo "Sending Anthropic-format request to router (port 3456)..."
RESPONSE=$(curl -s http://127.0.0.1:3456/v1/messages \
  -H "Content-Type: application/json" \
  -H "x-api-key: sk-test" \
  -H "anthropic-version: 2023-06-01" \
  -d '{
    "model": "claude-sonnet-4-5-20250929",
    "messages": [{"role": "user", "content": "Say hello"}],
    "max_tokens": 100
  }')

echo ""
echo "=== RAW RESPONSE ==="
echo "$RESPONSE" | jq -C '.' 2>&1 || echo "$RESPONSE"
echo ""

# Check if response is valid JSON
if echo "$RESPONSE" | jq empty 2>/dev/null; then
  echo "✅ Response is valid JSON"

  # Check for required Anthropic fields
  if echo "$RESPONSE" | jq -e '.type' >/dev/null 2>&1; then
    echo "✅ Has 'type' field"
  else
    echo "❌ Missing 'type' field"
  fi

  if echo "$RESPONSE" | jq -e '.content' >/dev/null 2>&1; then
    echo "✅ Has 'content' field"
  else
    echo "❌ Missing 'content' field"
  fi

  if echo "$RESPONSE" | jq -e '.role' >/dev/null 2>&1; then
    echo "✅ Has 'role' field"
  else
    echo "❌ Missing 'role' field"
  fi

  if echo "$RESPONSE" | jq -e '.model' >/dev/null 2>&1; then
    echo "✅ Has 'model' field"
  else
    echo "❌ Missing 'model' field"
  fi
else
  echo "❌ Response is NOT valid JSON"
  echo "First 500 chars:"
  echo "$RESPONSE" | head -c 500
fi
