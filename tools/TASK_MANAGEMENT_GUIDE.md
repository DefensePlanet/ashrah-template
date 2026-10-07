# Catalyst Task Management System

Complete guide to the persistent task management system for Catalyst capsules.

## Overview

The Catalyst Task Management System provides persistent, cross-session task tracking with three integrated interfaces:

1. **CLI Tools** - Command-line task management (`task_manager.py`)
2. **Web Dashboard** - Visual Kanban board at `localhost:3000`
3. **TodoWrite Integration** - Sync with Claude Code's TodoWrite tool

---

## Quick Start

### View All Pending Tasks
```bash
python3 tools/load_capsule_tasks.py
```

### Add a Task
```bash
python3 tools/task_manager.py add <capsule> "<description>" --priority high --tags feature
```

### Complete a Task
```bash
python3 tools/task_manager.py complete <capsule> <task-id>
```

### Start Dashboard
```bash
cd tools/task_dashboard
npm run dev
# Open http://localhost:3000
```

---

## CLI Tools

### task_manager.py - Core Task Operations

**Add Task:**
```bash
python3 tools/task_manager.py add brandjack "Add carousel scheduling" \
  --priority high \
  --tags feature scheduling \
  --agent "Frontend Specialist" \
  --notes "Use shadcn carousel component"
```

**List Tasks:**
```bash
# All tasks
python3 tools/task_manager.py list

# Filter by capsule
python3 tools/task_manager.py list --capsule brandjack

# Filter by status
python3 tools/task_manager.py list --status pending

# Filter by priority and tags
python3 tools/task_manager.py list --priority high --tags security
```

**Update Task:**
```bash
python3 tools/task_manager.py update brandjack abc123 \
  --status in_progress \
  --priority high \
  --description "Updated description"
```

**Complete Task:**
```bash
python3 tools/task_manager.py complete brandjack abc123
```

**Delete Task:**
```bash
python3 tools/task_manager.py delete brandjack abc123
```

**View Statistics:**
```bash
python3 tools/task_manager.py stats
```

**Suggest Capsule (Smart Routing):**
```bash
python3 tools/task_manager.py suggest "Fix Instagram scraping bug"
# → Suggested capsule: brandjack
```

### load_capsule_tasks.py - Session Startup

**Show Pending Tasks:**
```bash
python3 tools/load_capsule_tasks.py
```

**Verbose Mode (show details):**
```bash
python3 tools/load_capsule_tasks.py --verbose
```

**Statistics:**
```bash
python3 tools/load_capsule_tasks.py --stats
```

**Add to your shell startup** (optional):
```bash
# Add to ~/.zshrc or ~/.bashrc
cd {{CATALYST_ROOT}} && python3 tools/load_capsule_tasks.py
```

---

## Web Dashboard

### Features

- **Kanban Board** - Drag tasks between Pending → In Progress → Completed
- **Visual Priority** - 🔴 High, 🟡 Medium, 🔵 Low
- **Filtering** - By capsule and priority
- **Real-time Updates** - Auto-refresh every 5 seconds
- **Full CRUD** - Create, edit, delete tasks directly in UI
- **Task Details** - Click any task to view/edit

### Running the Dashboard

**Manual Start:**
```bash
cd {{CATALYST_ROOT}}/tools/task_dashboard
npm run dev
# Dashboard available at http://localhost:3000
```

**Quick Start Script:**
```bash
cd {{CATALYST_ROOT}}/tools/task_dashboard
./start.sh
```

**Install as LaunchAgent (auto-start on demand):**
```bash
cd {{CATALYST_ROOT}}/tools/task_dashboard
./install_launchagent.sh

# Start dashboard
launchctl start com.builderos.taskdashboard

# Stop dashboard
launchctl stop com.builderos.taskdashboard

# Check status
launchctl list | grep builderos
```

**Uninstall LaunchAgent:**
```bash
cd {{CATALYST_ROOT}}/tools/task_dashboard
./uninstall_launchagent.sh
```

### Dashboard Logs

```bash
# LaunchAgent logs
tail -f ~/Library/Logs/builderos-taskdashboard.log

# Manual run logs (if using start.sh or npm run dev)
tail -f /tmp/task_dashboard.log
```

