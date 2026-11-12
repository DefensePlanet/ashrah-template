---
name: account-login
description: Automate login to existing accounts using Strongbox credentials and browser automation with stealth mode and 2FA support
allowed-tools:
  - Bash
  - Read
metadata:
  version: "1.0.0"
  authority: "Bowser"
  execution: "Inline - no script files created"
  strongbox_cli: "tools/strongbox_cli.py"
  strongbox_access: "read-only"
  technology: "Direct Playwright library (playwright-stealth)"
  scope: "Login automation with existing credentials from Strongbox - dynamic field detection"
  related_skill: "account-registration (for new account creation)"
  last_updated: "2025-10-22"
---

# Account Login Skill

## Purpose
Automate browser-based login to existing accounts using:
1. **Credential retrieval** from Strongbox password manager
2. **Browser automation** with Playwright stealth mode
3. **2FA/TOTP support** using codes from Strongbox
4. **Human behavior simulation** for anti-detection
5. **Session management** for persistent logins

**Scope:** This skill handles **login automation** for existing accounts. For creating new accounts, use the `account-registration` skill.

## Trigger Keywords
- "log into [service]"
- "sign in to [service]"
- "login to [account]"
- "authenticate to [service]"
- "open [service] and login"

## Architecture

**Bowser uses direct Playwright Python library** with Strongbox integration:
- ✅ Read-only access to Strongbox (secure credential retrieval)
- ✅ Full playwright-stealth integration (anti-detection)
- ✅ Human behavior simulation (typing, mouse, pauses)
- ✅ TOTP/2FA code generation from Strongbox secrets
- ✅ Session persistence and management

## Workflow

### Standard Login Flow (Single Account)
```
User: "Log into GitHub"

Bowser Actions:
1. ✅ Retrieve credentials from Strongbox
   - Service: "GitHub"
   - Finds: "GitHub - dev" (only one)
   - Gets: email/username, password, TOTP secret from Strongbox
2. ✅ Navigate to login page
   - URL detection or manual specification
3. ✅ Fill credentials with human simulation
   - Email/username field
   - Password field (masked)
   - Typing delays and natural pauses
4. ✅ Handle 2FA if required
   - Generate TOTP code from Strongbox secret (stored with credential)
   - Enter 6-digit code with human timing
   - Verify code accepted
5. ✅ Verify successful login
   - Check for dashboard/profile URL
   - Verify logged-in state
6. ✅ Report status
   - Success: "Logged in successfully"
   - Failure: Error details + screenshots

Result:
- ✅ Logged into service
- ✅ Session active (browser stays open or cookies saved)
- ✅ Screenshots: /tmp/login_*.png
```

### Context-Aware Login Flow (Multiple Accounts)
```
User: "Log into Instagram for rawhide-organics"

Bowser Actions:
1. ✅ Parse context from request
   - Service: "Instagram"
   - Context: "rawhide-organics"
2. ✅ Retrieve specific credentials from Strongbox
   - Searches: "Instagram - rawhide-organics"
   - Gets: email, password, TOTP secret
3. ✅ Execute login automation
   - Navigate to Instagram login
   - Fill credentials
   - Handle 2FA with Strongbox TOTP
   - Verify success
4. ✅ Report status
   - "Logged into Instagram (rawhide-organics account)"

Alternative (Ambiguous Request):
User: "Log into Instagram"

Bowser:
1. Searches Strongbox for "instagram"
2. Finds multiple accounts
3. Asks: "Which Instagram account? (personal / rawhide-organics)"
4. Waits for user response
5. Proceeds with selected credential
```

## Execution

**Bowser executes login automation INLINE - no script files created.**

This skill is a **reusable workflow pattern** that works on ANY login screen dynamically.

### Inline Execution (Default)

**Bowser executes Playwright code directly via heredoc:**

