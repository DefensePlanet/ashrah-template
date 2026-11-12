# Claude Code - Backend Routing Modes

**One CLI, Two Backend Routes**

Claude Code CLI (`claude` command) supports two backend routing modes based on environment configuration.

---

## Architecture

```
                    ┌─ Legacy Mode ────────────────┐
                    │ (no ANTHROPIC_BASE_URL)        │
                    │ → api.anthropic.com            │
                    │ → Claude Sonnet 4.5, Opus      │
  Claude CLI        │ → Anthropic subscription       │
  (`claude`)  ──────┤                                │
                    └────────────────────────────────┘

                    ┌─ Infinity Mode ────────────────┐
                    │ (ANTHROPIC_BASE_URL=:3456)     │
                    │ → Claude Code Router (:3456)   │
                    │ → Bifrost Gateway (:8083)      │
                    │ → OpenAI/other providers       │
                    │ → GPT-4o, GPT-4o-mini, etc.    │
                    └────────────────────────────────┘
```

**Same CLI tool, different backend infrastructure based on environment variables.**

---

## Mode Comparison

| Aspect | Legacy Mode | Infinity Mode |
|--------|---------------|---------------|
| **Environment** | Default (no config) | `ANTHROPIC_BASE_URL=http://127.0.0.1:3456` |
| **Backend** | api.anthropic.com | Router → Bifrost → Multiple providers |
| **Models** | Claude Sonnet 4.5, Opus, Haiku | Configured in router (see `INFINITY-ROUTER-ARCHITECTURE.md`) |
| **Cost** | Anthropic subscription ($20/mo) | Pay-per-token (OpenAI pricing) |
| **Setup** | Works out of box | Requires router + gateway running |
| **CLI Command** | `claude` | `claude` (same) |
| **Features** | All native | All compatible (via router translation) |
| **Tool Calls** | Native Anthropic format | Translated by Router (Anthropic ↔ OpenAI) |
| **Streaming** | Native | Translated by Router (SSE conversion) |
| **Routing** | N/A | Smart rules (default/think/background/longContext) |
| **UI Management** | N/A | Web UI via `ccr ui` |

---

## Legacy Mode (Default)

**What**: Direct connection to Anthropic API
**When**: No `ANTHROPIC_BASE_URL` environment variable set

### How It Works
```
Claude CLI → api.anthropic.com → Claude Models
```

### Usage
```bash
# Just run Claude normally
claude

# Verify you're in Legacy Mode
echo $ANTHROPIC_BASE_URL
# (should be empty)
```

### Characteristics
- ✅ Official Anthropic API
- ✅ Latest Claude models
- ✅ Highest reliability
- ✅ No local infrastructure needed
- ✅ Subscription-based pricing

---

## Infinity Mode (Alternative)

**What**: Routes through Claude Code Router and Bifrost gateway to alternative providers
**When**: `ANTHROPIC_BASE_URL=http://127.0.0.1:3456` is set

### How It Works
```
Claude CLI → Claude Code Router (:3456) → Bifrost Gateway (:8083) → OpenAI API
              └─ Smart routing +           └─ Provider management
                 Format translation
```

### Usage
```bash
# Start the gateway infrastructure
./tools/start-infinity-gateway.sh

# Enable Infinity Mode for current terminal
source ./tools/use-infinity.sh

# Run Claude (same command)
claude

# Verify you're in Infinity Mode
echo $ANTHROPIC_BASE_URL
# → http://127.0.0.1:3456
```

### Characteristics
- ✅ Multi-provider support (OpenAI, Groq, 70+ providers)
- ✅ Cost optimization (GPT-4o-mini cheaper for simple tasks)
- ✅ Smart routing (context-aware model selection)
- ✅ Web UI for config management (`ccr ui`)
- ✅ Dynamic model switching (`/model` command)
- ✅ Load balancing across multiple API keys
- ✅ Built-in usage tracking via Bifrost
- ⚠️ Requires router + gateway running
- ⚠️ Adds ~25ms routing overhead

---

## Switching Between Modes

### Standard → Infinity
```bash
source ./tools/use-infinity.sh
# Sets ANTHROPIC_BASE_URL=http://localhost:3000
```

### Infinity → Standard
```bash
unset ANTHROPIC_BASE_URL
# Returns to direct Anthropic API
```

### Check Current Mode
```bash
if [ -n "$ANTHROPIC_BASE_URL" ]; then
  echo "Infinity Mode: $ANTHROPIC_BASE_URL"
else
  echo "Legacy Mode: Direct Anthropic API"
fi

# Or use the script
./tools/check-mode.sh
```

---

## Use Cases

### Use Legacy Mode For:
- ✅ Production workflows
- ✅ Tasks requiring Claude's latest capabilities
- ✅ Maximum reliability
- ✅ Official Anthropic support
- ✅ When you don't want to manage gateway infrastructure

### Use Infinity Mode For:
- ✅ Development iterations (save Anthropic credits)
- ✅ Cost-sensitive bulk operations
- ✅ Testing with different LLM providers
- ✅ Load balancing across multiple API keys
- ✅ Experimenting with GPT-4o, O1, other models

---

## Running Both Simultaneously (iTerm Profiles)

Catalyst uses dedicated iTerm profiles to keep modes completely isolated:

