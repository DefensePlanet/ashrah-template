# Phase 2 Architecture: Catalyst Loader

## System Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Telegram {{ORCHESTRATOR_NAME}} Bot                          │
└─────────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────┐
│                          src/index.ts                                │
│                     (Bot Entry Point)                                │
│                                                                       │
│  • Initialize grammy Bot                                             │
│  • Register handlers                                                 │
│  • Call initializeCatalyst() ◄──────────────────┐                   │
│  • Start bot                                     │                   │
└──────────────────────────────────────────────────┼───────────────────┘
                                                   │
                                                   │
┌──────────────────────────────────────────────────┼───────────────────┐
│                        src/config.ts             │                   │
│                   (Configuration & Init)         │                   │
│                                                  │                   │
│  initializeCatalyst() ───────────────────────────┘                   │
│      │                                                                │
│      ├─► catalystAgentLoader.loadAgents()                            │
│      ├─► catalystSkillLoader.loadSkills()                            │
│      └─► catalystWatcher.startWatching()                             │
│                                                                       │
│  Export: catalystAgentLoader, catalystSkillLoader,                   │
│          getSpecialistHandler()                                      │
└───────────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     src/catalyst-loader.ts                           │
│                   (Core Integration Layer)                           │
└─────────────────────────────────────────────────────────────────────┘
           │              │                │              │
           ▼              ▼                ▼              ▼
    ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐
    │  Agent   │   │  Skill   │   │Specialist│   │ Catalyst │
    │  Loader  │   │  Loader  │   │ Handler  │   │ Watcher  │
    └──────────┘   └──────────┘   └──────────┘   └──────────┘
         │              │                │              │
         ▼              ▼                ▼              ▼
    ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐
    │28 Agents │   │323 Skills│   │ Detect & │   │File Watch│
    │in Memory │   │in Memory │   │  Load    │   │ & Reload │
    └──────────┘   └──────────┘   └──────────┘   └──────────┘
         │              │
         ▼              ▼
    ┌──────────────────────────┐
    │  Agent Name Resolver     │
    │  (70 aliases)            │
    └──────────────────────────┘
```

## Component Details

### 1. CatalystAgentLoader

**Purpose:** Load and manage all Catalyst agents

```
Input: catalyst-agents/ (symlink → {{CATALYST_ROOT}}/.claude/agents/)
       ↓
Parse: *.md files with YAML frontmatter
       ↓
Extract:
  - name: "🏛️ Backend Developer"
  - description: "API design, backend systems..."
  - model: "sonnet" (optional)
  - infinity_model: "minimax-quickthink" (optional)
  - prompt: Full agent prompt text (22k+ chars)
  - mesh: { can_request: [...], provides: [...] }
       ↓
Store: Map<name, CatalystAgent>
       ↓
Output: 28 agents accessible via getAgent(name)
```

**Key Methods:**
- `loadAgents(dir)` → Parse and load all agents
- `getAgent(name)` → Retrieve agent by full name
- `listAgents()` → Get all agent names
- `resolveAgentName(friendly)` → "backend dev" → "🏛️ Backend Developer"

### 2. CatalystSkillLoader

**Purpose:** Index and provide access to all Catalyst skills

```
Input: catalyst-skills/ (symlink → {{CATALYST_ROOT}}/.claude/skills/)
       ↓
Scan: Recursive directory traversal
       ↓
Find: prompt.md or skill.md in each skill directory
       ↓
Load: Skill metadata + prompt content
       ↓
Store: Map<skillName, CatalystSkill>
       ↓
Output: 323 skills accessible via getSkillContext(name)
```

**Skill Structure:**
```
catalyst-skills/
├── native-data-fetching/
│   └── prompt.md (11,089 chars)
├── frontend-testing/
│   ├── prompt.md
│   └── examples/
│       └── ...
├── ios-testing/
│   └── prompt.md
└── ... (323 total)
```

### 3. SpecialistHandler

**Purpose:** Detect specialist requests and load specialist context

```
User Message: "have the backend dev create an API"
       ↓
