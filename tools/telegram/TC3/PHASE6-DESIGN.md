# Phase 6: Auto-Sync & Watchers - Design Document

**Status:** 🔨 In Progress
**Goal:** Enable automatic syncing of Catalyst changes and add management commands

---

## Overview

Phases 1-5 have built the foundation:
- ✅ Phase 1: Foundation (symlinks)
- ✅ Phase 2: Catalyst Loader (agents/skills)
- ✅ Phase 3: MCP Integration (17 servers)
- ✅ Phase 4: Identity Transformation ({{ORCHESTRATOR_NAME}} personality)
- ✅ Phase 5: Enhanced Session Context (specialist/skill persistence)

**Phase 6 Goals:**
1. Enable hot reload when Catalyst files change
2. Add `/sync` command for manual refresh
3. Add `/context` command to show session state
4. Add `/specialist` command to manage specialists
5. Add `/skills` command to manage skills

---

## Current State

### Existing CatalystWatcher (Phase 2)
**File:** `src/catalyst-loader.ts` (lines 400+)

```typescript
class CatalystWatcher {
  startWatching(paths, agentLoader, skillLoader) {
    // Watches agents/ and skills/ directories
    // Logs changes but doesn't reload
  }
}
```

**Problems:**
- Logs changes but doesn't trigger reloads
- No way to manually trigger refresh
- User has no visibility into what's loaded

---

## Solution: Enhanced Watcher + Commands

### 1. Hot Reload Enhancement

**Update CatalystWatcher to:**
- Actually reload agents when files change
- Actually reload skills when files change
- Notify active sessions of updates
- Debounce rapid changes (wait 500ms)

**New Methods:**
```typescript
class CatalystWatcher {
  // Existing
  startWatching(paths, agentLoader, skillLoader): void

  // New: Trigger manual reload
  async reloadAll(): Promise<void>

  // New: Get watcher status
  getStatus(): { watching: boolean, changes: number }
}
```

### 2. Command: /sync

**Purpose:** Manually refresh Catalyst agents and skills

**Implementation:**
```typescript
// In handlers/commands.ts
bot.command("sync", async (ctx) => {
  await ctx.reply("🔄 Syncing Catalyst resources...");

  const before = {
    agents: catalystAgentLoader.count,
    skills: catalystSkillLoader.count
  };

  // Reload
  await catalystWatcher.reloadAll();

  const after = {
    agents: catalystAgentLoader.count,
    skills: catalystSkillLoader.count
  };

  const message = `
✅ Sync Complete

**Agents:** ${after.agents} (${after.agents - before.agents >= 0 ? '+' : ''}${after.agents - before.agents})
**Skills:** ${after.skills} (${after.skills - before.skills >= 0 ? '+' : ''}${after.skills - before.skills})
  `;

  await ctx.reply(message);
});
```

### 3. Command: /context

**Purpose:** Show session context summary

**Implementation:**
```typescript
bot.command("context", async (ctx) => {
  const summary = session.sessionContext.formatSummary();
  await ctx.reply(summary);
});
```

**Output:**
```
📊 Session Context Summary

**Active Specialist:** 🏛️ Backend Developer
**Loaded Skills:** 2
  - frontend-testing
  - ios-testing

**Metrics:**
  - Messages: 5
  - Context Size: 52.3K chars
  - Specialist Changes: 1
  - Session Age: 12 minutes
```

### 4. Command: /specialist

**Purpose:** Manage active specialist

**Subcommands:**
- `/specialist` - Show current specialist
- `/specialist clear` - Clear active specialist

**Implementation:**
```typescript
bot.command("specialist", async (ctx) => {
  const args = ctx.message.text.split(" ").slice(1);

  if (args[0] === "clear") {
    session.sessionContext.clearSpecialist();
    await ctx.reply("✅ Specialist cleared - returned to {{ORCHESTRATOR_NAME}} mode");
    return;
  }

  const active = session.sessionContext.getActiveSpecialist();
  if (active) {
    await ctx.reply(`**Active Specialist:** ${active}`);
  } else {
    await ctx.reply("No specialist active ({{ORCHESTRATOR_NAME}} mode)");
  }
});
```

### 5. Command: /skills

**Purpose:** Manage loaded skills

**Subcommands:**
- `/skills` - List loaded skills
- `/skills clear` - Clear all skills
- `/skills clear [name]` - Clear specific skill
- `/skills search [query]` - Search available skills

