# Visual Media Generator - Complete Routing Architecture

**Date**: 2025-11-03
**Mode**: Claude Code Infinity
**Purpose**: Document how Visual Media Generator routes through Claude Code Router → Bifrost → Providers

---

## Architecture Overview

```
User Request
    ↓
{{ORCHESTRATOR_NAME}} (Orchestrator)
    ↓
🎬 Visual Media Generator Agent
    ↓
┌─────────────────────────────────────────────────────────────┐
│              Claude Code Infinity Stack                     │
│                                                              │
│  Claude Code CLI                                            │
│    ↓                                                         │
│  Claude Code Router (:3456)                                 │
│    ├─ Routing Strategy: "media"                            │
│    ├─ Rule: "bifrost-chat,openai/gpt-4o"                   │
│    └─ Models: All Flux variants registered                 │
│       ↓                                                      │
│  Bifrost Gateway (:8083)                                    │
│    ├─ Provider: together-ai (Flux Schnell FREE)            │
│    ├─ Provider: replicate (Flux Dev/Pro)                   │
│    ├─ Provider: fal-ai (Flux Pro fast)                     │
│    ├─ Provider: openai (GPT-4o, DALL-E 3)                  │
│    └─ Provider: openrouter (Minimax)                       │
│       ↓                                                      │
│  External Providers                                         │
│    ├─ Together AI API                                       │
│    ├─ Replicate API                                         │
│    ├─ Fal.ai API                                            │
│    ├─ OpenAI API                                            │
│    └─ OpenRouter API                                        │
└─────────────────────────────────────────────────────────────┘
    ↓
Generated Image/Video
    ↓
Saved to: generated-media/
```

---

## Configuration Files

### 1. Agent Definition
**File**: `.claude/agents/visual-media-generator.md`

```yaml
---
model: sonnet                    # Legacy mode fallback
infinity_model: sora-2           # Infinity mode (not used for thinking)
description: AI-generated visual content specialist
---
```

**What it does**:
- Defines agent capabilities and prompt
- Legacy mode would use Sonnet
- Infinity mode uses routing from agent_model_map.json

---

### 2. Agent Model Map
**File**: `global/claude-config/agent_model_map.json`

```json
{
  "🎬 Visual Media Generator": {
    "infinity_model": "openai/gpt-4o",
    "routing_strategy": "media",
    "generation_models": {
      "image_recommended": "together/black-forest-labs/FLUX.1-schnell-Free",
      "image_balanced": "replicate/black-forest-labs/flux-dev",
      "image_premium": "fal/fal-ai/flux-pro",
      "image_photorealistic": "openai/dall-e-3"
    }
  }
}
```

**What it does**:
- Maps agent to "media" routing strategy
- Specifies GPT-4o for agent's thinking/reasoning
- Lists available generation models for reference

---

### 3. Claude Code Router Config
**File**: `tools/claude-router/config/builderos.json`

```json
{
  "Providers": [
    {
      "name": "bifrost-chat",
      "api_base_url": "http://127.0.0.1:8083/v1/chat/completions",
      "models": [
        "openai/gpt-4o",
        "together/black-forest-labs/FLUX.1-schnell-Free",
        "replicate/black-forest-labs/flux-dev",
        "fal/fal-ai/flux-pro"
      ]
    }
  ],
  "Router": {
    "media": "bifrost-chat,openai/gpt-4o"
  }
}
```

**What it does**:
- Defines "bifrost-chat" provider (proxies to Bifrost)
- Registers all Flux models with the router
- Maps "media" strategy → bifrost-chat with GPT-4o

---

### 4. Bifrost Gateway Config
**File**: `tools/bifrost-data/config.json`

```json
{
  "providers": {
    "openai": {
      "keys": [{"value": "env.OPENAI_API_KEY"}],
      "models": ["gpt-4o", "gpt-4o-mini", "dall-e-3"]
    },
    "together": {
      "keys": [{"value": "env.TOGETHER_API_KEY"}],
      "models": ["black-forest-labs/FLUX.1-schnell-Free"],
      "network_config": {
        "base_url": "https://api.together.xyz/v1",
        "default_request_timeout_in_seconds": 180
      }
    },
    "replicate": {
      "keys": [{"value": "env.REPLICATE_API_KEY"}],
      "models": ["black-forest-labs/flux-dev"],
      "network_config": {
        "base_url": "https://api.replicate.com/v1",
        "default_request_timeout_in_seconds": 300
      }
    },
    "fal": {
      "keys": [{"value": "env.FAL_API_KEY"}],
      "models": ["fal-ai/flux-pro"],
      "network_config": {
        "base_url": "https://fal.run/v1",
        "default_request_timeout_in_seconds": 180
      }
    }
  }
}
```

