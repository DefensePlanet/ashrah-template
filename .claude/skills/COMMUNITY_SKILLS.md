# Community Skills from skills.sh

## Installed: January 22, 2026

Skills installed from the skills.sh ecosystem to enhance Catalyst agents with industry best practices.

---

## 🎨 Frontend Development Skills

### web-design-guidelines
**Source:** vercel-labs/agent-skills (24.3K installs)
**For Agents:** 📐 UI Designer, 🎨 Frontend Developer
**Purpose:** Design standards and UI/UX patterns
**Path:** `.claude/skills/web-design-guidelines/`

### react-best-practices
**Source:** vercel-labs/agent-skills (32K installs)
**For Agents:** 🎨 Frontend Developer
**Purpose:** Modern React patterns, hooks, server components
**Path:** `.claude/skills/react-best-practices/`

**Note:** Complements Context7 MCP. Use Context7 for API docs, use this skill for opinionated best practices.

---

## 🏛️ Backend Development Skills

### auth-best-practices
**Source:** better-auth/skills (1.7K installs)
**For Agents:** 🏛️ Backend Developer
**Purpose:** Modern authentication patterns (OAuth, JWT, session management)
**Path:** `.claude/skills/auth-best-practices/`
**Priority:** HIGH - Security-critical

### auth-create
**Source:** better-auth/skills
**For Agents:** 🏛️ Backend Developer
**Purpose:** Step-by-step auth implementation guidance
**Path:** `.claude/skills/auth-create/`
**Priority:** MEDIUM

---

## 📱 Mobile Development Skills

### building-native-ui
**Source:** expo/skills (2.1K installs)
**For Agents:** 📱 Mobile Developer
**Purpose:** Native mobile UI development patterns (iOS/React Native)
**Path:** `.claude/skills/building-native-ui/`
**Priority:** HIGH

### native-data-fetching
**Source:** expo/skills (1.8K installs)
**For Agents:** 📱 Mobile Developer
**Purpose:** Mobile data retrieval and state management
**Path:** `.claude/skills/native-data-fetching/`
**Priority:** MEDIUM

### upgrading-expo
**Source:** expo/skills (1.8K installs)
**For Agents:** 📱 Mobile Developer
**Purpose:** Expo framework upgrade patterns
**Path:** `.claude/skills/upgrading-expo/`
**Priority:** MEDIUM

---

## 🎬 Visual Media Skills

### remotion-video
**Source:** remotion-dev/skills (12.1K installs)
**For Agents:** 🎬 Visual Media Generator
**Purpose:** Programmatic video creation with React
**Path:** `.claude/skills/remotion-video/`
**Priority:** LOW (specialized use case)

---

## Installation Details

**Repository Structure:**
```
.claude/skills/
├── community/              # Source repositories
│   ├── vercel-labs/       # Cloned from github.com/vercel-labs/agent-skills
│   ├── better-auth/       # Cloned from github.com/better-auth/skills
│   ├── expo/              # Cloned from github.com/expo/skills
│   └── remotion/          # Cloned from github.com/remotion-dev/skills
│
├── web-design-guidelines@ → community/vercel-labs/skills/web-design-guidelines
├── react-best-practices@  → community/vercel-labs/skills/react-best-practices
├── auth-best-practices@   → community/better-auth/better-auth/best-practices
├── auth-create@           → community/better-auth/better-auth/create-auth
├── building-native-ui@    → community/expo/plugins/expo-app-design/skills/building-native-ui
├── native-data-fetching@  → community/expo/plugins/expo-app-design/skills/native-data-fetching
├── upgrading-expo@        → community/expo/plugins/upgrading-expo/skills/upgrading-expo
└── remotion-video@        → community/remotion/skills/remotion
```

---

## How Agents Use These Skills

### Automatic Discovery
Claude Code automatically discovers all skills in `.claude/skills/`. Agents can reference these skills when needed.

### Recommended Usage Patterns

