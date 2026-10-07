# Catalyst Integration Quick Reference

## 🚀 Quick Start

```bash
# Run comprehensive tests
bun run test-catalyst-loader.ts

# Run standalone initialization test
bun run test-catalyst-init.ts

# Start bot (requires env vars)
bun run src/index.ts
```

## 📦 Core Classes

### CatalystAgentLoader
```typescript
import { catalystAgentLoader } from "./src/config";

// Get agent by full name
const agent = catalystAgentLoader.getAgent("🏛️ Backend Developer");

// Resolve friendly name to full name
const fullName = catalystAgentLoader.resolveAgentName("backend dev");
// Returns: "🏛️ Backend Developer"

// List all agents
const agents = catalystAgentLoader.listAgents();
// Returns: ["🏛️ Backend Developer", "🎨 Frontend Developer", ...]

// Get agent count
console.log(catalystAgentLoader.count); // 28
```

### CatalystSkillLoader
```typescript
import { catalystSkillLoader } from "./src/config";

// Get skill context (prompt content)
const context = catalystSkillLoader.getSkillContext("native-data-fetching");
// Returns: "[11,089 chars of prompt text]" or null

// List all skills
const skills = catalystSkillLoader.listSkills();
// Returns: ["native-data-fetching", "frontend-testing", ...]

// Get skill count
console.log(catalystSkillLoader.count); // 323
```

### SpecialistHandler
```typescript
import { getSpecialistHandler } from "./src/config";

const handler = getSpecialistHandler();

// Detect specialist in user message
const specialist = handler.detectSpecialistRequest(
  "have the backend dev create an API"
);
// Returns: "🏛️ Backend Developer" or null

// Load full specialist context
const context = await handler.loadSpecialistContext(specialist);
// Returns: "# Specialist Context: 🏛️ Backend Developer\n\n[full prompt]"
```

## 🎯 Common Patterns

### Pattern 1: Detect and Load Specialist
```typescript
import { getSpecialistHandler } from "./src/config";

const handler = getSpecialistHandler();
const userMessage = "have the backend dev create an API";

// Step 1: Detect specialist
const specialist = handler.detectSpecialistRequest(userMessage);

if (specialist) {
  // Step 2: Load specialist context
  const context = await handler.loadSpecialistContext(specialist);

  // Step 3: Inject into system prompt
  systemPrompt += "\n\n" + context;
}
```

### Pattern 2: Get Agent Metadata
```typescript
import { catalystAgentLoader } from "./src/config";

const agent = catalystAgentLoader.getAgent("🏛️ Backend Developer");

if (agent) {
  console.log("Name:", agent.name);
  console.log("Description:", agent.description);
  console.log("Model:", agent.model || "default");
  console.log("Infinity Model:", agent.infinity_model || "none");
  console.log("Prompt length:", agent.prompt.length);

  // Agent mesh (collaboration capabilities)
  if (agent.mesh) {
    console.log("Can request help from:", agent.mesh.can_request);
    console.log("Provides capabilities:", agent.mesh.provides);
  }
}
```

### Pattern 3: List and Filter Agents
```typescript
import { catalystAgentLoader } from "./src/config";

// Get all agents
const allAgents = catalystAgentLoader.listAgents();

// Filter by emoji category (quality agents)
const qualityAgents = allAgents.filter(name =>
  ["🧐", "👾", "🧪"].some(emoji => name.startsWith(emoji))
);
// Returns: ["🧐 Code Reviewer", "👾 Debugger", "🧪 Validator"]

// Filter by name pattern
const devAgents = allAgents.filter(name =>
  name.toLowerCase().includes("developer")
);
```

## 🔍 Agent Name Resolution

### Supported Aliases (70 total)
```typescript
// All case-insensitive
"backend dev"           → "🏛️ Backend Developer"
"Backend Developer"     → "🏛️ Backend Developer"
"frontend dev"          → "🎨 Frontend Developer"
"mobile dev"            → "📱 Mobile Developer"
"code reviewer"         → "🧐 Code Reviewer"
"debugger"              → "👾 Debugger"
"validator"             → "🧪 Validator"
"ai nerd"               → "🤓 AI Nerd"
// ... 62 more aliases
```

### Resolution Example
```typescript
const testNames = [
  "backend dev",
  "Frontend Developer",
  "MOBILE DEV",
  "invalid name",
];

testNames.forEach(name => {
  const resolved = catalystAgentLoader.resolveAgentName(name);
  console.log(`"${name}" → ${resolved || "NOT FOUND"}`);
});
```

## 🎨 Specialist Detection Patterns

### Pattern Matching
```typescript
const patterns = [
  "have the backend dev create an API",         // ✅ Detected
  "ask frontend developer to update the UI",    // ✅ Detected
  "get mobile dev to fix the iOS bug",          // ✅ Detected
  "tell code reviewer to check this",           // ✅ Detected
  "delegate this to the debugger",              // ✅ Detected
  "can you help me with this?",                 // ❌ Not detected (correct)
];
```

### Detection Rules
1. `have [specialist] do/implement/create/build/fix X`
2. `ask [specialist] to Y`
3. `get [specialist] to Z`
4. `tell [specialist] to...`
5. `delegate/assign to [specialist]`

## 📁 File Structure

