# API Key Storage & Retrieval Protocol

**Purpose:** Complete guide for managing API keys using Strongbox password manager and per-capsule .env files.

---

## Storage Architecture

**Pattern:** All API keys stored as custom fields on existing account entries in Strongbox.

### Why This Approach
- **Single source of truth:** Strongbox is encrypted, backed up, version controlled
- **Per-capsule convenience:** .env files for easy access during development
- **Sync mechanism:** Populate .env from Strongbox on demand
- **Security:** Strongbox encrypted, .env auto-gitignored

---

## Strongbox Custom Field Convention

### Single API Key (Most Common)

**Entry structure:**
- **Username**: Account email/login
- **Password**: Account password
- **Custom Field**: `API_Key` = the actual API key value
- **URL**: Service URL
- **Notes**: Context about key creation/purpose

### Multiple API Keys (Different Environments)

**Custom fields:**
- `API_Key_Production`
- `API_Key_Development`
- `API_Key_Staging`

### Multiple API Keys (Different Purposes)

**Custom fields:**
- `API_Key_Main`
- `API_Key_Webhook`
- `API_Key_ReadOnly`

---

## Storage & Retrieval Commands

### Store API Key in Strongbox

```bash
# Default field name (API_Key)
tools/strongbox_cli.py set-api-key --service openai --purpose "main account" --api-key "sk-proj-xxxxx"

# Custom field name
tools/strongbox_cli.py set-api-key --service github --purpose "production" --field API_Key_Production --api-key "ghp_xxxxx"
```

### Get API Key from Strongbox

```bash
# Default field name (API_Key)
tools/strongbox_cli.py get-api-key --service openai --purpose "main account"

# Custom field name
tools/strongbox_cli.py get-api-key --service github --purpose "production" --field API_Key_Production

# Pipe to variable
API_KEY=$(tools/strongbox_cli.py get-api-key --service openai --purpose "main account")
```

**Output:** `get-api-key` returns just the API key value (for easy piping), or error to stderr.

---

## Hybrid Workflow: Strongbox + Capsule .env Files

### Architecture

- **Strongbox** = Source of truth (encrypted, backed up, version controlled)
- **Capsule .env files** = Local convenience (easy access during development)
- **Sync mechanism** = Populate .env from Strongbox on demand

### Per-Capsule Setup

#### 1. Create .env.template (Committed to Git)

```bash
# capsules/my-project/.env.template
OPENAI_API_KEY=  # strongbox:openai:main account
GITHUB_TOKEN=    # strongbox:github:production:API_Key_Production
STRIPE_KEY=      # strongbox:stripe:live account
```

#### 2. Sync to .env (Auto-gitignored)

```bash
# Sync specific capsule
tools/sync_capsule_env.py my-project

# Sync all capsules
tools/sync_capsule_env.py --all

# List available capsules
tools/sync_capsule_env.py --list
```

#### 3. Auto-generated .env (Never Committed)

```bash
# Auto-generated from Strongbox
# DO NOT COMMIT THIS FILE
OPENAI_API_KEY=sk-proj-xxxxx
GITHUB_TOKEN=ghp_xxxxx
STRIPE_KEY=sk_live_xxxxx
```

---

## Safety Features

- .env automatically added to .gitignore on sync
- Template files are committed, actual .env files never are
- Sync tool validates Strongbox access before writing

---

## When API Key Needed

### Step-by-Step Workflow

1. **Check if account exists** in Strongbox (search or list)

2. **If key exists:** Run `sync_capsule_env.py` to populate .env

3. **If key doesn't exist:**
   - Ensure account entry exists (create via account-creator skill if needed)
   - Navigate to service and generate API key via 🎭 Playwright Agent
   - Store key using `set-api-key` command
   - Run sync to populate .env

4. **Use key** from capsule .env or direct retrieval

### Manual Retrieval (If Needed)

```bash
# Direct API key retrieval (bypass .env)
export OPENAI_API_KEY=$(tools/strongbox_cli.py get-api-key --service openai --purpose "main account")
```

---

## Complete Example: Setting Up New Service

### Scenario: Adding OpenAI API to a capsule

```bash
# 1. Create account (if needed)
# Use account-creator skill or manual signup

# 2. Generate API key
# Navigate to service via 🎭 Playwright Agent
# Copy generated key

# 3. Store in Strongbox
tools/strongbox_cli.py set-api-key \
  --service openai \
  --purpose "main account" \
  --api-key "sk-proj-abc123..."

# 4. Create .env.template in capsule
echo "OPENAI_API_KEY=  # strongbox:openai:main account" > capsules/my-project/.env.template

# 5. Sync to .env
tools/sync_capsule_env.py my-project

# 6. Verify
cat capsules/my-project/.env
# Should show: OPENAI_API_KEY=sk-proj-abc123...

# 7. Use in code
# Load from .env file as usual
```

---

## Privacy & Security

### Privacy Rules
- **Never print** API keys, passwords, or secrets
- **Never modify** credentials directly (read-only access)
- **[PRIVATE] prefix** for info that should NOT be stored in MCP memory

### Security Best Practices
- Strongbox is master source (encrypted, backed up)
- .env files are local only (auto-gitignored)
- Sync tool validates access before writing
- Template files document structure without exposing values

---

*API Key Management Guide - BuilderOS Documentation*