Detection Patterns:
  - /have\s+(?:the\s+)?([a-z\s]+?)\s+(?:do|implement|create)/i
  - /ask\s+(?:the\s+)?([a-z\s]+?)\s+to/i
  - /get\s+(?:the\s+)?([a-z\s]+?)\s+to/i
       ↓
Extract: "backend dev"
       ↓
Resolve: "backend dev" → "🏛️ Backend Developer"
       ↓
Load: Full agent prompt (22k+ chars)
       ↓
Output: Specialist context ready for injection
```

**Detection Patterns (5 total):**
1. `have [specialist] do/implement/create/build/fix X`
2. `ask [specialist] to Y`
3. `get [specialist] to Z`
4. `tell [specialist] to...`
5. `delegate/assign to [specialist]`

### 4. CatalystWatcher

**Purpose:** Monitor Catalyst directories for changes and hot reload

```
Start: watch(catalyst-agents/), watch(catalyst-skills/)
       ↓
Events: fileChange, fileCreate, fileDelete
       ↓
Log: "🔄 Agent file changed: backend-specialist.md (change)"
     "🔄 Skill file changed: frontend-testing/prompt.md (change)"
       ↓
Future: Trigger selective reload
       ↓
Currently: Logs changes only
```

**Watched Paths:**
- `catalyst-agents/` → Agent file changes
- `catalyst-skills/` → Skill file changes (recursive)

### 5. AgentNameResolver

**Purpose:** Resolve friendly names to full emoji names

```
Input: "backend dev"
       ↓
Load: {{CATALYST_ROOT}}/.claude-context/agent-name-routing.json
       ↓
Aliases: 70 name mappings (case-insensitive)
       ↓
Lookup: Map.get("backend dev")
       ↓
Output: "🏛️ Backend Developer"
```

**Resolution Strategies:**
1. Direct lookup (exact match)
2. Case-insensitive match
3. Suffix removal ("backend developer" → "backend")
4. Best match algorithm

## Data Flow Example

### User Request: "Have the backend dev create a REST API"

```
1. User sends message to Telegram bot
       ↓
2. Bot handler receives message
       ↓
3. SpecialistHandler.detectSpecialistRequest(message)
   → Detects: "backend dev"
       ↓
4. AgentNameResolver.resolve("backend dev")
   → Returns: "🏛️ Backend Developer"
       ↓
5. CatalystAgentLoader.getAgent("🏛️ Backend Developer")
   → Returns: Full agent object with 22k char prompt
       ↓
6. SpecialistHandler.loadSpecialistContext(agent)
   → Returns: "# Specialist Context: 🏛️ Backend Developer\n\n[full prompt]"
       ↓
7. Session handler injects context into Claude prompt
       ↓
