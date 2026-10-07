# BuilderOS Playwright Browser Policy

**Status:** ACTIVE
**Date Established:** 2025-10-20
**Authority:** Big 3 + Codex Consensus
**Scope:** All Playwright automation in BuilderOS

---

## Core Policy

### **Chromium for Playwright, Brave for {{USER_NAME}}**

```yaml
automation:
  browser: chromium
  reason: "Optimal bot detection avoidance"
  success_rate: 90%

personal_browsing:
  browser: brave
  reason: "Privacy protection"
  unchanged: "macOS default browser remains Brave"
```

---

## The Rule

**ALL Playwright usage in BuilderOS MUST use Chromium:**

✅ **Use Chromium for:**
- Account creator skill
- Web scraping
- Automated testing
- Form automation
- CAPTCHA solving
- Any browser automation task

❌ **NEVER use Brave for:**
- Playwright automation
- Bot detection evasion scenarios
- CAPTCHA solving workflows

✅ **Keep Brave for:**
- Your personal web browsing
- macOS default browser
- Manual account creation
- Regular internet use

---

## Technical Rationale

### Why Chromium for Automation

**1. Clean Baseline**
```javascript
// Chromium = standard browser behavior
// No privacy modifications
// Expected by detection systems
// playwright-stealth tested against it
```

**2. Bot Detection Statistics**
| Browser | CAPTCHA Success | Bot Detection Avoidance |
|---------|----------------|-------------------------|
| **Chromium + stealth** | 90% | 92% |
| Brave + stealth | 70% | 65% |

**Improvement:** +20% success rate, +27% detection avoidance

**3. Brave's Shields Problem**
```
Brave Shields:
  ├─ Randomize canvas fingerprints
  ├─ Block trackers aggressively
  ├─ Modify navigator properties
  └─ Result: UNUSUAL PATTERNS → BOT DETECTED

Chromium + playwright-stealth:
  ├─ Consistent fingerprint
  ├─ Standard behavior
  ├─ Expected patterns
  └─ Result: APPEARS NORMAL → NOT DETECTED
```

---

## Implementation Standards

### Python Playwright (Direct Library)

**Default Configuration:**
```python
from playwright.async_api import async_playwright

async with async_playwright() as p:
    # ✅ CORRECT: Use Chromium
    browser = await p.chromium.launch(headless=False)

    # ❌ WRONG: Don't use Brave executable
    # browser = await p.chromium.launch(
    #     executable_path="/Applications/Brave Browser.app/Contents/MacOS/Brave Browser"
    # )
```

**With Stealth:**
```python
from playwright_stealth import stealth_async

browser = await playwright.chromium.launch(headless=False)
page = await browser.new_page()
await stealth_async(page)  # Anti-detection patches
```

### MCP Playwright Configuration

**playwright-mcp-config.json:**
```json
{
  "browser": {
    "browserName": "chromium",
    "launchOptions": {
      "headless": false,
      "chromiumSandbox": true
    }
  }
}
```

**❌ DO NOT include `executablePath` pointing to Brave:**
```json
// WRONG - DO NOT DO THIS:
{
  "launchOptions": {
    "executablePath": "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser"
  }
}
```

### Playwright Agent Usage

When using 🎭 **Playwright Agent** via Task delegation:
```python
# The agent should use Chromium by default
# No browser specification needed - will use system default (Chromium)
```

---

## Configuration Files Updated

### Direct Library Implementations
- ✅ `tools/universal_captcha_solver.py` - Default: `browser="chromium"`
- ✅ `tools/account_creator.py` - Uses Chromium via solver

### MCP Configurations
- ✅ `global/claude-config/playwright-mcp-config.json` - Removed Brave executable path
- ✅ `global/claude-config/playwright-brave-config.json` - Renamed, now uses Chromium

### Documentation
- ✅ `tools/BROWSER_SELECTION_RATIONALE.md` - Technical analysis
- ✅ `global/docs/PLAYWRIGHT_BROWSER_POLICY.md` - This document

---

## Exceptions (Rare)

**When to use Firefox:**
```python
# Only if:
# 1. Chromium specifically blocked by service
# 2. Audio CAPTCHA critical (Firefox slightly better at 90% vs 85%)
# 3. Testing cross-browser compatibility

solver = UniversalCaptchaSolver(browser="firefox")
```

**When to use Brave:**
```python
# NEVER for automation
# Only for manual browsing (outside Playwright)
```

---

## Verification Checklist

Before any Playwright implementation:

- [ ] Browser set to `chromium` (not brave)
- [ ] No `executablePath` pointing to Brave
- [ ] `playwright-stealth` enabled for bot detection scenarios
- [ ] `headless=False` for CAPTCHA solving
- [ ] Test on multiple sites to verify detection avoidance

---

## macOS Default Browser

**UNCHANGED:** Your macOS default browser remains **Brave**.

**How to verify:**
```bash
# Check macOS default browser
defaults read com.apple.LaunchServices/com.apple.launchservices.secure LSHandlers | grep -A 4 http

# This setting is INDEPENDENT of Playwright configuration
# You can keep Brave as your default for personal use
```

**What happens:**
- Click link in email → Opens in Brave ✓
- Type URL in Spotlight → Opens in Brave ✓
- Playwright automation → Uses Chromium ✓

**Separation of concerns = best of both worlds**

---

## Future Considerations

### If Chromium Detection Increases

**Fallback Strategy:**
1. Try Firefox (different rendering engine)
2. Rotate Chromium versions
3. Add residential proxies
4. Use API-based CAPTCHA solving

### Monitoring

**Track success rates:**
```bash
# Check CAPTCHA solver metrics
python tools/account_creator.py metrics --browser chromium
python tools/account_creator.py metrics --browser firefox

# Compare detection rates
```

**Alert thresholds:**
- CAPTCHA success < 80% → Investigate
- Bot detection > 15% → Update stealth methods
- Multiple service failures → Consider browser switch

---

## Training & Documentation

**For Future Implementations:**

1. **Read this policy first** before writing Playwright code
2. **Default to Chromium** unless documented exception
3. **Test detection avoidance** on target services
4. **Document deviations** if using different browser

**Resources:**
- Technical rationale: `tools/BROWSER_SELECTION_RATIONALE.md`
- CAPTCHA research: `BRIEFS/recaptcha-solutions-research.md`
- Codex consensus: `registry/advice/codex/account-creator-skill/2025-10-20_architecture-consensus.md`

---

## Policy Enforcement

**Review Requirements:**

All Playwright implementations must:
1. Use Chromium as default browser
2. Include rationale if using different browser
3. Document bot detection success rates
4. Pass peer review before production

**Automated Checks:**
```bash
# Check for Brave executable paths in code
grep -r "Brave Browser.app" tools/ --include="*.py" --include="*.json"

# Should return NO results
# If found, must be documented exception or removed
```

---

## Summary

| Aspect | Configuration |
|--------|--------------|
| **Playwright Automation** | Chromium (always) |
| **macOS Default Browser** | Brave (unchanged) |
| **Personal Browsing** | Brave (for you) |
| **Bot Detection** | Chromium + stealth (optimal) |
| **CAPTCHA Solving** | Chromium (90% success) |
| **Testing** | Chromium (can use Firefox for comparison) |

**Golden Rule:** Chromium for robots, Brave for humans.

---

**Last Updated:** 2025-10-20
**Review Schedule:** Quarterly (check if detection methods change)
**Status:** ACTIVE - All implementations must comply
