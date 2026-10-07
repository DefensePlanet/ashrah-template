#!/bin/bash
# Test fal.ai provider configuration in Bifrost

echo "Testing fal.ai provider configuration..."
echo ""

# Test 1: Check if FAL_API_KEY is exported in Bifrost process
echo "Test 1: Checking FAL_API_KEY in Bifrost process environment..."
BIFROST_PID=$(pgrep -f "bifrost-http")
if [ -n "$BIFROST_PID" ]; then
    # Try to read environment (this may fail due to permissions, but worth trying)
    if strings /proc/$BIFROST_PID/environ 2>/dev/null | grep FAL_API_KEY; then
        echo "✅ FAL_API_KEY found in Bifrost process"
    else
        echo "⚠️  Cannot read process environment (may require sudo)"
    fi
else
    echo "❌ Bifrost process not found"
fi
echo ""

# Test 2: Direct API call to Bifrost with fal-ai model
echo "Test 2: Testing direct model request to fal-ai/flux/schnell..."
curl -s -X POST http://localhost:8083/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer test" \
  -d '{
    "model": "fal-ai/flux/schnell",
    "messages": [{"role": "user", "content": "Generate an image of a sunset"}],
    "max_tokens": 100
  }' | jq '.'
echo ""

# Test 3: Try fal-ai/sora-2/text-to-video
echo "Test 3: Testing fal-ai/sora-2/text-to-video model..."
curl -s -X POST http://localhost:8083/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer test" \
  -d '{
    "model": "fal-ai/sora-2/text-to-video",
    "messages": [{"role": "user", "content": "Generate a video of waves crashing"}],
    "max_tokens": 100
  }' | jq '.'
echo ""

echo "Testing complete."
