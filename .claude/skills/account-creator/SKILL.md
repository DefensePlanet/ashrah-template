---
name: account-creator
description: "[DEPRECATED] Split into credential-creator ({{ORCHESTRATOR_NAME}}) and account-registration (Bowser) skills for better separation of concerns. See individual skills for current documentation."
allowed-tools:
  - Bash
  - Read
  - Task
metadata:
  version: "2.0.0-deprecated"
  status: "DEPRECATED - Use credential-creator + account-registration instead"
  replacement_skills:
    - "credential-creator: Generate email aliases and passwords ({{ORCHESTRATOR_NAME}})"
    - "account-registration: Browser automation for signup (Bowser)"
  last_updated: "2025-10-22"
---

# Account Creator Skill [DEPRECATED]

## ⚠️ DEPRECATION NOTICE

This skill has been **split into two separate skills** for better separation of concerns:

### 1. credential-creator ({{ORCHESTRATOR_NAME}}-owned)
**Purpose:** Generate credentials only
- Creates SimpleLogin email alias
- Generates Strongbox password
- Optional TOTP secrets
- **NO browser automation**

**Location:** `.claude/skills/credential-creator/SKILL.md`

**Use when:** You need credentials for manual signup or to provide to automation

### 2. account-registration (Bowser-owned)
**Purpose:** Browser automation only
- Takes credentials as input
- Executes registration_automation.py
- Handles stealth, CAPTCHA, human simulation
- **Requires credentials to be provided**

**Location:** `.claude/skills/account-registration/SKILL.md`

**Use when:** You want automated signup with existing credentials

## Why Split?

**Before (account-creator):**
- Mixed responsibilities: credentials AND automation
- {{ORCHESTRATOR_NAME}} and Bowser both involved
- Harder to use credentials without automation
- Harder to automate with existing credentials

**After (separated):**
- **credential-creator**: Single responsibility (credentials)
- **account-registration**: Single responsibility (browser work)
- Can use independently or together
- Clear ownership ({{ORCHESTRATOR_NAME}} vs Bowser)

## Migration Guide

### Old Workflow (account-creator)
```
User: "Create a GitHub account"
→ account-creator skill handles everything
```

### New Workflow (separated skills)
```
User: "Create a GitHub account"

1. {{ORCHESTRATOR_NAME}} invokes credential-creator
   → Email: github.wandering432@alias.example.com
   → Password: [Strongbox path]

2. {{ORCHESTRATOR_NAME}} delegates to Bowser with account-registration
   → Provides credentials to automation script

3. Reports success/failure
```

### For Credentials Only
```
User: "Create credentials for GitHub"
→ {{ORCHESTRATOR_NAME}} invokes credential-creator only
→ Returns credentials for manual use
```

### For Automation Only
```
User: "Register account with email@example.com"
→ Bowser invokes account-registration with provided credentials
→ No credential generation needed
```

## Original Documentation (Reference Only)

**The documentation below is preserved for reference but should not be used.**
**Use the new separated skills instead.**

---

# Account Creator Skill (Original)

## Purpose
Automate online account creation with enterprise-grade anti-detection:
1. Generate unique, **readable** email alias via SimpleLogin (e.g., `github.wandering432@alias.example.com`)
2. Create strong credentials
3. Use direct Playwright library with stealth mode for registration
4. Save everything securely to Strongbox

**Key Advantage:** Direct Playwright library provides full access to stealth plugins, CAPTCHA solving, and human behavior simulation - capabilities not available through MCP tools.

## Architecture: Direct Playwright Library

### Why Direct Library Over MCP?

**Playwright MCP Limitations:**
- ❌ No stealth plugins (playwright-stealth)
- ❌ No CAPTCHA solving libraries
- ❌ Limited fingerprint control
- ❌ No custom timing/behavior

**Direct Playwright Benefits:**
- ✅ Full playwright-stealth integration
- ✅ playwright-recaptcha for CAPTCHA solving
- ✅ Complete human behavior simulation
- ✅ Dynamic fingerprint randomization
- ✅ Custom timing and mouse movements

