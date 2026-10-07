# Integration Tools (Lazy-Loaded Section)
<!-- Last updated: 2026-02-24 -->

## Memory & Privacy Controls
**MCP Memory Location:** `~/.claude/mcp-data/builder-memory.json`
**Key Commands:**
- Status: `tools/memory/memory_status.sh`
- Backup: `tools/memory/backup_memory.sh`
- Clear: `tools/memory/clear_memory.sh`
- Setup: `tools/memory/setup_memory.sh`

**Privacy Rule:** Use `[PRIVATE]` prefix for sensitive information that should NOT be stored in MCP memory.

---

## TaskMaster: Work Item Management

**Summary:** TaskMaster is Catalyst's work item tracking system. Each capsule has `tasks.json` for managing work items with full lifecycle tracking. Native support for mobile app (Swift) and web dashboard (JavaScript).

**Note:** TaskMaster is separate from Claude Code's "Task tool" (which invokes specialist agents). TaskMaster manages persistent work items in capsules.

**Quick Reference:**
```bash
# Add task
python3 tools/task_manager.py add [capsule] "Task description" --priority high --tags feature

# List tasks
python3 tools/task_manager.py list --capsule [capsule] --status pending

# Update task
python3 tools/task_manager.py update [capsule] [task-id] --status in_progress

# Complete task
python3 tools/task_manager.py complete [capsule] [task-id]

# Statistics
python3 tools/task_manager.py stats
```

**Schema & Templates:**
- Reference schema: `recipes/schema/taskmaster-schema-v1.json`
- Template: `recipes/framework-templates/base/tasks.json.template`
- Complete guide: `global/docs/TaskMaster_Guide.md`

**Catalyst System Tasks:** Use root-level TaskMaster or Claude Code task tools for framework and infrastructure work.

---

## API Key Storage & Retrieval

**Summary:** All API keys stored as custom fields in Strongbox. Per-capsule .env files synced on demand.

### Architecture: PyKeePass for Custom Fields

**Key Insight:** `keepassxc-cli` doesn't support custom attributes. Use `PyKeePass` library for custom field operations.

**Database Details:**
- **Path:** Stored in `{{CATALYST_ROOT}}/.env` (STRONGBOX_DB_PATH)
- **Password:** Stored in `{{CATALYST_ROOT}}/.env` (STRONGBOX_PASSWORD)
- **Format:** KeePass 2.x (.kdbx)

**Python Pattern:**
```python
import os
from pykeepass import PyKeePass

# Open database (credentials from .env)
db_path = os.environ.get('STRONGBOX_DB_PATH')
kp = PyKeePass(db_path, password=os.environ.get('STRONGBOX_PASSWORD', ''))

# Find entry (exclude Recycle Bin)
entries = [e for e in kp.find_entries(title='ServiceName')
           if 'Recycle Bin' not in e.path]

if entries:
    entry = entries[0]
    # Add custom field (protect=True for sensitive data)
    entry.set_custom_property('API_Key', 'your-key-here', protect=True)
    kp.save()

    # Retrieve custom field
    api_key = entry.get_custom_property('API_Key')
```

**Quick Reference:**
```bash
# Store key
python3 tools/strongbox_cli.py set-api-key --service openai --purpose "main account" --api-key "sk-xxx"

# Get key
python3 tools/strongbox_cli.py get-api-key --service openai --purpose "main account"

# Sync capsule .env from Strongbox
python3 tools/sync_capsule_env.py my-project
```

**Tools:**
- `tools/strongbox_cli.py` - High-level API (uses PyKeePass internally)
- `.claude/skills/strongbox-manager/` - Complete skill documentation

**Complete guide:** See `global/docs/API_Key_Management.md`

---

## BridgeHub: Codex Communication

**CRITICAL:** When {{USER_NAME}} says "discuss with Codex" or "consult Codex", use BridgeHub CLI tool (NOT an MCP server).

**Quick Reference:**
```bash
node {{CATALYST_ROOT}}/tools/bridgehub/dist/bridgehub.js --request '{
  "version": "bridgehub/1.0",
  "action": "freeform",
  "capsule": "'"$(pwd)"'",
  "session": "{{ORCHESTRATOR_NAME_LOWER}}-codex-[topic]-[date]",
  "payload": {"message": "Your question for Codex"}
}'
```

