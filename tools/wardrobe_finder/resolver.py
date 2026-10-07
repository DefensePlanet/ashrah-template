"""
URL resolver -- unwraps Pinterest pins, short links, and other indirect URLs
to their original product page before extraction.

Supported patterns:
  - Pinterest full pins:  pinterest.com/pin/123456/
  - Pinterest short links: pin.it/abc123
  - Amazon short links:   a.co/d/xxxxx
  - Generic short links:  t.co, bit.ly, goo.gl, tinyurl.com, ow.ly

Resolution strategy for Pinterest:
  1. Follow redirects (pin.it -> full pin URL)
  2. Parse embedded JSON data in the page for the source link
  3. Find the outbound "Visit" link via DOM selectors
  4. Check og:see_also meta tag
  5. Fall back to original URL if all strategies fail

Non-Pinterest URLs that are short links are resolved by following HTTP
redirects. Direct product URLs pass through unchanged.
"""

import logging
import re
from typing import Optional, Tuple
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# User-Agent (consistent with existing extractors/searchers)
# ---------------------------------------------------------------------------

_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/131.0.0.0 Safari/537.36"
)

# ---------------------------------------------------------------------------
# Known short-link domains
# ---------------------------------------------------------------------------

_SHORT_DOMAINS = frozenset([
    "pin.it",
    "bit.ly",
    "t.co",
    "goo.gl",
    "tinyurl.com",
    "ow.ly",
    "a.co",
    "amzn.to",
    "amzn.com",
])

# Pinterest TLDs (covers .com, .co.uk, .ca, .com.au, .de, .fr, etc.)
_PINTEREST_RE = re.compile(
    r"^https?://(www\.)?pinterest\.[a-z.]+/pin/", re.IGNORECASE
)
_PINTEREST_SHORT_RE = re.compile(
    r"^https?://pin\.it/", re.IGNORECASE
)

_AMAZON_RE = re.compile(
    r"^https?://(www\.)?amazon\.[a-z.]+/", re.IGNORECASE
)
_AMAZON_SHORT_RE = re.compile(
    r"^https?://(a\.co|amzn\.to|amzn\.com)/", re.IGNORECASE
)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def resolve_url(url: str) -> Tuple[str, str]:
    """Resolve an indirect URL to the actual product page URL.

    Returns:
        (resolved_url, source) where source is one of:
          "pinterest"  - resolved from a Pinterest pin
          "amazon"     - resolved from an Amazon short link
          "shortlink"  - resolved from a generic short link service
          "direct"     - URL was already a direct product page
    """
    url = url.strip()

    # --- Pinterest ---
    if _is_pinterest(url) or _is_pinterest_short(url):
        resolved = _resolve_pinterest(url)
        if resolved:
            return resolved, "pinterest"
        # Pinterest resolution failed -- return original and let
        # the extractor try (it will likely fail on pinterest.com
        # but we don't want to crash)
        logger.warning("Pinterest resolution failed for %s", url)
        return url, "pinterest"

    # --- Amazon short links ---
    if _is_amazon_short(url):
        resolved = _follow_redirects(url)
        if resolved != url:
            return resolved, "amazon"
        return url, "amazon"

    # --- Generic short links ---
    if _is_short_link(url):
        resolved = _follow_redirects(url)
        if resolved != url:
            return resolved, "shortlink"
        return url, "shortlink"

    # --- Direct URL ---
    return url, "direct"


# ---------------------------------------------------------------------------
# Detection helpers
# ---------------------------------------------------------------------------

def _is_pinterest(url: str) -> bool:
    """Check if URL is a full Pinterest pin URL."""
    return bool(_PINTEREST_RE.match(url))


def _is_pinterest_short(url: str) -> bool:
    """Check if URL is a Pinterest short link (pin.it)."""
    return bool(_PINTEREST_SHORT_RE.match(url))


def _is_amazon(url: str) -> bool:
    """Check if URL is an Amazon product link."""
    return bool(_AMAZON_RE.match(url))


def _is_amazon_short(url: str) -> bool:
    """Check if URL is an Amazon short link."""
    return bool(_AMAZON_SHORT_RE.match(url))


def _is_short_link(url: str) -> bool:
    """Check if URL is from a known short link service."""
    try:
        host = urlparse(url).hostname or ""
    except Exception:
        return False
    host = host.lower().removeprefix("www.")
    return host in _SHORT_DOMAINS


# ---------------------------------------------------------------------------
# Redirect follower (requests-based, no browser)
# ---------------------------------------------------------------------------