---

## TodoWrite Integration

Sync ephemeral TodoWrite (session-based) with persistent tasks.json files.

### From Within a Capsule

**Navigate to capsule:**
```bash
cd {{CATALYST_ROOT}}/capsules/brandjack
```

**Load tasks for TodoWrite:**
```bash
../../tools/sync_todowrite.py load
# Shows tasks in text format

../../tools/sync_todowrite.py load --format json
# Shows tasks in JSON format (copy into TodoWrite tool)
```

**Check sync status:**
```bash
../../tools/sync_todowrite.py status
```

**Quick helper commands:**
```bash
../../tools/todowrite_helper.sh load          # Show tasks
../../tools/todowrite_helper.sh load-json     # Get JSON for TodoWrite
../../tools/todowrite_helper.sh status        # Show status
../../tools/todowrite_helper.sh complete abc  # Complete task
../../tools/todowrite_helper.sh add "Fix bug" # Quick add
```

### Workflow: TodoWrite ↔ Persistent Tasks

1. **Load tasks at session start:**
   ```bash
   cd capsules/brandjack
   ../../tools/sync_todowrite.py load --format json
   # Copy JSON into TodoWrite tool
   ```

2. **Work on tasks** (use TodoWrite normally in Claude Code)

3. **Sync completed tasks back:**
   - Manually update via CLI: `task_manager.py complete ...`
   - Or dashboard: Drag task to "Completed" column

---

## Task File Format

Each capsule has a `tasks.json` file:

```json
[
  {
    "id": "abc123",
    "description": "Add carousel post scheduling",
    "status": "pending",
    "priority": "high",
    "created": "2025-10-20T22:30:00Z",
    "updated": "2025-10-20T22:30:00Z",
    "assigned_agent": "Frontend Specialist",
    "dependencies": [],
    "tags": ["feature", "scheduling"],
    "source": "manual",
    "notes": "Use shadcn carousel component",
    "completed_at": null
  }
]
```

**Field Definitions:**
- `id` - Unique 8-char ID
- `description` - Task description
- `status` - `pending`, `in_progress`, or `completed`
- `priority` - `low`, `medium`, or `high`
- `created` - ISO 8601 timestamp (UTC)
- `updated` - ISO 8601 timestamp (UTC)
- `assigned_agent` - Optional agent name
- `dependencies` - Array of task IDs this depends on
- `tags` - Array of tags
- `source` - How task was created (`manual`, `todowrite`, `telegram`, etc.)
- `notes` - Additional notes
- `completed_at` - ISO 8601 timestamp when completed (null if pending)

---

## Smart Capsule Routing

The task manager includes keyword-based capsule suggestions:

```bash
python3 tools/task_manager.py suggest "Fix Instagram scraping"
# → brandjack

python3 tools/task_manager.py suggest "Add Jellyfin automation"
# → jellyfin-server-ops

python3 tools/task_manager.py suggest "Build iOS app feature"
# → builder-system-mobile
```

**Keyword Mappings:**
- `brandjack`: instagram, brand, social, content, posting, followers, scraping
- `jellyfin-server-ops`: media, server, jellyfin, streaming, plex, movies, tv
- `builder-system-mobile`: mobile, ios, android, app, swift, react native, xcode
- `ecommerce`: store, shop, shopify, products, checkout, sales
- `ops`: operations, deployment, infrastructure, servers, monitoring
- (See `task_manager.py` for full list)

---

## Common Workflows

### Daily Workflow

**Morning:**
```bash
# Check pending tasks
python3 tools/load_capsule_tasks.py

# Start dashboard for visual management
cd tools/task_dashboard && npm run dev
```

**During Work:**
- Use dashboard to drag tasks to "In Progress"
- Click tasks to add notes or update details
- Add new tasks as they come up (dashboard or CLI)

**End of Day:**
- Mark completed tasks via dashboard drag or CLI
- Review pending tasks for tomorrow

### Capsule-Specific Work

**When working on a specific capsule:**
```bash
cd capsules/brandjack

# See capsule tasks
../../tools/todowrite_helper.sh load

# Add quick task
../../tools/todowrite_helper.sh add "Fix authentication"

# Complete task
../../tools/todowrite_helper.sh complete abc123
```

