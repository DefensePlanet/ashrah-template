# Catalyst Skills Quick Reference

## Total Skills: 27

### 📁 Local Catalyst Skills (19)
**Location:** `{{CATALYST_ROOT}}/.claude/skills/`

- telegram-bot-setup
- new-capsule
- claudeception
- frontend-testing
- ios-testing
- ios-device-deployment
- git-commit-helper
- strongbox-manager
- orchestration
- credential-creator
- account-login
- account-registration
- appointment-booking
- agon-navigation
- idea
- backend-patterns (library)
- debugging-patterns (library)
- design-patterns (library)
- logo-design-workflow (library)

### 🌍 Community Skills from skills.sh (8)
**Installed:** January 22, 2026

#### Frontend (2)
- **web-design-guidelines** → 📐 UI Designer, 🎨 Frontend Developer
- **react-best-practices** → 🎨 Frontend Developer

#### Backend (2)
- **auth-best-practices** → 🏛️ Backend Developer (HIGH PRIORITY)
- **auth-create** → 🏛️ Backend Developer

#### Mobile (3)
- **building-native-ui** → 📱 Mobile Developer
- **native-data-fetching** → 📱 Mobile Developer
- **upgrading-expo** → 📱 Mobile Developer

#### Media (1)
- **remotion-video** → 🎬 Visual Media Generator

---

## Agent → Skills Mapping

| Agent | Skills Available |
|-------|------------------|
| 📐 UI Designer | web-design-guidelines |
| 🎨 Frontend Developer | web-design-guidelines, react-best-practices |
| 🏛️ Backend Developer | auth-best-practices, auth-create |
| 📱 Mobile Developer | building-native-ui, native-data-fetching, upgrading-expo |
| 🎬 Visual Media Generator | remotion-video |

---

## Quick Commands

### Update Community Skills
```bash
cd {{CATALYST_ROOT}}/.claude/skills/community
git -C vercel-labs pull
git -C better-auth pull
git -C expo pull
git -C remotion pull
```

### List All Skills
```bash
ls -1 {{CATALYST_ROOT}}/.claude/skills/ | grep -v "^_" | grep -v ".md$"
```

### Check Skill Status
```bash
cd {{CATALYST_ROOT}}/.claude/skills
ls -lah | grep "^l"  # Show symlinks (community skills)
```

---

## Documentation

- **Community Skills Details:** `.claude/skills/COMMUNITY_SKILLS.md`
- **Installation Summary:** `/tmp/skills_installation_summary.md`
- **Verification Report:** `/tmp/skills_verification.txt`

---

*Last updated: January 22, 2026*
