# CodeRabbit CLI Integration

## Overview
CodeRabbit CLI is an AI-powered code review tool integrated into BuilderOS as a **complementary automated scanning tool** that works alongside existing code review infrastructure.

## Complementary Architecture

**CodeRabbit does NOT replace existing systems:**

| Tool | Purpose | When to Use |
|------|---------|-------------|
| **CodeRabbit CLI** (`/review`) | Fast automated first-pass scanning | Quick feedback loop during development |
| **Code Reviewer Agent** | Deep capsule-aware quality analysis | Comprehensive Builder-specific review |
| **`/pr-review` Command** | Multi-perspective PR review | Full product/security/UX/DevOps review |

**Integration Philosophy:** CodeRabbit adds automated scanning as the first layer in a multi-tiered review system. It catches obvious issues quickly, allowing human/agent reviewers to focus on architecture, business logic, and Builder-specific concerns.

**Installed:** November 4, 2025
**Version:** 0.3.4
**Status:** Beta
**Authenticated User:** {{GITHUB_USER}} (GitHub)

## Quick Start

### Slash Command
```
/review
```
Runs CodeRabbit on current git repository changes and provides comprehensive feedback.

### Direct CLI Usage
```bash
# Detailed analysis with fix suggestions
coderabbit review --plain

# Token-efficient minimal output
coderabbit review --prompt-only

# Short alias
cr --help
```

## Multi-Tiered Review Workflow

```
┌─────────────────────────────────────────────────────────────┐
│                    CODE CHANGES MADE                         │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
         ┌────────────────────────┐
         │   Layer 1: Automated   │
         │   /review (CodeRabbit) │  ← Fast AI scanning
         │   - Security scan      │    (seconds)
         │   - Performance check  │
         │   - Quick fixes        │
         └────────┬───────────────┘
                  │
                  ▼ Apply obvious fixes
                  │
         ┌────────────────────────┐
         │   Layer 2: Builder-    │
         │   Aware Deep Review    │  ← Capsule compliance
         │   Code Reviewer Agent  │    (minutes)
         │   - Capsule patterns   │
         │   - DoD validation     │
         │   - requirements.yaml  │
         └────────┬───────────────┘
                  │
                  ▼ Fix architectural issues
                  │
         ┌────────────────────────┐
         │   Layer 3: Multi-      │
         │   Perspective Review   │  ← Holistic validation
         │   /pr-review command   │    (before PR)
         │   - Product Manager    │
         │   - Security Engineer  │
         │   - QE, DevOps, UX     │
         └────────┬───────────────┘
                  │
                  ▼
         ┌────────────────────────┐
         │   COMMIT / PULL        │
         │   REQUEST              │
         └────────────────────────┘
```

## Integration Points

### 1. Slash Command (`/review`)
- **Location:** `.claude/commands/review.md`
- **Purpose:** Fast automated first-pass scanning
- **Position:** Layer 1 in review workflow
- **Output:** Prioritized findings (security → bugs → performance → style)

### 2. Code Reviewer Agent Enhancement
- **Location:** `global/claude-config/agents/code-reviewer.md`
- **Enhancement:** Added optional CodeRabbit scan as step 2 in review process
- **Relationship:** CodeRabbit = quick scan, Agent = deep Builder-aware analysis
- **When to use each:**
  - CodeRabbit: Development phase, quick iteration
  - Agent: Pre-commit, architectural review

### 3. Agent Workflow Integration
Specialists can use CodeRabbit for fast iteration:

**Frontend Dev / Backend Dev:**
```
Implement → /review → Fix obvious issues → [iterate] → Code Reviewer agent → Commit
```

**Security Analyst:**
```
CodeRabbit scan (quick) → Deep security review (manual) → Final validation
```

### 4. Pre-Commit Hook (Optional)
**Not currently implemented** - can be added to `global/claude-config/hooks/pre_tool_use.py` if desired, but may slow down commits. Better used interactively during development.

## Review Modes

| Mode | Command | Use Case |
|------|---------|----------|
| Detailed | `--plain` | Comprehensive feedback with fix suggestions |
| Minimal | `--prompt-only` | Token-efficient output for AI agents |

## How It Works

1. **AI Agent writes code** (e.g., Frontend Dev implements feature)
2. **CodeRabbit analyzes** (`coderabbit review --plain`)
3. **Feedback applied** (agent or {{ORCHESTRATOR_NAME}} applies suggestions)
4. **Quality improves** through automated loop

## Example Workflow

```bash
# Developer/agent makes changes
git status

# Run review
coderabbit review --plain

# Review provides:
# - Security vulnerabilities
# - Performance issues
# - Code smells
# - Best practice violations
# - Suggested fixes

# Apply fixes and commit
git add .
git commit -m "feat: implement feature with CodeRabbit suggestions applied"
```

## Notes

- **Repository Root Required:** Must run from git repository root
- **Staged Changes:** Reviews staged changes (use `git add` first)
- **Token Efficiency:** Use `--prompt-only` for AI agent integrations to reduce token usage
- **Authentication:** Already configured for {{GITHUB_USER}} GitHub account

## Resources

- [CodeRabbit Documentation](https://docs.coderabbit.ai/cli/overview)
- [CLI Reference](https://www.coderabbit.ai/cli)
- Installation Location: `{{HOME_DIR}}/.local/bin/coderabbit`
- Alias: `cr` (short form)

## BuilderOS Philosophy

CodeRabbit enhances Builder System's "build everything" mission by:
- **Catching issues early** - Fast automated scanning during development
- **Complementary layers** - Works with (not against) existing review systems
- **Speed without compromise** - Quick feedback for fast iteration
- **Agent-friendly** - Token-efficient mode for AI agent integration
- **Focused reviews** - Automated tool handles obvious issues, human/agent reviews focus on architecture

## Summary

**CodeRabbit CLI is integrated as Layer 1 (automated scanning) in BuilderOS's three-tier code review system:**
1. **CodeRabbit** → Fast automated scanning
2. **Code Reviewer Agent** → Deep Builder-aware analysis
3. **`/pr-review`** → Multi-perspective validation

This complementary architecture maintains all existing review processes while adding fast automated feedback for tighter development iteration loops.

**Integration Status:** ✅ Active and Complementary