**What it does**:
- Connects to external provider APIs
- Manages API keys and authentication
- Handles request/response transformation
- Sets timeouts for slow generation requests

---

### 5. Media Generation API Reference
**File**: `tools/bifrost-data/media-generation-apis.json`

```json
{
  "image_generation": {
    "flux_schnell": {
      "provider": "multiple",
      "routing": "bifrost",
      "bifrost_providers": ["together", "replicate", "fal"],
      "usage_via_bifrost": {
        "model_string": "black-forest-labs/FLUX.1-schnell-Free",
        "provider_prefix": "together/",
        "example": "together/black-forest-labs/FLUX.1-schnell-Free"
      }
    }
  }
}
```

**What it does**:
- Documentation for all generation models
- API endpoints, costs, capabilities
- Routing instructions (bifrost vs direct)

---

## Request Flow Example

### Example 1: User Requests Image via Flux Schnell

**User**: "Generate a hero image using Flux Schnell"

**Step 1 - {{ORCHESTRATOR_NAME}} Routes**:
```
{{ORCHESTRATOR_NAME}} detects "generate" + "image" keywords
→ Routes to: 🎬 Visual Media Generator
```

**Step 2 - Agent Loads**:
```
Agent definition loaded from: .claude/agents/visual-media-generator.md
Agent reads routing config: global/claude-config/agent_model_map.json
Agent sees: routing_strategy = "media"
Agent sees: infinity_model = "openai/gpt-4o"
```

**Step 3 - Claude Code Router Routes**:
```
Router receives request with strategy: "media"
Router looks up: Router["media"] = "bifrost-chat,openai/gpt-4o"
Router forwards to: http://127.0.0.1:8083/v1/chat/completions
Router adds model parameter: "openai/gpt-4o"
```

**Step 4 - Bifrost Routes**:
```
Bifrost receives: POST /v1/chat/completions
Bifrost sees model: "openai/gpt-4o"
Bifrost looks up provider: openai
Bifrost uses API key: $OPENAI_API_KEY
Bifrost forwards to: https://api.openai.com/v1/chat/completions
```

**Step 5 - Agent Thinks (GPT-4o)**:
```
GPT-4o receives prompt from agent
GPT-4o optimizes image generation prompt
GPT-4o returns: "A cinematic hero image with gradient background,
                modern UI elements, glass morphism effects..."
```

**Step 6 - Agent Generates Image**:
```
Agent decides: Use Flux Schnell (FREE, fast)
Agent makes second request to Bifrost:
  Model: "together/black-forest-labs/FLUX.1-schnell-Free"

Router receives model with provider prefix
Router forwards to Bifrost with model string
Bifrost sees: together/ prefix
Bifrost routes to: Together AI provider
Bifrost uses API key: $TOGETHER_API_KEY
Bifrost forwards to: https://api.together.xyz/v1/images/generations
```

**Step 7 - Together AI Generates**:
```
Together AI receives optimized prompt
Flux Schnell generates image (2-3 seconds)
Returns: Image URL or base64 data
```

**Step 8 - Agent Saves & Returns**:
```
Agent downloads image
Agent saves to: generated-media/image_20251103_183045_flux-schnell_a3f7.png
Agent returns to {{ORCHESTRATOR_NAME}}: File path + metadata
{{ORCHESTRATOR_NAME}} returns to user: "Image generated and saved!"
```

---

## Two-Tier Architecture

### Tier 1: Thinking Layer (via Bifrost)

**Purpose**: Agent uses LLM for reasoning and prompt optimization

**Route**:
```
Agent → Router (media strategy) → Bifrost → OpenAI GPT-4o
```

**Why through Bifrost**:
- Consistent routing with other agents
- Cost tracking and caching
- Observability and logging
- Provider failover support

---

### Tier 2: Generation Layer (via Bifrost OR Direct)

**Purpose**: Generate actual images/videos

**Route A - Via Bifrost** (Flux models):
```
Agent → Router → Bifrost → [Together AI | Replicate | Fal.ai]
```

