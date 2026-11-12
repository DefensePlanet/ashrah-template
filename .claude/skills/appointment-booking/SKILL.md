---
name: appointment-booking
description: Automate booking appointments (haircuts, restaurants, services) using privacy-preserving defaults with Strongbox credential reuse and SimpleLogin aliases
allowed-tools:
  - Bash
  - Read
metadata:
  version: "1.0.0"
  authority: "Bowser"
  execution: "Inline Playwright - no script files created"
  strongbox_cli: "tools/strongbox_cli.py"
  simple_login_api: "tools/simple_login_api.py"
  technology: "Direct Playwright library (playwright-stealth)"
  scope: "Any appointment/booking automation with privacy-first defaults"
  related_skills:
    - "account-login (for sites requiring login)"
    - "credential-creator (for new account creation if needed)"
  last_updated: "2025-01-21"
---

# Appointment Booking Skill

## Purpose
Automate booking appointments on any website using:
1. **Privacy-first defaults** - Aliases and pseudonyms by default
2. **Strongbox credential reuse** - Use existing account if available
3. **SimpleLogin email aliases** - Never expose real email
4. **Dynamic form detection** - Works on any booking site
5. **Confirmation capture** - Screenshot + calendar sync

**Scope:** Haircuts, restaurants, services, medical (non-sensitive), car maintenance, etc.

**NOT for:** Legal/government appointments requiring verified identity, medical procedures requiring legal name, financial services.

## Privacy Philosophy

**Default: Privacy-Preserving**

| Field | Default Behavior |
|-------|-----------------|
| Email | SimpleLogin alias (forwards to {{USER_EMAIL}}) |
| Phone | Google Voice or secondary number |
| Name | First name only, or pseudonym |
| Address | Not provided unless required |

**Exception: Real Info Required**

Some bookings legitimately need real info (insurance, legal). When detected:
1. Bowser pauses and asks: "This booking appears to require [real name/insurance/ID]. Proceed with real info or skip?"
2. User confirms before real info is used
3. Real info pulled from separate "Real Identity" Strongbox entry

## Trigger Keywords
- "book [appointment type] at [location]"
- "schedule [service] for [date/time]"
- "make a reservation at [restaurant]"
- "book my haircut"
- "schedule oil change at [shop]"

## Workflow

### Standard Booking Flow

```
User: "Book my haircut at Floyd's"

Bowser Actions:
1. Check Strongbox for existing "Floyd's" or "Floyd's Barbershop" account
   → Found: Use existing credentials
   → Not found: Continue as guest or create account

2. Navigate to booking site
   - Try known URLs first (floyds99.com/book)
   - Or search and navigate

3. Select service + provider (if applicable)
   - "Men's haircut"
   - Preferred stylist (if stored in Strongbox notes)

4. Select date/time
   - Next available by default
   - Or specific date if requested

5. Fill booking form (PRIVACY DEFAULTS)
   - Email: Use SimpleLogin alias (or existing account email)
   - Phone: Secondary number from Strongbox
   - Name: First name only ("{{USER_NAME}}") unless full required
   - Skip optional fields

6. Confirm booking
   - Screenshot confirmation page
   - Extract confirmation number
   - Extract date/time/location

7. Report to user
   - "Booked: Haircut at Floyd's, Jan 25 @ 2pm"
   - "Confirmation #: ABC123"
   - Screenshot: /tmp/booking_confirmation_*.png
```

### Credential Lookup Logic

```
User: "Book at [Service]"

Bowser:
1. Search Strongbox for "[Service]" entries
   - Exact match: "Floyd's Barbershop"
   - Partial match: "Floyd's"
   - Category match: entries tagged "haircut" or "barbershop"

2. If found:
   - Use stored email/username
   - Use stored password (if login required)
   - Use stored phone (if available)
   - Check notes for preferences (stylist name, usual service)

3. If NOT found:
   - Proceed as guest booking
   - Use SimpleLogin alias for email
   - Use privacy defaults for other fields
   - Optionally: Create account after successful booking
```

## Execution

**Bowser executes booking automation INLINE - no script files created.**

### Inline Execution Pattern

