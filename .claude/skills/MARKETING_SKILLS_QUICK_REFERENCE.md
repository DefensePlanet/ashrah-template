# Marketing Skills Quick Reference

## Agent → Skills Mapping

### ✍️ Content Marketer
```
/copywriting         - Write marketing copy for any page
/copy-editing        - Polish and refine existing copy
/email-sequence      - Build email campaigns and drip sequences
/marketing-ideas     - 140 SaaS marketing ideas
/marketing-psychology - 70+ mental models and persuasion principles
```

### 📱 Social Media Marketer
```
/social-content      - Platform-specific social media content
/copywriting         - Persuasive messaging and headlines
```

### 🔍 SEO Analyzer
```
/seo-audit           - Technical and on-page SEO audits
/programmatic-seo    - Build SEO pages at scale
/competitor-alternatives - Create comparison pages
/schema-markup       - Add structured data
```

### 📈 Marketing Analyst
```
/analytics-tracking  - GA4, GTM, event tracking setup
/ab-test-setup       - Plan and implement experiments
/paid-ads            - Google Ads, Meta ads, paid campaigns
```

### 🎯 Product Strategist
```
/launch-strategy     - Product launches and announcements
/pricing-strategy    - Pricing, packaging, monetization
/free-tool-strategy  - Lead gen tools and calculators
```

## Common Workflows

### Homepage Copy Creation
1. "Write homepage copy for [product]"
2. Auto-invokes `/copywriting` skill
3. Follow up with `/copy-editing` for polish
4. Use `/marketing-psychology` for persuasion elements

### SEO Page Scaling
1. "Create SEO pages for [topics]"
2. Start with `/seo-audit` for baseline
3. Use `/programmatic-seo` for templates
4. Apply `/schema-markup` for rich snippets
5. Use `/competitor-alternatives` for competitive pages

### Product Launch
1. "Plan launch for [product]"
2. Invoke `/pricing-strategy` first
3. Follow with `/launch-strategy` for execution
4. Use `/email-sequence` for launch emails
5. Apply `/social-content` for social promotion

### Email Campaign
1. "Create onboarding sequence"
2. Invoke `/email-sequence` skill
3. Use `/copywriting` for email copy
4. Apply `/copy-editing` for polish
5. Use `/marketing-psychology` for persuasion

### Paid Campaign
1. "Set up Google Ads campaign"
2. Start with `/analytics-tracking` for measurement
3. Use `/paid-ads` for campaign structure
4. Apply `/ab-test-setup` for testing plan
5. Use `/copywriting` for ad copy

## All 23 Available Skills

**Conversion Optimization:**
- `/page-cro` - Marketing page optimization
- `/signup-flow-cro` - Registration flows
- `/onboarding-cro` - Post-signup activation
- `/form-cro` - Lead capture forms
- `/popup-cro` - Modals and overlays
- `/paywall-upgrade-cro` - In-app upgrades

**Content & Copy:**
- `/copywriting` - Marketing page copy
- `/copy-editing` - Copy polish and refinement
- `/email-sequence` - Email automation
- `/social-content` - Social media content

**SEO & Discovery:**
- `/seo-audit` - Technical SEO audits
- `/programmatic-seo` - Scaled page generation
- `/competitor-alternatives` - Comparison pages
- `/schema-markup` - Structured data

**Paid & Distribution:**
- `/paid-ads` - Ad campaigns
- `/social-content` - Social distribution

**Measurement & Testing:**
- `/analytics-tracking` - Tracking setup
- `/ab-test-setup` - Experiment design

**Growth Engineering:**
- `/free-tool-strategy` - Lead gen tools
- `/referral-program` - Referral programs

**Strategy & Monetization:**
- `/marketing-ideas` - 140 marketing ideas
- `/marketing-psychology` - Mental models
- `/launch-strategy` - Product launches
- `/pricing-strategy` - Pricing design

## Skill Documentation

Full documentation for each skill:
```
{{CATALYST_ROOT}}/.claude/skills/marketing-skills/skills/[skill-name]/SKILL.md
```

Example:
```
.claude/skills/marketing-skills/skills/copywriting/SKILL.md
.claude/skills/marketing-skills/skills/seo-audit/SKILL.md
.claude/skills/marketing-skills/skills/email-sequence/SKILL.md
```

## Usage Examples

**Request:** "Write homepage copy for our SaaS product"
**Auto-activates:** `/copywriting` skill
**Agent:** Content Marketer
**Output:** Headline variants, CTA copy, benefits sections

**Request:** "Audit our SEO and find issues"
**Auto-activates:** `/seo-audit` skill
**Agent:** SEO Analyzer
**Output:** Technical SEO audit, prioritized fixes

**Request:** "Create a 7-email welcome sequence"
**Auto-activates:** `/email-sequence` skill
**Agent:** Content Marketer
**Output:** Complete email sequence with timing

**Request:** "Design our pricing tiers"
**Auto-activates:** `/pricing-strategy` skill
**Agent:** Product Strategist
**Output:** Pricing model, tier structure, positioning

**Request:** "Set up GA4 event tracking"
**Auto-activates:** `/analytics-tracking` skill
**Agent:** Marketing Analyst
**Output:** Event schema, GTM setup, implementation

## Tips

1. **Skills auto-activate** based on keywords—just ask naturally
2. **Combine skills** for comprehensive solutions (copywriting + copy-editing)
3. **Reference skills** explicitly if needed: "Use the pricing-strategy skill"
4. **Update skills** occasionally: `cd .claude/skills/marketing-skills && git pull`
5. **Skills complement agents**—they provide frameworks, agents provide judgment

---

**Integration Date:** 2026-01-19
**Repository:** https://github.com/coreyhaines31/marketingskills
**Full Documentation:** `.claude/skills/MARKETING_SKILLS_INTEGRATION.md`
