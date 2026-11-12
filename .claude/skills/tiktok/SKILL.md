---
name: tiktok
description: TikTok Shop, Marketing, and Content Posting API integration for multi-brand e-commerce operations
when: Managing TikTok Shop products/orders/inventory, running TikTok ad campaigns, posting TikTok content, TikTok OAuth setup
allowed-tools:
  - Bash
  - Read
metadata:
  version: "1.0.0"
  authority: "{{ORCHESTRATOR_NAME}}"
  script: "tools/tiktok.py"
  scope: "TikTok Shop + Marketing + Content APIs"
  last_updated: "2026-02-10"
---

# TikTok Integration Skill

## Purpose
Unified TikTok CLI covering Shop (products, orders, fulfillment), Marketing (campaigns, ads, reports), and Content Posting (video upload, direct post) across multiple e-commerce brands.

**Three separate TikTok API ecosystems in one tool. No third-party dependencies.**

## Primary Agents
- **{{ORCHESTRATOR_NAME}}** (authority) — Can invoke directly
- **Shopify Exec** — TikTok Shop operations (products, orders, inventory)
- **CMO** — TikTok Marketing (ad campaigns, targeting, analytics)
- **Automator** — n8n workflow integration with TikTok APIs

## Prerequisites

### Per-Brand Setup

Each brand requires its own TikTok credentials. The tool isolates credentials per brand.