8. Claude responds with Backend Developer persona
```

## Memory Architecture

### Agent Storage
```typescript
Map<string, CatalystAgent> {
  "🏛️ Backend Developer" => {
    name: "🏛️ Backend Developer",
    description: "API design, backend systems...",
    prompt: "[22,061 chars]",
    mesh: { can_request: [...], provides: [...] },
    ...
  },
  "🎨 Frontend Developer" => { ... },
  ... (28 total)
}
```

**Memory Usage:** ~2-3 MB total for all agents

### Skill Storage
```typescript
Map<string, CatalystSkill> {
  "native-data-fetching" => {
    name: "native-data-fetching",
    path: "{{CATALYST_ROOT}}/.claude/skills/native-data-fetching",
    hasPrompt: true,
    promptContent: "[11,089 chars]"
  },
  "frontend-testing" => { ... },
  ... (323 total)
}
```

**Memory Usage:** ~5-10 MB total for all skills

### Alias Storage
```typescript
Map<string, string> {
  "backend dev" => "🏛️ Backend Developer",
  "backend developer" => "🏛️ Backend Developer",
  "frontend dev" => "🎨 Frontend Developer",
  ... (70 total)
}
```

**Memory Usage:** <1 KB

## Performance Metrics

| Operation | Time | Notes |
|-----------|------|-------|
| Load all agents | ~50ms | Parse 28 .md files |
| Load all skills | ~50ms | Scan 323 directories |
| Agent lookup | <1ms | O(1) Map access |
| Name resolution | <1ms | O(1) Map access |
| Specialist detection | <1ms | Regex pattern matching |
| Total initialization | ~100ms | One-time startup cost |

## File Structure

```
telegram-{{ORCHESTRATOR_NAME_LOWER}}-bot/
├── src/
│   ├── catalyst-loader.ts      ← Core implementation (496 lines)
│   ├── config.ts               ← Modified (added initialization)
│   └── index.ts                ← Modified (added startup call)
│
├── catalyst-agents/ (symlink)  ← Points to {{CATALYST_ROOT}}/.claude/agents/
│   ├── backend-specialist.md   (28 total)
│   ├── frontend-developer.md
│   └── ...
│
├── catalyst-skills/ (symlink)  ← Points to {{CATALYST_ROOT}}/.claude/skills/
│   ├── native-data-fetching/   (323 total)
│   ├── frontend-testing/
│   └── ...
│
├── test-catalyst-loader.ts     ← Comprehensive test (142 lines)
├── test-catalyst-init.ts       ← Standalone test (79 lines)
│
├── PHASE2-COMPLETION-REPORT.md ← This report (322 lines)
└── PHASE2-ARCHITECTURE.md      ← Architecture diagram (this file)
```

## Integration Points (Phase 3)

### Session Handler
```typescript
// Future: Inject specialist context
const specialist = specialistHandler.detectSpecialistRequest(userMessage);
if (specialist) {
  const context = await specialistHandler.loadSpecialistContext(specialist);
  systemPrompt += "\n\n" + context;
}
```

### {{ORCHESTRATOR_NAME}} Identity
```typescript
// Future: Load {{ORCHESTRATOR_NAME}} persona
const {{ORCHESTRATOR_NAME_LOWER}}mPrompt = readFileSync("CATALYST_{{ORCHESTRATOR_NAME_UPPER}}.md", "utf-8");
systemPrompt = {{ORCHESTRATOR_NAME_LOWER}}mPrompt + "\n\n" + conversationContext;
```

### Agent Mesh Collaboration
```typescript
// Future: Enable inter-agent collaboration
const agent = catalystAgentLoader.getAgent("🏛️ Backend Developer");
if (agent.mesh?.can_request?.includes("🎨 Frontend Developer")) {
  // Backend Dev can request help from Frontend Dev
  await collaborateWithAgent("🎨 Frontend Developer");
}
```

## Error Handling

### Graceful Degradation
- If agent file malformed → Log warning, skip file
- If skill directory unreadable → Log error, continue
- If name resolution fails → Return null, let caller handle
- If watcher fails → Log error, continue without hot reload

### No Crash Policy
- Catalyst loader failures never crash the bot
- Bot can start even if Catalyst resources unavailable
- Warnings logged for investigation

## Testing Strategy

### Unit Tests (test-catalyst-loader.ts)
- ✅ Agent loading (28 agents)
- ✅ Name resolution (8 test cases)
- ✅ Skill loading (323 skills)
- ✅ Specialist detection (6 patterns)
- ✅ Context loading

### Integration Tests (test-catalyst-init.ts)
- ✅ Initialization without Telegram credentials
- ✅ Resource loading verification
- ✅ Watcher startup

### Future: E2E Tests
- Bot receives message → Specialist detected → Context loaded → Response
- Agent mesh collaboration chains
- Hot reload triggers

## Next Phase Preview (Phase 3)

Phase 3 will connect this data layer to the session layer:

1. **Load {{ORCHESTRATOR_NAME}} identity** from `CATALYST_{{ORCHESTRATOR_NAME_UPPER}}.md` symlink
2. **Inject specialist context** when detected in user messages
3. **Track active specialist** in session state
4. **Enable skill context** on-demand
5. **Implement agent mesh** collaboration

Phase 2 provides the foundation - Phase 3 makes it interactive.
