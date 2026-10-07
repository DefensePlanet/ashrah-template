---
name: credential-creator
description: Generate email aliases via SimpleLogin and secure passwords via Strongbox for online account creation. Handles ONLY credential generation, not browser automation.
allowed-tools:
  - Bash
  - Read
metadata:
  version: "1.0.0"
  authority: "{{ORCHESTRATOR_NAME}}"
  simple_login_api: "tools/simple_login_api.py"
  strongbox_cli: "tools/strongbox_cli.py"
  scope: "Credential generation only - NO browser automation"
  companion_skill: "account-registration (for browser automation)"
  last_updated: "2025-10-22"
---

# Credential Creator Skill

## Purpose
Generate secure credentials for online account creation:
1. **Email alias** via SimpleLogin (forwards to {{USER_EMAIL}})
2. **Strong password** via Strongbox
3. **Optional TOTP secret** for 2FA

**Scope:** This skill handles **ONLY credential generation**. For browser automation to actually register accounts, use the `account-registration` skill (Bowser).

## Trigger Keywords
- "create credentials for [service]"
- "generate email alias for [service]"
- "make credentials for [service]"
- "I need login credentials for [service]"

## Workflow

### Credential Generation Only
```
User: "Create credentials for GitHub"

{{ORCHESTRATOR_NAME}} Actions:
1. ✅ Create SimpleLogin alias via API
   - Generates: github.wandering432@alias.example.com
   - Forwards to: {{USER_EMAIL}}
2. ✅ Generate password via Strongbox
   - 32+ characters, secure random
   - Stored as: "GitHub - [purpose]"
3. ✅ Return credentials to user
   - Email alias
   - Strongbox path
   - Optional: TOTP secret
```

**Result:** User has credentials but NO account created yet. They can:
- Use credentials for manual signup
- Provide credentials to Bowser for automated signup

## Execution

### Standard Credential Creation

```bash
cd {{CATALYST_ROOT}}

# Create credentials for a service
python3 tools/account_creator.py create \
  --service github \
  --purpose dev
```

**Output:**
```
✅ Credentials created for GitHub

Email: github.wandering432@alias.example.com
Strongbox Path: GitHub - dev
Password: ••••••••••••••• (saved in Strongbox)
SimpleLogin Alias ID: 33973652

Next steps:
- Manual signup: Use credentials at https://github.com/signup
- Automated signup: Delegate to Bowser with account-registration skill
```

### With TOTP/2FA

```bash
python3 tools/account_creator.py create \
  --service github \
  --purpose dev \
  --enable-totp
```

**Output includes:**
- Email alias
- Password
- TOTP secret (saved in Strongbox)

### Capsule-Aware Creation

When in a capsule, purpose is auto-set:
```
[In capsule: ecommerce-store]
User: "Create credentials for Shopify"

{{ORCHESTRATOR_NAME}}:
- Service: shopify
- Purpose: ecommerce-store (from capsule context)
- Strongbox Path: Shopify - ecommerce-store
```

## Integration with Account Registration

This skill **generates credentials only**. To actually register accounts:

**Manual Registration:**
```
1. Use credential-creator skill → Get credentials
2. User manually signs up using credentials
```

**Automated Registration:**
```
1. Use credential-creator skill → Get credentials
2. Delegate to Bowser with account-registration skill
3. Provide credentials to automation script
```

**Example Full Flow:**
```
User: "Create a GitHub account"

{{ORCHESTRATOR_NAME}}:
1. Invokes credential-creator skill
   → Email: github.wandering432@alias.example.com
   → Password: [Strongbox path]

2. Delegates to Bowser with account-registration skill
   → Provides: email, password, https://github.com/signup

3. Bowser runs browser automation

4. Reports success to user
```

## Credential Management

### List Credentials
```bash
# List all credentials
python3 tools/account_creator.py list

# List for specific service
python3 tools/account_creator.py list --service github
```

### Check Credential Info
```bash
python3 tools/account_creator.py info \
  --service github \
  --purpose dev
```

**Output:**
- Email alias
- Strongbox path
- Creation date
- SimpleLogin alias ID

### Retrieve Password
```bash
# Via Strongbox CLI
python3 tools/strongbox_cli.py get-password \
  --service github \
  --purpose dev
```

## Email Alias Management

### Check Alias Status
```bash
# Get alias info
python3 tools/simple_login_api.py info --alias-id 33973652
```

**Shows:**
- Email alias
- Enabled/disabled status
- Forward count
- Block count

### Disable/Enable Alias
```bash
# Disable alias (stop receiving emails)
python3 tools/simple_login_api.py toggle --alias-id 33973652

# Enable again
python3 tools/simple_login_api.py toggle --alias-id 33973652
```

### Delete Alias
```bash
# Permanently delete alias
python3 tools/simple_login_api.py delete-alias --alias-id 33973652
```

**Warning:** Deletion is permanent. Consider disabling instead.

