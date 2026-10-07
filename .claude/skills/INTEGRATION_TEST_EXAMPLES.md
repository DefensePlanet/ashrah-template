# Marketing Skills Integration - Test Examples

**Purpose:** Verify that marketing skills are properly integrated and accessible to marketing agents.

## Test Scenarios

### Test 1: Content Marketer - Copywriting Skill

**Request:**
```
"Write homepage copy for a SaaS analytics platform"
```

**Expected Behavior:**
1. Content Marketer agent activates
2. `/copywriting` skill auto-invokes based on "write...copy" trigger
3. Agent produces homepage copy using copywriting frameworks:
   - Multiple headline options using proven formulas
   - Value proposition subheadline
   - Benefits sections
   - CTA copy variants
   - Social proof section copy

**Success Criteria:**
- ✅ Copywriting skill framework visible in output
- ✅ Multiple headline formulas applied
- ✅ Structured page sections following skill guidance
- ✅ CTA follows "action + outcome" pattern from skill

---

### Test 2: SEO Analyzer - SEO Audit Skill

**Request:**
```
"Audit the SEO of mywebsite.com"
```

**Expected Behavior:**
1. SEO Analyzer agent activates
2. `/seo-audit` skill auto-invokes based on "audit...SEO" trigger
3. Agent produces comprehensive SEO audit:
   - Technical SEO checklist
   - On-page optimization findings
   - Core Web Vitals assessment
   - Prioritized action plan

**Success Criteria:**
- ✅ SEO audit skill framework visible in output
- ✅ Findings categorized by priority (Critical/High/Medium/Low)
- ✅ Technical SEO, on-page SEO, and content sections covered
- ✅ Actionable recommendations with "Issue → Impact → Fix" structure

---

### Test 3: Content Marketer - Email Sequence Skill

**Request:**
```
"Create a 5-email welcome sequence for new trial users"
```

**Expected Behavior:**
1. Content Marketer agent activates
2. `/email-sequence` skill auto-invokes based on "email...sequence" trigger
3. Agent produces complete email sequence:
   - Sequence overview (trigger, goal, timing)
   - 5 emails with subject lines, preview text, body copy
   - Each email has clear purpose and CTA
   - Timing delays specified

**Success Criteria:**
- ✅ Email sequence skill framework visible in output
- ✅ Sequence follows welcome/onboarding template from skill
- ✅ Each email has: subject, preview, body, CTA, timing
- ✅ Progressive narrative building toward conversion

---

### Test 4: Product Strategist - Pricing Strategy Skill

**Request:**
```
"Design pricing tiers for our project management SaaS"
```

**Expected Behavior:**
1. Product Strategist agent activates
2. `/pricing-strategy` skill auto-invokes based on "pricing" trigger
3. Agent produces pricing strategy:
   - Pricing model recommendation
   - Tier structure design
   - Feature allocation by tier
   - Value-based pricing justification

**Success Criteria:**
- ✅ Pricing strategy skill framework visible in output
- ✅ Multiple pricing models evaluated (usage-based, tier-based, freemium)
- ✅ Willingness to pay analysis included
- ✅ Clear differentiation between tiers

---

### Test 5: Marketing Analyst - A/B Test Setup Skill

**Request:**
```
"Set up an A/B test for our signup flow"
```

**Expected Behavior:**
1. Marketing Analyst agent activates
2. `/ab-test-setup` skill auto-invokes based on "A/B test" trigger
3. Agent produces test plan:
   - Hypothesis definition
   - Metrics and success criteria
   - Sample size calculation
   - Statistical significance framework

**Success Criteria:**
- ✅ A/B test skill framework visible in output
- ✅ Clear hypothesis with predicted impact
- ✅ Primary and secondary metrics defined
- ✅ Statistical rigor (sample size, significance level, power)

---

### Test 6: Social Media Marketer - Social Content Skill

**Request:**
```
"Create LinkedIn and Twitter posts announcing our new feature"
```

