# Agent Name Resolver

**Automatic agent name resolution for Claude Code Infinity Mode**

## Problem Solved

When using Infinity Mode, Task tool calls with shorthand agent names (e.g., "Research Agent") would fail with:
```
Agent type 'Research Agent' not found
```

The agent is registered as `🔍 Research Agent` (with emoji), but {{ORCHESTRATOR_NAME}} and users naturally use the shorthand version.

## Solution

The **agent-name-resolver** transformer automatically resolves friendly/shorthand agent names to their full emoji-prefixed names before the Task tool is invoked.

### How It Works

1. **Transformer Plugin** (`~/.claude-code-router/plugins/agent-name-resolver.js`)
   - Runs as the FIRST transformer in the Claude Code Router chain
   - Loads agent name mapping from `.claude-context/agent-name-routing.json`
   - Detects Task tool invocations in request messages
   - Resolves `subagent_type` field using case-insensitive fuzzy matching
   - Logs all resolutions for debugging

2. **Configuration**
   - Added to `~/.claude-code-router/config.json` as first transformer
   - Also in template config `tools/claude-router/config/infinity-bifrost.json`
   - Auto-loads 86+ agent name aliases on startup

3. **Name Resolution Algorithm**
   - Exact match first (e.g., "Research Agent" → mapping lookup)
   - Case-insensitive fallback (e.g., "research agent" → lowercase comparison)
   - If already has emoji prefix, pass through unchanged
   - If no match found, pass through original name (graceful degradation)

## Examples

```javascript
// Input Task tool call
{
  name: "Task",
  input: {
    subagent_type: "Research Agent",  // NO EMOJI
    prompt: "..."
  }
}

// After transformation
{
  name: "Task",
  input: {
    subagent_type: "🔍 Research Agent",  // EMOJI ADDED
    prompt: "..."
  }
}
```

**Supported aliases (case-insensitive):**
- "Research Agent" / "Researcher" → "🔍 Research Agent"
- "Backend Dev" / "Backend Developer" → "🏛️ Backend Developer"
- "AI Nerd" / "ai nerd" / "Gateway Specialist" → "🤓 AI Nerd"
- "Code Reviewer" / "code reviewer" → "🧐 Code Reviewer"
- "Debugger" / "debugger" → "👾 Debugger"
- ...and 80+ more (see `.claude-context/agent-name-routing.json`)

## Testing

### Unit Tests
```bash
# Basic test
node {{CATALYST_ROOT}}/tools/test-agent-name-resolver.js

# Comprehensive test suite
node {{CATALYST_ROOT}}/tools/test-agent-name-resolver-comprehensive.js
```

### Integration Test
Run a Claude Code session in Infinity Mode and invoke a Task with a shorthand name:
```bash
# Ensure Infinity Mode is active
source {{CATALYST_ROOT}}/tools/use-infinity.sh

# In Claude Code session
Task(subagent_type="Research Agent", prompt="Test")
# Should succeed with automatic resolution
```

### Monitoring
Check Claude Code Router logs for resolution activity:
```bash
tail -f ~/.claude-code-router/logs/ccr-*.log | grep agent-name-resolver
```

Expected output:
```
[agent-name-resolver] Loaded 86 agent name aliases
[agent-name-resolver] Resolved 'Research Agent' → '🔍 Research Agent'
[agent-name-resolver] Resolved 1 agent name(s) in request
```

## Architecture

```
Claude Code CLI
    ↓
    [User: Task(subagent_type="Research Agent")]
    ↓
Claude Code Router (port 3456)
    ↓
agent-name-resolver.js (FIRST transformer)
    ↓
    [Resolved: subagent_type="🔍 Research Agent"]
    ↓
bifrost-chat-endpoint.js (route to Bifrost)
    ↓
Bifrost Gateway (port 8083)
    ↓
Model Provider (OpenAI, etc.)
```

## Maintenance

### Adding New Agent Aliases

1. Edit `.claude-context/agent-name-routing.json`
2. Add alias mapping:
   ```json
   {
     "agent_name_aliases": {
       "New Alias": "🎯 Full Agent Name",
       "another alias": "🎯 Full Agent Name"
     }
   }
   ```
3. Restart Claude Code Router:
   ```bash
   ccr restart
   ```

### Debugging

**If resolution isn't working:**

1. Check transformer is loaded:
   ```bash
   grep agent-name-resolver ~/.claude-code-router/config.json
   ```

2. Verify mapping file exists:
   ```bash
   cat {{CATALYST_ROOT}}/.claude-context/agent-name-routing.json | jq '.agent_name_aliases | keys | length'
   ```

3. Check router logs for errors:
   ```bash
   tail -100 ~/.claude-code-router/logs/ccr-*.log | grep -i error
   ```

4. Run test suite:
   ```bash
   node {{CATALYST_ROOT}}/tools/test-agent-name-resolver-comprehensive.js
   ```

## Benefits

✅ **No more "Agent not found" errors** - Automatic resolution prevents failures
✅ **Natural interaction** - {{ORCHESTRATOR_NAME}}/users can use friendly shorthand names
✅ **Case-insensitive** - "Research Agent", "research agent", "RESEARCH AGENT" all work
✅ **Zero latency** - Resolution happens synchronously before API call
✅ **Graceful degradation** - Unknown names pass through unchanged
✅ **Logged for debugging** - All resolutions appear in router logs

## Files

**Core Implementation:**
- `{{HOME_DIR}}/.claude-code-router/plugins/agent-name-resolver.js` - Transformer plugin
- `{{CATALYST_ROOT}}/.claude-context/agent-name-routing.json` - Name mapping database

**Configuration:**
- `{{HOME_DIR}}/.claude-code-router/config.json` - Active router config
- `{{CATALYST_ROOT}}/tools/claude-router/config/infinity-bifrost.json` - Config template

**Testing:**
- `{{CATALYST_ROOT}}/tools/test-agent-name-resolver.js` - Basic test
- `{{CATALYST_ROOT}}/tools/test-agent-name-resolver-comprehensive.js` - Full test suite

**Documentation:**
- `{{CATALYST_ROOT}}/tools/AGENT-NAME-RESOLVER.md` - This file

## Status

✅ **Production Ready**
- Transformer implemented and tested
- Added to router configuration (first in chain)
- Router restarted and running
- All 8 test cases passing
- Zero performance impact

---

**Implementation Date:** 2025-11-11
**Owner:** 🤓 AI Nerd (AI gateway infrastructure specialist)
**Tested:** Comprehensive test suite (8/8 passing)