```bash
cd {{CATALYST_ROOT}}

# Execute login automation inline
python3 << 'EOF'
import asyncio
import json
import subprocess
import time
from playwright.async_api import async_playwright
from playwright_stealth import stealth_async

async def login(service='github', context=None, url=None, headless=False):
    # Retrieve credentials from Strongbox (context-aware)
    cmd = ['python3', 'tools/strongbox_cli.py', 'get-credential', '--service', service, '--output', 'json']

    # Add context if multiple accounts exist (e.g., Instagram - rawhide-organics)
    if context:
        cmd.extend(['--context', context])
        print(f"🔍 Looking for {service} credentials with context: {context}")

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        print(f"❌ Failed to retrieve credentials for {service}")
        if context:
            print(f"   Try: tools/strongbox_cli.py list | grep -i {service}")
        return

    creds = json.loads(result.stdout)
    login_url = url or creds.get('login_url', f'https://{service}.com/login')

    print(f"✅ Using credential: {creds.get('title', service)}")

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=headless,
            args=['--disable-blink-features=AutomationControlled']
        )
        context = await browser.new_context(
            viewport={'width': 1280, 'height': 720},
            locale='en-US',
            timezone_id='America/New_York'
        )
        page = await context.new_page()
        await stealth_async(page)

        await page.screenshot(path='/tmp/login_start.png')

        # Navigate to login page
        await page.goto(login_url)

        # Dynamic field detection - works on any login form
        email_selectors = [
            'input[type="email"]',
            'input[name*="email" i]',
            'input[name*="username" i]',
            'input[name*="login" i]',
            'input[autocomplete="username"]'
        ]

        password_selectors = [
            'input[type="password"]',
            'input[name*="password" i]',
            'input[autocomplete="current-password"]'
        ]

        # Fill email/username
        for selector in email_selectors:
            try:
                await page.fill(selector, creds['email'], timeout=2000)
                print(f"✅ Filled email field: {selector}")
                break
            except:
                continue

        # Fill password
        for selector in password_selectors:
            try:
                await page.fill(selector, creds['password'], timeout=2000)
                print(f"✅ Filled password field: {selector}")
                break
            except:
                continue

        # Submit form
        await page.click('button[type="submit"], input[type="submit"]')
        await page.wait_for_load_state('networkidle', timeout=10000)

        # Handle 2FA with TOTP from Strongbox
        if 'totp_secret' in creds and await page.locator('input[name*="code" i]').count() > 0:
            print("🔐 2FA detected - generating TOTP code from Strongbox...")

            # Generate TOTP code from Strongbox secret
            import pyotp
            totp = pyotp.TOTP(creds['totp_secret'])
            code = totp.now()

            print(f"✅ Generated 6-digit code (expires in {30 - (int(time.time()) % 30)}s)")

            # Fill TOTP code field
            await page.fill('input[name*="code" i]', code)
            await page.click('button[type="submit"]')
            await page.wait_for_load_state('networkidle', timeout=10000)

            print("✅ 2FA code submitted")

        await page.screenshot(path='/tmp/login_end.png')

        # Verify login success
        if 'dashboard' in page.url or 'profile' in page.url or service in page.url:
            print(f"✅ Successfully logged into {service}")
        else:
            print(f"⚠️ Login status unclear - check screenshots")

        if not headless:
            print("Browser kept open for inspection...")
            await page.pause()  # Keep browser open

        await browser.close()

# Execute login - Examples:

# Single account (GitHub - only one)
asyncio.run(login(service='github', url='https://github.com/login', headless=False))

# Multiple accounts - specify context (Instagram - rawhide-organics)
# asyncio.run(login(service='instagram', context='rawhide-organics', headless=False))

# Let Bowser use defaults (login URL from Strongbox)
# asyncio.run(login(service='shopify', context='rawhide-organics'))
EOF
```

**What happens:**
1. ✅ **Context-aware credential retrieval** from Strongbox
   - Single account: Auto-selects "GitHub - dev"
   - Multiple accounts: Uses specified context "rawhide-organics"