**Complete guide:** See `global/docs/BridgeHub_Protocol.md`

---

## Apple Provisioning (App Store Connect API)

**Summary:** Automates Apple Developer portal operations via REST API. Account-level — one API key covers all apps.

**Credentials:**
- **Key file:** `~/.apple-provision/keys/AuthKey_HBVJA6BAQX.p8` (permissions: 600)
- **Env vars:** `ASC_KEY_ID`, `ASC_ISSUER_ID`, `ASC_KEY_PATH` (set in `~/.zshrc`)
- **Key ID:** `HBVJA6BAQX`
- **Team ID:** `8XKPD356D2` (from `global/config/config.json`)

**Quick Reference:**
```bash
# Full provisioning for a new app (idempotent, safe to re-run)
python3 tools/apple_provision.py provision \
  --app-name "My App" --bundle-id "com.ty.myapp" \
  --capabilities push,siwa,app-groups --platform ios

# Validate credentials
python3 tools/apple_provision.py preflight

# List existing resources
python3 tools/apple_provision.py list-certs
python3 tools/apple_provision.py list-bundle-ids
python3 tools/apple_provision.py list-profiles
python3 tools/apple_provision.py list-devices

# Register a device
python3 tools/apple_provision.py register-device --name "{{USER_NAME}} iPhone" --udid "xxx"
```

**Capability shorthand:** push, siwa, app-groups, icloud, healthkit, homekit, wallet, siri, maps, game-center, in-app-purchase, associated-domains, nfc, data-protection, network-extensions, access-wifi

**Agents with access:** Mobile Dev, macOS Dev (skill sections in agent files), {{ORCHESTRATOR_NAME}} (authority)

**What requires the portal (rare):** APNs/SIWA/MusicKit keys, initial API key creation, agreement acceptance, tax/banking info

**Tool:** `tools/apple_provision.py` | **Skill:** `.claude/skills/apple-provision/SKILL.md`

---

## Browser Automation Strategy

**PRIMARY: Direct Playwright Library**

🐲 **Bowser uses direct Playwright Python library** for all complex automation:
- ✅ Full playwright-stealth integration (anti-detection)
- ✅ playwright-recaptcha for CAPTCHA solving (~85-90% success)
- ✅ Human behavior simulation (mouse, typing, pauses, typos)
- ✅ Dynamic field detection (site-agnostic)
- ✅ Complete control over timing and fingerprints

**Tool:**  `tools/registration_automation.py`

**When MCP Tools Used:**
- Quick tasks by {{ORCHESTRATOR_NAME}}/other agents (screenshots, page checks)
- **NOT for Bowser** - agent uses direct library

**Fallback: SeleniumBase UC mode** (extreme detection cases only)

**Complete guide:** See `global/docs/Browser_Automation_Guide.md`

---

## Workflow Automation

**Code-first approach.** All new automations are raw code (Python, TypeScript, shell scripts), version-controlled in git, triggered by LaunchAgents/cron/file watchers/webhooks.

### Default Stack
- **Scripts:** Python (primary) or TypeScript
- **Scheduling:** LaunchAgents (macOS launchd)
- **File watching:** `fswatch` or Python `watchdog`
- **Webhooks:** FastAPI micro-server when external push events are needed
- **Credentials:** Keychain via `global/lib/secret_provider.py`
- **Logging:** `quality.db` or structured log files
- **Visualization:** Pretty Mermaid (workflow logic) / FossFLOW (infrastructure)

### N8N (LEGACY — Available, Not Default)

An n8n instance exists but is **not the default for new automations.** Only use if explicitly requested.

**URL:** https://n8n.localhost
**Container:** builderos-n8n (Docker, via main docker-compose.yml)
**Credentials:** From Strongbox entry "n8n - Catalyst Docker"

```bash
# Start/stop (only when needed)
docker compose up -d n8n
docker compose stop n8n
```

**Existing n8n workflows** in `~/Catalyst/tools/n8n-local/workflows/` remain functional. New automations should be code-first unless there's a specific reason to use n8n.

**Complete n8n reference (if needed):** `.claude/references/agents/automation-specialist/n8n-api-and-workflows.md`
