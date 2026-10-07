# Ashrah Template

**Run your own AI chief of staff on top of Claude Code: one orchestrator you name, a bench of specialist agents, skills, CLI tools, hooks and isolated project capsules, wired together as one system.**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Built with Claude Code](https://img.shields.io/badge/Built_with-Claude_Code-blueviolet.svg)](https://claude.com/claude-code)

---

You talk to one agent. It decides who should do the work, sends independent tasks out in parallel, chains the ones that depend on each other, checks the results and reports back. Each project lives in its own capsule, so the agents only ever see the context and credentials of the project you are in.

This repository is a template generated from a working private system and scrubbed of everything personal. Run `./setup.sh` once and it becomes yours: your name, your orchestrator's name, your paths.

## What you get

- **One orchestrator, named by you.** `CLAUDE.md` is its rulebook: delegate instead of implementing, resolve agent names, parallelize by default, verify before claiming done. Deeper context loads on demand from `.claude-context/`.
- **Specialist agents** (`.claude/agents/`, 30+). Backend, frontend, mobile, macOS, automation, browser automation, UI and graphic design, AI media, 3D, security, research, algorithms, product, marketing, SEO, a quality pipeline (Code Reviewer, Debugger, Validator) and more. Each is one markdown file with its domain, tools and hand-off rules.
- **Skills** (`.claude/skills/`, 80+). Reusable playbooks: iOS testing, Playwright, Mermaid diagrams, Shopify, Remotion, Postgres tuning, security reviews and many others. `./setup-skills.sh` links in the community skills several agents reference.
- **Tools** (`tools/`). CLI-first Python, shell and TypeScript utilities the agents call directly. MCP servers (`.mcp.json`) only where they earn their place: live library docs, memory, browser and terminal control.
- **Hooks** (`.claude/settings.json`, `tools/hooks/`). Session start and end, routing reminders, an optional post-turn peer code review, and an optional spoken summary.
- **Capsules** (`capsules/`). One folder per project with its own `CLAUDE.md`, `.env`, specs and code. `capsules/example/` shows the shape; `templates/` holds starters for web, iOS, React Native, automation and e-commerce projects.

## Quick start

```bash
# 1. On GitHub: "Use this template" -> create your repository, then
git clone https://github.com/<you>/<your-repo>.git
cd <your-repo>

# 2. Personalize (asks your name and your orchestrator's name)
./setup.sh

# 3. Optional community skills
./setup-skills.sh

# 4. Go
claude
```

Then ask for real work:

- "Have Backend Dev scaffold a FastAPI service in a new capsule called notes-api"
- "Ask the Security Analyst to review this repo"
- "Have the UI Designer and Frontend Dev build a landing page for my side project"

The full walkthrough, including API keys and the optional layers, is in [GETTING-STARTED.md](GETTING-STARTED.md).

## Requirements

macOS (most shell tooling assumes it), Claude Code, Python 3.10+, Node.js 18+ and git. Docker, the Codex CLI and a Telegram bot are optional extras.

## Layout

```
CLAUDE.md          the orchestrator's rules (loaded every session)
.claude/           agents, skills, slash commands, hooks, settings
.claude-context/   on-demand context: architecture, orchestration, strategy
capsules/          one isolated workspace per project
global/            governance, config (port registry), shared libraries
tools/             CLI tools and small servers
templates/         capsule and project starters
scripts/           system-wide automations
docs/              system documentation
```

## Credits and license

Built by John Hartin. Released under the [MIT License](LICENSE).
