---
name: new-capsule
description: Create a new Catalyst capsule with Telegram supergroup and navigation shortcut
when: User requests a new capsule, or says "create capsule [name]" or "new capsule"
allowed-tools:
  - Bash
  - Read
  - Write
  - Edit
  - Task
metadata:
  version: "3.0.0"
  automation: "Full"
  creates:
    - Capsule directory structure
    - Telegram supergroup (auto, with {{ORCHESTRATOR_NAME}} as admin)
    - Navigation shortcut skill
    - CAPSULES_INDEX.md entry
  note: "Telegram supergroup creation is now AUTOMATIC. Bot creation is still OPT-IN (--with-bot) due to 20-bot limit."
  last_updated: "2026-03-02"
---

# Capsule Creator Skill (Fully Automated)

## Purpose
Create complete Catalyst capsules with all standard integrations:
1. **Directory structure** with CLAUDE.md, README.md
2. **Telegram supergroup** (auto — {{ORCHESTRATOR_NAME}} invited + admin, registered in capsule-registry.json)
3. **Navigation shortcut** (`/[name]` command)
4. **Index registration** in CAPSULES_INDEX.md

**NOTE:** Telegram bot creation is still **opt-in** due to Telegram's 20-bot limit.
- Use `--with-bot` flag during creation, OR
- Use `/telegram-bot-setup` skill after capsule is created

## When to Use
- "Create a new capsule called [name]"
- "New capsule for [purpose]"
- "Set up a capsule for [project]"

## Required Inputs
- **name**: Capsule name (kebab-case, e.g., "my-project")
- **purpose**: Brief description of what the capsule is for
- **privacy** (optional): "normal" or "high" (default: normal)

## Execution Flow

### Step 1: Validate & Derive Names
```python
# From capsule name "my-cool-project":
capsule_name = "my-cool-project"
short_name = "cool"  # First unique word for nav shortcut
display_name = "My Cool Project"
nav_command = "/cool"
bot_username = "MyCoolProjectBot"
```

### Step 2: Create Capsule Directory with YAML Spec
```bash
mkdir -p {{CATALYST_ROOT}}/capsules/[capsule-name]/specs
mkdir -p {{CATALYST_ROOT}}/capsules/[capsule-name]/docs
```

Create standard files:
- `specs/current.yaml` - Source of truth for context engineering
- `CLAUDE.md` - Auto-generated from specs (via generate_claude_md.py)
- `README.md` - Human-readable overview
- `.gitignore` - Standard ignores
- `docs/` - Documentation directory

### Step 3: Create Telegram Supergroup (Automatic)
- Creates a Telegram supergroup named after the capsule
- Invites @{{ORCHESTRATOR_NAME}}CatalystBot and promotes to admin
- Registers the chat ID in `capsule-registry.json`
- {{ORCHESTRATOR_NAME}} can see all messages without @tagging
- Skip with `--skip-supergroup` flag

### Step 4: Create Navigation Shortcut
Create skill at `.claude/skills/[short]/skill.md`:

**IMPORTANT: Shortcut names are ONE WORD ONLY. Never include "navigate", "navigation", or similar words.**

```yaml
---
name: [short]
description: Navigate to [Display Name] capsule
when: User types /[short] or mentions [capsule-name]
allowed-tools:
  - Bash
metadata:
  capsule: "[capsule-name]"
---
```

### Step 5: Update CAPSULES_INDEX.md
Append entry:
```markdown
### [capsule-name]/
**Purpose:** [purpose]
**Nav:** /[short]
**Bot:** (use /telegram-bot-setup if needed)
```

### Step 5: Report Success
```
✅ Capsule Created: [Display Name]

📁 Location: {{CATALYST_ROOT}}/capsules/[capsule-name]
🔗 Navigation: /[short]

Next steps:
1. Edit specs/current.yaml to customize context
2. (Optional) Create Telegram bot: /telegram-bot-setup
3. Use /[short] to navigate here
```

## Full Automation Script