2. ✅ Browser launches with stealth mode
3. ✅ Navigates to login URL (from Strongbox or specified)
4. ✅ **Dynamically detects** email and password fields (works on ANY site)
5. ✅ Fills credentials with human timing
6. ✅ **Handles 2FA automatically** if TOTP secret stored in Strongbox
   - Generates fresh 6-digit code
   - Enters with human timing
7. ✅ Verifies successful login
8. ✅ Takes screenshots for verification

**Benefits:**
- ✅ No script file clutter
- ✅ Works on ANY login screen
- ✅ Full flexibility for each service
- ✅ Immediate execution
- ✅ Easy to customize per-task

### When to Use This Skill

**Use inline execution for:**
- ✅ Logging into any service (GitHub, GitLab, Shopify, etc.)
- ✅ One-time logins
- ✅ Different login flows per service
- ✅ Custom session management needs

**This is NOT for:**
- ❌ Creating reusable script files
- ❌ Complex login workflows requiring separate tooling

## Strongbox Integration

### Credential Storage Format

**In Strongbox, credentials are organized with context in the title:**

```
Title: [Service] - [Context/Purpose]

Examples:
- "GitHub - dev" (single account, simple)
- "Instagram - rawhide-organics" (brand account)
- "Instagram - personal" (personal account)
- "Shopify - rawhide-organics" (e-commerce store)
- "OpenAI - personal" (API account)
```

**Full credential structure:**

```
Title: Instagram - rawhide-organics
Username: rawhide_organics@example.com
Password: ••••••••••••••
URL: https://instagram.com/accounts/login
Custom Fields:
  - totp_secret: BASE32TOTPSECRET (stored by Strongbox)
  - service_name: instagram
  - context: rawhide-organics
Notes: E-commerce brand account for Rawhide Organics
```

**TOTP/2FA Storage:**
- ✅ TOTP secrets stored directly in Strongbox with the credential
- ✅ Bowser retrieves and uses automatically
- ✅ No separate authenticator app needed
- ✅ Fresh 6-digit codes generated on-demand

### Context-Aware Credential Selection

**Single Account (Simple):**

```
User: "Log into GitHub"

Bowser:
1. Searches Strongbox for "github"
2. Finds: "GitHub - dev" (only one)
3. Uses it automatically
```

**Multiple Accounts (Context Required):**

```
User: "Log into Instagram for rawhide-organics"

Bowser:
1. Searches Strongbox for "instagram" + "rawhide-organics"
2. Finds: "Instagram - rawhide-organics"
3. Uses that specific credential
```

**Multiple Accounts (Ambiguous):**

```
User: "Log into Instagram"

Bowser:
1. Searches Strongbox for "instagram"
2. Finds multiple: "Instagram - personal", "Instagram - rawhide-organics"
3. Asks: "Which Instagram account? (personal / rawhide-organics)"
4. User specifies context
5. Uses selected credential
```

**Context Detection Patterns:**

Bowser looks for context in:
- ✅ Explicit mentions: "for rawhide-organics", "using personal account"
- ✅ Capsule context: If in rawhide-organics capsule, prefer that context
- ✅ Recent activity: Last used credential for that service
- ✅ User prompt: Ask when ambiguous

### Credential Retrieval

**Bowser uses strongbox_cli.py (read-only):**

```bash
# Single account - service only
python3 tools/strongbox_cli.py get-credential \
  --service github \
  --output json

# Multiple accounts - service + context
python3 tools/strongbox_cli.py get-credential \
  --service instagram \
  --context rawhide-organics \
  --output json

# Output includes TOTP secret:
{
  "title": "Instagram - rawhide-organics",
  "email": "rawhide_organics@example.com",
  "password": "SecurePassword123!",
  "totp_secret": "BASE32SECRET",
  "login_url": "https://instagram.com/accounts/login",
  "context": "rawhide-organics"
}
```