| iTerm Profile | Script | Backend |
|---------------|--------|---------|
| **Claude (Legacy) - Catalyst** | `run-subscription.sh` | Anthropic subscription |
| **Claude (Infinity) - Catalyst** | `start-infinity-shell.sh` | Bifrost gateway |

**Profile scripts ensure complete isolation:**
- `run-subscription.sh` - Unsets all gateway env vars, uses keychain auth
- `start-infinity-shell.sh` - Sets `ANTHROPIC_BASE_URL` and `ANTHROPIC_API_KEY=dev-router-key`

**No conflict** - Each profile runs its own initialization script.

---

## Infrastructure Requirements

### Legacy Mode
- ✅ Anthropic API key in environment
- ✅ Internet connection
- ✅ That's it!

### Infinity Mode
- ✅ OpenAI API key (or other provider keys)
- ✅ Bifrost gateway running (port 8083)
- ✅ Claude Code Router running (port 3456)
- ✅ Internet connection

**Start infrastructure**:
```bash
./tools/start-infinity-gateway.sh
```

**Stop infrastructure**:
```bash
./tools/stop-infinity-gateway.sh
```

**Open web UI**:
```bash
ccr ui
```

---

## Translation Layer (Infinity Mode)

The Claude Code Router makes OpenAI (and other providers) look like Anthropic's API:

### Request Translation
```
Claude CLI sends Anthropic Messages API request
↓
Router applies routing rules (default/think/background/longContext)
↓
Router converts to OpenAI Chat Completions format
↓
Bifrost routes to optimal provider
↓
Provider (OpenAI) responds
↓
Bifrost forwards back to Router
↓
Router converts response back to Anthropic format
↓
Claude CLI receives Anthropic-compatible response
```

### What Gets Translated
- ✅ Message formats
- ✅ Tool/function call schemas
- ✅ Streaming events (SSE format)
- ✅ Stop reasons
- ✅ Usage/token counts

**Result**: Claude CLI works identically in both modes.

---

## Cost Example

### Task: "Write a Python function to parse JSON"

**Legacy Mode (Claude Sonnet 4.5)**
- Input: ~50 tokens
- Output: ~300 tokens
- Cost: ~$0.01 (amortized via subscription)

**Infinity Mode (GPT-4o-mini)**
- Input: ~50 tokens × $0.00015/1k = $0.0000075
- Output: ~300 tokens × $0.0006/1k = $0.00018
- Cost: ~$0.00019 (~50x cheaper)

**Infinity Mode (GPT-4o)**
- Input: ~50 tokens × $0.0025/1k = $0.000125
- Output: ~300 tokens × $0.01/1k = $0.003
- Cost: ~$0.0031 (comparable to Claude)

---

## Performance

| Metric | Legacy Mode | Infinity Mode |
|--------|---------------|---------------|
| Latency | ~500ms-2s | ~525ms-2.025s (+~25ms) |
| Reliability | Highest | High |
| Startup | Instant | ~5s (router + gateway start) |
| Uptime | Anthropic SLA | Local + provider SLA |
| Features | Standard | Enhanced (routing rules, UI, /model switching) |

---

## Recommendations

### Default Setup
Keep **Legacy Mode** as your default:
```bash
# No special config needed
claude
```

### Optional Infinity Setup
Enable **Infinity Mode** when needed:
```bash
source ./tools/use-infinity.sh
claude
```

### Per-Session Choice
Choose mode based on context:
- **Production work** → Legacy Mode
- **Development/testing** → Infinity Mode
- **Cost-sensitive bulk ops** → Infinity Mode
- **Latest Claude features** → Legacy Mode

---

## Troubleshooting

### "Which mode am I using?"
```bash
echo $ANTHROPIC_BASE_URL
# or
./tools/check-mode.sh
```
- **Empty** = Legacy Mode
- **http://127.0.0.1:3456** = Infinity Mode

### "Infinity Mode not working"
```bash
# Check services are running
ps aux | grep -E "bifrost|claude-code-router"

# Check ports are listening
lsof -i :8083 -i :3456

# Check logs
tail -f logs/bifrost.log
tail -f ~/.claude-code-router/logs/ccr-*.log

# Restart gateway
./tools/stop-infinity-gateway.sh
./tools/start-infinity-gateway.sh
```

### "Switch back to Standard"
```bash
unset ANTHROPIC_BASE_URL
```

---

## Quick Reference

| Action | Command |
|--------|---------|
| **Check mode** | `echo $ANTHROPIC_BASE_URL` |
| **Use Standard** | `unset ANTHROPIC_BASE_URL` |
| **Use Infinity** | `source ./tools/use-infinity.sh` |
| **Start gateway** | `./tools/start-infinity-gateway.sh` |
| **Stop gateway** | `./tools/stop-infinity-gateway.sh` |
| **Test gateway** | `./tools/test-infinity-cli.sh` |

---

## Summary

You have **one Claude Code CLI** with **two routing backends**:

1. **Legacy Mode** - Direct to Anthropic (default)
2. **Infinity Mode** - Through Bifrost to OpenAI/others (opt-in)

Same CLI tool (`claude`), same features, different infrastructure based on environment configuration.

Choose the mode that fits your current context - both work identically from Claude CLI's perspective.

---

**Last Updated**: 2025-11-24
**Status**: Both modes operational
**Default**: Legacy Mode (subscription)
**Alternative**: Infinity Mode (see `INFINITY-ROUTER-ARCHITECTURE.md` for current providers)
**Isolation**: iTerm profiles with dedicated startup scripts
