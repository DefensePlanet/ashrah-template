# Phase 5: Enhanced Session Context - Design Document

**Status:** 🔨 In Progress
**Goal:** Add intelligent session-level context management with specialist tracking and skill loading

---

## Overview

Phase 4 gave the bot {{ORCHESTRATOR_NAME}}'s identity and specialist detection. Phase 5 makes context **persistent and intelligent** across the conversation.

### Problems to Solve

1. **Specialist context is re-detected every message** - Wasteful, should persist
2. **No memory of active specialist** - Can't maintain specialist persona across messages
3. **Skills loaded at startup but never injected** - 323 skills available but unused
4. **Context grows unbounded** - No strategy for when to clear/refresh

### Solution: Session State Management

Add a `SessionContext` class that tracks:
- Active specialist (persists across messages)
- Loaded skills (on-demand, scoped to conversation)
- Context metrics (size tracking, pruning strategy)
- Session metadata (start time, message count, tokens used)

---

## Architecture

### Current State (Phase 4)
```
Message → Detect Specialist → Load Context → Query Agent SDK → Response
          (every message)      (30K + 22K)
```

**Problems:**
- Specialist detected fresh every message
- Context injected even when specialist already active
- No persistence of specialist across messages

### Proposed State (Phase 5)
```
Message → SessionContext
            ↓
          Check Active Specialist
            ↓
          Load if new, reuse if active
            ↓
          Check for skill requests
            ↓
          Load skills on-demand
            ↓
          Build optimized context
            ↓
          Query Agent SDK → Response
            ↓
          Update SessionContext
```

**Benefits:**
- Specialist detected once, persists
- Context reused when possible
- Skills loaded only when needed
- Smaller prompts on follow-up messages

---

## Components

### 1. SessionContext Class

**File:** `src/session-context.ts` (NEW)

```typescript
export class SessionContext {
  // Specialist tracking
  activeSpecialist: string | null = null;
  specialistLoadedAt: Date | null = null;
  specialistContext: string | null = null;

  // Skill tracking
  loadedSkills: Map<string, string> = new Map(); // skillName → content
  skillsLoadedAt: Map<string, Date> = new Map();

  // Context metrics
  totalContextSize: number = 0;
  messageCount: number = 0;

  // Session metadata
  sessionStartedAt: Date = new Date();
  lastActivity: Date = new Date();

  /**
   * Set active specialist (loads context if needed)
   */
  setActiveSpecialist(name: string, context: string): void

  /**
   * Clear active specialist
   */
  clearSpecialist(): void

  /**
   * Load skill context on-demand
   */
  loadSkill(skillName: string, content: string): void

  /**
   * Check if specialist is active
   */
  hasActiveSpecialist(): boolean

  /**
   * Get current context summary
   */
  getContextSummary(): string

  /**
   * Reset context (for /clear command)
   */
  reset(): void
}
```

### 2. Enhanced Session Class

**File:** `src/session.ts` (MODIFIED)

Add `SessionContext` instance:
```typescript
class ClaudeSession {
  // Existing fields...
  sessionContext: SessionContext = new SessionContext();

  // Enhanced sendMessageStreaming
  async sendMessageStreaming(...) {
    // 1. Check for specialist persistence
    // 2. Detect new specialist request
    // 3. Build optimized context
    // 4. Query Agent SDK
    // 5. Update session context
  }
}
```

### 3. Skill Context Loader

**File:** `src/skill-context-loader.ts` (NEW)

```typescript
export class SkillContextLoader {
  private skillLoader: CatalystSkillLoader;

  /**
   * Detect skill invocation in message
   * Patterns: "use skill X", "apply skill Y", "load skill Z"
   */
  detectSkillRequest(message: string): string | null

  /**
   * Load skill content
   */
  async loadSkillContent(skillName: string): Promise<string>

  /**
   * Build skill context block for injection
   */
  buildSkillContext(skills: Map<string, string>): string
}
```

---

## Detection Patterns

### Specialist Persistence

```typescript
// Current message: "have backend dev create API"
// → Specialist detected: "🏛️ Backend Developer"
// → Load specialist context
// → sessionContext.setActiveSpecialist("🏛️ Backend Developer", context)

// Next message: "make it use PostgreSQL"
// → No specialist detected in message
// → Check sessionContext.hasActiveSpecialist() → TRUE
// → Reuse existing specialist context (no reload)

// User wants to clear: "thanks, back to {{ORCHESTRATOR_NAME}}"
// → Detect clear pattern: "back to {{ORCHESTRATOR_NAME_LOWER}}", "return to {{ORCHESTRATOR_NAME_LOWER}}", "exit specialist"
// → sessionContext.clearSpecialist()
// → Next message uses {{ORCHESTRATOR_NAME}}-only context
```