**Security:**
- ✅ Read-only access (Bowser cannot modify Strongbox)
- ✅ Passwords never logged or displayed
- ✅ TOTP secrets kept secure
- ✅ Fresh TOTP codes generated each time

### 2FA/TOTP Support

**If TOTP secret exists in Strongbox:**

```python
# Bowser automatically:
1. Retrieves TOTP secret from Strongbox
2. Generates current 6-digit code
3. Waits for 2FA prompt
4. Enters code with human timing
5. Verifies code accepted
```

**Supported 2FA types:**
- ✅ TOTP/Authenticator apps (Google Authenticator, Authy, etc.)
- ✅ Backup codes (if stored in Strongbox notes)
- ❌ SMS codes (requires manual input)
- ❌ Hardware keys (requires manual action)

## Login Detection Patterns

### Dynamic Form Detection

**Email/Username field patterns:**
```
input[type="email"]
input[name*="email" i]
input[name*="username" i]
input[id*="login" i]
input[autocomplete="username"]
input[autocomplete="email"]
```

**Password field patterns:**
```
input[type="password"]
input[name*="password" i]
input[autocomplete="current-password"]
```

**2FA code field patterns:**
```
input[name*="code" i]
input[name*="token" i]
input[name*="otp" i]
input[autocomplete="one-time-code"]
input[inputmode="numeric"]
```

**Benefits:**
- Works on unfamiliar sites
- No hardcoded selectors needed
- Adapts to framework changes
- Handles custom implementations

## Human Behavior Simulation

### Typing Behavior
- **Character delay:** 80-250ms per character (human range)
- **Method:** Character-by-character (no instant filling)
- **Variation:** Random delays within range
- **Typos:** 5% chance + immediate correction

### Pauses
- **Between fields:** 500-1500ms (reading/navigation time)
- **Before submit:** 900-2000ms (final review)
- **After 2FA prompt:** 800-1500ms (code retrieval time)

### Mouse Movements
- Curved paths to form fields
- 10-20 steps per movement
- Natural speed variation
- Click position randomization (±5px)

## Supported Services

### Common Services (Pre-configured URLs)

**Code repositories:**
- GitHub: https://github.com/login
- GitLab: https://gitlab.com/users/sign_in
- Bitbucket: https://bitbucket.org/account/signin

**Development platforms:**
- OpenAI: https://platform.openai.com/login
- Vercel: https://vercel.com/login
- Netlify: https://app.netlify.com/login

**E-commerce:**
- Shopify: https://accounts.shopify.com/login

**Social media:**
- Instagram: https://www.instagram.com/accounts/login
- Twitter/X: https://twitter.com/i/flow/login

### Service-Agnostic Design

The skill **doesn't require pre-configuration**:
- Tries multiple selector patterns per field
- Adapts to different CSS frameworks
- Works with custom login forms
- Handles dynamic content loading

**For new services:**
- Bowser executes the same inline pattern
- Just changes the service name and URL parameters
- Dynamic field detection adapts automatically

## Session Management

### Session Persistence

Bowser can manage sessions in several ways when executing inline:

**1. Keep Browser Open (Visual Mode)**
- Include `await page.pause()` before browser.close()
- Allows manual inspection and continued use
- Browser stays open until manually closed

**2. Save Cookies**
- Use `context.storage_state(path='session.json')` to save
- Stores cookies and local storage
- Can be reloaded in future executions

**3. Reuse Saved Session**
- Load with `browser.new_context(storage_state='session.json')`
- Skip login if session still valid
- Validate session before using

### Session Validation

**Before attempting login, check if session valid:**
```python
1. Load saved cookies
2. Navigate to dashboard/profile page
3. Check for logged-in indicators
4. If valid: Skip login, return success
5. If invalid: Proceed with login flow
```

## Error Handling

### Common Issues

**1. Credentials Not Found in Strongbox**
```
❌ Error: No credentials found for service "github"

Solution:
- Check service name matches Strongbox entry
- Use strongbox_cli.py list to see available services
- Create credentials if missing
```

