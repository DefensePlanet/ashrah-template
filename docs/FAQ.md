# Catalyst FAQ

Common questions about the framework, how it works, and how to use it.

---

## General

### Is this just a Claude Code configuration?

**No.** Catalyst is a complete orchestration framework with:
- 29 specialist agents (each with defined roles, tools, and collaboration patterns)
- Quality pipeline (pre-commit hooks, automatic code review, quality.db observability)
- Governance framework (risk classification, privacy rules, cost gates)
- 70+ reusable skills and 30+ CLI tools
- Agent memory system (semantic search, pattern retrieval, learning loops)
- Capsule architecture for project isolation
- Stratified context loading system

A "configuration" is a `.json` file with settings. Catalyst is a multi-agent orchestration system built on top of Claude Code.

### Do I need all 29 agents?

**No.** Use what you need, delete what you don't.

Building web apps? Keep Backend Dev, Frontend Dev, Security Analyst, Code Reviewer. Delete the rest.

Running a marketing agency? Keep CMO, Graphic Designer, Camera Man, SEO Analyzer. Delete the dev agents.

Agents are just markdown files. Keep the ones relevant to your work.

### Can I use my own model?

**Yes.** Each agent has a `model:` field in its frontmatter:
- `claude-opus-4-8` (default for coding agents)
- `claude-sonnet-4-5` (default for content/design)
- `claude-haiku-4` (default for research/analysis)

### How is this different from CrewAI/Swarms?

**CrewAI/Swarms** are separate Python frameworks. You write Python scripts that orchestrate LLM calls.

**Catalyst** is Claude Code-native. Lives inside your IDE as agent definitions. No separate runtime, no Python orchestration scripts.

Key differences:
- **Quality gates** — Catalyst has automatic pre-commit review. CrewAI/Swarms don't.
- **Context management** — Stratified loading, capsule isolation, persistent memory with semantic retrieval.
- **Collaboration** — Agents have mesh coordination for peer-to-peer communication.

**Use Catalyst if** you want Claude Code to act like a coordinated team without leaving your IDE.

### Does this work with other AI assistants?

**Currently Claude Code specific.** The patterns (agent definitions, capsule architecture, quality gates) are transferable, but the implementation uses Claude Code's Task tool and hook system.

The *concepts* are universal. The *implementation* is Claude Code-native.

### What's the learning curve?

1. **Run `./setup.sh`** — 5 minutes
2. **Read `ARCHITECTURE.md`** — 15 minutes
3. **Start building** — Agents handle the complexity

You don't need to understand everything upfront. The framework is designed for progressive disclosure.

---

## Architecture

### How do capsules work?

Capsules are self-contained project workspaces. Each has its own `CLAUDE.md` with project-specific context (tech stack, specs, API docs).

```bash
cd capsules/my-web-app    # Claude loads web app context
cd capsules/my-mobile-app  # Claude loads mobile app context
```

This solves the "context soup" problem — projects don't bleed into each other.

### What is stratified context loading?

**Problem:** Claude has a context window limit. Loading everything at session start wastes tokens.

**Solution:** Main `CLAUDE.md` (~15k tokens) loads at session start. Deeper context in `.claude-context/` files loads on-demand when topics match.

{{ORCHESTRATOR_NAME}} decides what to load based on the conversation topic. You don't manage this manually.

---

## Agents

### How do I know which agent to use?

**You don't have to.** {{ORCHESTRATOR_NAME}} routes automatically.

Just describe what you want:
- "Build a REST API" -> Backend Dev
- "Design a landing page" -> UI Designer
- "Run a security audit" -> Security Analyst

For explicit control: `"Have Mobile Dev build an iOS onboarding flow"`

### Can agents collaborate?

**Yes, three ways:**
1. **Sequential handoff** — Backend Dev builds API, then Frontend Dev builds UI
2. **Mesh coordination** — Agents message each other directly to align work
3. **Agent teams** — Multiple agents work in parallel with shared task list

### What if an agent fails?

Fallback protocol:
1. First failure -> Try same agent again (may be transient)
2. Second failure -> {{ORCHESTRATOR_NAME}} implements directly
3. After implementing -> Informs you the agent needs attention

Work doesn't block on broken agents.

---

## Quality & Governance

### How does pre-commit review work?

Automatic on every `git commit`:
1. Static analysis runs (ruff, eslint, SwiftLint)
2. Code Reviewer agent analyzes changes
3. Lightweight analysis for simple changes, comprehensive for complex
4. **Blocks commit** on critical issues (security vulnerabilities, breaking bugs)
5. **Allows commit** on major/minor issues (warnings, style)

Override: `git commit --no-verify` (use sparingly)

### What are the governance rules?

Defined in `global/governance/guardrails.yaml`:
- **Privacy** — Never print secrets, never modify credentials
- **Spend** — No external costs without explicit approval
- **Safety** — Production changes require confirmation, destructive ops require explicit request

Agents enforce these automatically.

---

## Customization

### How do I add my own agent?

1. Create `.claude/agents/your-agent.md`
2. Define role, tools, skills, model, coordination
3. Update routing map in `CLAUDE.md`
4. Test: `"Have [Your Agent] do [task]"`

See [CONTRIBUTING.md](../CONTRIBUTING.md) for the full guide.

### Can I use this with my own tools?

**Yes.** Agents have full terminal access. Any CLI tool you install, they can use. Add it to the agent's tools list in their `.md` file.

---

## Performance

### Does this slow down Claude Code?

Overhead per delegation: <500ms (hook execution + memory retrieval). Negligible compared to LLM inference time. Stratified context loading keeps the window small.

---

**More questions?** Open an issue: https://github.com/{{GITHUB_USER}}/catalyst-os/issues