## Anti-Detection Features

### 1. Stealth Mode (playwright-stealth)
- Removes webdriver detection
- Randomizes browser fingerprints
- Mimics real Chrome/Chromium

### 2. Human Behavior Simulation
- **Mouse movements:** Curved paths, realistic speed
- **Typing speed:** 45 WPM average (human range)
- **Random pauses:** 0.5-2 seconds between actions
- **Typo correction:** 5% chance of typo + backspace correction
- **Scroll behavior:** Smooth scrolling to view form

### 3. Dynamic Field Detection
- Auto-discovers form fields across any site
- No hardcoded selectors needed
- Adapts to different form structures
- Tries multiple selector patterns

### 4. CAPTCHA Solving
- **reCAPTCHA v2/v3:** playwright-recaptcha library
- **Audio solving:** ~85-90% success rate
- **Free:** No API costs
- **Fallback:** Manual intervention if solving fails

## Workflow

### Standard Account Creation
```
User: "Create a GitHub account"

{{ORCHESTRATOR_NAME}} Actions:
1. ✅ Create SimpleLogin alias via API
   - Generates: github.wandering432@alias.example.com
   - Forwards to: {{USER_EMAIL}}
2. ✅ Generate strong password via Strongbox
3. ✅ Delegate to Bowser with registration script
   - Provides: email, password, username
   - Agent uses tools/registration_automation.py
4. ✅ Agent executes with stealth + human simulation
5. ✅ Returns success/failure status
6. ✅ {{ORCHESTRATOR_NAME}} confirms credentials saved
```

## Execution

### Step 1: {{ORCHESTRATOR_NAME}} Generates Credentials

```bash
cd {{CATALYST_ROOT}}
python3 tools/account_creator.py create \
  --service github \
  --purpose dev
```

**Output:**
- ✅ SimpleLogin alias: github.wandering432@alias.example.com
- ✅ Password saved to Strongbox: "GitHub - dev"
- ✅ Strongbox entry path returned

### Step 2: Delegate to Bowser

**Task Tool Invocation:**
```
subagent_type: 🎭 Bowser
description: Automate GitHub signup with stealth mode

prompt: |
  Execute GitHub account registration using direct Playwright library.

  IMPORTANT: Use tools/registration_automation.py (NOT MCP tools)

  Command to run:
  python3 {{CATALYST_ROOT}}/tools/registration_automation.py \
    https://github.com/signup \
    --email github.wandering432@alias.example.com \
    --password [password from Strongbox] \
    --username [generated username]

  This script includes:
  - playwright-stealth for anti-detection
  - Human behavior simulation (mouse, timing, typos)
  - Dynamic field detection (adapts to any site)
  - CAPTCHA solving with playwright-recaptcha

  Monitor output for:
  - ✅ SUCCESS or ❌ FAILED status
  - CAPTCHA detection/solving results
  - Screenshot paths for debugging
  - Email verification requirements

  Return detailed status including:
  - Registration success/failure
  - CAPTCHA encountered/solved
  - Error messages if any
  - Screenshot locations
```

### Step 3: Confirm and Report

**Success Response:**
```
✅ Account created successfully for GitHub

Email: github.wandering432@alias.example.com
Username: BuilderUser2024
Password: ••••••••••••••• (saved in Strongbox)
Strongbox Path: GitHub - dev

CAPTCHA: Detected and solved automatically
Verification: Email verification required

Next steps:
- Check github.wandering432@alias.example.com for verification email
  (forwards to {{USER_EMAIL}})
- Click verification link
- Login at github.com

Screenshots:
- /tmp/registration_start_1729622400.png
- /tmp/registration_end_1729622415.png
```

## Supported Sites

### Tested Services
The registration script uses dynamic detection and works on most sites:

- **GitHub** - Standard forms, reCAPTCHA v2
- **GitLab** - Standard forms
- **Shopify** - hCaptcha (requires manual intervention)
- **OpenAI** - Cloudflare Turnstile (challenging)
- **Most standard signup forms** - Auto-detects fields