**2. Login Form Not Detected**
```
❌ Error: Email field not found on login page

Solution:
- Check login URL is correct
- Review screenshot: /tmp/login_start_*.png
- May need custom selectors for unusual forms
```

**3. 2FA Code Rejected**
```
❌ Error: 2FA code invalid or expired

Solution:
- Check TOTP secret in Strongbox is correct
- Time sync issues (rare on macOS)
- Try manual code entry to verify
```

**4. Already Logged In**
```
✅ Success: Already logged in (session valid)

No action needed - session reused
```

### Error Screenshots

Automatically captured at:
```
/tmp/login_start_[timestamp].png    # Initial login page
/tmp/login_2fa_[timestamp].png      # 2FA prompt (if encountered)
/tmp/login_end_[timestamp].png      # After login attempt
/tmp/login_error_[timestamp].png    # If error occurred
```

**View screenshots:**
```bash
ls -lt /tmp/login_*.png
open /tmp/login_error_*.png
```

## Configuration

### Human Behavior Tuning

Create custom config in script if needed:

```python
config = LoginConfig(
    headless=False,                      # Visual/headless mode

    # Character-based timing
    char_delay_min=80,                   # 80ms minimum per character
    char_delay_max=250,                  # 250ms maximum per character

    # Pause ranges
    pause_between_fields_min=500,        # 500ms min between fields
    pause_between_fields_max=1500,       # 1500ms max between fields
    pause_before_submit_min=900,         # 900ms min before submit
    pause_before_submit_max=2000,        # 2000ms max before submit

    # Behavior simulation
    mouse_movement_enabled=True,         # Curved mouse paths
    random_pauses_enabled=True,          # Natural thinking pauses
    typo_correction_enabled=True,        # Realistic typos
    typo_rate=0.05,                      # 5% chance per word

    # Session management
    keep_browser_open=False,             # Close after login
    save_cookies=False,                  # Don't save by default
    session_timeout=3600                 # 1 hour session validity
)
```

## Output Interpretation

### Success Indicators

```
✅ SUCCESS - Logged in to GitHub
Session active, dashboard loaded
```

**Means:**
- Login successful
- Authenticated session established
- Browser on logged-in page

**Next steps:**
- Use the open browser session
- Or save cookies for later reuse

### Failure Indicators

```
❌ FAILED - Login unsuccessful
Error: Invalid password
```

**Means:**
- Login attempt failed
- Check credentials in Strongbox
- Review error screenshot

**Next steps:**
- Verify credentials correct
- Update Strongbox if password changed
- Check if account locked/2FA required

### Session Reuse

```
✅ SUCCESS - Session already valid
Skipped login (using saved cookies)
```

**Means:**
- Previous session still active
- No login needed
- Saved time and detection risk

## Best Practices

