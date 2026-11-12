# Visual Media Generator Setup

**Date**: 2025-11-03
**Status**: ✅ Agent configured and ready for testing
**Agent**: 🎬 Visual Media Generator

---

## Overview

The Visual Media Generator is a specialist agent that integrates AI-generated video and image capabilities into Claude Code Infinity. It enables on-demand creation of visual content for product demos, marketing materials, and concept visualization.

### Supported Models

| Model | Type | Status | Provider |
|-------|------|--------|----------|
| **DALL-E 3** | Image | ✅ Active | OpenAI |
| **Sora 2** | Video | ⏳ Awaiting beta access | OpenAI |
| **Veo 3** | Video | ❌ Requires Google Cloud | Google |
| **Stable Diffusion 3** | Image | ❌ Requires API key | Stability AI |

---

## Architecture

### Two-Tier Design

```
User Request → {{ORCHESTRATOR_NAME}} → 🎬 Visual Media Generator
                              ↓
                        ┌─────────────┬──────────────┐
                        │             │              │
                   THINKING LAYER  GENERATION LAYER  │
                        │             │              │
                   GPT-4o (Bifrost)  Direct API     │
                        │             │              │
                   Prompt Engineering  DALL-E 3      │
                   Parameter Tuning    Sora 2        │
                   Model Selection     Veo 3         │
                        │             │              │
                        └─────────────┴──────────────┘
                              ↓
                        Generated Media
                    (saved to generated-media/)
```

**Why two tiers?**
- **Thinking layer**: Agent uses GPT-4o (via Bifrost) for intelligent prompt optimization
- **Generation layer**: Direct API calls to specialized models (different API structure than chat)

### Key Files

| File | Purpose |
|------|---------|
| `.claude/agents/visual-media-generator.md` | Agent definition and capabilities |
| `global/claude-config/agent_model_map.json` | Model routing (thinking layer) |
| `tools/bifrost-data/media-generation-apis.json` | API configuration (generation layer) |
| `.claude-context/agent-name-routing.json` | Name resolution for Task tool |
| `CLAUDE.md` | Specialist routing map |

---

## Current Status

### ✅ Ready to Use

**DALL-E 3 (Image Generation):**
- Uses existing `OPENAI_API_KEY` ✅
- Fully documented API calls ✅
- Cost: $0.04-$0.12 per image
- Rate limit: 50 images/minute

### ⏳ Pending Access

**Sora 2 (Video Generation):**
- Requires OpenAI beta program enrollment
- API structure placeholder documented
- Estimated cost: $0.10-$0.50 per video
- Will use same `OPENAI_API_KEY` when available

### ❌ Requires Setup

**Veo 3 (Video Generation):**
- Needs Google Cloud project
- Requires `GOOGLE_API_KEY` environment variable
- Setup: https://ai.google.dev/gemini-api/docs/api-key

**Stable Diffusion 3 (Image Generation):**
- Needs Stability AI account
- Requires `STABILITY_API_KEY` environment variable
- Setup: https://platform.stability.ai/account/keys

---

## Usage in Claude Code

### 1. Invoke the Agent

```
User: Generate a product demo image for our new app
{{ORCHESTRATOR_NAME}}: *delegates to 🎬 Visual Media Generator*
```

**Routing is automatic** when you mention:
- "Generate a video..."
- "Create an image..."
- "Need visual content..."
- "Make a concept video..."

### 2. Alternative Names

The agent responds to:
- `Visual Media Generator` (full name)
- `Media Generator`
- `Video Generator`
- `Image Generator`

All resolve to **🎬 Visual Media Generator**

### 3. Example Workflow

```
User: I need a hero image for our landing page - modern SaaS dashboard

{{ORCHESTRATOR_NAME}}: *Routes to Visual Media Generator*

Agent:
1. Analyzes request (GPT-4o via Bifrost)
2. Optimizes prompt: "Modern SaaS dashboard interface, clean design,
   gradient purple-blue theme, glass morphism effects, 4K quality"
3. Selects DALL-E 3 (image, not video)
4. Makes direct API call to OpenAI
5. Saves: generated-media/image_20251103_143022_dalle3_a3f7.png
6. Returns: File path + URL

Result: Landing page hero image ready to use
```

---

## Testing

### Quick Test (DALL-E 3)

**Via Claude Code:**
```
Ask {{ORCHESTRATOR_NAME}}: "Have the Visual Media Generator create a test image"
```

**Direct API test:**
```bash
curl https://api.openai.com/v1/images/generations \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $OPENAI_API_KEY" \
  -d '{
    "model": "dall-e-3",
    "prompt": "A futuristic robot assistant in a modern office",
    "n": 1,
    "size": "1024x1024",
    "quality": "hd"
  }'
```

