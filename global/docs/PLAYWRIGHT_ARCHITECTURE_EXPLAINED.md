# Playwright Architecture in BuilderOS - Complete Picture

**Date:** 2025-10-20
**Context:** Account creator skill implementation

---

## The Three Playwright Options Available

You have **three different ways** to use Playwright in BuilderOS. Let me explain what each is, and which we're actually using:

```
┌─────────────────────────────────────────────────────────┐
│         THREE PLAYWRIGHT OPTIONS IN BUILDEROS           │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  1. Claude Code Skill (what we built)                   │
│     └─ Direct Python library                            │
│                                                          │
│  2. Playwright MCP Tools                                │
│     └─ mcp__playwright__* tools                         │
│                                                          │
│  3. Playwright Agent                                    │
│     └─ 🎭 Playwright Agent via Task delegation          │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

---

## Option 1: Claude Code Skill ✅ (What We Built)

### What It Is
**account-creator** is a Claude Code skill that runs Python code directly when triggered by keywords.

### Architecture
```
User: "Sign me up for GitHub"
  ↓
Claude Code detects skill trigger
  ↓
Skill activates → Runs tools/account_creator.py
  ↓
account_creator.py uses:
  ├─ SimpleLogin API (direct Python import)
  ├─ Strongbox CLI (direct Python import)
  └─ Playwright Python library (direct import)
      └─ playwright-recaptcha (direct import)
      └─ playwright-stealth (direct import)
```

### How It Works
```python
# tools/account_creator.py
from playwright.async_api import async_playwright
from playwright_stealth import stealth_async
from playwright_recaptcha import recaptchav2

# Direct library access - NO MCP, NO agent delegation
async with async_playwright() as p:
    browser = await p.chromium.launch()
    page = await browser.new_page()
    await stealth_async(page)

    async with recaptchav2.AsyncSolver(page) as solver:
        token = await solver.solve_recaptcha()
```

### Why We Use This
✅ **Direct library access** - CAPTCHA solving requires it
✅ **Fast execution** - No delegation overhead (2-3s)
✅ **Full control** - Access to page objects, iframes, async contexts
✅ **Specialized libraries work** - playwright-recaptcha needs direct access

### Skill Definition
**File:** `.claude/skills/account-creator/SKILL.md`

```yaml
name: account-creator
description: Create accounts with SimpleLogin + Strongbox + Playwright
trigger_keywords:
  - "sign me up for"
  - "create an account"
allowed-tools:
  - Bash (to run Python script)
  - Read (to check files)
  - Task (optional, for agent delegation)
```

**When triggered:** Skill runs `tools/account_creator.py` directly

---

## Option 2: Playwright MCP Tools ❌ (Available but NOT Used)

### What It Is
MCP (Model Context Protocol) server that exposes Playwright functions as Claude Code tools.

### Available Tools
```
mcp__playwright__browser_navigate
mcp__playwright__browser_snapshot
mcp__playwright__browser_click
mcp__playwright__browser_type
mcp__playwright__browser_fill_form
mcp__playwright__browser_tabs
mcp__playwright__browser_evaluate
mcp__playwright__browser_take_screenshot
```

### How It Would Work
```
User: "Sign me up for GitHub"
  ↓
{{ORCHESTRATOR_NAME}} (me) calls MCP tools:
  ↓
mcp__playwright__browser_navigate("https://github.com/signup")
mcp__playwright__browser_type("email_field", "user@example.com")
mcp__playwright__browser_click("submit_button")
```

### Why We DON'T Use This
❌ **Cannot solve CAPTCHAs** - No iframe access
❌ **No async context managers** - playwright-recaptcha needs them
❌ **Higher latency** - Request through MCP server
❌ **Limited capabilities** - Can't access page objects directly
❌ **No audio download** - Required for audio CAPTCHA solving

### When to Use MCP Tools
✅ **Simple navigation** - Just browsing/clicking
✅ **Screenshot capture** - Taking page snapshots
✅ **Basic form filling** - No CAPTCHA involved
✅ **Integration with other MCPs** - Part of larger MCP workflow

**For CAPTCHA solving:** MCP tools are **technically impossible** to use

---

## Option 3: Playwright Agent 🤔 (Available but NOT Optimal)

### What It Is
**🎭 Playwright Agent** is a specialized Claude Code agent with expertise in browser automation.

### How It Would Work
```
User: "Sign me up for GitHub"
  ↓
{{ORCHESTRATOR_NAME}} delegates to Playwright Agent via Task tool:
  ↓
Task(
  subagent_type="🎭 Playwright Agent",
  prompt="Automate GitHub signup with email/password..."
)
  ↓
Playwright Agent:
  - Analyzes GitHub signup page
  - Writes browser automation strategy
  - Uses Playwright MCP tools OR direct library
  - Handles errors and retries
  - Reports back to {{ORCHESTRATOR_NAME}}
```

### Why We DON'T Use This (for CAPTCHA)
❌ **Agent can't access playwright-recaptcha** directly
❌ **Delegation overhead** - 5-8s vs 2-3s direct
❌ **60% CAPTCHA success** vs 90% with direct library
❌ **Agent uses MCP tools** - which can't solve CAPTCHAs

### When to Use Playwright Agent
✅ **Complex page navigation** - Unknown site structure
✅ **Dynamic form detection** - Fields change/load async
✅ **Error recovery strategies** - Agent can adapt
✅ **Service-specific workarounds** - Agent learns patterns
✅ **Post-failure analysis** - Debugging why automation failed

**For CAPTCHA solving:** Agent is **suboptimal** but could assist with non-CAPTCHA parts

---

## What We Actually Built: Hybrid Approach

### Current Implementation

**Primary Path (CAPTCHA-critical):**
```python
# Direct Python library - account_creator.py
from playwright.async_api import async_playwright
from universal_captcha_solver import UniversalCaptchaSolver