```bash
cd {{CATALYST_ROOT}}

python3 << 'EOF'
import asyncio
import json
import subprocess
import time
from datetime import datetime
from playwright.async_api import async_playwright
from playwright_stealth import stealth_async

async def book_appointment(
    service_name: str,
    booking_url: str = None,
    service_type: str = None,
    preferred_date: str = None,
    preferred_time: str = None,
    headless: bool = False
):
    """
    Generic appointment booking with privacy-first defaults.

    Args:
        service_name: Name of service (e.g., "Floyd's Barbershop")
        booking_url: Direct URL to booking page (optional)
        service_type: Type of service to book (e.g., "Men's haircut")
        preferred_date: Preferred date (e.g., "next Saturday")
        preferred_time: Preferred time (e.g., "afternoon", "2pm")
        headless: Run without visible browser
    """

    # === STEP 1: Check Strongbox for existing credentials ===
    print(f"🔍 Checking Strongbox for '{service_name}' credentials...")

    credential = None
    try:
        result = subprocess.run([
            'python3', 'tools/strongbox_cli.py',
            'get-credential', '--service', service_name, '--output', 'json'
        ], capture_output=True, text=True, cwd='{{CATALYST_ROOT}}')

        if result.returncode == 0:
            credential = json.loads(result.stdout)
            print(f"✅ Found existing account: {credential.get('title', service_name)}")
        else:
            print(f"ℹ️  No existing account found - using guest booking with privacy defaults")
    except Exception as e:
        print(f"⚠️  Strongbox lookup failed: {e}")

    # === STEP 2: Get privacy profile (SimpleLogin alias, secondary phone) ===
    privacy_profile = {
        'email': None,
        'phone': None,
        'first_name': '{{USER_NAME}}',  # First name only by default
        'full_name': None,   # Only if explicitly needed
    }

    if credential:
        # Use existing account info
        privacy_profile['email'] = credential.get('email') or credential.get('username')
        privacy_profile['phone'] = credential.get('phone')
    else:
        # Create new SimpleLogin alias for this booking
        try:
            alias_result = subprocess.run([
                'python3', 'tools/simple_login_api.py',
                'create-alias', '--prefix', service_name.lower().replace(' ', '-').replace("'", '')
            ], capture_output=True, text=True, cwd='{{CATALYST_ROOT}}')

            if alias_result.returncode == 0:
                alias_data = json.loads(alias_result.stdout)
                privacy_profile['email'] = alias_data.get('email')
                print(f"✅ Created SimpleLogin alias: {privacy_profile['email']}")
        except Exception as e:
            print(f"⚠️  Could not create alias, will need manual email entry: {e}")

        # Get secondary phone from Strongbox "Privacy Profile" entry
        try:
            phone_result = subprocess.run([
                'python3', 'tools/strongbox_cli.py',
                'get-credential', '--service', 'Privacy Profile', '--output', 'json'
            ], capture_output=True, text=True, cwd='{{CATALYST_ROOT}}')

            if phone_result.returncode == 0:
                profile = json.loads(phone_result.stdout)
                privacy_profile['phone'] = profile.get('phone')
        except:
            pass

    # === STEP 3: Launch browser and navigate ===
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=headless,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-dev-shm-usage',
                '--no-sandbox'
            ]
        )
        context = await browser.new_context(
            viewport={'width': 1280, 'height': 720},
            locale='en-US',
            timezone_id='America/New_York'
        )
        page = await context.new_page()
        await stealth_async(page)

        # Take initial screenshot
        await page.screenshot(path='/tmp/booking_start.png')
        print(f"📸 Screenshot: /tmp/booking_start.png")

        # Navigate to booking page
        if booking_url:
            print(f"🌐 Navigating to {booking_url}")
            await page.goto(booking_url, wait_until='networkidle', timeout=30000)
        else:
            # Search for booking page
            search_url = f"https://www.google.com/search?q={service_name}+book+appointment"
            print(f"🔍 Searching for booking page...")
            await page.goto(search_url)
            # Would need logic to find and click booking link

        await asyncio.sleep(3)  # Let page settle

        # === STEP 4: Login if credentials exist ===
        if credential and credential.get('password'):
            print("🔐 Attempting login with existing credentials...")
            # Dynamic login detection (same as account-login skill)
            login_selectors = [
                'a:has-text("Sign in")', 'a:has-text("Log in")',
                'button:has-text("Sign in")', 'button:has-text("Log in")'
            ]
            for selector in login_selectors:
                try:
                    login_link = await page.query_selector(selector)
                    if login_link and await login_link.is_visible():
                        await login_link.click()
                        await asyncio.sleep(2)
                        break
                except:
                    continue

            # Fill login form
            email_selectors = ['input[type="email"]', 'input[name*="email" i]', 'input[name*="username" i]']
            password_selectors = ['input[type="password"]']

            for selector in email_selectors:
                try:
                    await page.fill(selector, privacy_profile['email'], timeout=2000)
                    break
                except:
                    continue

            for selector in password_selectors:
                try:
                    await page.fill(selector, credential['password'], timeout=2000)
                    break
                except:
                    continue

            # Submit login
            try:
                await page.click('button[type="submit"]')
                await asyncio.sleep(3)
            except:
                pass

        # === STEP 5: Fill booking form (PRIVACY DEFAULTS) ===
        print("📝 Filling booking form with privacy defaults...")

        # Dynamic form field detection
        form_fields = {
            'email': ['input[type="email"]', 'input[name*="email" i]', 'input[id*="email" i]'],
            'phone': ['input[type="tel"]', 'input[name*="phone" i]', 'input[id*="phone" i]'],
            'first_name': ['input[name*="first" i]', 'input[id*="first" i]', 'input[placeholder*="first" i]'],
            'last_name': ['input[name*="last" i]', 'input[id*="last" i]', 'input[placeholder*="last" i]'],
            'name': ['input[name*="name" i]:not([name*="last"]):not([name*="first"])', 'input[id*="name" i]'],
        }

        # Fill email (always use alias)
        if privacy_profile['email']:
            for selector in form_fields['email']:
                try:
                    field = await page.query_selector(selector)
                    if field and await field.is_visible():
                        await page.fill(selector, privacy_profile['email'])
                        print(f"  ✅ Email: {privacy_profile['email']}")
                        break
                except:
                    continue

        # Fill phone (secondary number)
        if privacy_profile['phone']:
            for selector in form_fields['phone']:
                try:
                    field = await page.query_selector(selector)
                    if field and await field.is_visible():
                        await page.fill(selector, privacy_profile['phone'])
                        print(f"  ✅ Phone: {privacy_profile['phone'][:3]}***")
                        break
                except:
                    continue

        # Fill name (first name only by default)
        for selector in form_fields['first_name']:
            try:
                field = await page.query_selector(selector)
                if field and await field.is_visible():
                    await page.fill(selector, privacy_profile['first_name'])
                    print(f"  ✅ First name: {privacy_profile['first_name']}")
                    break
            except:
                continue

        # Last name - leave blank or use initial if required
        for selector in form_fields['last_name']:
            try:
                field = await page.query_selector(selector)
                if field and await field.is_visible():
                    # Check if required
                    is_required = await field.get_attribute('required')
                    if is_required:
                        await page.fill(selector, 'L')  # Just initial
                        print(f"  ✅ Last name: L (initial only - required field)")
                    break
            except:
                continue

        # Take screenshot of filled form
        await page.screenshot(path='/tmp/booking_form_filled.png')

        # === STEP 6: Select date/time (placeholder - site-specific) ===
        print("📅 Date/time selection would happen here...")
        print("   (Site-specific logic needed - pausing for manual selection)")

        # === STEP 7: Confirmation ===
        await page.screenshot(path='/tmp/booking_confirmation.png')

        # Keep browser open for manual completion
        if not headless:
            print("\n🖱️  Browser kept open for manual date/time selection and confirmation.")
            print("   Close browser when done, or press Ctrl+C to exit.")
            await page.pause()

        await browser.close()

        return {
            'status': 'form_filled',
            'service': service_name,
            'email_used': privacy_profile['email'],
            'screenshots': [
                '/tmp/booking_start.png',
                '/tmp/booking_form_filled.png',
                '/tmp/booking_confirmation.png'
            ]
        }

# === EXECUTE ===
# Example: Book haircut at Floyd's
asyncio.run(book_appointment(
    service_name="Floyd's Barbershop",
    booking_url="https://www.floyds99.com/book-now/",  # Or None to search
    service_type="Men's haircut",
    headless=False  # Visual mode for debugging
))
EOF
```