## Configuration

### SimpleLogin Settings
- **API Key**: Stored in `SIMPLELOGIN_API_KEY` environment variable
- **Default mailbox**: {{USER_EMAIL}} (automatically configured)
- **Alias format**: Readable words (e.g., `github.wandering432@alias.example.com`)

### Strongbox Settings
- **Database path**: `{{HOME_DIR}}/Library/Mobile Documents/iCloud~com~strongbox/Documents/Roth Pass.kdbx`
- **Master password**: Empty string (no password required)
- **Entry format**: `[Service] - [purpose]`
- **Password length**: 32+ characters
- **Password generator**: Secure random

### Verify Configuration
```bash
# Test SimpleLogin connection
python3 tools/simple_login_api.py test

# List available mailboxes
python3 tools/simple_login_api.py mailboxes

# Verify Strongbox access (prompts for password)
python3 tools/strongbox_cli.py list
```

## Error Handling

### SimpleLogin API Failures
**Symptom:** Cannot create email alias

**Solutions:**
1. Check API key: `echo $SIMPLELOGIN_API_KEY`
2. Test connection: `python3 tools/simple_login_api.py test`
3. Check rate limits (60/minute)
4. Verify account has alias quota

### Strongbox Authentication Failures
**Symptom:** Cannot save password

**Solutions:**
1. Ensure Strongbox app is installed
2. Verify database path
3. Check master password
4. Try interactive mode (prompts for password)

### Email Already Exists
**Symptom:** Alias creation fails - email exists

**Solutions:**
1. List existing aliases: `python3 tools/simple_login_api.py list --service [service]`
2. Use different purpose: `--purpose dev-2`
3. Delete old alias if no longer needed

## Security & Privacy

### Email Privacy
- **Real email never exposed** - All aliases forward to {{USER_EMAIL}}
- **Service isolation** - Each service gets unique alias
- **Reversible** - Can disable/delete aliases anytime
- **No spam** - Disable alias to stop receiving emails

### Password Security
- **Never displayed** - Passwords shown as •••••••••
- **Encrypted storage** - Strongbox database encrypted
- **Master password required** - No plaintext storage
- **Secure generation** - Cryptographically secure random

### Credential Exposure
- **Never logged** - Credentials not written to logs
- **Not in code** - Passwords retrieved securely
- **No external storage** - Only Strongbox and SimpleLogin

## Best Practices

### Credential Organization
- **Use descriptive purposes**: `github-dev`, `github-prod`, `github-personal`
- **Capsule-aware naming**: Purpose auto-set from capsule context
- **Consistent naming**: [service]-[environment]-[purpose]

### Alias Management
- **Don't delete immediately** - Disable first, delete later if needed
- **Check forwarding** - Verify emails arrive at {{USER_EMAIL}}
- **Monitor usage** - Check forward counts periodically

### Password Rotation
```bash
# Create new credentials (old ones remain)
python3 tools/account_creator.py create \
  --service github \
  --purpose dev-2

# Update login on service to use new credentials
# Delete old Strongbox entry and SimpleLogin alias when confirmed
```

## Troubleshooting

### "SimpleLogin API key not found"
```bash
# Set API key
export SIMPLELOGIN_API_KEY="your-key-here"

# Or get from Strongbox
python3 tools/strongbox_cli.py get-api-key \
  --service simplelogin
```

### "Mailbox {{USER_EMAIL}} not found"
```bash
# List available mailboxes
python3 tools/simple_login_api.py mailboxes

# Should show {{USER_EMAIL}} (ID: 49502)
# If missing, add mailbox in SimpleLogin web interface
```

### "Cannot connect to Strongbox"
```bash
# Verify Strongbox installation
which strongbox-cli

# Check database path
ls -la ~/Documents/Strongbox/

# Test with list command
python3 tools/strongbox_cli.py list
```

## Quick Reference

**Create credentials:**
```bash
python3 tools/account_creator.py create --service [service] --purpose [purpose]
```

**List credentials:**
```bash
python3 tools/account_creator.py list --service [service]
```

**Get credential info:**
```bash
python3 tools/account_creator.py info --service [service] --purpose [purpose]
```

**Retrieve password:**
```bash
python3 tools/strongbox_cli.py get-password --service [service] --purpose [purpose]
```

**Manage alias:**
```bash
# List aliases
python3 tools/simple_login_api.py list

# Get alias info
python3 tools/simple_login_api.py info --alias-id [id]

# Toggle enabled/disabled
python3 tools/simple_login_api.py toggle --alias-id [id]

# Delete alias
python3 tools/simple_login_api.py delete-alias --alias-id [id]
```

---

**End of Credential Creator Skill**

## Relationship to Other Skills

**credential-creator** (this skill) - {{ORCHESTRATOR_NAME}} handles credential generation
**account-registration** - Bowser handles browser automation

Use together for fully automated account creation, or use credential-creator alone for manual signups.