def _follow_redirects(url: str) -> str:
    """Follow HTTP redirects to find the final URL.

    Uses requests.head with allow_redirects=True. Falls back to
    requests.get if HEAD is rejected (some servers don't support HEAD).
    Returns the original URL if anything goes wrong.
    """
    try:
        import requests
    except ImportError:
        logger.warning("requests not available, cannot follow redirects")
        return url

    headers = {
        "User-Agent": _USER_AGENT,
        "Accept": "text/html,application/xhtml+xml",
        "Accept-Language": "en-US,en;q=0.9",
    }

    # Try HEAD first (lighter)
    try:
        resp = requests.head(
            url,
            allow_redirects=True,
            timeout=10,
            headers=headers,
        )
        if resp.url and resp.url != url:
            return resp.url
    except Exception as e:
        logger.debug("HEAD redirect failed for %s: %s", url, e)

    # Fallback: GET (some servers reject HEAD)
    try:
        resp = requests.get(
            url,
            allow_redirects=True,
            timeout=10,
            headers=headers,
            stream=True,  # Don't download body
        )
        final = resp.url
        resp.close()
        if final and final != url:
            return final
    except Exception as e:
        logger.debug("GET redirect failed for %s: %s", url, e)

    return url


# ---------------------------------------------------------------------------
# Pinterest resolver (Playwright-based)
# ---------------------------------------------------------------------------

def _resolve_pinterest(url: str) -> Optional[str]:
    """Extract the source product URL from a Pinterest pin.

    Strategy:
      1. If pin.it short link, follow redirects to get full pin URL.
      2. Launch headless Playwright to render the pin page.
      3. Try multiple extraction strategies for the outbound link.
      4. Validate the result is an external URL.
      5. Return None if all strategies fail.
    """
    # Step 1: Unwrap pin.it short links to full Pinterest URLs
    if _is_pinterest_short(url):
        expanded = _follow_redirects(url)
        if expanded != url:
            logger.info("Expanded pin.it link: %s -> %s", url, expanded)
            url = expanded
        # If still a pin.it link after redirect, we can't proceed without
        # a real Pinterest URL. Try Playwright on it anyway.

    # Step 2: Launch Playwright and extract the outbound link
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        logger.warning(
            "Playwright not installed. Cannot resolve Pinterest pins. "
            "Install with: pip install playwright && playwright install chromium"
        )
        return None

    pw = None
    browser = None
    try:
        pw = sync_playwright().start()
        browser = pw.chromium.launch(
            headless=True,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-dev-shm-usage",
            ],
        )
        context = browser.new_context(
            user_agent=_USER_AGENT,
            viewport={"width": 1920, "height": 1080},
            locale="en-US",
            timezone_id="America/New_York",
            color_scheme="light",
        )

        # Apply stealth if available (consistent with structured_data.py)
        try:
            from playwright_stealth import Stealth
            stealth = Stealth(
                navigator_platform_override="MacIntel",
                navigator_user_agent_override=_USER_AGENT,
                navigator_vendor_override="Google Inc.",
            )
            stealth.apply_stealth_sync(context)
        except ImportError:
            logger.debug("playwright-stealth not installed, proceeding without")

        page = context.new_page()
        page.goto(url, wait_until="domcontentloaded", timeout=30_000)

        # Give the page time to hydrate (Pinterest is a React SPA)
        page.wait_for_timeout(3000)

        # Strategy A: Parse embedded JSON data
        resolved = _pinterest_strategy_json(page)
        if resolved and _is_external_url(resolved, "pinterest"):
            logger.info("Pinterest resolved via JSON data: %s", resolved)
            return resolved

        # Strategy B: Find outbound link in the DOM
        resolved = _pinterest_strategy_dom(page)
        if resolved and _is_external_url(resolved, "pinterest"):
            logger.info("Pinterest resolved via DOM link: %s", resolved)
            return resolved

        # Strategy C: Check meta tags
        resolved = _pinterest_strategy_meta(page)
        if resolved and _is_external_url(resolved, "pinterest"):
            logger.info("Pinterest resolved via meta tag: %s", resolved)
            return resolved

        logger.warning("All Pinterest resolution strategies failed for %s", url)
        return None

    except Exception as e:
        logger.error("Pinterest resolution error for %s: %s", url, e)
        return None
    finally:
        if browser:
            try:
                browser.close()
            except Exception:
                pass
        if pw:
            try:
                pw.stop()
            except Exception:
                pass


