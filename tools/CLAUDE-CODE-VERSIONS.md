# Claude Code Versions - Comparison Guide

Catalyst supports **two Claude Code setups** that coexist:

---

## 1. Standard Claude Code (Subscription)

**What**: Official Claude Code using Anthropic API directly
**Access**: Anthropic subscription credits
**Models**: Claude 3.5 Sonnet, Claude 3 Opus, Claude 3 Haiku
**Execution**: `claude` (normal command)

### When to Use
- ✅ Production work requiring Claude's native capabilities
- ✅ Tasks needing Claude 3.5 Sonnet's reasoning
- ✅ When you want official Anthropic API support
- ✅ Maximum reliability and feature completeness

### Characteristics
- **Cost**: Anthropic subscription ($20/month Pro)
- **Models**: Latest Claude models (Sonnet 4.5, etc.)
- **Reliability**: Direct Anthropic API, highest stability
- **Features**: Full Claude Code feature set
- **Speed**: Direct API calls, no middleware

---

## 2. Infinity Claude Code (Gateway)

**What**: Alternative setup using Router + Bifrost gateway with multi-provider support
**Access**: OpenAI API keys (or other providers)
**Models**: GPT-4o, GPT-4o-mini, O1-mini (OpenAI) + 70 more via Bifrost
**Execution**: Terminal with `ANTHROPIC_BASE_URL=http://127.0.0.1:3456`

### When to Use
- ✅ Experimentation with different LLM providers
- ✅ Cost optimization (GPT-4o-mini cheaper than Claude for simple tasks)
- ✅ Testing multi-provider routing strategies
- ✅ Load balancing across multiple API keys
- ✅ Development/testing alternative to burning Anthropic credits

### Characteristics
- **Cost**: Pay-per-token (OpenAI API pricing)
- **Models**: 70+ providers supported via Bifrost (OpenAI, Groq, etc.)
- **Reliability**: Good, but adds middleware layers (Router + Bifrost)
- **Features**: Compatible with Claude Code tools/delegations via Router translation layer
- **Speed**: ~25ms overhead from routing + translation
- **Bonus**: Smart routing rules, Web UI (`ccr ui`), dynamic model switching (`/model`)

---

## Architecture Comparison

### Standard Claude Code
```
Claude CLI → Anthropic API → Claude Models
```

### Infinity Claude Code
```
Claude CLI → Claude Code Router (:3456) → Bifrost Gateway (:8083) → OpenAI/Other APIs
              └─ Smart routing +           └─ Provider management
                 Format translation           & load balancing
```

---

## Side-by-Side Comparison

| Feature | Standard | Infinity |
|---------|----------|----------|
| **API** | Anthropic | OpenAI (+ 70 others via Bifrost) |
| **Models** | Claude 3.5 Sonnet, Opus, Haiku | GPT-4o, GPT-4o-mini, O1, etc. |
| **Cost Model** | Subscription ($20/mo) | Pay-per-token |
| **Setup** | Official installation | Router + Gateway stack |
| **Reliability** | Highest | High (adds router + gateway) |
| **Tool Calls** | Native | Translated by Router (Anthropic ↔ OpenAI) |
| **Streaming** | Native | Translated by Router (SSE conversion) |
| **Multi-provider** | No | Yes (route across providers) |
| **Load Balancing** | No | Yes (multiple keys per provider) |
| **Smart Routing** | No | Yes (default/think/background/longContext) |
| **UI Management** | No | Yes (Web UI via `ccr ui`) |
| **Cost Tracking** | Via Anthropic dashboard | Via Bifrost built-in metrics |
| **Startup** | Instant | Requires router + gateway start (~5s) |

---

## Use Cases

### Use Standard Claude Code For:
1. **Production Workflows** - Mission-critical tasks
2. **Claude-Specific Features** - Latest Sonnet/Opus capabilities
3. **Simplicity** - No gateway management needed
4. **Official Support** - Direct Anthropic relationship

