# Catalyst Setup Guide

## Prerequisites

- **Claude Code** — Anthropic's CLI (`npm install -g @anthropic-ai/claude-code`)
- **Python 3.10+** — For tools and hooks
- **Node.js 18+** — For MCP servers and skill tooling
- **Git** — For version control and community skills
- **Docker** (optional) — For monitoring stack and agent memory

## First-Time Setup

### 1. Run the Setup Script

```bash
./setup.sh
```

This will:
- Ask for your name and orchestrator preferences
- Replace all `{{PLACEHOLDER}}` tokens in config files
- Create `.env` from `.env.example`
- Save your choices to `.catalyst-config` for future updates

### 2. Configure API Keys

Edit `.env` and add your API keys:

```bash
ANTHROPIC_API_KEY=sk-ant-...     # Required for Claude Code
OPENROUTER_API_KEY=sk-or-...     # For multi-model routing (optional)
GEMINI_API_KEY=...                # For image/video generation (optional)
```

### 3. Install Community Skills (Optional)

```bash
./setup-skills.sh
```

This clones 13 community skill repositories and creates symlinks. See `.claude/skills/community/README.md` for the full list.

### 4. Set Up MCP Servers (Optional)

Edit `.mcp.json` to configure MCP servers for your environment. Key servers:

- **filesystem** — File system access (works out of the box)
- **playwright** — Browser automation
- **context7** — Library documentation lookup
- **agent-memory** — Long-term agent learning (requires Docker)

### 5. Start Claude Code

```bash
cd /path/to/your/catalyst
claude
```

Your orchestrator will activate with the full agent system.

---

## Understanding the System

### Agent System

29 specialist agents live in `.claude/agents/`. Each has:
- A defined role and expertise domain
- A model tier (Opus for coding, Sonnet/Haiku for non-coding)
- Skills and reference documentation
- Routing rules for when to invoke them

Your orchestrator (the main Claude instance) routes tasks to the right specialist automatically.

### Capsules

Capsules are self-contained project environments at `capsules/`. Each capsule has:

```
capsules/my-project/
  CLAUDE.md          # Project-specific instructions
  .env               # Project credentials (gitignored)
  specs/             # Data models and schemas
  docs/              # Project documentation
  src/               # Source code
```

Create a new capsule:
```bash
cp -r templates/capsule-base capsules/my-project
# Edit capsules/my-project/CLAUDE.md with your project details
```

### Skills

Skills are markdown files that give agents specialized knowledge. They live in `.claude/skills/` and include:

- **Custom skills** (38) — Catalyst-specific capabilities
- **Community skills** (400+) — Third-party repos covering SwiftUI, React, SEO, etc.

Install individual skills: `npx skills find <topic>`

### Commands

Slash commands in `.claude/commands/` provide shortcuts for common workflows:
- `/build-feature` — Autonomous feature development loop
- `/code-review` — Manual code review
- `/debug` — Systematic debugging
- `/validate` — Comprehensive testing

### Hooks

Pre/post tool-use hooks in `global/claude-config/hooks/` provide:
- Orchestration routing reminders
- Task outcome logging
- Agent memory integration

### Monitoring (Optional)

The monitoring stack uses Docker Compose:

```bash
cd monitoring
docker compose up -d
```

This starts Loki (logs), Grafana (dashboards), and Prometheus (metrics).

---

## Updating

When the upstream skeleton branch gets new features:

```bash
# Fetch updates
git fetch origin skeleton
git merge origin/skeleton

# Re-apply your personalization
./setup.sh --apply
```

The `--apply` flag reads your saved `.catalyst-config` and re-runs the placeholder replacement without prompting.

---

## Customization

### Adding a New Agent

1. Create `.claude/agents/my-specialist.md` with YAML frontmatter
2. Add routing rules to `CLAUDE.md` under the agent routing section
3. Add name mapping to `.claude-context/agent-name-routing.json`

### Adding a New Command

1. Create `.claude/commands/my-command.md`
2. The command becomes available as `/my-command` in Claude Code

### Adding a New Skill

1. Create `.claude/skills/my-skill/SKILL.md`
2. Reference it in relevant agent files

### Creating Capsule-Specific Commands

Commands can navigate to capsules:
```markdown
# .claude/commands/my-project.md
Navigate to capsule: capsules/my-project
Load capsule CLAUDE.md and begin work.
```