def _pinterest_strategy_json(page) -> Optional[str]:
    """Strategy A: Extract source URL from Pinterest's embedded JSON data.

    Pinterest embeds pin data as JSON inside script tags. The data
    contains a "link" field pointing to the original source URL.
    """
    try:
        # Pinterest embeds JSON in multiple formats. Try them all.
        result = page.evaluate("""() => {
            // Method 1: Look through all script tags for JSON containing pin data
            const scripts = document.querySelectorAll('script[type="application/json"]');
            for (const script of scripts) {
                try {
                    const data = JSON.parse(script.textContent);
                    // Pinterest Redux store has pin data at various paths
                    const str = JSON.stringify(data);

                    // Look for "link" field that contains an external URL
                    // Pinterest stores the source URL in "link" or "source_url"
                    const linkMatch = str.match(/"link"\\s*:\\s*"(https?:\\/\\/[^"]+)"/);
                    if (linkMatch) {
                        const url = linkMatch[1];
                        // Make sure it's not a pinterest.com URL
                        if (!url.includes('pinterest.com') && !url.includes('pin.it')) {
                            return url;
                        }
                    }

                    const sourceMatch = str.match(/"source_url"\\s*:\\s*"(https?:\\/\\/[^"]+)"/);
                    if (sourceMatch) {
                        const url = sourceMatch[1];
                        if (!url.includes('pinterest.com') && !url.includes('pin.it')) {
                            return url;
                        }
                    }
                } catch (e) {
                    // Not valid JSON, skip
                }
            }

            // Method 2: Check ld+json for source
            const ldScripts = document.querySelectorAll('script[type="application/ld+json"]');
            for (const script of ldScripts) {
                try {
                    const data = JSON.parse(script.textContent);
                    if (data.mainEntityOfPage) {
                        const url = typeof data.mainEntityOfPage === 'string'
                            ? data.mainEntityOfPage
                            : data.mainEntityOfPage['@id'] || data.mainEntityOfPage.url;
                        if (url && !url.includes('pinterest.com')) {
                            return url;
                        }
                    }
                } catch(e) {}
            }

            // Method 3: Look in __PWS_DATA__ (Pinterest's window state)
            if (window.__PWS_DATA__) {
                const str = JSON.stringify(window.__PWS_DATA__);
                const linkMatch = str.match(/"link"\\s*:\\s*"(https?:\\/\\/[^"]+)"/);
                if (linkMatch) {
                    const url = linkMatch[1];
                    if (!url.includes('pinterest.com') && !url.includes('pin.it')) {
                        return url;
                    }
                }
            }

            return null;
        }""")
        return result
    except Exception as e:
        logger.debug("Pinterest JSON strategy failed: %s", e)
        return None


def _pinterest_strategy_dom(page) -> Optional[str]:
    """Strategy B: Find the outbound link via DOM selectors.

    Pinterest's pin pages have a "Visit" button or similar link that
    points to the original source. We try multiple selectors.
    """
    selectors = [
        # The "Visit" button on pin pages
        'a[data-test-id="pin-action-bar-link"]',
        # Official/source link
        'a[data-test-id="official-link"]',
        # Link button in the pin action bar
        'a[data-test-id="pin-closeup-link"]',
        # Generic external links with nofollow
        'a[rel="nofollow noopener"][target="_blank"]',
        # Broader nofollow
        'a[rel*="nofollow"][href^="http"]',
    ]

    for selector in selectors:
        try:
            elements = page.query_selector_all(selector)
            for el in elements:
                href = el.get_attribute("href")
                if href and _is_external_url(href, "pinterest"):
                    return href
        except Exception as e:
            logger.debug("DOM selector %s failed: %s", selector, e)
            continue

    return None


def _pinterest_strategy_meta(page) -> Optional[str]:
    """Strategy C: Check meta tags for the source URL.

    Pinterest sometimes puts the source in og:see_also or
    a custom meta tag.
    """
    meta_properties = [
        'og:see_also',
        'pinterestapp:source',
    ]

    for prop in meta_properties:
        try:
            content = page.evaluate(
                f'document.querySelector(\'meta[property="{prop}"]\')'
                f'?.getAttribute("content")'
            )
            if content and _is_external_url(content, "pinterest"):
                return content
        except Exception as e:
            logger.debug("Meta tag %s check failed: %s", prop, e)
            continue

    # Also check for a canonical link that points elsewhere
    try:
        canonical = page.evaluate(
            'document.querySelector(\'link[rel="canonical"]\')'
            '?.getAttribute("href")'
        )
        if canonical and _is_external_url(canonical, "pinterest"):
            return canonical
    except Exception:
        pass

    return None


def _is_external_url(url: str, source_platform: str) -> bool:
    """Check if a URL points to an external domain (not the source platform).

    Filters out:
      - Same-platform URLs (pinterest.com links when resolving Pinterest)
      - Empty/invalid URLs
      - JavaScript URLs
      - Hash-only URLs
    """
    if not url or not url.startswith("http"):
        return False

    try:
        host = urlparse(url).hostname or ""
    except Exception:
        return False

    host = host.lower()

    # Filter out same-platform URLs
    blocked_hosts = {
        "pinterest": [
            "pinterest.com", "www.pinterest.com",
            "pin.it", "pinterest.co.uk", "pinterest.ca",
            "pinterest.com.au", "pinterest.de", "pinterest.fr",
            "pinterest.es", "pinterest.it", "pinterest.pt",
            "pinterest.at", "pinterest.ch", "pinterest.nz",
            "i.pinimg.com",  # Pinterest image CDN
        ],
        "amazon": [
            "amazon.com", "www.amazon.com",
            "a.co", "amzn.to", "amzn.com",
        ],
    }

    for blocked in blocked_hosts.get(source_platform, []):
        if host == blocked or host.endswith("." + blocked):
            return False

    return True
