#!/bin/bash
# Test Claude CLI through Infinity Gateway
# This script simulates Claude CLI behavior to validate the stack

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CATALYST_ROOT="$(dirname "$SCRIPT_DIR")"

echo "🧪 Testing Claude CLI Integration with Infinity Gateway"
echo "=========================================================="
echo ""

# Check if gateway is running
if ! pgrep -f "bifrost-http" > /dev/null; then
    echo "❌ Bifrost not running. Start with: ./tools/start-infinity-gateway.sh"
    exit 1
fi

ROUTER_URL="http://127.0.0.1:3456"
if ! curl -s --max-time 3 "$ROUTER_URL/health" > /dev/null 2>&1; then
    echo "❌ Claude Code Router not responding. Start with: ./tools/start-infinity-gateway.sh"
    exit 1
fi

echo "✅ Gateway components running"
echo ""

# Test 1: Health Check
echo "Test 1: Health Check"
echo "--------------------"
HEALTH_TEST=$(curl -s --max-time 5 "$ROUTER_URL/v1/messages" \
  -H "Content-Type: application/json" \
  -H "anthropic-version: 2023-06-01" \
  -d '{"model":"claude-3-5-sonnet-20241022","max_tokens":10,"messages":[{"role":"user","content":"Hi"}]}' \
  | jq -r '.content[0].text // "ERROR"')

if [ "$HEALTH_TEST" != "ERROR" ]; then
    echo "✅ Basic completion: '$HEALTH_TEST'"
else
    echo "❌ Health check failed"
    exit 1
fi
echo ""

# Test 2: Tool Call
echo "Test 2: Tool Call Translation"
echo "------------------------------"
TOOL_TEST=$(curl -s --max-time 5 "$ROUTER_URL/v1/messages" \
  -H "Content-Type: application/json" \
  -H "anthropic-version: 2023-06-01" \
  -d '{
    "model":"claude-3-5-sonnet-20241022",
    "max_tokens":100,
    "messages":[{"role":"user","content":"Use calculator to add 2+2"}],
    "tools":[{
      "name":"calculator",
      "description":"Basic math",
      "input_schema":{
        "type":"object",
        "properties":{"op":{"type":"string"},"a":{"type":"number"},"b":{"type":"number"}},
        "required":["op","a","b"]
      }
    }]
  }' | jq -r '.stop_reason // "ERROR"')

if [ "$TOOL_TEST" = "tool_use" ]; then
    echo "✅ Tool call translation working (stop_reason: tool_use)"
else
    echo "❌ Tool call failed (got: $TOOL_TEST)"
    exit 1
fi
echo ""

# Test 3: Streaming
echo "Test 3: Streaming Response"
echo "--------------------------"
STREAM_TEST=$(curl -s --max-time 5 "$ROUTER_URL/v1/messages" \
  -H "Content-Type: application/json" \
  -H "anthropic-version: 2023-06-01" \
  -d '{"model":"claude-3-5-sonnet-20241022","max_tokens":5,"messages":[{"role":"user","content":"Hi"}],"stream":true}' \
  | head -5 | grep -c "event:" || echo "0")

if [ "$STREAM_TEST" -gt 0 ]; then
    echo "✅ Streaming events detected ($STREAM_TEST events)"
else
    echo "❌ Streaming failed"
    exit 1
fi
echo ""

# Test 4: Model Routing
echo "Test 4: Model Availability"
echo "--------------------------"
MODEL_COUNT=$(curl -s http://localhost:8083/v1/models | jq -r '.data | length')
if [ "$MODEL_COUNT" -gt 0 ]; then
    echo "✅ Bifrost serving $MODEL_COUNT models"
else
    echo "❌ No models available"
    exit 1
fi
echo ""

# Summary
echo "=========================================================="
echo "✅ All tests passed!"
echo ""
echo "Infinity Gateway is ready for Claude CLI:"
echo "  1. In a NEW terminal session, run:"
echo "     source ./tools/use-infinity.sh"
echo ""
echo "  2. Then start Claude CLI normally:"
echo "     claude"
echo ""
echo "  3. Verify routing by checking logs:"
echo "     tail -f logs/bifrost.log"
echo "     tail -f logs/anthropic-shim.log"
echo ""
echo "Current session will NOT be affected (env is isolated)."
echo ""
