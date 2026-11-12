---
name: wardrobe-finder
description: Secondhand clothing search — paste a retail URL, find it cheaper across resale marketplaces with size matching and price comparison
when: User pastes a clothing retail URL, asks to "find this cheaper", "search secondhand", "wardrobe search", or uses /wardrobe command
allowed-tools:
  - Bash
  - Read
metadata:
  version: "1.0.0"
  authority: "{{ORCHESTRATOR_NAME}}"
  script: "tools/wardrobe_finder.py"
  scope: "Secondhand marketplace search"
  last_updated: "2026-02-15"
---

# Wardrobe Finder Skill

## Purpose
Search secondhand marketplaces for clothing items found at retail. Takes a retail product URL, extracts details (brand, model, size, color, price), searches 9 resale platforms in parallel, and returns matches ranked by price with confidence scoring. Facebook Marketplace is handled separately by {{ORCHESTRATOR_NAME}} via Chrome MCP.

## Primary Agent
- **{{ORCHESTRATOR_NAME}}** (authority) -- Invokes directly in conversation

## Trigger Conditions

Activate this skill when:
- User pastes a clothing retail URL (Nike, Nordstrom, Zara, ASOS, etc.)
- User says "find this cheaper", "search secondhand", "wardrobe search"
- User types `/wardrobe search <url>`
- User asks about secondhand alternatives to a linked product

## CLI Reference

Entry point: `python3 {{CATALYST_ROOT}}/tools/wardrobe_finder.py`

### Global Flags
```bash
--verbose / -v    # Debug logging to stderr
--version         # Print version
```

### search -- Search resale marketplaces
```bash
python3 {{CATALYST_ROOT}}/tools/wardrobe_finder.py search <url>
python3 {{CATALYST_ROOT}}/tools/wardrobe_finder.py search <url> --json
python3 {{CATALYST_ROOT}}/tools/wardrobe_finder.py search <url> --platforms poshmark,depop
python3 {{CATALYST_ROOT}}/tools/wardrobe_finder.py search <url> --limit 10
python3 {{CATALYST_ROOT}}/tools/wardrobe_finder.py search <url> --max-price 100
python3 {{CATALYST_ROOT}}/tools/wardrobe_finder.py search <url> --color-strict
python3 {{CATALYST_ROOT}}/tools/wardrobe_finder.py search <url> --no-expand
python3 {{CATALYST_ROOT}}/tools/wardrobe_finder.py search <url> --no-vision
python3 {{CATALYST_ROOT}}/tools/wardrobe_finder.py search <url> --no-resolve
python3 {{CATALYST_ROOT}}/tools/wardrobe_finder.py search <url> --dry-run
```

