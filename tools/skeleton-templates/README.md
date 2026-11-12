# Catalyst

A multi-agent AI development system for Claude Code.

## What Is This?

Catalyst is a complete Claude Code power-user framework that gives you:

- **29 specialist agents** with defined roles, expertise, and routing rules
- **Intelligent orchestration** — your main agent delegates to specialists automatically
- **Capsule architecture** — isolated project environments with their own configs and credentials
- **Quality pipeline** — Code Review, Debug, and Validate agents work in sequence
- **Feature loop** — autonomous development cycles from spec to implementation
- **484+ skills** — community and custom skills covering every major language and framework
- **Media production pipeline** — config-driven image, video, and vector generation
- **Monitoring infrastructure** — observability stack with Loki, Grafana, Prometheus
- **Governance framework** — risk classification and guardrails
- **Templates** — starter scaffolds for web, mobile, automation, and more

## Quick Start

```bash
# 1. Clone and enter the repo
git clone -b skeleton <your-repo-url> my-catalyst
cd my-catalyst

# 2. Run interactive setup
./setup.sh

# 3. (Optional) Install community skills
./setup-skills.sh

# 4. Open Claude Code
claude
```

The setup script will ask for your name and preferences, then personalize all config files.

## Architecture Overview

```
.claude/
  agents/       # 29 specialist agent definitions
  commands/     # Slash commands for common workflows
  skills/       # 484+ skills (markdown-based, model-agnostic)

.claude-context/ # Stratified context (lazy-loaded for token efficiency)

tools/           # Infrastructure tools (media engine, hooks, monitoring)

global/
  claude-config/ # Hook system, model mapping
  governance/    # Risk framework and guardrails
  docs/          # Reference documentation
  config/        # Port registry, paths

monitoring/      # Observability stack (Docker Compose)

templates/       # Project starter templates

capsules/        # Your projects live here (create with templates)
```

## Key Concepts

### Agents
Specialists like Backend Developer, Frontend Developer, Mobile Developer, etc. Each has a defined role, model tier, and skill set. Your orchestrator agent routes tasks to the right specialist.

### Capsules
Self-contained project environments. Each capsule has its own `CLAUDE.md`, credentials (`.env`), specs, and source code. Create new capsules from templates.

### Skills
Markdown-based knowledge files that any agent can reference. Includes community skills (cloned from GitHub) and custom Catalyst skills.

### Orchestration
Your main agent (the orchestrator) coordinates specialists. It routes tasks based on domain, manages handoffs, and synthesizes outputs.

## Documentation

- `docs/SETUP.md` — Detailed setup guide
- `CLAUDE.md` — Main operational instructions (read by Claude Code)
- `SOUL.md` — Operating principles and personality
- `.claude-context/` — Extended context files (architecture, integrations, strategy)

## Creating Your First Capsule

```bash
# Use the capsule template
cp -r templates/capsule-base capsules/my-project

# Edit the capsule's CLAUDE.md
# Add project-specific instructions, specs, credentials
```

See `templates/capsule-claude-md.template.md` for the full template reference.

## Community Skills

Run `./setup-skills.sh` to clone community skill repositories and set up symlinks. See `.claude/skills/community/README.md` for the full list.

## License

Private framework. Not for public distribution.
