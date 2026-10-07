---
name: strongbox-manager
description: Manage Strongbox password manager entries, including adding/retrieving custom fields like API keys using PyKeePass library.
allowed-tools:
  - Bash
  - Read
  - Write
metadata:
  version: "1.0.0"
  authority: "{{ORCHESTRATOR_NAME}}"
  strongbox_cli: "tools/strongbox_cli.py"
  scope: "Strongbox/KeePass database operations via PyKeePass"
  last_updated: "2025-10-29"
---

# Strongbox Manager Skill

## Purpose
Manage credentials in Strongbox password manager, with special support for adding custom fields (like API keys) that keepassxc-cli doesn't support.

**Key Capability:** Add custom fields to existing Strongbox entries using PyKeePass library.

## When to Use This Skill
- Adding API keys as custom fields to credential entries
- Retrieving API keys or other custom fields from Strongbox
- Managing credentials programmatically via Python
- When keepassxc-cli limitations require direct database access

## Architecture Pattern

### The Problem
**keepassxc-cli** doesn't support custom attributes, but many Catalyst workflows need to store API keys as custom fields on credential entries.

### The Solution
Use **PyKeePass** library to directly manipulate the KeePass database for custom field operations:

```python
from pykeepass import PyKeePass

# Open database
kp = PyKeePass(db_path, password='')  # Empty password for {{USER_NAME}}'s database

# Find entry by title (filtering out Recycle Bin)
entries = [e for e in kp.find_entries(title='Groq')
           if 'Recycle Bin' not in e.path]
entry = entries[0]

# Add custom field (protected=True for sensitive data)
entry.set_custom_property('API_Key', 'your-api-key-here', protect=True)

# Save database
kp.save()

# Retrieve custom field
api_key = entry.get_custom_property('API_Key')
```

## Database Configuration

### Location
```
{{HOME_DIR}}/Library/Mobile Documents/iCloud~com~strongbox/Documents/Roth Pass.kdbx
```

### Master Password
**Empty string** - No password required

### Entry Structure
```
Catalyst/
  └── Auto-Created/
      ├── Groq
      ├── Fireworks AI
      ├── OpenAI
      └── [other services]
```

## Common Operations

### 1. Add API Key to Existing Entry

**Using Python directly:**
```python
from pykeepass import PyKeePass

db_path = "{{HOME_DIR}}/Library/Mobile Documents/iCloud~com~strongbox/Documents/Roth Pass.kdbx"
kp = PyKeePass(db_path, password='')

# Find entry (exclude Recycle Bin)
entries = [e for e in kp.find_entries(title='ServiceName')
           if 'Recycle Bin' not in e.path]

if entries:
    entry = entries[0]
    entry.set_custom_property('API_Key', 'your-key-here', protect=True)
    kp.save()
    print(f"✅ Added API key to {'/'.join(entry.path)}")
```

**Using strongbox_cli.py:**
```bash
cd {{CATALYST_ROOT}}

python3 tools/strongbox_cli.py set-api-key \
  --service groq \
  --purpose "main account" \
  --api-key "gsk_abc123..." \
  --field "API_Key"
```

### 2. Retrieve API Key from Entry

**Using Python directly:**
```python
from pykeepass import PyKeePass

kp = PyKeePass(db_path, password='')
entries = [e for e in kp.find_entries(title='Groq')
           if 'Recycle Bin' not in e.path]

if entries:
    api_key = entries[0].get_custom_property('API_Key')
    print(f"API Key: {api_key}")
```

**Using strongbox_cli.py:**
```bash
python3 tools/strongbox_cli.py get-api-key \
  --service groq \
  --purpose "main account" \
  --field "API_Key"
```

### 3. Search for Entries

**Using keepassxc-cli (fast):**
```bash
export KEEPASS_DB="{{HOME_DIR}}/Library/Mobile Documents/iCloud~com~strongbox/Documents/Roth Pass.kdbx"

# Locate entries by name
keepassxc-cli locate "$KEEPASS_DB" "Groq"
# Returns: /Catalyst/Auto-Created/Groq
```

**Using PyKeePass (more flexible):**
```python
from pykeepass import PyKeePass

kp = PyKeePass(db_path, password='')

# Search by title with regex
entries = kp.find_entries(title='.*groq.*', regex=True)

for entry in entries:
    if 'Recycle Bin' not in entry.path:
        print(f"Found: {'/'.join(entry.path)}")
```

### 4. List All Custom Properties

```python
from pykeepass import PyKeePass

kp = PyKeePass(db_path, password='')
entry = [e for e in kp.find_entries(title='Groq')
         if 'Recycle Bin' not in e.path][0]

print("Custom properties:")
for prop, value in entry.custom_properties.items():
    print(f"  {prop}: {value}")
```

## Working with tools/strongbox_cli.py

The `StrongboxCLI` class provides high-level methods:

### Initialize
```python
from tools.strongbox_cli import StrongboxCLI

strongbox = StrongboxCLI(
    db_path="{{HOME_DIR}}/Library/Mobile Documents/iCloud~com~strongbox/Documents/Roth Pass.kdbx",
    master_password=""  # Empty for {{USER_NAME}}'s database
)
```