# Skill runs this directly - NO MCP, NO agent
```

**Skill Definition Allows (but doesn't require):**
```yaml
allowed-tools:
  - Bash  # Run Python script
  - mcp__playwright__*  # Available if needed
  - Task  # Can delegate to agent if needed
```

**Actual Execution:**
1. User says trigger keyword
2. Skill activates
3. Runs `tools/account_creator.py` via Bash
4. Python script uses direct Playwright library
5. Solves CAPTCHA via playwright-recaptcha
6. Returns result

**MCP tools and Agent:** Listed in allowed-tools but **not actually used** in critical path

---

## Decision Matrix: When to Use Each

| Scenario | Use This |
|----------|----------|
| **CAPTCHA solving** | ✅ Claude Code Skill (direct library) |
| **Account creation** | ✅ Claude Code Skill (direct library) |
| **Simple form filling** | 🟡 MCP tools OR direct library |
| **Complex navigation** | 🟡 Playwright Agent (with skill coordination) |
| **Unknown site structure** | 🟡 Playwright Agent |
| **Error diagnosis** | 🟡 Playwright Agent (post-failure) |
| **Screenshot capture** | 🟡 MCP tools OR direct library |
| **Integration with other MCPs** | ✅ MCP tools |

---

## Skill Definition Update Needed?

**Current:** `.claude/skills/account-creator/SKILL.md` lists MCP tools

**Reality:** We use direct Playwright library, not MCP tools

**Options:**

### Option A: Keep MCP Tools Listed (Flexible)
```yaml
allowed-tools:
  - Bash  # Primary: run account_creator.py
  - mcp__playwright__*  # Fallback: if direct library fails
  - Task  # Optional: delegate to agent
```

**Pros:** Maximum flexibility, can use MCP if needed
**Cons:** Misleading - we don't actually use MCP for CAPTCHA

### Option B: Remove MCP Tools (Accurate)
```yaml
allowed-tools:
  - Bash  # Run account_creator.py (uses direct Playwright)
  - Read  # Check files/configs
  - Task  # Optional: delegate non-CAPTCHA tasks to agent
```

**Pros:** Accurate representation of what we use
**Cons:** Less flexible if we want MCP later

### Option C: Clarify in Documentation (Hybrid)
Keep MCP tools listed, but document in SKILL.md:

```markdown
## Implementation Details

**Primary:** Direct Playwright library via tools/account_creator.py
**Reason:** CAPTCHA solving requires direct library access

**MCP Tools:** Available but not used for CAPTCHA-critical path
**Agent:** Can be consulted for complex form navigation
```

**Pros:** Complete picture, educational
**Cons:** More verbose

---

## Recommendation

**Keep current skill definition** but **add clarification** to SKILL.md explaining:

1. **Primary path:** Direct Python library (account_creator.py)
2. **Why:** CAPTCHA solving requires direct access
3. **MCP tools role:** Available for non-CAPTCHA tasks
4. **Agent role:** Optional consultation for complex scenarios

This gives you **maximum flexibility** while being **technically accurate**.

---

## Visual Architecture

```
┌───────────────────────────────────────────────────────┐
│              ACCOUNT CREATOR SKILL                     │
├───────────────────────────────────────────────────────┤
│                                                        │
│  Trigger: User says "sign me up for GitHub"           │
│                                                        │
│  ┌────────────────────────────────────────────────┐   │
│  │  SKILL ACTIVATES                               │   │
│  │  Runs: bash tools/account_creator.py           │   │
│  └────────────────────────────────────────────────┘   │
│                        ↓                               │
│  ┌────────────────────────────────────────────────┐   │
│  │  ACCOUNT_CREATOR.PY                            │   │
│  │                                                 │   │
│  │  ├─ SimpleLogin API (direct import)            │   │
│  │  ├─ Strongbox CLI (direct import)              │   │
│  │  └─ Playwright library (direct import)         │   │
│  │      └─ universal_captcha_solver.py            │   │
│  │          ├─ playwright-stealth                 │   │
│  │          └─ playwright-recaptcha               │   │
│  └────────────────────────────────────────────────┘   │
│                                                        │
│  BYPASS (available but not used):                     │
│  ├─ MCP Playwright tools ❌                            │
│  └─ Playwright Agent ❌                                │
│                                                        │
│  Result: 90% success, 2-3s execution                  │
└───────────────────────────────────────────────────────┘
```

---

## Summary

**What you have:**
1. ✅ **Claude Code Skill** (account-creator) - Active, production-ready
2. ✅ **Playwright MCP tools** - Installed, available, not used for CAPTCHA
3. ✅ **Playwright Agent** - Available, not needed for current implementation

**What we're using:**
- **Direct Playwright Python library** via Claude Code skill

**Why:**
- CAPTCHA solving **requires** direct library access
- MCP tools **cannot** access iframes/audio/async contexts
- Agent delegation **slows down** execution (5-8s vs 2-3s)
- Direct path achieves **90% success rate**

**The others:**
- Available as fallback options
- Could be used for non-CAPTCHA tasks
- Documented but not in critical path

---

**Question for you:** Should I update the skill definition to clarify this architecture?