### Use Infinity Claude Code For:
1. **Cost Optimization** - GPT-4o-mini for simple tasks
2. **Experimentation** - Test different models/providers
3. **Development** - Burn OpenAI credits instead of Anthropic subscription
4. **Multi-Provider** - Route to cheapest/fastest provider per request
5. **Load Balancing** - Distribute across multiple API keys

---

## Running Both Simultaneously

Both versions can coexist. They're isolated by:

### Standard Claude Code
```bash
# Terminal 1: Standard mode (default)
claude
# Uses ANTHROPIC_API_KEY from environment
# Connects directly to api.anthropic.com
```

### Infinity Claude Code
```bash
# Terminal 2: Infinity mode
source ./tools/use-infinity.sh
claude
# Uses ANTHROPIC_BASE_URL=http://127.0.0.1:3456
# Routes through Router → Bifrost gateway
```

**No conflict** - different terminals, different environment variables.

---

## Migration Strategy (Optional)

You **do not need** to migrate from one to the other. Use both based on context:

### Recommended Approach
- **Default**: Standard Claude Code for production
- **Optional**: Infinity for testing, cost optimization, experimentation

### If You Want to Make Infinity Default
Add to `~/.zshrc`:
```bash
# Use Infinity by default
export ANTHROPIC_BASE_URL=http://127.0.0.1:3456
```

Then standard mode requires:
```bash
unset ANTHROPIC_BASE_URL
claude
```

---

## Cost Comparison Example

### Task: "Write a simple Python function"

**Standard Claude Code (Sonnet 3.5)**
- Input: ~50 tokens
- Output: ~200 tokens
- Cost: ~$0.0075 (via subscription, amortized)

**Infinity (GPT-4o-mini)**
- Input: ~50 tokens × $0.00015/1k = $0.0000075
- Output: ~200 tokens × $0.0006/1k = $0.00012
- Cost: ~$0.00013 (~50x cheaper)

**Infinity (GPT-4o)**
- Input: ~50 tokens × $0.0025/1k = $0.000125
- Output: ~200 tokens × $0.01/1k = $0.002
- Cost: ~$0.0021 (comparable to Sonnet)

---

## Quick Commands

### Standard Claude Code
```bash
# Just run normally
claude

# Check you're in standard mode
echo $ANTHROPIC_BASE_URL
# Should output: (empty)
```

### Infinity Claude Code
```bash
# Start gateway
./tools/start-infinity-gateway.sh

# Enable in terminal
source ./tools/use-infinity.sh

# Run Claude CLI
claude

# Check you're in Infinity mode
echo $ANTHROPIC_BASE_URL
# Should output: http://127.0.0.1:3456
```

---

## Troubleshooting

### "Which version am I using?"
```bash
echo $ANTHROPIC_BASE_URL
# or
./tools/check-mode.sh
```
- **Empty** = Standard Claude Code (Anthropic API)
- **http://127.0.0.1:3456** = Infinity (Router + Bifrost gateway)

### "I want to switch versions"
**Standard → Infinity:**
```bash
source ./tools/use-infinity.sh
```

**Infinity → Standard:**
```bash
unset ANTHROPIC_BASE_URL
```

### "Both are showing the same behavior"
Infinity translation layer is designed to be transparent. The main differences are:
- Model being used (check logs)
- Cost tracking source
- API endpoints hit

---

## Recommendations

1. **Keep both available** - Use based on context
2. **Default to Standard** - For production work
3. **Use Infinity for**:
   - Development iterations (save Anthropic credits)
   - Cost-sensitive bulk operations
   - Provider/model experimentation
4. **Monitor costs** - Track usage in both systems

---

## Summary

You now have **two Claude Code setups**:

| Setup | Primary Use | When to Use |
|-------|-------------|-------------|
| **Standard** | Production work | Default for most tasks |
| **Infinity** | Cost optimization & experimentation | Development, testing, bulk ops |

Both coexist peacefully. Choose per terminal session based on your needs.

---

**Last Updated**: 2025-10-31
**Status**: Both versions operational
**Default**: Standard Claude Code
**Alternative**: Infinity (opt-in per terminal)
