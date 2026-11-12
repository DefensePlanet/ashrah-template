# System Architecture (Lazy-Loaded Section)
<!-- Last updated: 2026-02-24 -->

## How The System Currently Works

### Architecture Pattern: Capsules
- Each project = self-contained capsule with full lifecycle folders
- Immutable once deployed for stability
- Clean isolation between projects
- **Framework Structure**: Every capsule includes:
  - `standards.yaml` - Quality/compliance framework
  - `product.yaml` - Capability roadmap & vision
  - `specs/current.yaml` & `specs/next.yaml` - Implementation specifications
  - `context/` - Decisions, patterns, and evolution documentation

### Workflow Pattern: Unified Pipeline
- Streamlined build process with consistent quality standards
- Automated validation and deployment pipeline
- **Spec-Kit Enhanced Tools**: Schema validation, documentation generation, and sophisticated template substitution

### Agent Pattern: Collaborative Intelligence
- Claude Code agents + human approval loops
- Context persists via CLAUDE.md + MCP memory
- **Memory Intelligence System**: 36 learned patterns, 189 knowledge documents, 100% operational
- **Consultation Mode**: Provide reasoning and alternatives, not just compliance
- **Wisdom Over Agreement**: Challenge decisions when technical merit warrants it
- **Bypass Permissions - DEFAULT MODE**: Automatic for all Catalyst work. {{ORCHESTRATOR_NAME}} provides technical consultation and risk analysis; {{USER_NAME}} proceeds with full authority

**Agent System Overview:**
- **30 specialist agents** available (full list in "Orchestration Self-Awareness" section below)
- **Agent behavior** defined within each agent's prompt (specialized capabilities and standards)
- **82+ skills** (26 custom + community) for workflow automation and specialist capabilities
- Agent names include emojis - use EXACT names when invoking via Task tool
- See Orchestration section for complete agent domain mapping

### Maintenance Pattern: Lifecycle Care
- Not just build-and-forget
- Ongoing health monitoring and refinement
- Daily automation at 9:10 AM via LaunchAgent

### Repository Architecture: Single Private Repo

**{{ORCHESTRATOR_NAME}} lives in ONE private repository: `{{GITHUB_USER}}/{{ORCHESTRATOR_NAME_LOWER}}`. There is no upstream and no public mirror.**

| | |
|---|---|
| **Repo** | `{{GITHUB_USER}}/{{ORCHESTRATOR_NAME_LOWER}}` (private) |
| **Purpose** | Full system backup — restores everything if the machine dies |
| **Contains** | Complete system (minus .gitignore) — capsules, agents, tools, hooks, context. Credentials stay in `.env`/Keychain and are never committed |
| **Local** | `~/catalyst-os` (folder rename to `~/{{ORCHESTRATOR_NAME_LOWER}}` is a separate pass) |
| **Legacy history** | branch `catalyst-legacy` — read-only lineage from the original Catalyst fork; never merged |

**Rules:**
- `origin` is the only remote. Never add another
- Never fetch from the original Catalyst repositories — {{ORCHESTRATOR_NAME}} does not receive upstream updates
- There is no public sync pipeline. A public export, if ever wanted, is a deliberate new project

## Current State (What You're Working With)
- **Production:** 31 capsules in active use (see `capsules/` directory)
- **Templates:** 14 starter templates
- **Health:** Daily audits passing, test isolation working
- **Integration:** Code-first automations (Python/LaunchAgents), shadcn-ui components, Xcode project linking
