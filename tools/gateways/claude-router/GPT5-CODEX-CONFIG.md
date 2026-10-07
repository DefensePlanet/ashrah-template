# GPT-5 Codex Configuration for Claude Code Router

## WORKING CONFIGURATION (Verified 2025-11-11)

### Provider Configuration

```json
{
  "name": "bifrost-responses",
  "api_base_url": "http://127.0.0.1:8083/v1/responses",
  "api_key": "$OPENAI_API_KEY",
  "models": [
    "openai/gpt-5-codex"
  ],
  "transformer": {
    "use": ["openai-responses"]
  }
}
```

### Router Configuration

```json
"Router": {
  "default": "bifrost-responses,openai/gpt-5-codex",
  "think": "bifrost-responses,openai/gpt-5-codex"
}
```

## Key Requirements

1. **Endpoint**: MUST use `/v1/responses` (NOT `/v1/chat/completions`)
2. **Transformer**: MUST use `"openai-responses"` (built-in transformer)
3. **Route through Bifrost**: Port 8083 at `http://127.0.0.1:8083/v1/responses`
4. **Model prefix**: Use `openai/gpt-5-codex` (with provider prefix)

## API Format Differences

### Request Format
- Responses API uses `input` (NOT `messages`)
- Max tokens: `max_output_tokens` (NOT `max_tokens` or `max_completion_tokens`)
- Minimum max_output_tokens: 16

### Response Format
OpenAI Responses API returns:
```json
{
  "output": [
    {"type": "reasoning", "summary": []},
    {
      "type": "message",
      "content": [{"type": "output_text", "text": "response here"}],
      "role": "assistant"
    }
  ]
}
```

## Verified Working Test

```bash
curl -s http://localhost:3456/v1/messages \
  -H "Content-Type: application/json" \
  -H "x-api-key: test" \
  -d '{
    "model":"openai/gpt-5-codex",
    "messages":[{"role":"user","content":"Say hello"}],
    "max_tokens":50
  }'
```

**Result**: Model responds successfully with reasoning + output

## Current Status

✅ **Model Connection**: Working
✅ **Request Transformation**: Working (messages → input)
⚠️ **Response Transformation**: Needs fix - `convertOpenAIResponseToAnthropic` doesn't handle responses format

The `openai-responses` built-in transformer handles request transformation but needs response conversion logic for the new responses format.

## Files

- **Config**: `{{CATALYST_ROOT}}/tools/claude-router/config/builderos.json`
- **Active Config**: `{{HOME_DIR}}/.claude-code-router/config.json` (auto-copied from builderos.json on startup)
- **Bifrost Config**: `{{CATALYST_ROOT}}/tools/claude-router/config/infinity-bifrost.json` (reference implementation)
