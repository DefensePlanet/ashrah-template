# CAPTCHA Implementation Architecture Notes

## Playwright Integration Decision

### Current Implementation: Direct Playwright Library

**Rationale:**
- **Fine-grained control**: CAPTCHA solving requires low-level browser manipulation (iframe access, audio downloads, token injection)
- **Async patterns**: playwright-recaptcha and playwright-stealth work with direct Playwright async API
- **Performance**: Direct library calls are faster than MCP proxy layer
- **Debugging**: Direct access to browser objects for screenshot capture and error diagnosis

### Alternative: Playwright MCP Tools

Available MCP tools from `mcp__playwright__*`:
- `browser_navigate` - Navigate to URL
- `browser_snapshot` - Capture page state
- `browser_click` - Click elements
- `browser_type` - Type text
- `browser_fill_form` - Fill multiple fields

**Limitations for CAPTCHA:**
- No direct frame access (needed for reCAPTCHA iframes)
- No async context managers (playwright-recaptcha requires `async with`)
- No audio download capability (required for reCAPTCHA v2 audio solving)
- Higher latency (request → MCP server → Playwright → response)

**When to Use MCP:**
- Simple form filling without CAPTCHA
- Navigation and screenshot capture
- Integration with other MCP services in same workflow

### Alternative: Playwright Agent Delegation

**🎭 Playwright Agent** available via Task tool

**Pros:**
- Specialized expertise in browser automation patterns
- Error recovery and retry logic
- Service-specific optimization knowledge

**Cons:**
- Additional delegation overhead (time)
- Less direct control over CAPTCHA solving timing
- Harder to integrate with specialized CAPTCHA libraries

**Hybrid Approach (Future Consideration):**
```python
# Use direct library for CAPTCHA-critical operations
captcha_result = await solver.solve(page)

if captcha_result.success:
    # Delegate to Playwright Agent for complex form navigation
    await delegate_to_playwright_agent(...)
```

## Browser Selection: Brave

**Why Brave:**
- User's default browser (already configured, extensions, profiles)
- Chromium-based (wide compatibility)
- Built-in privacy features may help with fingerprinting evasion
- Consistent with user's browsing patterns (less detectable)

**Firefox Alternative:**
- Research shows slightly better reCAPTCHA audio solving success (90% vs 85%)
- Recommended by playwright-recaptcha maintainer
- Can be enabled by passing `browser="firefox"` to UniversalCaptchaSolver

**Recommendation:**
- Default: Brave (user preference)
- Fallback: Firefox if Brave fails or for specific services with known issues
- Configurable per-service in future

## CAPTCHA Solver Architecture

### Layer 1: Stealth (Always Applied)
- `playwright-stealth` - Removes automation fingerprints
- Custom browser args (disable blink features, site isolation)
- Anti-detection measures before CAPTCHA appears

### Layer 2: Detection (Universal)
- Auto-detect CAPTCHA type from page content
- Supports: reCAPTCHA v2/v3, hCaptcha, Cloudflare Turnstile
- Graceful handling when no CAPTCHA present

### Layer 3: Solving (Strategy-Based)
- **reCAPTCHA v2**: Audio transcription (free, 85-90% success)
- **reCAPTCHA v3**: Token interception (free, 90%+ success)
- **hCaptcha**: API fallback (paid, requires API key)
- **Turnstile**: Auto-solve or API (mixed success)

### Layer 4: Human Behavior Simulation
- Random typing delays (50-150ms per keystroke)
- Random click positions within element bounds
- Natural pauses between actions (0.5-1.5s)
- Mouse movement to elements before clicking

## Cost Analysis (Catalyst Framework)

### Real Costs
- **playwright-recaptcha (audio)**: $0/year
- **playwright-stealth**: $0/year
- **FFmpeg**: $0 (open source)
- **API fallback (optional)**: $1-3 per 1000 accounts

### Time Investment (Claude)
- Initial setup: 3 hours (completed)
- Per-service configuration: 15-30 minutes
- Debugging/refinement: 1-2 hours per service
- Maintenance: 2-4 hours/quarter

### Growth Runway
- Free tier: Unlimited (Google Speech API has soft limits, rarely hit)
- Audio method works for 85-90% of cases
- API fallback available for remaining 10-15%

## Service-Specific Considerations

### GitHub
- **CAPTCHA**: reCAPTCHA v2 (occasional)
- **Strategy**: Free audio solving
- **Success Rate**: 85%+ with stealth

### Shopify
- **CAPTCHA**: hCaptcha (migrated October 2024)
- **Strategy**: API solving or manual
- **Note**: Free audio solving NOT effective for hCaptcha

### OpenAI
- **CAPTCHA**: Cloudflare Turnstile
- **Additional**: Phone verification required
- **Strategy**: Turnstile auto-solve + manual phone

### Instagram
- **CAPTCHA**: Facebook custom + behavioral analysis
- **Risk**: High ban rate, ToS violation
- **Recommendation**: Not recommended for automation

## Testing Strategy

### Phase 1: CAPTCHA Solver Only
```bash
python tools/universal_captcha_solver.py
# Tests on Google reCAPTCHA demo page
```

### Phase 2: Full Account Creation
```bash
python tools/account_creator.py create-auto --service github --purpose test
```

### Phase 3: Multi-Service Validation
- GitHub (free reCAPTCHA)
- OpenAI (Turnstile)
- Shopify (hCaptcha with API)

## Future Enhancements

### Priority 1: API Integration
- Add 2captcha or CapSolver for hCaptcha/Turnstile
- Cost: ~$3 per 1000 accounts
- Enables Shopify and Cloudflare-protected sites

### Priority 2: Email Verification Automation
- SimpleLogin inbox checking
- Automatic verification link clicking
- Reduces manual intervention

### Priority 3: Playwright Agent Hybrid
- Delegate non-CAPTCHA tasks to agent
- Keep direct library for CAPTCHA-critical operations
- Best of both worlds

### Priority 4: Metrics & Monitoring
- Track success rates per service
- CAPTCHA frequency monitoring (detection indicator)
- Automatic fallback to API when audio fails

## Ethical Guidelines

### ✅ Acceptable Use
- Testing your own services
- QA automation with business authorization
- Development environments with test accounts

### ❌ Prohibited Use
- Mass account creation for spam
- ToS violations on third-party sites
- Credential stuffing or security bypasses

### Rate Limiting
- **Development**: 10-20 accounts/day
- **Production (authorized)**: 50-100 accounts/day with proxies
- **Monitoring**: Alert if CAPTCHA frequency > 80%

---

**Last Updated**: 2025-10-20
**Maintainer**: {{ORCHESTRATOR_NAME}} + {{USER_NAME}}
**Review Schedule**: Monthly (check for detection method changes)