### Multi-Capsule Projects

**Filter tasks across multiple capsules:**
```bash
# See all high-priority tasks
python3 tools/task_manager.py list --priority high

# See all tasks with 'security' tag
python3 tools/task_manager.py list --tags security

# Use dashboard filters for visual overview
```

---

## Tips & Best Practices

### Task Descriptions
- **Be specific:** "Add carousel post scheduling" > "Fix UI"
- **Include context:** "Fix Instagram API rate limiting (429 errors)"
- **Action-oriented:** Start with verb (Add, Fix, Implement, Refactor)

### Priority Guidelines
- 🔴 **High**: Blocking work, critical bugs, urgent features
- 🟡 **Medium**: Important but not blocking, planned features
- 🔵 **Low**: Nice-to-haves, tech debt, documentation

### Tags
Use tags for cross-cutting concerns:
- `feature`, `bug`, `refactor`, `docs`, `test`
- `security`, `performance`, `ux`
- `blocked`, `waiting`, `research`

### Dependencies
Track task dependencies explicitly:
```bash
# Task B depends on Task A
python3 tools/task_manager.py add brandjack "Deploy feature" \
  --tags deployment \
  --notes "Dependencies: [abc123]"
```

### Agent Assignment
Assign tasks to specific agents for routing:
```bash
--agent "Frontend Specialist"
--agent "Backend Specialist"
--agent "Security Analyst"
```

---

## Troubleshooting

### Dashboard Won't Start

**Check if port 3000 is in use:**
```bash
lsof -ti:3000
# If something is using port 3000, kill it:
kill -9 $(lsof -ti:3000)
```

**Check Node.js version:**
```bash
node --version  # Should be 18+
```

**Reinstall dependencies:**
```bash
cd tools/task_dashboard
rm -rf node_modules package-lock.json
npm install
```

### Tasks Not Showing

**Check if tasks.json exists:**
```bash
ls capsules/*/tasks.json
```

**Validate JSON format:**
```bash
cat capsules/brandjack/tasks.json | python3 -m json.tool
```

**Check file permissions:**
```bash
ls -la capsules/brandjack/tasks.json
```

### TodoWrite Sync Issues

**Verify you're in a capsule directory:**
```bash
pwd  # Should be {{CATALYST_ROOT}}/capsules/<name>
ls   # Should see specs/ or spec/ directory
```

**Check Python path:**
```bash
which python3
python3 --version  # Should be 3.9+
```

---

## Future Enhancements (Telegram Bot - Phase 2)

Coming soon: Capture tasks on-the-go via Telegram bot.

**Planned workflow:**
1. Message bot: `/task brandjack Add carousel feature`
2. Bot creates task in `capsules/brandjack/tasks.json`
3. Task appears in dashboard and CLI immediately
4. Confirmation sent to Telegram

**Setup will include:**
- `tools/telegram_task_bot.py` - Bot implementation
- BotFather bot creation
- LaunchAgent for auto-start
- Smart capsule routing from message content

---

## File Reference

### Core Tools
- `tools/task_manager.py` - Main task CRUD operations
- `tools/load_capsule_tasks.py` - Session startup task display
- `tools/sync_todowrite.py` - TodoWrite integration
- `tools/todowrite_helper.sh` - Convenience wrapper for capsule work

### Dashboard
- `tools/task_dashboard/` - Next.js web app
- `tools/task_dashboard/start.sh` - Quick start script
- `tools/task_dashboard/install_launchagent.sh` - Auto-start setup
- `tools/task_dashboard/README.md` - Dashboard-specific docs

### Data Files
- `capsules/*/tasks.json` - Persistent task storage (one per capsule)
- `~/Library/Logs/builderos-taskdashboard.log` - Dashboard logs (LaunchAgent)

---

## Support

For issues or questions:
1. Check this guide
2. Review README files in specific tools
3. Check Catalyst main CLAUDE.md for system context

---

**Built by {{ORCHESTRATOR_NAME}} on 2025-10-20**
*Evolution principle: This system will adapt as Catalyst needs evolve.*