## Privacy Profile Setup

### Required Strongbox Entry: "Privacy Profile"

Create a Strongbox entry with secondary contact info:

```
Title: Privacy Profile
Username: [not used]
Password: [not used]
Custom Fields:
  - phone: [Google Voice or secondary number]
  - first_name: {{USER_NAME}}
  - city: [City for location-based bookings]
Notes: Default privacy info for appointment bookings
```

### Per-Service Preferences

Store preferences in Strongbox entry notes:

```
Title: Floyd's Barbershop
Username: floyds.booking123@alias.example.com
Password: [if account exists]
URL: https://www.floyds99.com
Custom Fields:
  - phone: [number used for this service]
Notes:
  Preferred stylist: [Name]
  Usual service: Men's haircut
  Location: Downtown
```

## Real Info Detection

**Bowser pauses when detecting fields that likely require real info:**

| Detected Field | Action |
|----------------|--------|
| Insurance ID | PAUSE - Ask user |
| SSN / Tax ID | REFUSE - Not automated |
| Driver's License | PAUSE - Ask user |
| Legal Name (explicit) | PAUSE - Ask user |
| Date of Birth (medical) | PAUSE - Ask user |
| Address (required, not optional) | PAUSE - Ask user |

**Detection patterns:**
```python
sensitive_patterns = [
    'insurance', 'policy', 'member id',
    'ssn', 'social security', 'tax id',
    'driver', 'license', 'id number',
    'legal name', 'full legal',
    'date of birth', 'dob', 'birthday',
    'street address', 'mailing address'
]

# If any field label matches, pause and ask
```

