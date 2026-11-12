# GPT-5 Codex Routing Status - 2025-11-12

## Current Status: ✅ Routing Works, ⚠️ Response Conversion Fails

### What's Working

1. **✅ Config Templates Fixed**
   - `tools/claude-router/config/builderos.json` - Correct
   - `tools/claude-router/config/infinity-bifrost.json` - Correct
   - Removed `openai/gpt-5-codex` from `bifrost-chat` provider
   - Only `bifrost-responses` provider handles gpt-5-codex now

2. **✅ Router Configuration**
   - `Router.default` = `bifrost-responses,openai/gpt-5-codex`
   - `Router.think` = `bifrost-responses,openai/gpt-5-codex`
   - Router successfully loads and starts

3. **✅ Bifrost Leg Works**
   - Direct test: `curl http://127.0.0.1:8083/v1/responses` → SUCCESS
   - GPT-5 Codex responds correctly: "Hello there!"
   - Transformer `openai-responses-fixed` is properly configured

4. **✅ End-to-End Routing Works**
   - Request: Claude Code Router `/v1/messages` (model="default")
   - Routes to: `bifrost-responses` provider
   - Forwards to: Bifrost gateway → OpenAI Responses API
   - GPT-5 Codex responds: "Hello!"
   - Response metadata confirms: `model_requested: gpt-5-codex`, `provider: openai`

### What's Broken

**⚠️ Response Format Conversion**

The router receives a valid OpenAI Responses API response but fails to convert it back to Anthropic Messages API format.

**Error:**
```
Provider error: {...valid responses API payload...}
at bs.convertOpenAIResponseToAnthropic
```

**Root Cause:**
- The router's `@musistudio/llms` dependency has built-in OpenAI→Anthropic conversion logic
- This built-in logic expects OpenAI **Chat Completions** API format
- It doesn't understand OpenAI **Responses** API format (different structure)
- Our `openai-responses-fixed` transformer plugin should handle this, but the router's built-in logic runs first/instead

**Response Structure Difference:**
- Chat Completions: `{choices: [{message: {...}}]}`
- Responses API: `{output: [{type: "message", content: [...]}]}`

### Test Files Created

1. **Direct Bifrost Test** (works ✅)
   - `/tmp/test-bifrost-direct.sh`
   - Tests Bifrost `/v1/responses` endpoint directly
   - Result: GPT-5 Codex responds successfully

2. **Router Test** (routing works, conversion fails ⚠️)
   - `{{CATALYST_ROOT}}/tools/test-gpt5-codex-claude-code.sh`
   - Tests full router → Bifrost → OpenAI flow
   - Result: Routing successful, response conversion fails

### Next Steps

**Option A: Fix the Router's Built-in Transformer**
- Investigate `@musistudio/llms` source code
- Patch or extend the built-in `convertOpenAIResponseToAnthropic` method
- Make it handle Responses API format in addition to Chat Completions

**Option B: Ensure Plugin Transformer Takes Priority**
- Verify our `openai-responses-fixed` plugin is being invoked
- Check if there's a way to disable the router's built-in conversion
- Ensure plugin transformers run before built-in logic

**Option C: Use Streaming Mode**
- Test if streaming mode bypasses the failing conversion
- The transformer has SSE handling that might work differently
- Worth testing: `"stream": true` in the request

**Option D: Direct Integration (Bypass Router)**
- Configure Claude Code Infinity mode to hit Bifrost directly
- Skip the router layer entirely for GPT-5 Codex
- Simpler architecture, fewer failure points

### Recommendation

**Try Option C first** (streaming mode) - quickest test to see if different code path works.

If that fails, **pursue Option A** - investigate and patch the router's dependency to handle Responses API format.

Option D is the fallback if the router proves too difficult to fix.

## Architecture Confirmed

```
Claude Code (Infinity Mode)
  ↓ /v1/messages (Anthropic format)
Claude Code Router (port 3456)
  ↓ Applies routing rules (Router.default)
  ↓ Routes to: bifrost-responses,openai/gpt-5-codex
Bifrost Gateway (port 8083)
  ↓ /v1/responses (OpenAI format)
OpenAI API
  ↓ GPT-5 Codex responds
  ↓ ✅ Response successful
[⚠️ Conversion fails here]
Claude Code Router
  ↓ ❌ Cannot convert Responses API → Messages API
[Error returned to Claude Code]
```

## Files Modified

- `tools/claude-router/config/builderos.json` - Removed gpt-5-codex from bifrost-chat
- `tools/claude-router/config/infinity-bifrost.json` - Removed gpt-5-codex from bifrost-chat
- `~/.claude-code-router/config.json` - Live config updated
- Router service restarted

## Verification Commands

```bash
# Test Bifrost directly (works)
bash /tmp/test-bifrost-direct.sh

# Test through router (routing works, conversion fails)
bash {{CATALYST_ROOT}}/tools/test-gpt5-codex-claude-code.sh

# Check router status
cd {{CATALYST_ROOT}}/tools/claude-router
node dist/cli.js status
```
