# Browser Automation Guide

**Purpose:** Complete guide for browser automation in BuilderOS using direct Playwright library.

---

## Architecture

BuilderOS uses **direct Playwright Python library** as the primary browser automation tool, with additional fallback options.

### Primary: Direct Playwright Library

**Why Direct Library?**
- ✅ Full access to playwright-stealth for anti-detection
- ✅ playwright-recaptcha for CAPTCHA solving (~85-90% success)
- ✅ Complete control over timing and human behavior simulation
- ✅ Dynamic field detection (site-agnostic)
- ✅ All Playwright plugins and features available
- ✅ Production-grade reliability

**When to use:**
- Account creation and registration
- Complex multi-step automation
- Sites with bot detection
- CAPTCHA-protected forms
- Any serious browser automation

### Secondary: Playwright MCP Tools

**Why MCP Tools?**
- Fast for quick tasks
- Integrated with Claude Code
- Good for simple operations
- Interactive debugging

**When to use:**
- Quick page checks ({{ORCHESTRATOR_NAME}}, other agents)
- Simple screenshots
- One-off navigation
- Debugging cooperative sites
- **NOT for Bowser's complex automation**

### Fallback: SeleniumBase UC Mode

**Why SeleniumBase?**
- Undetected ChromeDriver (UC mode)
- Extreme anti-detection scenarios
- Last resort when Playwright stealth fails

**When to use:**
- Sites that detect even Playwright stealth (rare)
- Extremely aggressive bot protection
- Specific UC mode requirements

---

## Tool Selection Matrix

| Use Case | Tool | Reason |
|----------|------|--------|
| Account creation | Direct Playwright | Full stealth + CAPTCHA solving |
| Complex automation | Direct Playwright | Complete control and anti-detection |
| Form filling (anti-bot) | Direct Playwright | Human behavior simulation |
| CAPTCHA challenges | Direct Playwright | playwright-recaptcha integration |
| Multi-step workflows | Direct Playwright | Custom timing and logic |
| Quick screenshot | MCP Tools | Fast, simple task |
| Page inspection | MCP Tools | Interactive debugging |
| Extreme detection | SeleniumBase | UC mode fallback |

---

## Implementation Tools

### 1. Registration Automation Script (`tools/registration_automation.py`)
- **Primary tool** for browser automation in BuilderOS
- Direct Playwright library with full plugin access
- Built-in stealth mode (playwright-stealth)
- Human behavior simulation
- Dynamic field detection
- CAPTCHA solving (playwright-recaptcha)

### 2. Account Creator Skill v2.0 (`.claude/skills/account-creator/`)
- Orchestrates SimpleLogin + Strongbox + Bowser
- Uses registration_automation.py for browser work
- {{ORCHESTRATOR_NAME}} handles credentials, Bowser handles automation

### 3. Bowser (🎭 agent)
- Defaults to direct Playwright library
- Executes registration_automation.py script
- MCP tools available for simple tasks
- SeleniumBase fallback for extreme cases

### 4. Hybrid Browser Wrapper (`tools/hybrid_browser.py`)
- Legacy wrapper, kept for SeleniumBase fallback
- Not primary automation tool
- Used only when direct Playwright fails

---

## Usage Examples

### Primary: Direct Playwright Library

**Account Creation (Most Common):**
```bash
# Via Bowser
python3 {{CATALYST_ROOT}}/tools/registration_automation.py \
  https://github.com/signup \
  --email github.wandering432@alias.example.com \
  --password SecurePass123! \
  --username BuilderUser2024
```

**Features:**
- Stealth mode: ✅ automatic
- Human simulation: ✅ automatic
- CAPTCHA solving: ✅ automatic
- Dynamic fields: ✅ automatic
- Screenshots: ✅ automatic

**Visual Debugging:**
```bash
# Watch automation in browser window
python3 tools/registration_automation.py \
  https://site.com/signup \
  --email test@test.com \
  --password pass123
```

### Secondary: MCP Tools (Simple Tasks)

**Quick Screenshot ({{ORCHESTRATOR_NAME}} or other agents):**
```python
# Via MCP tools
mcp__playwright__browser_navigate("https://example.com")
mcp__playwright__browser_take_screenshot()
```

### Fallback: SeleniumBase