**🎨 Frontend Developer:**
```
When implementing React components:
1. Query Context7 for API documentation (e.g., React hooks, Next.js app router)
2. Reference react-best-practices for opinionated patterns
3. Use web-design-guidelines for UI/UX standards
```

**🏛️ Backend Developer:**
```
When implementing authentication:
1. Reference auth-best-practices for security patterns
2. Use auth-create for step-by-step implementation
3. Query Context7 for framework-specific auth libraries
```

**📱 Mobile Developer:**
```
When building mobile UI:
1. Reference building-native-ui for platform patterns
2. Use native-data-fetching for data management
3. Query Context7 for platform-specific APIs
```

---

## Maintenance

### Updating Skills
```bash
cd {{CATALYST_ROOT}}/.claude/skills/community

# Update all repositories
cd vercel-labs && git pull && cd ..
cd better-auth && git pull && cd ..
cd expo && git pull && cd ..
cd remotion && git pull && cd ..
```

### Checking for New Skills
Visit https://skills.sh/ to discover new community skills.

### Removing Skills
```bash
cd {{CATALYST_ROOT}}/.claude/skills

# Remove symlink
rm skill-name

# Remove source (if no longer needed)
rm -rf community/repo-name
```

---

## Strategy: Local vs Community Skills

| Type | Purpose | Examples | Maintenance |
|------|---------|----------|-------------|
| **Local Skills** | Catalyst-specific workflows | telegram-bot-setup, new-capsule | You maintain |
| **Community Skills** | Industry best practices | react-best-practices, auth-best-practices | Community maintains |

**Best Practice:** Use both together. Local skills for Catalyst automation, community skills for development guidance.

---

## Expected Impact

### Before Community Skills
- Agents rely solely on Context7 for framework documentation
- No standardized best practices for common patterns
- Inconsistent approaches to auth, design, mobile development

### After Community Skills
- **Frontend Dev** has React best practices + design guidelines
- **Backend Dev** has security-focused auth patterns
- **Mobile Dev** has platform-specific UI and data patterns
- **All agents** benefit from battle-tested community knowledge

---

## Notes

1. **Skills are additive** - They enhance agents, don't replace existing capabilities
2. **Context7 + Skills work together** - Context7 for "what", Skills for "how"
3. **Symlinks allow organization** - Source repos in `community/`, discovered skills at root level
4. **Update regularly** - Community skills evolve, pull updates monthly
5. **Can be removed anytime** - Low risk, high value additions

---

## 🛠️ Development & Meta Skills (Added Jan 22, 2026)

### skill-creator
**Source:** anthropics/skills (2.4K installs)
**For Agents:** {{ORCHESTRATOR_NAME}}, 👔 BOSS, Claudeception (centralized skill management)
**Purpose:** Guide for creating effective skills - transforms general agent into specialized agent
**Path:** `.claude/skills/skill-creator/`
**Priority:** HIGH - Essential for skill development
**Rationale:** Prevents skill sprawl, ensures quality control, maintains strategic curation

**Key Principles:**
- Concise is key (context window is a public good)
- Set appropriate degrees of freedom (high/medium/low)
- Skills = "onboarding guides" for specialized domains

### mcp-builder
**Source:** anthropics/skills
**For Agents:** 🏄🏼‍♂️ MCP Server Dude
**Purpose:** MCP server creation patterns and protocol compliance
**Path:** `.claude/skills/mcp-builder/`
**Priority:** MEDIUM

### frontend-design
**Source:** anthropics/skills (3.7K installs)
**For Agents:** 📐 UI Designer, 🎨 Frontend Developer
**Purpose:** Frontend design patterns and best practices
**Path:** `.claude/skills/frontend-design/`
**Priority:** MEDIUM

---

## Updated Count: 11 Community Skills

**Total Skills in Catalyst:** 30
- 19 local Catalyst-specific skills
- 11 community skills from skills.sh

**Last Updated:** January 22, 2026