### Store Credential with Custom Fields
```python
success = strongbox.store_credential(
    service="openai",
    purpose="production",
    username="api-key",
    password="generated-or-provided",
    url="https://platform.openai.com",
    custom_fields={
        "API_Key": "sk-abc123...",
        "Organization_ID": "org-xyz789..."
    }
)
```

### Get API Key
```python
api_key = strongbox.get_api_key(
    service="openai",
    purpose="production",
    field_name="API_Key"  # Default field name
)

if api_key:
    print(f"Retrieved API key: {api_key[:10]}...")
```

### Set API Key on Existing Entry
```python
success = strongbox.set_api_key(
    service="groq",
    purpose="main account",
    api_key="gsk_abc123...",
    field_name="API_Key"
)
```

## Entry Path Patterns

The `strongbox_cli.py` uses these folder mappings:

```python
service_folders = {
    "github": "Development/GitHub",
    "gitlab": "Development/GitLab",
    "openai": "AI/OpenAI",
    "anthropic": "AI/Anthropic",
    "groq": "Catalyst/Auto-Created",  # Falls to default
    "fireworks": "Catalyst/Auto-Created",
    "default": "Catalyst/Auto-Created"
}
```

Entry titles follow format: `{Service} - {purpose}`
- Example: "Groq - main account" → `/Catalyst/Auto-Created/Groq - main account`

## Error Handling

### PyKeePass Not Installed
```bash
# Install PyKeePass
pip3 install --break-system-packages pykeepass
```

### Entry Not Found
```python
from pykeepass import PyKeePass

kp = PyKeePass(db_path, password='')
entries = [e for e in kp.find_entries(title='NonExistent')
           if 'Recycle Bin' not in e.path]

if not entries:
    print("Entry not found - create it first")
    # Use strongbox.store_credential() to create
```

### Database Locked
- Ensure no other process has the database open
- Check if Strongbox app is running and accessing the file
- Wait a moment and retry

### Custom Field Already Exists
- `set_custom_property()` overwrites existing fields
- To preserve: read existing value first, modify, then write back

## Best Practices

### 1. Always Filter Out Recycle Bin
```python
# Good
entries = [e for e in kp.find_entries(title='Service')
           if 'Recycle Bin' not in e.path]

# Bad - might find deleted entries
entries = kp.find_entries(title='Service')
```

### 2. Use Protected Fields for Sensitive Data
```python
# Protected (recommended for passwords, API keys)
entry.set_custom_property('API_Key', 'secret', protect=True)

# Unprotected (for metadata only)
entry.set_custom_property('service', 'groq', protect=False)
```

### 3. Always Save After Modifications
```python
entry.set_custom_property('API_Key', 'new-key', protect=True)
kp.save()  # Don't forget this!
```

### 4. Verify After Write Operations
```python
entry.set_custom_property('API_Key', 'test-key', protect=True)
kp.save()

# Verify
retrieved = entry.get_custom_property('API_Key')
assert retrieved == 'test-key', "Write verification failed"
```

## Integration with Other Skills

### credential-creator
Uses strongbox_cli.py to store generated credentials:
```python
from tools.strongbox_cli import StrongboxCLI

strongbox = StrongboxCLI()
strongbox.store_credential(
    service="github",
    purpose="dev-account",
    username="generated-email-alias@alias.example.com",
    password="generated-password",
    custom_fields={"service": "github", "purpose": "dev"}
)
```

### account-login
Retrieves credentials for browser automation:
```python
credential = strongbox.get_credential("github", "dev-account")
api_key = strongbox.get_api_key("github", "dev-account")
```

## Quick Reference

**Add API key to existing entry:**
```bash
python3 tools/strongbox_cli.py set-api-key \
  --service [service] \
  --purpose "[purpose]" \
  --api-key "[key]"
```

**Get API key from entry:**
```bash
python3 tools/strongbox_cli.py get-api-key \
  --service [service] \
  --purpose "[purpose]"
```

**Python pattern for custom fields:**
```python
from pykeepass import PyKeePass

kp = PyKeePass(db_path, password='')
entry = [e for e in kp.find_entries(title='Name')
         if 'Recycle Bin' not in e.path][0]
entry.set_custom_property('FieldName', 'value', protect=True)
kp.save()
```

**Locate entry path:**
```bash
keepassxc-cli locate "$KEEPASS_DB" "[search-term]"
```

---

**End of Strongbox Manager Skill**

## Real-World Example: Today's Task

This skill documents the exact pattern used to add Groq and Fireworks API keys:

```python
from pykeepass import PyKeePass

db_path = "{{HOME_DIR}}/Library/Mobile Documents/iCloud~com~strongbox/Documents/Roth Pass.kdbx"
kp = PyKeePass(db_path, password='')

# Groq
groq = [e for e in kp.find_entries(title='Groq') if 'Recycle Bin' not in e.path][0]
groq.set_custom_property('API_Key', 'gsk_your_groq_key_here', protect=True)

# Fireworks
fireworks = [e for e in kp.find_entries(title='Fireworks AI') if 'Recycle Bin' not in e.path][0]
fireworks.set_custom_property('API_Key', 'fw_your_fireworks_key_here', protect=True)

kp.save()
```

This pattern is now encoded in `tools/strongbox_cli.py` methods: `set_api_key()` and `get_api_key()`.