**Extreme Detection (Rarely Needed):**
```bash
# Via hybrid browser wrapper
python3 tools/hybrid_browser.py create-account \
  --url https://extreme-detection-site.com \
  --mode seleniumbase \
  --email test@test.com
```

---

## Stealth-Required Sites

These sites automatically trigger SeleniumBase stealth mode:

**Social media:**
- instagram.com
- facebook.com
- twitter.com / x.com
- linkedin.com
- tiktok.com

**E-commerce:**
- amazon.com

**Protection services:**
- cloudflare.com

**Forums:**
- reddit.com

---

## CAPTCHA Handling

### Playwright
- Uses `playwright-recaptcha` library
- Good for reCAPTCHA v2/v3
- ~90% success rate
- Best for cooperative sites

### SeleniumBase
- Built-in UC mode bypass
- Supports 2Captcha integration (requires API key)
- Best for challenging CAPTCHAs
- Handles reCAPTCHA v2/v3, hCaptcha, Turnstile

### Auto-Switching
Hybrid browser automatically switches to SeleniumBase when CAPTCHA detected.

---

## Integration with Account Creation

### Account Creation Workflow

**{{ORCHESTRATOR_NAME}} role:**
- Handles infrastructure (SimpleLogin for email aliases)
- Handles infrastructure (Strongbox for credential storage)

**🎭 Bowser role:**
- Website automation (form filling, CAPTCHA handling, browser interaction)
- Uses 🌐 browser-automation output style
- Uses hybrid browser strategy automatically

### Example Flow

1. **User:** "Create Instagram account"

2. **{{ORCHESTRATOR_NAME}}:**
   - Creates email alias via SimpleLogin API
   - Generates secure password
   - Delegates browser automation to 🎭 Bowser

3. **🎭 Bowser:**
   - Detects instagram.com → uses SeleniumBase (stealth mode)
   - Fills signup form
   - Handles CAPTCHA if present
   - Completes account creation

4. **{{ORCHESTRATOR_NAME}}:**
   - Stores credentials in Strongbox
   - Reports success to user

---

## Configuration

### Service-Specific Settings

Edit `tools/account_creator.py` or `tools/hybrid_browser.py` for service-specific configurations:

```python
STEALTH_SITES = [
    'instagram.com',
    'facebook.com',
    'twitter.com',
    'x.com',
    'linkedin.com',
    'tiktok.com',
    'amazon.com',
    'cloudflare.com',
    'reddit.com'
]
```

### Adding New Services

To add a new service that requires stealth mode:

1. Add domain to `STEALTH_SITES` list
2. Test signup flow
3. Adjust selectors/timing if needed

---

## Troubleshooting

### Bot Detection Issues

**Symptoms:** Site blocks automation, shows CAPTCHA, or rejects signup

**Solution:**
1. Verify site is in `STEALTH_SITES` list
2. Try forcing SeleniumBase mode
3. Check for recent site changes (selectors, flow)

### CAPTCHA Failures

**Symptoms:** CAPTCHA not solving automatically

**Solutions:**
1. **Playwright:** Verify `playwright-recaptcha` installed
2. **SeleniumBase:** Consider adding 2Captcha API key for difficult CAPTCHAs
3. **Manual intervention:** Implement human-in-the-loop for critical accounts

### Selector Not Found

**Symptoms:** Script fails to find form elements

**Solutions:**
1. Check site HTML (may have changed)
2. Update selectors in service config
3. Add wait time for dynamic content loading

---

## Best Practices

### 1. Start with Playwright
Default to Playwright MCP for new sites unless you know they have bot detection.

### 2. Use Auto-Selection
Let hybrid browser choose the best tool based on domain/service config.

### 3. Test in Stealth Mode First
For social media and protected sites, always test with SeleniumBase first.

### 4. Monitor Success Rates
Track which sites work with which tool to optimize configurations.

### 5. Human-in-the-Loop for Critical
For important accounts (production services), consider human verification step.

---

## Cost Analysis

- Playwright MCP: $0/year (included with Claude Code)
- SeleniumBase: $0/year (open source)
- 2Captcha (optional): ~$3/1000 CAPTCHAs
- **Total: $0-minimal depending on CAPTCHA volume**

---

*Browser Automation Guide - BuilderOS Documentation*
