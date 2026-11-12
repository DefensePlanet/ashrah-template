# Getting Started

This template is a multi-agent operating layer for Claude Code. One orchestrator agent, which you name during setup, sits between you and a bench of specialist agents. Work happens inside isolated project folders called capsules. Skills give the agents reusable know-how, hooks wire behaviour around every turn, and CLI tools give them hands.

Read this page first. Everything else is linked at the bottom.

## Prerequisites

- **Claude Code**, logged in (`claude login`) or with `ANTHROPIC_API_KEY` set
- **Python 3.10+** for tools and hooks
- **Node.js 18+** for MCP servers (run through `npx`) and skill tooling
- **git**
- **macOS**: most shell tooling and LaunchAgents assume it
- Optional: **Docker** (ChromaDB agent memory), **OpenAI Codex CLI** (peer review hook), **gitleaks** (secret scanning before you publish anything)

## 1. Create your repository

On GitHub, open the template and choose **Use this template → Create a new repository**. Then clone it:

```bash
git clone https://github.com/<you>/<your-repo>.git
cd <your-repo>
```

## 2. Run setup

```bash
./setup.sh
```

The tree carries double-curly placeholder tokens wherever a name, path or handle belongs. Setup asks for the values and rewrites every file, and every file or folder name, that contains one.

| Prompt | Token it fills | Used for |
|---|---|---|
| Your name | `USER_NAME` | how the agents address you |
| Orchestrator name | `ORCHESTRATOR_NAME` (plus `_LOWER` and `_UPPER` forms) | the main agent's identity in `CLAUDE.md`, file names such as `tools/<name>_session_manager.py`, env-var prefixes |
| Email (optional) | `USER_EMAIL` | tool configs that need a contact address |
| GitHub user (optional) | `GITHUB_USER` | repo URLs |
| Telegram bot and chat ID (optional) | `TELEGRAM_BOT`, `TELEGRAM_CHAT_ID` | tools that post a status line to a chat |

It also derives, without asking: `CATALYST_ROOT` (this folder), `HOME_DIR`, `USER_LOGIN` and `CLAUDE_PROJECT_SLUG` (the folder name Claude Code uses for this project's memory). It then copies `.env.example` to `.env` (mode 600), creates `memory/`, `logs/` and `capsules/`, and saves your answers to `.catalyst-config`, which also marks the copy as set up. Running `./setup.sh` again is harmless: it reports that the copy is already personalized. After pulling template updates, run `./setup.sh --apply` to fill any new tokens with your saved answers.

The orchestrator name must start with a letter. Spaces and hyphens become underscores in the lower-case form, so it stays a valid Python module name.

## 3. Add API keys

Open `.env`. Every key is listed with an empty value, grouped by the tool that reads it.

- Set `ANTHROPIC_API_KEY` first if you want the tools and hooks that call the API to work. Claude Code itself can run on your login session.
- Leave everything else empty until a tool asks for it.
- For long-lived secrets prefer the macOS Keychain: `global/lib/secret_provider.py` reads the Keychain first, then the environment.

## 4. Optional layers

Each of these is independent; skip any of them and the rest still works.

- **Community skills.** `./setup-skills.sh` clones third-party skill repositories into `.claude/skills/community/` and links the ones the agents reference.
- **MCP servers.** `.mcp.json` registers live library docs (Context7), a persistent memory graph, filesystem, terminal and browser control, shadcn/ui and Google Workspace. Remove any entry you do not want; the Google Workspace one needs your own OAuth client.
- **Peer code review.** `.claude/hooks/codex_peer_review.py` asks the Codex CLI to review each turn that changed code. Without Codex installed it does nothing.
- **Spoken summaries.** `CLAUDE.md` asks the orchestrator to end each reply with a short summary tag; a Stop hook in `.claude/settings.json` can speak it through a local Kokoro TTS server. If you do not run one, delete that hook entry and the TTS section of `CLAUDE.md`.
- **Agent memory.** A ChromaDB-backed memory server stores patterns and outcomes the orchestrator searches before delegating. When it is not running, memory steps are skipped.
- **Telegram.** `tools/telegram/` holds bot code for driving the system from your phone. Bot tokens go in the Keychain, never in tracked files.

## 5. First run

```bash
claude
```

Say hello: the orchestrator introduces itself by the name you chose. Then try:

> have Backend Dev scaffold a FastAPI hello world in a new capsule

What happens:

1. The orchestrator recognises an explicit delegation and does not write the code itself.
2. "Backend Dev" resolves through `.claude-context/agent-name-routing.json` to the registered specialist.
3. A capsule is created (or you are asked for a name) and the task is dispatched with the capsule path.
4. The specialist reads current framework docs, writes code inside `capsules/<name>/` and reports back.
5. The orchestrator summarises. `/code-review`, `/debug` and `/validate` run the quality pipeline over the result.

## 6. Create a capsule

```bash
python3 tools/capsule_creator.py --name my-project --purpose "One line on what it is for"
cd capsules/my-project && claude
```

A capsule has its own `CLAUDE.md`, `.env`, specs and code. Its `CLAUDE.md` loads on top of the root one, so agents get project context without seeing your other projects. To do it by hand, copy `templates/capsule-base` and start its `CLAUDE.md` from `templates/capsule-claude-md.template.md`.

## 7. Make it yours

- `CLAUDE.md`: tone, routing rules, non-negotiables. The Communication Style section asks for emojis; change it if you prefer plain text.
- `.claude-context/CLAUDE-strategy.md`: your priorities and portfolio, a fill-in page.
- `global/config/port-registry.yaml`: register a port for every dev server you start.
- `.claude/settings.json`: permissions and hooks. Review `defaultMode` before letting agents run unattended.

## 8. Never commit

- `.env` and any `.env.*` (root or capsule)
- `.catalyst-config` (your setup answers)
- `memory/` (session notes and checkpoints)

All of them are in `.gitignore`. Before publishing anything, run `gitleaks detect --no-git --redact`.

## 9. Building a template from your own copy

`scripts/export-template/` is the pipeline that produced this repository. Copy `export.example.yaml` to `export.yaml`, list your own names, paths and private folders, and run `scripts/export-template/export.sh --dry-run` to see what would ship.

## 10. Where next

- `CLAUDE.md`: the orchestrator's operating rules
- `ARCHITECTURE.md`: how the pieces fit
- `docs/SETUP.md`: the longer setup and customisation guide
- `.claude/agents/`: open any specialist to see how a domain is defined
- `.claude/skills/` and `.claude/commands/`: skills and slash commands
- `CONTRIBUTING.md`: conventions for adding agents, skills and capsules
- `./catalyst-doctor.sh`: checks the installation; `--fix` repairs common problems
