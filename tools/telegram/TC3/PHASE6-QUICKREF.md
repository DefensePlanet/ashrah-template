# Phase 6 Quick Reference - Auto-Sync & Watchers

## New Commands

### `/sync` - Manual Resource Sync
Manually reload Catalyst agents and skills. Returns before/after counts.

**Usage:**
```
/sync
```

**Output:**
```
✅ Sync Complete

Agents: 28 → 29 (+1)
Skills: 323 → 323 (unchanged)

📊 Watcher Status:
- Watching: Active
- Hot reloads: 3
```

---

### `/context` - View Session Context
Display current session state including specialist, skills, and metrics.

**Usage:**
```
/context
```

**Output:**
```
📊 Session Context Summary

Active Specialist: 🏛️ Backend Developer
Loaded Skills: 2
  - native-data-fetching
  - frontend-testing

Metrics:
  - Messages: 12
  - Context Size: 65.3K chars
  - Specialist Changes: 1
  - Session Age: 45 minutes
```

---

### `/specialist` - Manage Specialist
Show or clear the active specialist.

**Usage:**
```
/specialist              # Show active specialist
/specialist clear        # Clear and return to {{ORCHESTRATOR_NAME}}
```

**Output (show):**
```
🎯 Active Specialist

Name: 🏛️ Backend Developer
Active for: 23 minutes

To clear: /specialist clear
```

**Output (clear):**
```
✅ Cleared specialist: 🏛️ Backend Developer

Returned to {{ORCHESTRATOR_NAME}} mode.
```

**Output (none active):**
```
ℹ️ No specialist is currently active.

To activate a specialist, say:
- "Have [specialist] do X"
- "Ask [specialist] to Y"
```

---

### `/skills` - Manage Skills
List, search, or clear loaded skills.

**Usage:**
```
/skills                  # List loaded skills
/skills clear            # Clear all skills
/skills clear <name>     # Clear specific skill
/skills search <query>   # Search available skills
```

**Output (list):**
```
📚 Loaded Skills (2):

- native-data-fetching
- frontend-testing

Commands:
- /skills clear - Clear all skills
- /skills clear <name> - Clear specific skill
- /skills search <query> - Search available skills
```

**Output (clear all):**
```
✅ Cleared 2 skill(s):
- native-data-fetching
- frontend-testing
```

**Output (clear specific):**
```
✅ Cleared skill: native-data-fetching
```

**Output (search):**
```
🔍 Skills matching "test" (5):

- frontend-testing
- ios-testing
- testing-patterns
- test-automation
- unit-test-guide

To load a skill, say:
"Use the [skill-name] skill"
```

**Output (none loaded):**
```
ℹ️ No skills are currently loaded.

To load a skill, say:
- "Use skill X"
- "Apply the Y skill"

To search skills: /skills search <query>
```

---

## Hot Reload System

### Automatic Detection
The bot watches Catalyst directories for changes:
- **Agents:** `catalyst-agents/` (any .md file)
- **Skills:** `catalyst-skills/` (recursive, all files)

### Debouncing
Changes are debounced with a 500ms delay. Multiple rapid changes result in a single reload.

**Example:**
```
Edit 1: backend-specialist.md
Edit 2: backend-specialist.md (50ms later)
Edit 3: backend-specialist.md (100ms later)

→ Single reload after 500ms from last edit
```

### Console Output
```
🔄 Agent file changed: backend-specialist.md (rename)
✅ Agents hot-reloaded
```

---

## Use Cases

### 1. Verify Catalyst Changes
```
# After editing agent in Catalyst
User: /sync
Bot: Shows updated counts
```

### 2. Debug Context Size
```
User: /context
Bot: Shows metrics including context size
```

### 3. Switch Specialists
```
User: have backend dev create API
Bot: [Backend Dev active]

User: /specialist
Bot: Active Specialist: 🏛️ Backend Developer

User: /specialist clear
Bot: Cleared, returned to {{ORCHESTRATOR_NAME}}

User: have frontend dev build UI
Bot: [Frontend Dev active]
```

### 4. Find and Load Skills
```
User: /skills search data
Bot: Shows 10 skills matching "data"

User: use the native-data-fetching skill
Bot: [Loads skill]

User: /skills
Bot: Shows native-data-fetching is loaded

User: /skills clear
Bot: Cleared all skills
```

---

## Technical Details

### Hot Reload Flow
```
File Change → Debounce (500ms) → Reload → Update Count
```

### Resource Counts
- **Agents:** 28 (from Catalyst)
- **Skills:** 323 (from Catalyst)
- **Watchers:** 2 (agents dir + skills dir)

### Integration
Phase 6 builds on:
- **Phase 4:** {{ORCHESTRATOR_NAME}} identity, specialist detection
- **Phase 5:** Session context, specialist persistence

All previous features remain functional.

---

## Testing

Run Phase 6 tests:
```bash
bun run test-phase6-autosync.ts
```

**Expected output:** 16/16 tests passed

---

## Files Added

- `src/handlers/management.ts` - Management command handlers
- `test-phase6-autosync.ts` - Test suite
- `PHASE6-COMPLETION-REPORT.md` - Full report
- `PHASE6-QUICKREF.md` - This file

## Files Modified

- `src/catalyst-loader.ts` - Enhanced CatalystWatcher
- `src/config.ts` - Added getCatalystWatcher()
- `src/index.ts` - Registered commands
- `src/handlers/commands.ts` - Updated help

---

*Phase 6 Complete - All systems operational*
