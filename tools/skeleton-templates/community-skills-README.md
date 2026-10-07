# Community Skills

These are third-party skill repositories from the Claude Code skills ecosystem. Clone them into this directory, then run `../../setup-skills.sh` to create symlinks.

## Repositories

| Directory | Repository | Description |
|-----------|-----------|-------------|
| `addyosmani-web-quality/` | [addyosmani/web-quality-skills](https://github.com/addyosmani/web-quality-skills) | SEO and Core Web Vitals optimization (by Google Chrome lead) |
| `andreev-danila-skills/` | [andreev-danila/skills](https://github.com/andreev-danila/skills) | Reanimated + Skia performance patterns |
| `anthropic/` | [anthropics/skills](https://github.com/anthropics/skills) | Official Anthropic skills (frontend-design, MCP builder, skill-creator) |
| `avdlee-swiftui/` | [AvdLee/SwiftUI-Agent-Skill](https://github.com/AvdLee/SwiftUI-Agent-Skill) | SwiftUI expert with 14 reference docs |
| `better-auth/` | [better-auth/skills](https://github.com/better-auth/skills) | Authentication best practices and creation |
| `cloudflare-skills/` | [cloudflare/skills](https://github.com/cloudflare/skills) | Web performance auditing via Chrome DevTools |
| `dimillian-skills/` | [dimillian/skills](https://github.com/dimillian/skills) | SwiftUI (Liquid Glass, performance audit, UI patterns, view refactor), Swift concurrency |
| `expo/` | [expo/skills](https://github.com/expo/skills) | Expo app design, native UI, data fetching, upgrading |
| `kv0906-cc-skills/` | [kv0906/cc-skills](https://github.com/kv0906/cc-skills) | Premium frontend design (production-grade interfaces) |
| `pluginagentmarketplace-rn/` | [pluginagentmarketplace/custom-plugin-react-native](https://github.com/pluginagentmarketplace/custom-plugin-react-native) | React Native animations |
| `remotion/` | [remotion-dev/skills](https://github.com/remotion-dev/skills) | Remotion video creation |
| `vercel-labs/` | [vercel-labs/agent-skills](https://github.com/vercel-labs/agent-skills) | React best practices, composition patterns, web design |
| `wondelai-skills/` | [wondelai/skills](https://github.com/wondelai/skills) | CRO methodology, top design patterns |

## Manual Installation

```bash
cd .claude/skills/community
git clone https://github.com/anthropics/skills.git anthropic
git clone https://github.com/vercel-labs/agent-skills.git vercel-labs
# ... etc.
```

Or use `./setup-skills.sh` from the repo root to clone all repos and create symlinks automatically.
