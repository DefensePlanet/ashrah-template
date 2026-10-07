#!/bin/bash
# Test Semantic Caching in Bifrost
# Makes identical requests to verify cache hits

set -e

# Load environment
if [ -f {{CATALYST_ROOT}}/.env ]; then
    source {{CATALYST_ROOT}}/.env
fi

if [ -z "$OPENAI_API_KEY" ]; then
    echo "❌ OPENAI_API_KEY not set"
    exit 1
fi

echo "🧪 Testing Semantic Caching"
echo "============================"
echo ""

# Test query
QUERY='{"model":"gpt-4o-mini","messages":[{"role":"user","content":"What is semantic caching? Answer in 20 words."}],"max_tokens":50}'

# Request 1 (uncached)
echo "Request 1: First request (should be UNCACHED)"
echo "----------------------------------------------"
START1=$(date +%s%N)
RESPONSE1=$(curl -s http://localhost:8083/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ${OPENAI_API_KEY}" \
  -d "$QUERY")
END1=$(date +%s%N)
LATENCY1=$(( (END1 - START1) / 1000000 ))
echo "Response: $(echo "$RESPONSE1" | jq -r '.choices[0].message.content')"
echo "Latency: ${LATENCY1}ms"
echo ""

# Wait a moment for cache to be written
sleep 3

# Request 2 (should be cached)
echo "Request 2: Identical request (should be CACHED)"
echo "------------------------------------------------"
START2=$(date +%s%N)
RESPONSE2=$(curl -s http://localhost:8083/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ${OPENAI_API_KEY}" \
  -d "$QUERY")
END2=$(date +%s%N)
LATENCY2=$(( (END2 - START2) / 1000000 ))
echo "Response: $(echo "$RESPONSE2" | jq -r '.choices[0].message.content')"
echo "Latency: ${LATENCY2}ms"
echo ""

# Check Weaviate for cached entries
CACHE_COUNT=$(curl -s "http://127.0.0.1:8082/v1/objects?class=BifrostSemanticCachePlugin&limit=10" | jq '.objects | length')
echo "============================"
echo "Cache Statistics"
echo "============================"
echo "Cached entries in Weaviate: $CACHE_COUNT"
echo ""

# Performance comparison
if [ "$LATENCY2" -lt "$LATENCY1" ]; then
    SPEEDUP=$(( (LATENCY1 - LATENCY2) * 100 / LATENCY1 ))
    echo "✅ Cache HIT detected! ${SPEEDUP}% faster (${LATENCY1}ms → ${LATENCY2}ms)"
else
    echo "⚠️  No speedup detected - cache may not be working"
    echo "   Request 1: ${LATENCY1}ms"
    echo "   Request 2: ${LATENCY2}ms"
fi
echo ""

# Show sample cached entry
if [ "$CACHE_COUNT" -gt 0 ]; then
    echo "Sample cached entry:"
    curl -s "http://127.0.0.1:8082/v1/objects?class=BifrostSemanticCachePlugin&limit=1" \
      | jq '.objects[0].properties | {model, provider, expires_at}'
fi
