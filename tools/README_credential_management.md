# Catalyst Credential Management

Complete integration between Simple Login, Strongbox, and automated account creation for the Catalyst.

## Overview

This system provides automated credential management for account creation workflows:

- **Simple Login Integration** - Creates email aliases for new accounts
- **Strongbox Integration** - Stores credentials securely in your password manager
- **Account Creation Workflow** - Unified process for creating service accounts
- **Playwright Integration** - Automated signup forms (when available)

## Components

### 1. Simple Login API (`simple_login_api.py`)
- Creates email aliases programmatically
- Manages alias lifecycle
- Searches and organizes aliases by service

### 2. Strongbox CLI (`strongbox_cli.py`) 
- Interfaces with KeePassXC CLI to manage Strongbox database
- Generates secure passwords
- Stores credentials in organized folder structure
- Supports TOTP/2FA integration

### 3. Account Creator (`account_creator.py`)
- Orchestrates complete account creation workflow
- Combines Simple Login + Strongbox + optional Playwright automation
- Handles manual and automated account creation

## Setup

### Prerequisites
1. **KeePassXC** installed with CLI access
2. **Simple Login** account with API key
3. **Strongbox** database accessible via KeePassXC CLI

### Installation
```bash
cd {{CATALYST_ROOT}}/tools
pip install -r requirements.txt
```

### Configuration
1. Set Simple Login API key:
```bash
export SIMPLELOGIN_API_KEY="your-api-key-here"
```

2. Ensure Strongbox database is accessible:
   - Default path: `{{HOME_DIR}}/Library/Mobile Documents/iCloud~com~strongbox/Documents/Roth Pass.kdbx`
   - Or provide custom path when initializing

## Usage Examples

### Basic Account Creation (Manual)
```bash
# Create account with Simple Login alias + Strongbox storage
python account_creator.py create --service github --purpose my-project --username myusername --enable-totp

# Output:
# ✅ Account created successfully
# Service: github
# Email: github-my-project-abc123@simplelogin.co
# Username: myusername
# Password: [generated secure password]
# TOTP Code: 123456
# Strongbox: Development/GitHub/GitHub - my-project
```

### Automated Account Creation (with Playwright)
```bash
# Fully automated signup including form filling
python account_creator.py create-auto --service github --purpose my-project --enable-totp

# This will:
# 1. Create Simple Login alias
# 2. Generate secure credentials in Strongbox
# 3. Use Playwright to fill signup form
# 4. Handle email verification (when possible)
```

### Direct Simple Login Management
```bash
# Test Simple Login API connection
python simple_login_api.py test

# Create alias for specific service
python simple_login_api.py create --service github --purpose my-new-project

# List all aliases for a service
python simple_login_api.py list --service github

# Search aliases by note content
python simple_login_api.py search --search "Catalyst"
```

### Direct Strongbox Management  
```bash
# Test Strongbox connection
python strongbox_cli.py test

# Create complete account entry
python strongbox_cli.py create-account --service github --purpose api-access --username myuser --email myuser@example.com --enable-totp

# Get stored credentials
python strongbox_cli.py get --service github --purpose api-access

# Get current TOTP code
python strongbox_cli.py get-totp --service github --purpose api-access

# List all entries for a service
python strongbox_cli.py list --service github
```

## Integration with Catalyst

### {{ORCHESTRATOR_NAME}} Auto-Detection
When {{ORCHESTRATOR_NAME}} detects that an account is needed during a build process:

```python
# In any Builder agent or workflow
from tools.account_creator import AccountCreator

creator = AccountCreator()
result = creator.create_account_automated(
    service="github", 
    purpose="api-access-for-project-x",
    enable_totp=True
)

if result.success:
    # Use credentials immediately
    api_key = result.password  # Or retrieve API key separately
    # Continue with build process
```

### Service Configuration
Pre-configured services with automated signup support:
- **GitHub** - Full automation including 2FA setup
- **GitLab** - Full automation with email verification
- **OpenAI** - API account creation
- **Shopify** - Store account creation
- **Instagram** - Social media account setup

### Folder Structure in Strongbox
```
Development/
  ├── GitHub/
  │   ├── GitHub - my-project
  │   └── GitHub - api-access
  └── GitLab/
      └── GitLab - work-project

AI/
  ├── OpenAI/
  │   └── OpenAI - api-access
  └── Anthropic/
      └── Anthropic - claude-api

Social Media/
  ├── Instagram/
  │   └── Instagram - brand-account
  └── Twitter/
      └── Twitter - personal

E-commerce/
  └── Shopify/
      └── Shopify - test-store
```

## Security Considerations

### What's Stored Where
- **Environment Variables**: Simple Login API key only
- **Strongbox Database**: All passwords, TOTP secrets, account details
- **MCP Memory**: Metadata only (service names, purposes) - NEVER credentials
- **Temporary Files**: None - all operations are direct API/CLI calls

### Privacy Protection
- Passwords are generated cryptographically secure (16+ characters)
- TOTP secrets use 160-bit entropy
- API keys are never logged or displayed
- Failed operations automatically clean up created resources

### Backup Strategy
```bash
# Backup Strongbox database
python strongbox_cli.py backup

# Backup stored in: {{CATALYST_ROOT}}/global/backups/
```

## Error Handling

### Common Issues
1. **"KeePassXC CLI not found"**
   - Install KeePassXC: `brew install keepassxc`
   - Or download from https://keepassxc.org/

2. **"Simple Login API key required"**
   - Set environment variable: `export SIMPLELOGIN_API_KEY="your-key"`
   - Get API key from Simple Login dashboard

3. **"Strongbox database not found"**
   - Verify database path exists
   - Check if Strongbox is synced from iCloud

### Cleanup After Failures
```bash
# If account creation fails, clean up created resources
python account_creator.py cleanup --service github --purpose failed-project
```

## Advanced Usage

### Custom Email Domains
If you have custom Simple Login domains configured:
```python
# The system will automatically use your custom domains
# when creating aliases, falling back to random aliases if needed
```

### Bulk Account Creation
```bash
# Create multiple accounts for different purposes
services=("github" "gitlab" "openai")
for service in "${services[@]}"; do
    python account_creator.py create-auto --service "$service" --purpose "project-x-integration"
done
```

### Integration with Existing Capsules
```python
# In capsule code that needs service access
from tools.strongbox_cli import StrongboxCLI

strongbox = StrongboxCLI()
credential = strongbox.get_credential("github", "api-access")

if not credential:
    # Trigger account creation
    from tools.account_creator import AccountCreator
    creator = AccountCreator()
    result = creator.create_account_automated("github", "api-access")
    credential = strongbox.get_credential("github", "api-access")

# Use credential.password as API key
api_key = credential.password
```

## Monitoring and Maintenance

### List All Created Accounts
```bash
python account_creator.py list
# Shows all accounts created by Catalyst

python account_creator.py list --service github  
# Shows all GitHub accounts
```

### Verify Account Access
```bash
python account_creator.py verify --service github --purpose my-project
# Checks if stored credentials are still valid
```

### Cleanup Old/Unused Aliases
```bash
python simple_login_api.py cleanup --days 365 --dry-run
# Shows which aliases would be deleted (older than 1 year, unused)

python simple_login_api.py cleanup --days 365
# Actually delete old unused aliases
```

This credential management system integrates seamlessly with the Catalyst's existing patterns while providing secure, automated account creation capabilities.