**Expected Behavior:**
1. Social Media Marketer agent activates
2. `/social-content` skill auto-invokes based on "LinkedIn...Twitter" trigger
3. Agent produces platform-specific content:
   - LinkedIn post (professional tone, formatted)
   - Twitter thread (3-5 tweets with hooks)
   - Platform-appropriate CTAs

**Success Criteria:**
- ✅ Social content skill framework visible in output
- ✅ Distinct content for each platform (not copy-paste)
- ✅ LinkedIn: professional, formatted with breaks
- ✅ Twitter: thread with hooks, hashtags, <280 chars per tweet

---

### Test 7: SEO Analyzer - Programmatic SEO Skill

**Request:**
```
"Create a programmatic SEO strategy for city landing pages"
```

**Expected Behavior:**
1. SEO Analyzer agent activates
2. `/programmatic-seo` skill auto-invokes based on "programmatic SEO" trigger
3. Agent produces scaled SEO strategy:
   - Template page structure
   - Dynamic content sections
   - URL structure pattern
   - Data source requirements

**Success Criteria:**
- ✅ Programmatic SEO skill framework visible in output
- ✅ Scalable template design
- ✅ Dynamic data insertion strategy
- ✅ SEO best practices for scaled content

---

### Test 8: Content Marketer - Multi-Skill Workflow

**Request:**
```
"Write pricing page copy, then polish it"
```

**Expected Behavior:**
1. Content Marketer agent activates
2. `/copywriting` skill invokes first for initial copy
3. `/copy-editing` skill invokes second for polish
4. Agent produces:
   - Initial pricing page copy with all sections
   - Refined version after Seven Sweeps editing framework

**Success Criteria:**
- ✅ Both skills invoked in sequence
- ✅ Clear before/after showing copywriting → copy-editing workflow
- ✅ Editing improvements visible (clarity, brevity, specificity)
- ✅ Copy-editing skill's Seven Sweeps framework applied

---

## How to Run Tests

**Command format:**
```
Ask [Agent Name]: "[Test Request]"
```

**Examples:**
```
Ask Content Marketer: "Write homepage copy for a SaaS analytics platform"
Ask SEO Analyzer: "Audit the SEO of mywebsite.com"
Ask Product Strategist: "Design pricing tiers for our project management SaaS"
```

**What to look for:**
1. Skill auto-activation based on keywords
2. Skill frameworks visible in agent output
3. Quality improvement vs. agent working without skills
4. Appropriate skill selection for task

## Verification Checklist

After running tests:

- [ ] Skills auto-activate based on keywords
- [ ] Agent output reflects skill frameworks and best practices
- [ ] Multiple skills can be used in sequence (e.g., copywriting → copy-editing)
- [ ] Manual skill invocation works (`/copywriting`, `/seo-audit`, etc.)
- [ ] Skill documentation is accessible at `.claude/skills/marketing-skills/skills/[skill-name]/SKILL.md`
- [ ] All 5 enhanced agents have skills sections in their agent files
- [ ] Quick reference guide is available at `.claude/skills/MARKETING_SKILLS_QUICK_REFERENCE.md`

## Troubleshooting

**Skills not activating:**
1. Check keywords match skill triggers in SKILL.md files
2. Try manual invocation with `/skill-name`
3. Verify skills directory exists at `.claude/skills/marketing-skills/`

**Skills missing:**
1. Verify repository cloned: `ls -la .claude/skills/marketing-skills/`
2. Check skill count: `ls -1 .claude/skills/marketing-skills/skills/ | wc -l` (should be 23)
3. Pull latest: `cd .claude/skills/marketing-skills && git pull`

**Agent not using skill frameworks:**
1. Check agent file has "Marketing Skills Integration" section
2. Modified agents: content-marketer, social-media-copywriter, seo-analyzer, marketing-attribution-analyst, product-strategist
3. Re-read agent file or restart Claude Code session

---

**Integration Date:** 2026-01-19
**Status:** ✅ Ready for Testing
**Next Steps:** Run test scenarios above to verify integration