## Service-Specific Configurations

### Haircuts / Barbershops

**Common platforms:** Booksy, Vagaro, Square Appointments, Boulevard

```python
haircut_config = {
    'service_type_keywords': ['haircut', 'cut', 'trim', 'fade', 'buzz'],
    'fields_needed': ['email', 'phone', 'first_name'],
    'fields_skip': ['last_name', 'address', 'birthday'],
    'privacy_level': 'high'  # First name only
}
```

### Restaurants

**Common platforms:** OpenTable, Resy, Yelp Reservations

```python
restaurant_config = {
    'fields_needed': ['email', 'phone', 'name', 'party_size'],
    'fields_skip': ['occasion', 'special_requests'],  # Optional
    'privacy_level': 'medium'  # First name usually fine
}
```

### Medical (Non-Sensitive)

**For:** Eye exams, dental cleanings, general checkups

```python
medical_config = {
    'fields_needed': ['email', 'phone', 'full_name', 'dob'],
    'fields_skip': [],
    'privacy_level': 'low',  # May need real info
    'pause_for_confirmation': True  # Ask before submitting
}
```

## Calendar Integration

After successful booking, optionally add to Apple Calendar:

```bash
# Via AppleScript
osascript << 'APPLESCRIPT'
tell application "Calendar"
    tell calendar "Personal"
        make new event with properties {
            summary: "Haircut at Floyd's",
            start date: date "January 25, 2025 2:00 PM",
            end date: date "January 25, 2025 3:00 PM",
            location: "Floyd's Barbershop, 123 Main St"
        }
    end tell
end tell
APPLESCRIPT
```

## Error Handling

### Common Issues

**1. No booking URL found**
```
⚠️ Could not find booking page for [service]
→ Ask user for direct URL
→ Or search and present options
```

**2. Login required but no credentials**
```
ℹ️ This site requires an account to book
→ Proceed as guest if possible
→ Or create account first (credential-creator + account-registration)
```

**3. Booking form not detected**
```
⚠️ Could not detect booking form fields
→ Take screenshot for user
→ Pause for manual completion
```

**4. Date/time selection too complex**
```
ℹ️ Date picker requires manual selection
→ Fill other fields automatically
→ Pause for user to select date/time
→ Continue with confirmation after
```

## Output

### Success
```
✅ BOOKING COMPLETE

Service: Floyd's Barbershop
Date: Saturday, January 25, 2025
Time: 2:00 PM
Confirmation #: ABC123456

Email used: floyds.booking123@alias.example.com (alias)
Phone used: ***-***-7890 (secondary)

📸 Screenshots:
  - /tmp/booking_confirmation.png

📅 Added to Calendar: Yes
```

### Partial (Manual Completion Needed)
```
⚠️ BOOKING PARTIALLY COMPLETE

Service: Floyd's Barbershop
Form filled with privacy defaults
Browser kept open for date/time selection

📸 Screenshots:
  - /tmp/booking_form_filled.png

Next: Select date/time and confirm booking
```

## Quick Reference

**Book with existing account:**
```
"Book my haircut at Floyd's"
→ Checks Strongbox for Floyd's credentials
→ Uses existing email/phone if found
→ Fills form and navigates to date selection
```

**Book as guest (privacy mode):**
```
"Book a table at [new restaurant]"
→ Creates SimpleLogin alias
→ Uses secondary phone
→ First name only
→ Skips optional fields
```