### Security
- **Never log passwords** - Script masks all credential output
- **Review screenshots** - May contain sensitive data
- **Clean up /tmp/** - Delete old screenshots periodically
- **Read-only Strongbox** - Bowser cannot modify credentials
- **TOTP secrets secured** - Never displayed or logged

### Testing New Services
1. **Visual mode first** - Watch login work
2. **Check screenshots** - Verify field detection
3. **Monitor console output** - Look for errors
4. **Verify result** - Check you're actually logged in

### Production Use
1. **Headless mode** - Faster execution
2. **Session reuse** - Skip login when possible
3. **Error handling** - Capture failures for retry
4. **Rate limiting** - Don't hammer login endpoints

### Credential Management
- **Consistent naming** - Use "Service - purpose" format
- **Add TOTP secrets** - Enable 2FA automation
- **Include login URL** - Speeds up automation
- **Document purposes** - Dev, prod, testing, etc.

## Advanced Usage

### Custom Login Scripts (One-Off)

**For unusual login flows, execute inline:**

```bash
python3 << 'EOF'
import asyncio
from playwright.async_api import async_playwright
from playwright_stealth import stealth_async
import subprocess
import json

async def main():
    # Get credentials from Strongbox
    result = subprocess.run([
        'python3', 'tools/strongbox_cli.py',
        'get-credential', '--service', 'github', '--output', 'json'
    ], capture_output=True, text=True)
    creds = json.loads(result.stdout)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(
            viewport={'width': 1280, 'height': 720},
            locale='en-US',
            timezone_id='America/New_York'
        )
        page = await context.new_page()
        await stealth_async(page)

        # Custom login flow for this specific service
        await page.goto('https://example.com/login')

        # Your specific logic here
        # ... multi-step login
        # ... custom 2FA handling
        # ... session verification

        await browser.close()

asyncio.run(main())
EOF
```

### Batch Login Operations

```python
# Login to multiple services
services = ['github', 'gitlab', 'bitbucket']

for service in services:
    # Login to each service
    # Save session for each
    # Add delays between attempts (rate limiting)
    pass
```

### Session Cookie Export

**Bowser can save session cookies inline:**

```python
# Save session state after login
await context.storage_state(path='github_cookies.json')

# Cookies can then be used in:
# - curl commands
# - Python requests library
# - Other automation tools
```

## Integration with Other Skills

### With account-registration

**Full lifecycle automation:**

```
1. User: "Create and login to GitHub"

2. Bowser (account-registration skill):
   - Creates new account
   - Verifies email if needed

3. Bowser (account-login skill):
   - Retrieves saved credentials
   - Logs into new account
   - Verifies access
```

### With credential-creator

**{{ORCHESTRATOR_NAME}} creates, Bowser uses:**

```
1. {{ORCHESTRATOR_NAME}} (credential-creator):
   - Creates SimpleLogin alias
   - Generates Strongbox password
   - Stores in Strongbox

2. Bowser (account-registration):
   - Uses credentials to create account

3. Bowser (account-login):
   - Uses same credentials to login later
```

## Troubleshooting

### "Credentials not found"
```bash
# List available services in Strongbox
python3 tools/strongbox_cli.py list

# Check specific service
python3 tools/strongbox_cli.py get-credential \
  --service github \
  --output json
```

### "2FA code invalid"
```bash
# Generate TOTP code manually to test
python3 tools/strongbox_cli.py generate-totp \
  --service github

# Verify the code works on the website
```

### Login fails silently
- Check `/tmp/login_*.png` screenshots
- Look for error messages on page
- Verify credentials in Strongbox are current
- Try manual login to test account status

### Browser won't launch
```bash
# Install Playwright browsers
playwright install chromium

# Or via Python
python3 -m playwright install chromium
```

## Quick Reference

**Bowser executes login automation inline - see full example in Execution section above.**

**Key workflow:**
1. Bowser retrieves credentials from Strongbox
2. Executes Playwright code inline via heredoc
3. Dynamically detects login form fields
4. Fills credentials with human behavior
5. Handles 2FA if TOTP secret configured
6. Verifies successful login

**Parameters to customize:**
- `service='github'` - Service name in Strongbox
- `url='https://github.com/login'` - Login page URL
- `headless=False` - Visual or headless mode

**Check screenshots:**
```bash
ls -lt /tmp/login_*.png
open /tmp/login_error_*.png
```

**Retrieve credentials manually:**
```bash
python3 tools/strongbox_cli.py get-credential \
  --service github \
  --output json
```

---

## Relationship to Other Skills

**credential-creator** - {{ORCHESTRATOR_NAME}} generates credentials and stores in Strongbox
**account-registration** - Bowser creates new accounts with credentials
**account-login** (this skill) - Bowser logs into existing accounts from Strongbox

Complete automation workflow: create → register → login

## Version History

- **v1.0.0** (2025-10-22) - Initial release with Strongbox integration, 2FA support, session management

---

**End of Account Login Skill**
