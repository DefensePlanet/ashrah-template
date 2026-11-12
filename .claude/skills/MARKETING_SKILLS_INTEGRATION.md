# Marketing Skills Integration Summary

**Integration Date:** 2026-01-19
**Repository:** https://github.com/coreyhaines31/marketingskills
**License:** MIT

## Overview

Successfully integrated 23 specialized marketing skills from Corey Haines' marketingskills repository into Catalyst. These skills provide expert frameworks and best practices for conversion optimization, copywriting, SEO, analytics, and growth engineering.

## Installation Location

```
{{CATALYST_ROOT}}/.claude/skills/marketing-skills/
```

The repository was cloned directly to preserve future update capability.

## Enhanced Marketing Agents

### ✍️ Content Marketer (`content-marketer.md`)
**Added Skills:**
- `/copywriting` - Write or improve marketing copy for any page
- `/copy-editing` - Edit and polish existing copy with Seven Sweeps framework
- `/email-sequence` - Build email sequences and drip campaigns
- `/marketing-ideas` - Access 140 SaaS marketing ideas and growth strategies
- `/marketing-psychology` - Apply 70+ mental models and cognitive biases

**Skill Integration:** Content creation → copywriting → copy-editing workflow

### 📱 Social Media Marketer (`social-media-copywriter.md`)
**Added Skills:**
- `/social-content` - Create and schedule social media content (LinkedIn, Twitter, Instagram)
- `/copywriting` - Compelling copy with proven frameworks and headline formulas

**Skill Integration:** Platform-specific content strategy with persuasive messaging

### 🔍 SEO Analyzer (`seo-analyzer.md`)
**Added Skills:**
- `/seo-audit` - Comprehensive technical and on-page SEO audits
- `/programmatic-seo` - Build SEO pages at scale
- `/competitor-alternatives` - Create competitor comparison pages
- `/schema-markup` - Add structured data and rich snippets

**Skill Integration:** Audit → implement schema → scale with programmatic SEO

### 📈 Marketing Analyst (`marketing-attribution-analyst.md`)
**Added Skills:**
- `/analytics-tracking` - Set up GA4, GTM, event tracking systems
- `/ab-test-setup` - Plan and implement A/B tests
- `/paid-ads` - Create and optimize paid ad campaigns

**Skill Integration:** Tracking → testing → optimization workflow

### 🎯 Product Strategist (`product-strategist.md`)
**Added Skills:**
- `/launch-strategy` - Plan product launches and feature announcements
- `/pricing-strategy` - Design pricing, packaging, and monetization
- `/free-tool-strategy` - Plan engineering-as-marketing tools

**Skill Integration:** Market analysis → positioning → pricing → launch execution

## Complete Skills Inventory

**Conversion Optimization (6 skills):**
- `page-cro` - Any marketing page optimization
- `signup-flow-cro` - Registration flow optimization
- `onboarding-cro` - Post-signup activation
- `form-cro` - Lead capture forms
- `popup-cro` - Modals and overlays
- `paywall-upgrade-cro` - In-app upgrade moments

**Content & Copy (4 skills):**
- `copywriting` - Marketing page copy
- `copy-editing` - Edit and polish copy
- `email-sequence` - Automated email flows
- `social-content` - Social media content

**SEO & Discovery (4 skills):**
- `seo-audit` - Technical and on-page SEO
- `programmatic-seo` - Scaled page generation
- `competitor-alternatives` - Comparison pages
- `schema-markup` - Structured data

**Paid & Distribution (2 skills):**
- `paid-ads` - Google, Meta, LinkedIn campaigns
- `social-content` - Social media scheduling

**Measurement & Testing (2 skills):**
- `analytics-tracking` - Event tracking setup
- `ab-test-setup` - Experiment design

**Growth Engineering (2 skills):**
- `free-tool-strategy` - Marketing tools and calculators
- `referral-program` - Referral and affiliate programs

**Strategy & Monetization (3 skills):**
- `marketing-ideas` - 140 SaaS marketing ideas
- `marketing-psychology` - Mental models and psychology
- `launch-strategy` - Product launches
- `pricing-strategy` - Pricing and monetization

## Skill Activation Methods

### Automatic Activation
Skills auto-activate based on keyword triggers in user requests:
- "Write copy" → `/copywriting`
- "SEO audit" → `/seo-audit`
- "Email sequence" → `/email-sequence`
- "Launch strategy" → `/launch-strategy`

### Manual Invocation
Agents can explicitly invoke skills:
```
/copywriting
/seo-audit
/email-sequence
```

### {{ORCHESTRATOR_NAME}} Delegation
When {{ORCHESTRATOR_NAME}} delegates to marketing agents, it can include skill context:
```
"Have Content Marketer create homepage copy using the copywriting skill"
```

## Usage Guidelines

**For Marketing Agents:**
1. Check for relevant skills before starting work
2. Invoke skills to access expert frameworks
3. Combine multiple skills for comprehensive solutions
4. Store successful patterns in agent memory after using skills

**For {{ORCHESTRATOR_NAME}}:**
1. When delegating marketing work, suggest relevant skills
2. Multiple skills can be used in sequence (copywriting → copy-editing)
3. Skills complement agent expertise—they don't replace it

**For {{USER_NAME}}:**
1. Reference skills by name in requests: "Use the pricing-strategy skill"
2. Skills work automatically based on keywords
3. All skills are documented in `.claude/skills/marketing-skills/skills/[skill-name]/SKILL.md`

## Future Maintenance

**Updating Skills:**
```bash
cd {{CATALYST_ROOT}}/.claude/skills/marketing-skills
git pull origin main
```

**Adding Custom Skills:**
Add custom skills to `{{CATALYST_ROOT}}/.claude/skills/` following the SKILL.md format.

**Verifying Skills:**
Claude Code automatically discovers skills in `.claude/skills/` directories.

## Integration Testing

**Test Commands:**
- Ask Content Marketer: "Write homepage copy" (should auto-invoke `/copywriting`)
- Ask SEO Analyzer: "Audit my site" (should auto-invoke `/seo-audit`)
- Ask Product Strategist: "Plan our pricing" (should auto-invoke `/pricing-strategy`)

## Benefits

**For Catalyst:**
- 23 specialized marketing frameworks instantly available
- Proven best practices from conversion optimization expert
- Consistent quality across all marketing work
- Scalable expertise through skill composition

**For Marketing Agents:**
- Access to detailed frameworks and checklists
- Comprehensive coverage of marketing domains
- Continuous improvement through community contributions
- Reduced need for constant instruction updates

**For {{USER_NAME}}:**
- Professional-grade marketing output
- Less need to provide detailed instructions
- Consistent application of best practices
- Skills improve over time via upstream updates

---

**Next Steps:**
1. ✅ Marketing skills repository cloned
2. ✅ Agent files updated with skills integration
3. ✅ All 5 marketing agents enhanced
4. ✅ Documentation created
5. ⏭️ Ready for testing with real marketing requests

**Questions or issues:** Reference this file or the skills README at `.claude/skills/marketing-skills/README.md`