Run everything via:
```bash
# Standard capsule (auto-creates Telegram supergroup)
python3.12 {{CATALYST_ROOT}}/tools/capsule_creator.py \
  --name "[capsule-name]" \
  --purpose "[description]" \
  --privacy "normal|high"

# Skip Telegram supergroup creation
python3.12 {{CATALYST_ROOT}}/tools/capsule_creator.py \
  --name "[capsule-name]" \
  --purpose "[description]" \
  --skip-supergroup

# With Telegram bot (opt-in, mind the 20-bot limit)
python3.12 {{CATALYST_ROOT}}/tools/capsule_creator.py \
  --name "[capsule-name]" \
  --purpose "[description]" \
  --with-bot
```

## Examples

**Example 1: Simple capsule**
```
User: Create a capsule for tracking my fitness goals
{{ORCHESTRATOR_NAME}}: Creating "fitness-tracker" capsule...

✅ Capsule Created: Fitness Tracker

📁 Location: capsules/fitness-tracker
🔗 Navigation: /fitness

Next: Use /telegram-bot-setup if you want a bot for this capsule
```

**Example 2: Privacy-sensitive capsule**
```
User: Create a capsule for my therapy notes, high privacy
{{ORCHESTRATOR_NAME}}: Creating "therapy-notes" capsule with high privacy...

✅ Capsule Created: Therapy Notes

📁 Location: capsules/therapy-notes
🔗 Navigation: /therapy
🔒 Privacy: High (local-only by default)
```

**Example 3: Capsule with Telegram bot (explicit request)**
```
User: Create a capsule for my meal prep with a bot
{{ORCHESTRATOR_NAME}}: Creating "meal-prep" capsule with Telegram bot...

✅ Capsule Created: Meal Prep

📁 Location: capsules/meal-prep
📱 Telegram: @MealPrepBot
🔗 Navigation: /meal
```

## Directory Structure Created

```
capsules/[capsule-name]/
├── CLAUDE.md           # Auto-generated from specs (don't edit directly)
├── README.md           # Human-readable overview
├── .gitignore          # Ignore sensitive files
├── specs/
│   └── current.yaml    # Source of truth for context engineering
├── docs/
│   └── README.md       # Documentation home
└── notes/              # (if high privacy)
    └── .gitkeep
```

## Context Engineering with YAML Specs

Each capsule uses **YAML specifications** for context engineering. The `specs/current.yaml` is the source of truth:

```yaml
name: [Display Name]
version: 0.1.0
status: active
last_updated: [date]

purpose:
  what: [purpose description]
  why: To be defined
  for_whom: {{USER_NAME}}

current:
  phase: setup
  health: healthy

technical:
  stack:
    - To be defined
  dependencies:
    external: []
    internal: []

capabilities:
  - Initial setup complete

guardrails:
  - Standard security practices
  - Follow Catalyst conventions

development:
  workflow: Standard Catalyst workflow
  tools:
    - Claude Code
    - Telegram bot (optional, use /telegram-bot-setup)

vision:
  statement: To be defined
  roadmap: []

relationships:
  feeds_into: []
  consumes_from: []
  shared_with: []
```

## Regenerating CLAUDE.md

After editing `specs/current.yaml`, regenerate CLAUDE.md:
```bash
python3 {{CATALYST_ROOT}}/tools/generate_claude_md.py {{CATALYST_ROOT}}/capsules/[capsule-name]
```

Or regenerate all capsules:
```bash
python3 {{CATALYST_ROOT}}/tools/generate_claude_md.py --all
```

## Integration Points

- **telegram-bot-setup skill**: Available for on-demand bot creation (not auto-called)
- **nav.py**: Capsule auto-discovered for keyword navigation
- **CAPSULES_INDEX.md**: Master registry of all capsules

## On-Demand Telegram Bot Creation

If the user needs a Telegram bot for an existing capsule (or wants one during creation):

```
User: "Add a telegram bot to my fitness capsule"
→ Use /telegram-bot-setup skill

User: "Create a capsule with a bot"
→ Add --with-bot flag to capsule_creator.py
```

**Note:** Telegram limits accounts to 20 bots. Only create bots for capsules that truly need mobile access.

## Error Handling

- If capsule already exists → Ask to overwrite or pick new name

**If creating with --with-bot:**
- If bot username taken → Suggest alternatives
- If Telethon not authenticated → Prompt to run telethon_auth.py