**Route B - Direct API** (DALL-E 3, Imagen, SD3):
```
Agent → Direct HTTP call → Provider API
```

**Why some direct**:
- Different API structure (not OpenAI-compatible)
- Require special authentication (Google Cloud)
- Legacy integrations (Stability AI)
- Future: May migrate to Bifrost as support improves

---

## Environment Variables Required

### Thinking Layer (Required):
```bash
export OPENAI_API_KEY="sk-..."  # ✅ Already configured
```

### Generation Layer (Choose providers):
```bash
# FREE testing (recommended first)
export TOGETHER_API_KEY="..."   # Flux Schnell FREE

# Production quality
export REPLICATE_API_KEY="..."  # Flux Dev/Pro
export FAL_API_KEY="..."        # Flux Pro (fastest)

# Alternatives
export GOOGLE_API_KEY="..."     # Imagen 3 / nano banana
export STABILITY_API_KEY="..."  # Stable Diffusion 3
```

---

## Testing the Complete Stack

### 1. Verify Each Layer

**Check Router**:
```bash
curl http://localhost:3456/health
```

**Check Bifrost**:
```bash
curl http://localhost:8083/health
```

**Check Providers**:
```bash
# OpenAI
curl https://api.openai.com/v1/models \
  -H "Authorization: Bearer $OPENAI_API_KEY"

# Together AI
curl https://api.together.xyz/v1/models \
  -H "Authorization: Bearer $TOGETHER_API_KEY"
```

---

### 2. Test Complete Flow

**In Claude Code**:
```
You: "Generate a test image using Flux Schnell"

Expected flow:
1. {{ORCHESTRATOR_NAME}} → Visual Media Generator
2. Router (media) → Bifrost → GPT-4o (thinking)
3. Agent decides model selection
4. Router → Bifrost → Together AI (generation)
5. Image saved to generated-media/
6. Success message returned
```

---

### 3. Monitor Requests

**Watch Router Logs**:
```bash
tail -f ~/.claude-code-router/logs/router.log
```

**Watch Bifrost Logs**:
```bash
tail -f tools/bifrost-data/logs/bifrost.log
```

**Check Bifrost Dashboard**:
```
http://localhost:8083
```

---

## Troubleshooting

### Router not finding model

**Problem**: "Model not found: together/flux-schnell"

**Solution**:
```bash
# Verify model is in router config
cat tools/claude-router/config/builderos.json | grep "flux"

# Restart router
cd tools/claude-router
ccr stop
ccr start
```

---

### Bifrost not routing to provider

**Problem**: "Provider not configured: together"

**Solution**:
```bash
# Verify provider in Bifrost config
cat tools/bifrost-data/config.json | grep "together"

# Check API key is set
echo $TOGETHER_API_KEY

# Restart Bifrost
./tools/start-infinity-gateway.sh
```

---

### Agent not using correct model

**Problem**: Agent uses wrong model or provider

**Solution**:
```bash
# Check agent model map
cat global/claude-config/agent_model_map.json | grep "Visual Media"

# Verify routing strategy exists in router
cat tools/claude-router/config/builderos.json | grep "media"
```

---

## Complete Configuration Checklist

- [x] Agent definition created: `.claude/agents/visual-media-generator.md`
- [x] Agent routing configured: `agent_model_map.json`
- [x] Router knows about media strategy: `builderos.json`
- [x] Router knows about Flux models: `builderos.json` providers list
- [x] Bifrost has providers configured: `config.json`
- [x] API keys set in environment
- [ ] Together AI API key configured (recommended first)
- [ ] Replicate API key configured (optional)
- [ ] Fal.ai API key configured (optional)
- [x] Router running on port 3456
- [x] Bifrost running on port 8083

---

## Summary

**Yes, Claude Code Router is the model router in Infinity mode!**

The complete flow:
1. **Agent** specifies `routing_strategy: "media"` in `agent_model_map.json`
2. **Router** maps `"media"` → `"bifrost-chat,openai/gpt-4o"` in `builderos.json`
3. **Bifrost** routes to appropriate provider based on model prefix
4. **Provider** (Together AI, Replicate, etc.) generates the image
5. **Result** flows back through stack to agent → {{ORCHESTRATOR_NAME}} → user

The router is configured and ready to route Visual Media Generator requests!

---

*Complete routing architecture documented: 2025-11-03*