**Clear Patterns:**
- "back to {{ORCHESTRATOR_NAME_LOWER}}"
- "return to {{ORCHESTRATOR_NAME_LOWER}}"
- "exit specialist"
- "clear specialist"
- "thanks" (when specialist active, interpret as completion)

### Skill Loading

```typescript
// Message: "use the frontend-testing skill"
// → Detect skill: "frontend-testing"
// → Load skill content from catalystSkillLoader
// → sessionContext.loadSkill("frontend-testing", content)
// → Inject into system prompt

// Next message: "run those tests"
// → Skill still loaded in sessionContext
// → Reuse skill context (no reload)
```

**Skill Patterns:**
- "use skill X"
- "apply skill X"
- "load skill X"
- "with skill X"
- "using X skill"

---

## Context Building Strategy

### New Session (First Message)
```
System Prompt = {{ORCHESTRATOR_NAME}} Identity (30K)
              + Specialist Context (if detected, 22K)
              + Skill Contexts (if detected, ~10K each)
```

### Follow-up Messages

**Specialist Active:**
```
System Prompt = SAFETY_PROMPT (2K)  ← Lighter!
              + "Active: [specialist name]"
              + Skill Contexts (if any)
```

**{{ORCHESTRATOR_NAME}} Only:**
```
System Prompt = SAFETY_PROMPT (2K)  ← Much lighter!
              + Skill Contexts (if any)
```

**Rationale:**
- Agent SDK session already has {{ORCHESTRATOR_NAME}} + specialist context from first message
- No need to re-inject full context on every message
- Only inject deltas (new skills, specialist changes)

---

## Implementation Plan

### Step 1: Create SessionContext Class
- [x] Design data structure
- [ ] Implement specialist tracking
- [ ] Implement skill tracking
- [ ] Add context metrics
- [ ] Add reset/clear methods

### Step 2: Create SkillContextLoader
- [ ] Implement skill detection patterns
- [ ] Integrate with CatalystSkillLoader
- [ ] Build skill context formatting
- [ ] Add caching

### Step 3: Enhance ClaudeSession
- [ ] Add SessionContext instance
- [ ] Modify sendMessageStreaming to use SessionContext
- [ ] Implement specialist persistence logic
- [ ] Implement skill loading logic
- [ ] Add context optimization

### Step 4: Add Commands
- [ ] `/specialist` - Show active specialist
- [ ] `/skills` - Show loaded skills
- [ ] `/context` - Show context summary
- [ ] `/clear` - Clear specialist/skills

### Step 5: Testing
- [ ] Test specialist persistence
- [ ] Test skill loading
- [ ] Test context optimization
- [ ] Test clear patterns
- [ ] E2E conversation testing

---

## Success Metrics

**Performance:**
- ✅ Follow-up messages use <5K context (vs 30K+ currently)
- ✅ Specialist context loaded once, reused N times
- ✅ Skills loaded on-demand, not upfront

**Functionality:**
- ✅ Specialist persists across messages
- ✅ Skills loadable via natural language
- ✅ Context clearable via commands or patterns
- ✅ Session state survives restarts (via session resume)

**User Experience:**
- ✅ Natural conversations with specialists
- ✅ No need to repeat "have backend dev..." every message
- ✅ Skills invokable mid-conversation
- ✅ Clear commands for context management

---

## Example Conversation

```
User: have the backend dev create an API
Bot:  [Loads Backend Dev context, ~52K system prompt]
      [Responds as Backend Developer]

User: make it use PostgreSQL
Bot:  [Reuses Backend Dev context, ~2K system prompt]
      [Continues as Backend Developer]

User: use the native-data-fetching skill
Bot:  [Loads skill, ~12K added to context]
      [Responds with skill knowledge]

User: back to {{ORCHESTRATOR_NAME_LOWER}}
Bot:  [Clears specialist context]
      [Responds as {{ORCHESTRATOR_NAME}}]
```

---

## Next Steps

1. ✅ Complete design document
2. Implement SessionContext class
3. Implement SkillContextLoader
4. Integrate into ClaudeSession
5. Add /commands
6. Test and validate

**Estimated Time:** 2-3 hours
**Complexity:** Medium (new state management, but clean boundaries)

---

*Phase 5 Design Complete - Ready for implementation.*