```
telegram-{{ORCHESTRATOR_NAME_LOWER}}-bot/
├── src/
│   ├── catalyst-loader.ts       Core integration (496 lines)
│   ├── config.ts               Global instances + init
│   └── index.ts                Bot startup
│
├── catalyst-agents/ (symlink)   → {{CATALYST_ROOT}}/.claude/agents/
├── catalyst-skills/ (symlink)   → {{CATALYST_ROOT}}/.claude/skills/
│
├── test-catalyst-loader.ts      Comprehensive tests
└── test-catalyst-init.ts        Standalone tests
```

## 🔧 Initialization

### Automatic (Bot Startup)
```typescript
// In src/index.ts
import { initializeCatalyst } from "./config";

// Called automatically on bot startup
await initializeCatalyst();
```

### Manual (Testing)
```typescript
import {
  CatalystAgentLoader,
  CatalystSkillLoader,
  CatalystWatcher
} from "./src/catalyst-loader";

const agentLoader = new CatalystAgentLoader();
await agentLoader.loadAgents("./catalyst-agents");

const skillLoader = new CatalystSkillLoader();
await skillLoader.loadSkills("./catalyst-skills");

const watcher = new CatalystWatcher();
watcher.startWatching(
  { agents: "./catalyst-agents", skills: "./catalyst-skills" },
  agentLoader,
  skillLoader
);
```

## 📊 Available Resources

### Agents (28 total)
```
🏛️ Backend Developer
🎨 Frontend Developer
📱 Mobile Developer
📐 UI Designer
🎨 Graphic Designer
💻 macOS Dev
🛒 Shopify Exec
🤖 Automator
🐲 Bowser
🔍 Research Agent
👔 BOSS
🏗️ System Architect
🛡️ Security Analyst
📊 Business Analyst
🔍 SEO Analyzer
🎯 Product Strategist
📣 Chief Marketing Officer
🏄🏼‍♂️ MCP Server Dude
⛓️ Blockchain Agent
🧠 2nd Brain Wizard
🎯 Brand Specialist
🤓 AI Nerd
🎬 Visual Media Generator
🎬 Studio Engineer
🧐 Code Reviewer
👾 Debugger
🧪 Validator
🧭 Venture Analyst
```

### Top Skills (323 total)
```
native-data-fetching        (11,089 chars)
frontend-testing
ios-testing
auth-create
debugging-patterns
remotion-video
web-design-guidelines
git-commit-helper
account-login
credential-creator
auth-best-practices
appointment-booking
... (313 more)
```

## ⚡ Performance

| Operation | Time | Notes |
|-----------|------|-------|
| Load all agents | ~50ms | One-time startup |
| Load all skills | ~50ms | One-time startup |
| Agent lookup | <1ms | O(1) Map access |
| Name resolution | <1ms | O(1) alias lookup |
| Specialist detection | <1ms | Regex matching |
| **Total initialization** | **~100ms** | **All resources ready** |

## 🎓 Best Practices

### 1. Always Use Resolved Names
```typescript
// ❌ Don't use friendly names directly
const agent = catalystAgentLoader.getAgent("backend dev"); // undefined

// ✅ Resolve first
const resolved = catalystAgentLoader.resolveAgentName("backend dev");
if (resolved) {
  const agent = catalystAgentLoader.getAgent(resolved); // ✅ Works
}
```

### 2. Check for Null/Undefined
```typescript
// ✅ Always check
const agent = catalystAgentLoader.getAgent(name);
if (!agent) {
  console.log("Agent not found");
  return;
}

// ✅ Use optional chaining
const description = agent?.description ?? "No description";
```

### 3. Use Type Safety
```typescript
import type { CatalystAgent, CatalystSkill } from "./src/catalyst-loader";

function processAgent(agent: CatalystAgent) {
  // TypeScript ensures agent has expected properties
  console.log(agent.name);
  console.log(agent.prompt);
}
```

## 🐛 Troubleshooting

### Issue: "Agent not found"
```typescript
// Check if name needs resolution
const resolved = catalystAgentLoader.resolveAgentName("your input");
console.log("Resolved to:", resolved);

// List all available agents
console.log("Available agents:", catalystAgentLoader.listAgents());
```

### Issue: "Skill has no context"
```typescript
const skill = catalystSkillLoader.getSkillContext("skill-name");
if (!skill) {
  // Skill might not have prompt.md
  console.log("Available skills:", catalystSkillLoader.listSkills());
}
```

### Issue: "Initialization failed"
```bash
# Check symlinks exist
ls -la catalyst-agents/
ls -la catalyst-skills/

# Verify files are accessible
ls {{CATALYST_ROOT}}/.claude/agents/
ls {{CATALYST_ROOT}}/.claude/skills/
```

## 📚 Documentation

- **Completion Report:** `PHASE2-COMPLETION-REPORT.md`
- **Architecture:** `PHASE2-ARCHITECTURE.md`
- **This Quick Reference:** `CATALYST-INTEGRATION-QUICKREF.md`

## 🚀 Next Phase

Phase 3 will integrate this data layer with the session layer:
1. Inject specialist context into Claude prompts
2. Track active specialist in session state
3. Enable skill context on-demand
4. Implement agent mesh collaboration

---

*Quick Reference for Catalyst Integration - Phase 2*
