# Task Manager Quick Reference

## Basic Commands

### Add Task
```bash
python3 tools/task_manager.py add <capsule> "<description>" \
  --priority [low|medium|high] \
  --tags tag1 tag2 \
  --agent "Agent Name" \
  --notes "Additional notes"
```

**Example:**
```bash
python3 tools/task_manager.py add catalyst-mobile "Implement biometric auth" \
  --priority high \
  --tags mobile security ios \
  --agent "Mobile Dev" \
  --notes "Use Face ID and Touch ID"
```

### List Tasks
```bash
# All tasks across all capsules
python3 tools/task_manager.py list

# Specific capsule
python3 tools/task_manager.py list --capsule jellyfin-server-ops

# Filter by status
python3 tools/task_manager.py list --status pending

# Filter by priority
python3 tools/task_manager.py list --priority high

# Filter by tags
python3 tools/task_manager.py list --tags mobile auth

# Combine filters
python3 tools/task_manager.py list --capsule ops --status in_progress --priority high
```

### Update Task
```bash
python3 tools/task_manager.py update <capsule> <task_id> \
  --status [pending|in_progress|completed] \
  --priority [low|medium|high] \
  --description "New description" \
  --agent "New Agent"
```

**Example:**
```bash
python3 tools/task_manager.py update ops a1b2c3d4 --status in_progress
```

### Complete Task
```bash
python3 tools/task_manager.py complete <capsule> <task_id>
```

### Delete Task
```bash
python3 tools/task_manager.py delete <capsule> <task_id>
```

### Show Statistics
```bash
python3 tools/task_manager.py stats
```

### Suggest Capsule
```bash
python3 tools/task_manager.py suggest "Build iOS app with authentication"
```

## Migration Commands (JSON → YAML)

### Migrate Single Capsule
```bash
python3 tools/task_manager.py migrate <capsule>
```

**Example:**
```bash
python3 tools/task_manager.py migrate jellyfin-server-ops
```

### Migrate All Capsules
```bash
python3 tools/task_manager.py migrate --all
```

## Task Status Values

- `pending` - Not started yet (⏳)
- `in_progress` - Currently being worked on (🔄)
- `completed` - Finished (✅)

## Priority Values

- `low` - Nice to have (🔵)
- `medium` - Should be done (🟡)
- `high` - Must be done soon (🔴)

## Task Structure

```yaml
- id: a1b2c3d4              # 8-character UUID
  description: Task title   # What needs to be done
  status: pending           # pending | in_progress | completed
  priority: high            # low | medium | high
  created: '2025-01-15T10:30:00Z'    # ISO8601 timestamp
  updated: '2025-01-15T10:30:00Z'    # ISO8601 timestamp
  assigned_agent: Backend Dev        # Agent responsible
  dependencies: []                   # List of task IDs
  tags:                              # List of tags
  - backend
  - security
  source: manual            # How task was created
  notes: Additional info    # Extra details
  completed_at: null        # Completion timestamp (or null)
```

## Capsule Keywords (for auto-routing)

Use `suggest` command to find the right capsule:

- **jellyfin-server-ops:** media, server, jellyfin, streaming, plex, movies, tv
- **brandjack:** instagram, brand, social, content, posting, engagement
- **catalyst-mobile:** mobile, ios, android, app, swift, react native, xcode
- **ecommerce:** store, shop, shopify, products, checkout, sales
- **builder-system:** system, builder, {{ORCHESTRATOR_NAME_LOWER}}, framework, core, tools
- **ops:** operations, deployment, infrastructure, servers, monitoring

## File Locations

**Task Files:**
- New format: `capsules/<capsule>/tasks.yaml`
- Legacy format: `capsules/<capsule>/tasks.json` (auto-upgraded on save)
- Backup: `capsules/<capsule>/tasks.json.backup` (after migration)

## Pro Tips

### 1. Use Tags for Filtering
Tags help organize and filter tasks across capsules:
```bash
python3 tools/task_manager.py list --tags security auth
```

### 2. Track Dependencies
Link tasks that depend on each other:
```yaml
dependencies:
- a1b2c3d4  # Wait for auth task to complete
```

### 3. Assign Agents
Route work to the right specialist:
```bash
--agent "Backend Dev"
--agent "Mobile Dev"
--agent "UI Designer"
```

### 4. Add Detailed Notes
Use notes for context:
```bash
--notes "Implement JWT-based auth with refresh tokens, use bcrypt for password hashing"
```

### 5. Monitor with Statistics
Track overall progress:
```bash
python3 tools/task_manager.py stats
```

## Common Workflows

### Starting a New Feature
```bash
# 1. Add task with high priority
python3 tools/task_manager.py add catalyst-mobile "Build user profile screen" \
  --priority high \
  --tags frontend ui mobile \
  --agent "Mobile Dev"

# 2. Mark as in progress when starting
python3 tools/task_manager.py update catalyst-mobile <task_id> --status in_progress

# 3. Complete when done
python3 tools/task_manager.py complete catalyst-mobile <task_id>
```

### Reviewing Capsule Tasks
```bash
# See all tasks for a capsule
python3 tools/task_manager.py list --capsule ops

# Check what's in progress
python3 tools/task_manager.py list --capsule ops --status in_progress

# View high-priority items
python3 tools/task_manager.py list --capsule ops --priority high
```

### Cross-Capsule Task Management
```bash
# See all high-priority tasks across all capsules
python3 tools/task_manager.py list --priority high

# Find all security-related tasks
python3 tools/task_manager.py list --tags security

# Review everything in progress
python3 tools/task_manager.py list --status in_progress
```

---

**Version:** task_manager.py v2.0 (YAML support)
**Updated:** 2025-10-27