| Flag | Purpose |
|------|---------|
| `--json` | Machine-readable JSON output (use for orchestration) |
| `--platforms` | Comma-separated platform filter (default: all enabled in profile) |
| `--limit N` | Max results to display (default: 20) |
| `--max-price N` | Price ceiling filter |
| `--color-strict` | Only show exact color matches |
| `--no-expand` | Skip AI query expansion (faster, no Gemini API call) |
| `--no-vision` | Skip vision matching (faster, no image comparison) |
| `--no-resolve` | Skip URL resolution (don't unwrap Pinterest pins or short links) |
| `--dry-run` | Extract product details only, don't search |

### config -- Manage size profile
```bash
python3 {{CATALYST_ROOT}}/tools/wardrobe_finder.py config --show
python3 {{CATALYST_ROOT}}/tools/wardrobe_finder.py config --show --json
python3 {{CATALYST_ROOT}}/tools/wardrobe_finder.py config --tops M --bottoms 32x32 --shoes 10.5
python3 {{CATALYST_ROOT}}/tools/wardrobe_finder.py config --outerwear L --dresses 8 --accessories OS
python3 {{CATALYST_ROOT}}/tools/wardrobe_finder.py config --max-price 150
python3 {{CATALYST_ROOT}}/tools/wardrobe_finder.py config --color-strict
python3 {{CATALYST_ROOT}}/tools/wardrobe_finder.py config --no-color-strict
python3 {{CATALYST_ROOT}}/tools/wardrobe_finder.py config --platforms ebay,poshmark,depop,mercari
```

Profile stored at `~/.wardrobe/profile.yaml`. Set sizes once, used for all searches.

Size categories: `tops`, `bottoms`, `shoes`, `outerwear`, `accessories`, `dresses`

### test-extractor -- Debug product extraction
```bash
python3 {{CATALYST_ROOT}}/tools/wardrobe_finder.py test-extractor <url>
python3 {{CATALYST_ROOT}}/tools/wardrobe_finder.py test-extractor <url> --json
python3 {{CATALYST_ROOT}}/tools/wardrobe_finder.py test-extractor <url> --no-resolve
```

### test-searcher -- Check platform health
```bash
python3 {{CATALYST_ROOT}}/tools/wardrobe_finder.py test-searcher ebay
python3 {{CATALYST_ROOT}}/tools/wardrobe_finder.py test-searcher poshmark --json
```

### history -- View past searches
```bash
python3 {{CATALYST_ROOT}}/tools/wardrobe_finder.py history
python3 {{CATALYST_ROOT}}/tools/wardrobe_finder.py history --limit 5
python3 {{CATALYST_ROOT}}/tools/wardrobe_finder.py history --json
```

History stored at `~/.wardrobe/history/`.

### watch -- Manage watchlist
```bash
python3 {{CATALYST_ROOT}}/tools/wardrobe_finder.py watch "<url>"
python3 {{CATALYST_ROOT}}/tools/wardrobe_finder.py watch "<url>" --name "AF1 White"
python3 {{CATALYST_ROOT}}/tools/wardrobe_finder.py watch "<url>" --max-price 80
python3 {{CATALYST_ROOT}}/tools/wardrobe_finder.py watch --list
python3 {{CATALYST_ROOT}}/tools/wardrobe_finder.py watch --list --json
python3 {{CATALYST_ROOT}}/tools/wardrobe_finder.py watch --remove <id>
python3 {{CATALYST_ROOT}}/tools/wardrobe_finder.py watch --check
```

Watchlist stored at `~/.wardrobe/watchlist.json`. Watch state at `~/.wardrobe/watch-state/`.
Background checks run via LaunchAgent (`com.catalyst.wardrobe-watcher`) every 4 hours.
Notifications sent to Wardrobe Shopper Telegram group on new matches and price drops.

### stats -- Search analytics
```bash
python3 {{CATALYST_ROOT}}/tools/wardrobe_finder.py stats
python3 {{CATALYST_ROOT}}/tools/wardrobe_finder.py stats --json
```

## Orchestration Flow

When {{USER_NAME}} pastes a retail URL or asks to find something cheaper:

**Step 1: Run CLI with --json**
```bash
python3 {{CATALYST_ROOT}}/tools/wardrobe_finder.py search "<url>" --json
```

**Step 2: Parse JSON output**
JSON contains `product` (extracted details), `results` (array of matches), and `summary` (retail price, best price, savings).

**Step 3: Facebook Marketplace (optional)**
If {{USER_NAME}} wants Facebook results or says "check Facebook too", {{ORCHESTRATOR_NAME}} handles this directly:
1. `mcp__claude-in-chrome__tabs_create_mcp` -- Open new tab
2. `mcp__claude-in-chrome__navigate` -- Go to `https://www.facebook.com/marketplace/search/?query=<product>`
3. `mcp__claude-in-chrome__read_page` or `get_page_text` -- Parse visible results
4. Manually extract: title, price, condition, URL for each listing
5. Merge into CLI results

**Step 4: Format results**
Present as a table with savings summary. Include direct links for each listing.

**Step 5: Present to {{USER_NAME}}**
Show the formatted output with the savings calculation.

## Output Format

```
Platform    | Title                    | Price  | Size | Color | Condition | Match
------------|--------------------------|--------|------|-------|-----------|------
Poshmark    | Nike Air Force 1 '07 WHT | $45.00 | 10.5 | White | Like New  |  95
eBay        | Nike Air Force Low White | $52.00 | 10.5 | White | NWT       |  92
Depop       | AF1 White Low            | $50.00 | 10.5 | White | Good      |  88
Mercari     | Air Force 1 Sneakers     | $55.00 | 11   | White | Like New  |  75

Retail: $110.00 | Best Secondhand: $45.00 | Savings: $65.00 (59%)
```

## Platforms

### CLI Platforms (9)

| Platform | Method | Notes |
|----------|--------|-------|
| eBay | Browse API (official) | Free tier, most reliable |
| Poshmark | Playwright scraper | Via Bowser subprocess |
| Depop | Playwright scraper | Via Bowser subprocess |
| Mercari | GraphQL API / scraper | |
| ThredUp | Playwright scraper | |
| Grailed | Unofficial API | Menswear/streetwear focus |
| The RealReal | Playwright scraper | Luxury consignment |
| Vestiaire Collective | Playwright scraper | Luxury resale |
| Goodwill | Playwright scraper | shopgoodwill.com |

### Facebook Marketplace ({{ORCHESTRATOR_NAME}}-direct)

Facebook is NOT in the CLI. Bot detection is too aggressive for headless scraping.

When {{USER_NAME}} asks for Facebook results:
- Requires {{USER_NAME}}'s Brave browser to be open
- {{ORCHESTRATOR_NAME}} navigates via Chrome MCP tools (`mcp__claude-in-chrome__*`)
- Search URL pattern: `https://www.facebook.com/marketplace/search/?query=<brand+model>`
- Parse visible listings from page text
- Merge results into CLI output manually

## Matching Pipeline

1. **Text-based** (always active) -- Brand, model, size, color fuzzy matching with alias resolution ("AF1" = "Air Force 1")
2. **SKU/UPC** (when available) -- Machine-readable product identifiers searched as secondary query
3. **AI Semantic** (optional, needs `GEMINI_API_KEY`) -- LLM generates alternative search queries sellers might use. Disable with `--no-expand`.
4. **Vision** (optional, needs `GEMINI_API_KEY`) -- Compare product image to listing thumbnails via Gemini Vision. Disable with `--no-vision`.

## Profile Management

Set up sizes once (persisted at `~/.wardrobe/profile.yaml`):

```bash
# Initial setup
python3 {{CATALYST_ROOT}}/tools/wardrobe_finder.py config --tops M --bottoms 32x32 --shoes 10.5

# Verify
python3 {{CATALYST_ROOT}}/tools/wardrobe_finder.py config --show

# Update individual sizes
python3 {{CATALYST_ROOT}}/tools/wardrobe_finder.py config --outerwear L

# Set default price ceiling
python3 {{CATALYST_ROOT}}/tools/wardrobe_finder.py config --max-price 150

# Enable/disable specific platforms
python3 {{CATALYST_ROOT}}/tools/wardrobe_finder.py config --platforms ebay,poshmark,depop,mercari,thredup,grailed
```

## Dependencies

- `extruct` -- JSON-LD + OpenGraph product data extraction
- `requests` -- eBay API, image downloading, Gemini API
- `pyyaml` -- Config/profile files
- `playwright` + `playwright-stealth` -- Scraping platforms and SPA extraction fallback

Install: `pip install extruct requests pyyaml playwright playwright-stealth`

## What This Skill Does NOT Handle

- Marketplace account management (login, credentials)
- Purchasing or checkout (planned Phase 2.0)
- Non-clothing items (clothing only for now)
- Facebook Marketplace scraping ({{ORCHESTRATOR_NAME}}-direct via Chrome MCP, not CLI)