### Site-Agnostic Design
The script doesn't require pre-configuration for each site:
- **Dynamic field detection** finds email/password/username fields
- **Multiple selector patterns** work across different frameworks
- **Adaptive submit detection** finds the right button
- **Generic CAPTCHA detection** works on any CAPTCHA type

## Configuration

### Human Behavior Settings
Edit `tools/registration_automation.py`:

```python
config = RegistrationConfig(
    headless=False,           # Visual mode for debugging
    typing_speed_wpm=45,      # Human typing speed
    mouse_movement_enabled=True,
    random_pauses_enabled=True,
    typo_correction_enabled=True,
    typo_rate=0.05           # 5% typo rate
)
```

### Stealth Settings
Already optimized for anti-detection:
- ✅ playwright-stealth applied to all pages
- ✅ navigator.webdriver removed
- ✅ Realistic viewport (1280x720)
- ✅ Random timing variations
- ✅ Human-like mouse movements

## Testing the Registration Script

### Manual Test
```bash
cd {{CATALYST_ROOT}}

# Test on a site (watch it work in browser)
python3 tools/registration_automation.py \
  https://example.com/signup \
  --email test@example.com \
  --password TestPass123! \
  --fullname "Test User"

# Check output:
# - ✅ SUCCESS or ❌ FAILED
# - Screenshots in /tmp/registration_*.png
# - CAPTCHA detection/solving results
```

### Debug Mode
Run with browser visible (default):
```bash
# Browser opens and you can watch automation
python3 tools/registration_automation.py \
  https://site.com/signup \
  --email test@test.com \
  --password pass123
```

### Headless Mode
```bash
# Run without browser UI (faster)
python3 tools/registration_automation.py \
  https://site.com/signup \
  --email test@test.com \
  --password pass123 \
  --headless
```

## Error Handling

### Common Issues

**1. CAPTCHA Solving Fails**
- **Cause:** playwright-recaptcha not installed or CAPTCHA too difficult
- **Solution:** Script will report CAPTCHA failure, credentials still saved for manual signup
- **Manual Intervention:** Use saved credentials from Strongbox to complete signup manually

**2. Form Fields Not Found**
- **Cause:** Unusual form structure or non-standard selectors
- **Solution:** Script takes screenshots, add custom selectors if needed
- **Enhancement:** Update `FIELD_PATTERNS` in DynamicFormDetector class

**3. Bot Detection Triggered**
- **Cause:** Site has aggressive anti-automation (Instagram, Facebook, etc.)
- **Solution:** Manual signup recommended for highly protected sites
- **Alternative:** Use SeleniumBase UC mode for most challenging sites

**4. Email Already Exists**
- **Cause:** Email alias was used before
- **Solution:** Create new alias and retry
```bash
python3 tools/account_creator.py create --service github --purpose dev-2
```

### Cleanup Failed Attempts

```bash
# Delete SimpleLogin alias if registration failed
python3 tools/simple_login_api.py list --service github
python3 tools/simple_login_api.py delete-alias --alias-id [ID]

# Remove Strongbox entry manually
# (Strongbox doesn't support deletion via CLI for safety)
```

## Integration with {{ORCHESTRATOR_NAME}} Orchestration

### Capsule-Aware Account Creation
When in a capsule, account purpose auto-set to capsule name:

```
[In capsule: ecommerce-store]
User: "Create a Shopify account"

{{ORCHESTRATOR_NAME}}:
- Service: shopify
- Purpose: ecommerce-store (from capsule context)
- Strongbox Path: Shopify - ecommerce-store
```

### Account Reuse Across Capsules
```
User: "Use the GitHub account from catalyst-mobile"

{{ORCHESTRATOR_NAME}}:
1. Retrieves credentials from Strongbox: GitHub - catalyst-mobile
2. Provides credentials for current task
3. No new account created
```

## Security & Privacy

### Credential Storage
- **Passwords:** Generated by Strongbox (32+ chars, secure random)
- **Storage:** Encrypted in Strongbox database
- **Access:** Requires master password (never stored)
- **Display:** Never shown in plain text (use •••••••••)