### Verify Configuration

```bash
# Check Bifrost health (thinking layer)
curl http://localhost:8083/health

# Check environment variables
echo $OPENAI_API_KEY  # Should be set
echo $GOOGLE_API_KEY  # Optional (Veo 3)
echo $STABILITY_API_KEY  # Optional (SD3)

# Verify agent exists
ls -la .claude/agents/visual-media-generator.md

# Check agent model map
cat global/claude-config/agent_model_map.json | grep "Visual Media"
```

---

## Cost Management

### Current Pricing (OpenAI)

**DALL-E 3:**
- Standard 1024x1024: $0.040/image
- Standard 1792x1024: $0.080/image
- HD 1024x1024: $0.080/image
- HD 1792x1024: $0.120/image

**Sora 2 (estimated when available):**
- ~$0.10-$0.50 per generation
- Varies by duration and resolution

### Budget Protection

The agent implements:
- ✅ User confirmation for high-cost operations (>$0.50)
- ✅ Cost logging to SQLite for tracking
- ✅ Daily spend limit recommendations
- ✅ Metadata caching to avoid duplicates

---

## Integration with n8n

### Current: Testing in Claude Code
- Interactive prompt refinement
- Immediate visual feedback
- Cost/quality experimentation

### Future: Production Workflows

**Migration path:**
1. Test and refine prompts in Claude Code
2. Document successful patterns
3. Export to n8n workflow templates
4. Automate bulk generation

**n8n Implementation Options:**

**Option A - Call agent:**
```javascript
// n8n HTTP Request node
POST https://builderos-api.local/agents/visual-media-generator
{
  "action": "generate_image",
  "prompt": "{{$json.prompt}}",
  "model": "dall-e-3"
}
```

**Option B - Direct API:**
```javascript
// n8n OpenAI node (bypasses agent for efficiency)
POST https://api.openai.com/v1/images/generations
{
  "model": "dall-e-3",
  "prompt": "{{$json.optimized_prompt}}"
}
```

---

## Troubleshooting

### Agent not found
```bash
# Verify agent file exists
ls -la .claude/agents/visual-media-generator.md

# Check agent is in routing map
grep "Visual Media" CLAUDE.md
```

### Bifrost connection failed
```bash
# Restart Infinity stack
./tools/start-infinity-gateway.sh

# Check Bifrost health
curl http://localhost:8083/health
```

### API key issues
```bash
# Verify environment variable
echo $OPENAI_API_KEY

# Test API directly
curl https://api.openai.com/v1/models \
  -H "Authorization: Bearer $OPENAI_API_KEY"
```

### Generation fails
- **Content policy violation**: Refine prompt, avoid restricted content
- **Rate limit**: Wait 60 seconds, retry
- **Timeout**: Reduce complexity, try lower resolution
- **Cost**: Confirm you want to proceed with generation

---

## Next Steps

### Immediate (Testing Phase)
1. ✅ Agent definition complete
2. ✅ Model routing configured
3. ⏳ **Test DALL-E 3 generation** (next step)
4. ⏳ Document successful prompt patterns
5. ⏳ Refine cost/quality trade-offs

### Short-term (Expansion)
1. ⏳ Apply for Sora 2 beta access
2. ⏳ Set up Google Cloud for Veo 3
3. ⏳ Configure Stability AI for SD3 fallback
4. ⏳ Build prompt template library

### Long-term (Production)
1. ⏳ Create n8n workflow templates
2. ⏳ Implement batch generation
3. ⏳ Add style preset library
4. ⏳ Integrate with Social Media Marketer
5. ⏳ Add to Content Marketer workflow

---

## Resources

**Documentation:**
- Agent definition: `.claude/agents/visual-media-generator.md`
- API config: `tools/bifrost-data/media-generation-apis.json`
- This setup guide: `tools/VISUAL-MEDIA-GENERATOR-SETUP.md`

**External Links:**
- OpenAI Images API: https://platform.openai.com/docs/guides/images
- Google Veo docs: https://ai.google.dev/gemini-api/docs
- Stability AI docs: https://platform.stability.ai/docs

**Related Agents:**
- 🎨 Graphic Designer (static design work)
- 📱 Social Media Marketer (can request generated images)
- ✍️ Content Marketer (can request blog visuals)
- 📐 UI Designer (can request mockup concepts)

---

*Visual Media Generator - AI-generated video and images for the Catalyst*
*Setup complete: 2025-11-03*