**Book with real info (when required):**
```
"Book dentist appointment at [clinic]"
→ Detects medical booking
→ Pauses: "This may require real info. Use real name and DOB?"
→ User confirms
→ Proceeds with real info from "Real Identity" Strongbox entry
```

---

## Privacy.com Virtual Card Management (UI Automation)

**Privacy.com does not offer consumer API access.** Bowser automates the web interface instead.

### Capabilities

| Action | Method |
|--------|--------|
| Create merchant-locked card | UI automation |
| Create single-use card | UI automation |
| Look up existing card | UI automation |
| Get card details (number, expiry, CVV) | UI automation → Strongbox |
| Pause/close card | UI automation |

### Workflow: Auto-Create Card for Booking

```
User: "Book haircut at Floyd's"

Bowser:
1. Check Strongbox for existing "Privacy - Floyd's" card
   → Found: Use stored card details
   → Not found: Continue to step 2

2. Log into Privacy.com via account-login skill
   - Credentials from Strongbox "Privacy.com" entry

3. Create new merchant-locked card
   - Navigate to "New Card"
   - Select "Merchant Lock"
   - Set merchant name: "Floyd's 99 Barbershop"
   - Set optional spending limit
   - Create card

4. Extract card details from UI
   - Card number
   - Expiry date
   - CVV

5. Store in Strongbox
   - Title: "Privacy - Floyd's Barbershop"
   - Card Number: [extracted]
   - Custom Fields: expiry, cvv, merchant, spend_limit

6. Use card for booking payment
```

### Inline Execution Pattern

```python
async def create_privacy_card(
    merchant_name: str,
    card_type: str = "merchant_locked",  # or "single_use", "category_locked"
    spend_limit: float = None,
    headless: bool = False
):
    """
    Create a Privacy.com virtual card via UI automation.

    Args:
        merchant_name: Name to lock card to (e.g., "Floyd's Barbershop")
        card_type: "merchant_locked", "single_use", or "category_locked"
        spend_limit: Optional spending limit in dollars
        headless: Run without visible browser

    Returns:
        dict with card_number, expiry, cvv, or None if failed
    """

    # === STEP 1: Get Privacy.com credentials from Strongbox ===
    credential = get_strongbox_credential("Privacy.com")
    if not credential:
        print("❌ Privacy.com credentials not found in Strongbox")
        return None

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=headless)
        context = await browser.new_context()
        page = await context.new_page()
        await stealth_async(page)

        # === STEP 2: Login to Privacy.com ===
        print("🔐 Logging into Privacy.com...")
        await page.goto("https://app.privacy.com/login")
        await page.fill('input[name="email"]', credential['email'])
        await page.fill('input[type="password"]', credential['password'])
        await page.click('button[type="submit"]')
        await page.wait_for_load_state('networkidle')

        # Handle 2FA if needed (may need manual intervention)
        if "verify" in page.url.lower() or await page.query_selector('text=verification'):
            print("⚠️ 2FA required - pausing for manual entry...")
            await page.pause()

        # === STEP 3: Navigate to card creation ===
        print(f"💳 Creating {card_type} card for '{merchant_name}'...")
        await page.click('button:has-text("New Card")')
        await asyncio.sleep(2)

        # Select card type
        if card_type == "merchant_locked":
            await page.click('text=Merchant Locked')
        elif card_type == "single_use":
            await page.click('text=Single Use')
        elif card_type == "category_locked":
            await page.click('text=Category Locked')

        await asyncio.sleep(1)

        # Set merchant name for merchant-locked cards
        if card_type == "merchant_locked":
            await page.fill('input[placeholder*="merchant" i]', merchant_name)

        # Set spending limit if specified
        if spend_limit:
            await page.fill('input[placeholder*="limit" i]', str(int(spend_limit)))

        # Create the card
        await page.click('button:has-text("Create Card")')
        await page.wait_for_load_state('networkidle')
        await asyncio.sleep(3)

        # === STEP 4: Extract card details ===
        print("📋 Extracting card details...")

        card_details = {
            'card_number': None,
            'expiry': None,
            'cvv': None,
            'merchant': merchant_name,
            'card_type': card_type
        }

        # Look for card number display (Privacy.com shows it after creation)
        # Pattern: XXXX XXXX XXXX XXXX
        card_number_el = await page.query_selector('[data-testid="card-number"], .card-number')
        if card_number_el:
            card_details['card_number'] = await card_number_el.inner_text()

        # Expiry: MM/YY
        expiry_el = await page.query_selector('[data-testid="expiry"], .expiry')
        if expiry_el:
            card_details['expiry'] = await expiry_el.inner_text()

        # CVV
        cvv_el = await page.query_selector('[data-testid="cvv"], .cvv')
        if cvv_el:
            card_details['cvv'] = await cvv_el.inner_text()

        # Take screenshot as backup
        await page.screenshot(path=f'/tmp/privacy_card_{merchant_name.replace(" ", "_")}.png')

        await browser.close()

        # === STEP 5: Store in Strongbox ===
        if card_details['card_number']:
            print(f"💾 Storing card in Strongbox as 'Privacy - {merchant_name}'...")
            store_privacy_card_in_strongbox(merchant_name, card_details)
            print(f"✅ Card created and stored: ****{card_details['card_number'][-4:]}")
        else:
            print("⚠️ Could not extract card details - check screenshot")

        return card_details


def get_privacy_card(merchant_name: str) -> dict:
    """
    Look up existing Privacy.com card from Strongbox.

    Returns card details dict or None if not found.
    """
    result = subprocess.run([
        'python3', 'tools/strongbox_cli.py',
        'get-credential', '--service', f'Privacy - {merchant_name}', '--output', 'json'
    ], capture_output=True, text=True, cwd='{{CATALYST_ROOT}}')

    if result.returncode == 0:
        entry = json.loads(result.stdout)
        return {
            'card_number': entry.get('password'),  # Stored as password field
            'expiry': entry.get('custom_fields', {}).get('expiry'),
            'cvv': entry.get('custom_fields', {}).get('cvv'),
            'merchant': merchant_name
        }
    return None


def store_privacy_card_in_strongbox(merchant_name: str, card_details: dict):
    """Store Privacy.com card details in Strongbox."""
    subprocess.run([
        'python3', 'tools/strongbox_cli.py',
        'store-credential',
        '--service', f'Privacy - {merchant_name}',
        '--username', card_details.get('card_number', '')[:4] + '****',  # Masked for title
        '--password', card_details.get('card_number', ''),  # Full number in password field
        '--custom-field', f"expiry={card_details.get('expiry', '')}",
        '--custom-field', f"cvv={card_details.get('cvv', '')}",
        '--custom-field', f"merchant={merchant_name}",
        '--custom-field', f"card_type={card_details.get('card_type', 'merchant_locked')}",
    ], cwd='{{CATALYST_ROOT}}')
```

