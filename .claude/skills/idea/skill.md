---
name: idea
description: Navigate to Idea Incubator capsule - Capture zone for orphaned ideas before they become capsules
when: User types /idea or mentions idea-incubator
allowed-tools:
  - Bash
metadata:
  version: "1.0.0"
  capsule: "idea-incubator"
  privacy: "normal"
  last_updated: "2026-01-19"
---

# /idea - Navigate to Idea Incubator

## Purpose
Quick navigation to the Idea Incubator capsule.

**Capsule purpose:** Capture zone for orphaned ideas - personal projects, Catalyst enhancements, random inspirations

## Trigger Conditions
- User types `/idea`
- User mentions "idea-incubator"
- User wants to work on idea incubator

## What This Skill Does

1. **Navigates to capsule:**
   ```bash
   cd {{CATALYST_ROOT}}/capsules/idea-incubator
   ```

2. **Confirms navigation:**
   - Reports current location
   - Shows available next steps
   

## Navigation Command

```bash
cd {{CATALYST_ROOT}}/capsules/idea-incubator && pwd
```

## Response Template

When this skill is invoked, respond with:

```
✓ Navigated to Idea Incubator

📍 {{CATALYST_ROOT}}/capsules/idea-incubator

**What would you like to work on?**

- Review README.md for overview
- Check docs/ for documentation
- Start working on your task


```

## Mobile Access

Telegram bot: Available via capsule's dedicated bot