### Email Privacy
- **Aliases:** Real email never exposed to services
- **Forwarding:** All aliases forward to {{USER_EMAIL}}
- **Control:** Can disable/delete aliases anytime
- **Isolation:** Each service gets unique alias

### Browser Security
- **Stealth Mode:** Anti-detection without data leakage
- **Screenshots:** Saved to /tmp/ (review before sharing)
- **Credentials:** Never logged or exposed in browser console
- **Context Isolation:** Each registration uses fresh browser context

## Governance & Approvals

### No User Approval Required:
- Creating SimpleLogin aliases (reversible)
- Generating passwords in Strongbox (no external action)
- Running registration script (automated by Bowser)
- Taking screenshots for debugging

### User Approval Required:
- Deleting aliases or Strongbox entries
- Sharing credentials outside Catalyst
- Manual CAPTCHA solving (if automation fails)

### Privacy Protection:
- Passwords NEVER displayed (use ••••••••)
- Screenshots reviewed before sharing
- Credentials stay in Strongbox encrypted
- Browser closed after registration

## Metrics & Monitoring

### Success Tracking
```bash
# View created accounts
python3 tools/account_creator.py list

# Check specific account
python3 tools/account_creator.py info --service github --purpose dev

# Verify credentials work
python3 tools/account_creator.py verify --service github --purpose dev
```

### Registration Success Rates
Monitor via screenshots and logs:
- CAPTCHA encountered: Check `/tmp/registration_*.png`
- Success indicators: "✅ SUCCESS" in output
- Failure reasons: Error messages in output

## Future Enhancements

**Planned:**
1. **Email verification automation** - Auto-check inbox for verification links
2. **Phone number handling** - Integrate temp phone services if needed
3. **Enhanced CAPTCHA** - Add hCaptcha and Turnstile solving
4. **SeleniumBase fallback** - Switch to UC mode for difficult sites
5. **Success rate tracking** - Store registration attempts and outcomes
6. **Site-specific configs** - Pre-configured strategies for popular sites

**Experimental:**
- 2Captcha API integration for difficult CAPTCHAs (paid service)
- Residential proxy rotation for IP diversity
- Browser fingerprint randomization per attempt

## Troubleshooting

### "playwright-recaptcha not available"
```bash
pip3 install playwright-recaptcha
```

### "playwright-stealth not available"
```bash
pip3 install playwright-stealth
```

### Registration fails silently
- Check screenshots in /tmp/registration_*.png
- Look for error messages on page
- Try manual registration with saved credentials

### CAPTCHA not being solved
- Verify playwright-recaptcha installed
- Try running in visual mode (remove --headless)
- Manual intervention: complete CAPTCHA, credentials already saved

## Quick Reference

**Create Account (Full Automation):**
```bash
# 1. Create credentials
python3 tools/account_creator.py create --service github --purpose dev

# 2. Run registration (via Bowser)
python3 tools/registration_automation.py \
  https://github.com/signup \
  --email [alias from step 1] \
  --password [from Strongbox] \
  --username [generated]
```

**Manual Registration (Credentials Only):**
```bash
# Just create email + password, no browser automation
python3 tools/account_creator.py create --service newsite --purpose test
# Use credentials manually for signup
```

---

**End of Account Creator Skill - Version 2.0**

## Summary of Changes from v1.x

**v2.0 Improvements:**
- ✅ Switched to direct Playwright library (from MCP tools)
- ✅ Added playwright-stealth integration
- ✅ Implemented human behavior simulation
- ✅ Dynamic field detection (site-agnostic)
- ✅ Enhanced CAPTCHA solving
- ✅ Removed Penpot from stealth sites (manual signup completed)
- ✅ Simplified architecture ({{ORCHESTRATOR_NAME}} + Bowser)

**Breaking Changes:**
- Registration now uses `registration_automation.py` script
- Playwright MCP tools NO LONGER USED for registration
- Direct Bash execution of Python script by Bowser