### Card Lookup Before Booking

The booking flow automatically checks for existing Privacy cards:

```python
# In book_appointment() function, before payment:

# Check for existing Privacy card for this merchant
existing_card = get_privacy_card(service_name)

if existing_card:
    print(f"💳 Found existing Privacy card: ****{existing_card['card_number'][-4:]}")
    # Use for payment
else:
    # Create new card if payment required
    print(f"💳 No Privacy card found for '{service_name}' - creating one...")
    card = await create_privacy_card(
        merchant_name=service_name,
        card_type="merchant_locked"
    )
```

### Strongbox Entry Format for Privacy Cards

```
Title: Privacy - Floyd's Barbershop
Username: 4532****  (masked number for reference)
Password: 4532XXXXXXXX1234  (full card number - protected)
URL: https://app.privacy.com
Custom Fields:
  - expiry: 12/28
  - cvv: 123 (protected)
  - merchant: Floyd's Barbershop
  - card_type: merchant_locked
  - spend_limit: 50.00 (if set)
  - created: 2025-01-21
Notes: Auto-created by Bowser for appointment booking
```

### Limitations

- **2FA may require manual intervention** - Privacy.com often requires SMS/email verification
- **UI selectors may change** - Privacy.com updates their interface periodically
- **Rate limiting** - Don't create cards too rapidly
- **Card details visibility** - Some details only shown once; screenshot is taken as backup

---

## Relationship to Other Skills

**credential-creator** - Create new account if booking site requires one
**account-login** - Login to existing account before booking (including Privacy.com)
**account-registration** - Register new account if needed for booking

**appointment-booking** (this skill) - The actual booking automation with privacy defaults, including Privacy.com virtual card management via UI automation

---

## Version History

- **v1.1.0** (2025-01-21) - Added Privacy.com virtual card management via UI automation
- **v1.0.0** (2025-01-21) - Initial release with privacy-first defaults, Strongbox integration, SimpleLogin aliases

---

**End of Appointment Booking Skill**