**Implementation:**
```typescript
bot.command("skills", async (ctx) => {
  const args = ctx.message.text.split(" ").slice(1);

  // List loaded skills
  if (args.length === 0) {
    const loaded = session.sessionContext.getLoadedSkills();
    if (loaded.length === 0) {
      await ctx.reply("No skills loaded");
      return;
    }
    await ctx.reply(`**Loaded Skills (${loaded.length}):**\n${loaded.map(s => `  - ${s}`).join("\n")}`);
    return;
  }

  // Clear skills
  if (args[0] === "clear") {
    if (args[1]) {
      session.sessionContext.clearSkill(args[1]);
      await ctx.reply(`✅ Skill cleared: ${args[1]}`);
    } else {
      session.sessionContext.clearAllSkills();
      await ctx.reply("✅ All skills cleared");
    }
    return;
  }

  // Search skills
  if (args[0] === "search") {
    const query = args.slice(1).join(" ");
    const results = session.skillLoader.searchSkills(query, 10);
    await ctx.reply(`**Skills matching "${query}" (${results.length}):**\n${results.map(s => `  - ${s}`).join("\n")}`);
    return;
  }
});
```

---

## Implementation Plan

### Step 1: Enhance CatalystWatcher
- [x] Design reload methods
- [ ] Implement `reloadAll()` method
- [ ] Add debouncing for file changes
- [ ] Add reload triggers on file watch events
- [ ] Test hot reload

### Step 2: Add Commands File
- [ ] Create `src/handlers/management.ts`
- [ ] Implement `/sync` command
- [ ] Implement `/context` command
- [ ] Implement `/specialist` command
- [ ] Implement `/skills` command
- [ ] Register commands in `src/index.ts`

### Step 3: Update Help Command
- [ ] Add new commands to `/help` output
- [ ] Document command usage

### Step 4: Testing
- [ ] Test file watcher reload
- [ ] Test `/sync` command
- [ ] Test `/context` command
- [ ] Test `/specialist` command
- [ ] Test `/skills` command
- [ ] E2E conversation with hot reload

---

## File Structure

```
src/
├── handlers/
│   ├── commands.ts        # Existing bot commands
│   ├── management.ts      # NEW: Session management commands
│   └── streaming.ts       # Existing streaming handler
├── catalyst-loader.ts     # MODIFY: Enhance CatalystWatcher
├── session.ts             # Existing (no changes needed)
└── index.ts              # MODIFY: Register new commands
```

---

## Success Metrics

**Functionality:**
- ✅ Agent file changes trigger reload
- ✅ Skill file changes trigger reload
- ✅ `/sync` command reloads resources
- ✅ `/context` shows session state
- ✅ `/specialist` manages specialists
- ✅ `/skills` manages skills

**User Experience:**
- ✅ No bot restart needed for Catalyst updates
- ✅ Clear visibility into session state
- ✅ Easy context management
- ✅ Discoverable commands via `/help`

---

## Example Workflow

### Auto-Sync Flow
```
1. User working in Claude Code
2. Updates .claude/agents/backend-specialist.md
3. CatalystWatcher detects change
4. Debounces for 500ms (in case more edits)
5. Reloads agents
6. Logs: "🔄 Agent reloaded: backend-specialist.md"
7. Next message uses updated agent context
```

### Manual Sync Flow
```
User: /sync
Bot:  🔄 Syncing Catalyst resources...
      ✅ Sync Complete
      Agents: 28 (+0)
      Skills: 323 (+0)
```

### Context Management Flow
```
User: have backend dev create API
Bot:  [Responds as Backend Developer]

User: /context
Bot:  📊 Session Context Summary
      Active Specialist: 🏛️ Backend Developer
      Loaded Skills: 0
      Messages: 2
      Context Size: 52.3K chars

User: /specialist clear
Bot:  ✅ Specialist cleared - returned to {{ORCHESTRATOR_NAME}} mode
```

---

## Next Steps

1. ✅ Complete design document
2. Implement enhanced CatalystWatcher
3. Create management commands handler
4. Register commands
5. Update help text
6. Test and validate

**Estimated Time:** 1-2 hours
**Complexity:** Low-Medium (mostly plumbing, clean APIs)

---

*Phase 6 Design Complete - Ready for implementation.*