#### TikTok Shop (Partner Center)
1. Register at [TikTok Shop Partner Center](https://partner.tiktokshop.com/)
2. Create an app and obtain App Key + App Secret
3. Store credentials:
```bash
# Option A: Brand .env file
# capsules/ecommerce/brands/{brand}/.env
TIKTOK_SHOP_APP_KEY=your_app_key
TIKTOK_SHOP_APP_SECRET=your_app_secret
TIKTOK_SHOP_SELLER_ID=your_seller_id

# Option B: macOS Keychain (preferred)
security add-generic-password -s "ecommerce/{brand}/tiktok-app" -a "app_key_value" -w "app_secret_value"
```
4. Complete OAuth:
```bash
python3 tools/tiktok.py auth-shop --generate-url --brand {brand}
# Open URL in browser, authorize, copy code
python3 tools/tiktok.py auth-shop --code YOUR_CODE --brand {brand}
```

#### TikTok Marketing API
1. Register at [TikTok for Business](https://business-api.tiktok.com/portal)
2. Create an app and get approved
3. Store Ad Account ID in brand .env
4. Complete OAuth:
```bash
python3 tools/tiktok.py auth-marketing --generate-url --brand {brand}
python3 tools/tiktok.py auth-marketing --code YOUR_CODE --brand {brand}
```

#### TikTok Content Posting API
1. Register at [TikTok Developers](https://developers.tiktok.com/)
2. Create app with `video.publish` scope
3. Complete OAuth:
```bash
python3 tools/tiktok.py auth-content --generate-url --brand {brand}
python3 tools/tiktok.py auth-content --code YOUR_CODE --brand {brand}
```

**Note:** Content API starts in unaudited mode (private posts only). Public posting requires passing TikTok's compliance audit.

## Quick Reference

### Global Flags
```bash
--brand BRAND   # Which brand's credentials to use (required for multi-brand)
--json          # Machine-readable JSON output
--dry-run       # Preview mutations without executing
--verbose / -v  # Detailed logging
```

### Shop Commands
```bash
# Status
python3 tools/tiktok.py status --brand asset-labs

# Products
python3 tools/tiktok.py products --brand asset-labs
python3 tools/tiktok.py product-detail PRODUCT_ID --brand asset-labs
python3 tools/tiktok.py create-product --title "Name" --price 9.99 --category-id CAT --brand asset-labs --dry-run
python3 tools/tiktok.py update-product PRODUCT_ID --title "New Name" --brand asset-labs --dry-run

# Orders
python3 tools/tiktok.py orders --brand asset-labs
python3 tools/tiktok.py orders --status AWAITING_SHIPMENT --brand asset-labs
python3 tools/tiktok.py order-detail ORDER_ID --brand asset-labs
python3 tools/tiktok.py fulfill-order ORDER_ID --tracking TRACK123 --provider ups --brand asset-labs --dry-run

# Inventory
python3 tools/tiktok.py inventory PRODUCT_ID --brand asset-labs
python3 tools/tiktok.py update-inventory --sku-id SKU --warehouse-id WH --quantity 500 --brand asset-labs --dry-run
```

### Marketing Commands
```bash
# Campaigns
python3 tools/tiktok.py campaigns --brand asset-labs --json
python3 tools/tiktok.py campaign-detail CAMPAIGN_ID --brand asset-labs
python3 tools/tiktok.py create-campaign --name "Campaign" --objective CONVERSIONS --budget 50 --brand asset-labs --dry-run

# Ad Groups
python3 tools/tiktok.py ad-groups --campaign-id CAMP_ID --brand asset-labs
python3 tools/tiktok.py create-ad-group --campaign-id CAMP_ID --name "Group" --placement PLACEMENT_TYPE_AUTOMATIC --budget 25 --start-date 2026-02-15 --brand asset-labs --dry-run

# Ads
python3 tools/tiktok.py ads --adgroup-id AG_ID --brand asset-labs
python3 tools/tiktok.py create-ad --adgroup-id AG_ID --name "Ad" --format SINGLE_VIDEO --creative-json '{}' --brand asset-labs --dry-run

# Audiences & Reports
python3 tools/tiktok.py audiences --brand asset-labs
python3 tools/tiktok.py reports --type BASIC --dimensions campaign_id --metrics spend,impressions,clicks,ctr --start-date 2026-02-01 --end-date 2026-02-10 --brand asset-labs --json
```

### Content Commands
```bash
# Creator info
python3 tools/tiktok.py creator-info --brand asset-labs

# Post video from URL
python3 tools/tiktok.py post-video --url "https://example.com/video.mp4" --title "Title" --privacy SELF_ONLY --brand asset-labs --dry-run

# Upload local video
python3 tools/tiktok.py upload-video --file /path/to/video.mp4 --title "Title" --privacy SELF_ONLY --brand asset-labs --dry-run

# Check post status
python3 tools/tiktok.py post-status PUBLISH_ID --brand asset-labs
```

### OAuth Management
```bash
# Generate authorization URL (opens in browser)
python3 tools/tiktok.py auth-shop --generate-url --brand asset-labs
python3 tools/tiktok.py auth-marketing --generate-url --brand asset-labs
python3 tools/tiktok.py auth-content --generate-url --brand asset-labs

# Exchange authorization code for tokens
python3 tools/tiktok.py auth-shop --code CODE --brand asset-labs
python3 tools/tiktok.py auth-marketing --code CODE --brand asset-labs
python3 tools/tiktok.py auth-content --code CODE --brand asset-labs

# Refresh expired tokens
python3 tools/tiktok.py auth-shop --refresh --brand asset-labs
python3 tools/tiktok.py auth-marketing --refresh --brand asset-labs
python3 tools/tiktok.py auth-content --refresh --brand asset-labs
```

## Security

- **Always `--dry-run` first** for any mutation (create, update, fulfill, post)
- **Credentials isolated per brand** — each brand has its own Keychain entries and .env
- **OAuth tokens in Keychain** — not stored in .env files (rotated automatically)
- **No secrets in output** — JSON output never includes tokens or credentials
- **Content defaults to SELF_ONLY** — prevents accidental public posts before audit approval

## Credential Resolution Order

1. Brand `.env` → `capsules/ecommerce/brands/{brand}/.env`
2. Capsule `.env` → `capsules/ecommerce/.env`
3. Environment variables → `TIKTOK_SHOP_APP_KEY`, etc.
4. macOS Keychain → `keychain://ecommerce/{brand}/tiktok-shop`, etc.

## Rate Limits

| API | Limit | Tool Enforcement |
|-----|-------|-----------------|
| Shop | Varies by endpoint | 0.5s minimum interval |
| Marketing | Varies by endpoint | 0.5s minimum interval |
| Content | 6 req/min, 20 videos/day | 10s minimum interval |

## What This Skill Does NOT Handle

- TikTok Developer account registration (web portal)
- TikTok Shop seller account creation (web portal)
- TikTok for Business account setup (web portal)
- Content Posting API compliance audit (TikTok review process)
- TikTok Creator Fund enrollment
