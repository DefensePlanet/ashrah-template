# Account Creator Skill

## Overview
Automates online account creation by integrating SimpleLogin (email aliases) + Strongbox (password management) + Playwright (browser automation).

## What It Does
When you say "Sign me up for GitHub", {{ORCHESTRATOR_NAME}} will:
1. Execute account_creator.py to generate credentials:
   - Creates SimpleLogin email alias (e.g., `github.wandering432@alias.example.com`)
   - Generates strong password
   - Saves credentials to Strongbox
2. Delegate to Playwright Agent for browser automation:
   - Fills signup forms
   - Solves CAPTCHAs (90% success)
3. Report success with access details

**Architecture:** {{ORCHESTRATOR_NAME}} handles simple operations (API/CLI), delegates specialized work (browser automation) to agents.

## Quick Start

### First Time Setup
```bash
# 1. Ensure SimpleLogin API key is configured
export SIMPLELOGIN_API_KEY="your-key-here"

# 2. Verify Strongbox is accessible
# (The skill will prompt for master password if needed)

# 3. Check Playwright MCP is configured
cat {{CATALYST_ROOT}}/global/claude-config/mcp_servers.json | grep playwright
```

### Usage Examples

**Automated Signup (Supported Services)**
```
You: "Sign me up for GitHub"
{{ORCHESTRATOR_NAME}}: Creates alias + credentials + automates signup → Reports success
```

**Manual Signup (Any Service)**
```
You: "Create an account for newsite.com"
{{ORCHESTRATOR_NAME}}: Creates alias + credentials → Provides credentials for you to use
```

**With 2FA**
```
You: "Sign me up for GitHub with 2FA"
{{ORCHESTRATOR_NAME}}: Includes TOTP secret in Strongbox
```

## Supported Services (Automated)
- GitHub
- GitLab
- OpenAI
- Shopify
- Instagram

More can be added by updating `tools/account_creator.py`

## File Structure
```
.claude/skills/account-creator/
├── SKILL.md              # Main skill definition (Claude reads this)
├── README.md             # This file (human documentation)
└── examples/             # (Optional) Example workflows
```

## Dependencies
- **Python Script:** `{{CATALYST_ROOT}}/tools/account_creator.py`
- **SimpleLogin API:** `{{CATALYST_ROOT}}/tools/simple_login_api.py`
- **Strongbox CLI:** `{{CATALYST_ROOT}}/tools/strongbox_hub.py`
- **Playwright MCP:** Configured in `global/claude-config/mcp_servers.json`

## Testing

### Test Manual Creation
```bash
cd {{CATALYST_ROOT}}
python tools/account_creator.py create \
  --service test-service \
  --purpose skill-test \
  --email custom@example.com
```

### Test Automated Creation
```bash
python tools/account_creator.py create-auto \
  --service github \
  --purpose skill-test
```

### Verify Skill Triggers
Try these phrases in conversation:
- "Sign me up for GitHub"
- "Create an account on OpenAI"
- "I need a new login for Shopify"
- "Register me at GitLab"

## Troubleshooting

**Skill not triggering?**
- Check the `description` field in SKILL.md matches user intent
- Verify `.claude/skills/` directory is in the right location
- Restart Claude Code session to reload skills

**SimpleLogin errors?**
```bash
# Verify API key is set
echo $SIMPLELOGIN_API_KEY

# Test API directly
python -c "from tools.simple_login_api import SimpleLoginAPI; api = SimpleLoginAPI(); print('API OK')"
```

**Strongbox errors?**
```bash
# Verify Strongbox CLI is accessible
which keepassxc-cli

# Test credential retrieval
python tools/strongbox_hub.py --test
```

**Playwright not automating?**
- Check MCP server is running: `claude mcp list | grep playwright`
- Verify browser is installed: `python -c "from playwright import sync_api; print('OK')"`
- Review Playwright Agent logs for errors

## Governance

**Risk Classification:** 🟢 GREEN
- **Scope:** Isolated to account creation workflow
- **Reversibility:** Email aliases can be deleted, Strongbox entries removed
- **External Dependencies:** SimpleLogin API (authenticated), Strongbox (local)
- **Privacy:** Credentials never leave Catalyst, stored encrypted

**Approval Requirements:**
- No approval needed for creating aliases or generating passwords
- Playwright automation uses `allowed-tools` (pre-approved)

## Metrics

View skill usage:
```bash
# List all created accounts
python tools/account_creator.py list

# Check specific account
python tools/account_creator.py info --service github --purpose test

# Verify access
python tools/account_creator.py verify --service github --purpose test
```

## Future Enhancements
- [ ] Email verification automation (check SimpleLogin inbox)
- [ ] Temp phone number integration for SMS verification
- [ ] Service template library (community configs)
- [ ] Batch account creation for testing
- [ ] Account health monitoring

## Related Skills
- **capsule-navigator** - Auto-navigate to project context for account usage
- **governance-classifier** - Risk assessment for external service signups

---

**Created:** 2025-10-17
**Version:** 1.2.0
**Updated:** 2025-10-20
**Architecture:** {{ORCHESTRATOR_NAME}} orchestration + Playwright Agent for browser automation
**Status:** Production Ready
