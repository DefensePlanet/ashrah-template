"""
Output formatters — table display, JSON, Telegram, watchlist, and stats output.

Handles rendering search results in multiple modes:
1. Human-readable table (default terminal output)
2. Machine-readable JSON (--json flag)
3. Telegram-friendly plaintext (--telegram flag)
4. Watchlist display (watch --list)
5. Stats analytics (stats)
6. Watch notification formatting (Telegram alerts)
"""

import json
import sys
from typing import Dict, List, Optional

from .models import Product, SearchResult, WatchEntry

# ---------------------------------------------------------------------------
# Terminal colours
# ---------------------------------------------------------------------------

GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
BOLD = "\033[1m"
DIM = "\033[2m"
RESET = "\033[0m"

# Disable colors if not a terminal
if not sys.stdout.isatty():
    GREEN = RED = YELLOW = CYAN = BOLD = DIM = RESET = ""


# ---------------------------------------------------------------------------
# JSON output
# ---------------------------------------------------------------------------

def output_json(
    product: Product,
    results: List[SearchResult],
    metadata: Optional[Dict] = None,
) -> str:
    """Format results as JSON string."""
    output = {
        "product": product.to_dict(),
        "results": [r.to_dict() for r in results],
        "total_results": len(results),
    }
    if metadata:
        output["metadata"] = metadata
    return json.dumps(output, indent=2)


# ---------------------------------------------------------------------------
# Table output
# ---------------------------------------------------------------------------

def output_table(
    product: Product,
    results: List[SearchResult],
    limit: int = 20,
) -> str:
    """Format results as a readable terminal table."""
    lines = []

    # Product header
    lines.append("")
    lines.append(f"{BOLD}Product:{RESET} {product.brand} {product.model}")
    if product.color and product.color != "Unknown":
        lines.append(f"{BOLD}Color:{RESET}   {product.color}")
    if product.size and product.size != "Unknown":
        lines.append(f"{BOLD}Size:{RESET}    {product.size}")
    if product.retail_price > 0:
        lines.append(f"{BOLD}Retail:{RESET}  ${product.retail_price:.2f}")
    if product.category.value != "unknown":
        lines.append(f"{BOLD}Category:{RESET} {product.category.value}")
    if hasattr(product, "gender") and product.gender.value != "unknown":
        lines.append(f"{BOLD}Gender:{RESET}   {product.gender.value}")
    lines.append("")

    if not results:
        lines.append(f"{YELLOW}No secondhand listings found.{RESET}")
        return "\n".join(lines)

    # Table header
    # Columns: # | Score | Platform | Price | Size | Condition | Title (truncated)
    header = (
        f"  {DIM}#{RESET}  "
        f"{BOLD}{'Score':>5}{RESET}  "
        f"{BOLD}{'Platform':<10}{RESET}  "
        f"{BOLD}{'Price':>8}{RESET}  "
        f"{BOLD}{'Size':<6}{RESET}  "
        f"{BOLD}{'Cond':<9}{RESET}  "
        f"{BOLD}Title{RESET}"
    )
    lines.append(header)
    lines.append(f"  {DIM}{'─' * 90}{RESET}")

    displayed = results[:limit]
    for i, r in enumerate(displayed, 1):
        # Score coloring: >80% green, 60-80% yellow, <60% red
        if r.match_score >= 80:
            score_color = GREEN
        elif r.match_score >= 60:
            score_color = YELLOW
        else:
            score_color = RED
        score_str = f"{score_color}{r.match_score:>3}%{RESET}"

        # Price coloring
        if product.retail_price > 0 and r.price < product.retail_price:
            savings_pct = (1 - r.price / product.retail_price) * 100
            price_str = f"{GREEN}${r.price:>6.2f}{RESET}"
        else:
            savings_pct = 0
            price_str = f"${r.price:>6.2f}"

        # Truncate title
        title = r.title[:42] + "..." if len(r.title) > 45 else r.title

        # Size display
        size_str = r.size[:6] if r.size else "?"

        # Condition display
        cond_str = r.condition.value[:9]

        line = (
            f"  {DIM}{i:>2}{RESET}  "
            f"{score_str}  "
            f"{r.platform:<10}  "
            f"{price_str}  "
            f"{size_str:<6}  "
            f"{cond_str:<9}  "
            f"{title}"
        )
        lines.append(line)

    lines.append(f"  {DIM}{'─' * 90}{RESET}")

    # Summary
    total = len(results)
    if total > limit:
        lines.append(
            f"  {DIM}Showing {limit} of {total} results{RESET}"
        )

    # Savings summary
    if product.retail_price > 0 and results:
        best = min(results, key=lambda r: r.price)
        if best.price < product.retail_price:
            savings = product.retail_price - best.price
            savings_pct = (savings / product.retail_price) * 100
            lines.append(
                f"\n  {GREEN}{BOLD}Best deal:{RESET} "
                f"${best.price:.2f} on {best.platform} "
                f"({GREEN}save ${savings:.2f} / {savings_pct:.0f}%{RESET} "
                f"vs ${product.retail_price:.2f} retail)"
            )

    # Platform breakdown
    platforms = {}
    for r in results:
        platforms[r.platform] = platforms.get(r.platform, 0) + 1
    platform_summary = ", ".join(
        f"{p}: {c}" for p, c in sorted(platforms.items())
    )
    lines.append(
        f"  {DIM}Platforms: {platform_summary}{RESET}"
    )
    lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Telegram output
# ---------------------------------------------------------------------------

def format_telegram(
    product: Product,
    results: List[SearchResult],
    limit: int = 5,
    platforms_searched: Optional[List[str]] = None,
) -> str:
    """Format results as Telegram-friendly plaintext.

    Uses Telegram-compatible bold (*text*) and keeps everything compact
    for phone-screen readability. No wide tables, no ANSI escapes, no
    HTML tags, no em dashes.
    """
    if not results:
        platform_names = ", ".join(platforms_searched) if platforms_searched else "all platforms"
        return f"No matches found on {platform_names}."

    lines: List[str] = []
    displayed = results[:limit]

    for r in displayed:
        # Title line: [Platform] Title - $Price
        title = r.title[:60] + "..." if len(r.title) > 63 else r.title
        lines.append(f"[{r.platform}] {title} - ${r.price:.2f}")

        # Details line: Size | Condition | Match
        size_str = r.size if r.size else "?"
        cond_str = r.condition.value
        lines.append(f"Size: {size_str} | Condition: {cond_str} | Match: {r.match_score}%")

        # Link line
        lines.append(r.url)

        # Blank separator between listings
        lines.append("")

    # Savings summary
    if product.retail_price > 0:
        best = min(results, key=lambda r: r.price)
        savings = product.retail_price - best.price
        if savings > 0:
            savings_pct = (savings / product.retail_price) * 100
            lines.append(
                f"Retail: ${product.retail_price:.2f} | "
                f"Best: ${best.price:.2f} | "
                f"Save: ${savings:.2f} ({savings_pct:.0f}%)"
            )
        else:
            lines.append(
                f"Retail: ${product.retail_price:.2f} | "
                f"Best: ${best.price:.2f} (no savings found)"
            )

    # If more results were trimmed, note it
    total = len(results)
    if total > limit:
        lines.append(f"{total - limit} more results not shown.")

    return "\n".join(lines).rstrip()


# ---------------------------------------------------------------------------
# Product display (for dry-run / test-extractor)
# ---------------------------------------------------------------------------

def output_product(product: Product, as_json: bool = False) -> str:
    """Format a single product for display."""
    if as_json:
        return json.dumps(product.to_dict(), indent=2)

    lines = [
        "",
        f"  {BOLD}Extracted Product Details{RESET}",
        f"  {'─' * 40}",
        f"  {BOLD}Brand:{RESET}    {product.brand}",
        f"  {BOLD}Model:{RESET}    {product.model}",
        f"  {BOLD}Size:{RESET}     {product.size}",
        f"  {BOLD}Color:{RESET}    {product.color}",
        f"  {BOLD}Category:{RESET} {product.category.value}",
    ]
    if hasattr(product, "gender") and product.gender.value != "unknown":
        lines.append(f"  {BOLD}Gender:{RESET}   {product.gender.value}")
    if product.retail_price > 0:
        lines.append(f"  {BOLD}Price:{RESET}    ${product.retail_price:.2f}")
    if product.sku:
        lines.append(f"  {BOLD}SKU:{RESET}      {product.sku}")
    if product.upc:
        lines.append(f"  {BOLD}UPC:{RESET}      {product.upc}")
    if product.mpn:
        lines.append(f"  {BOLD}MPN:{RESET}      {product.mpn}")
    if product.image_url:
        lines.append(f"  {BOLD}Image:{RESET}    {product.image_url[:80]}")
    if product.description:
        desc = product.description[:120] + "..." if len(product.description) > 120 else product.description
        lines.append(f"  {BOLD}Desc:{RESET}     {desc}")
    lines.append(f"  {BOLD}URL:{RESET}      {product.url}")
    lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Profile display
# ---------------------------------------------------------------------------

def output_profile(profile_data: dict, as_json: bool = False) -> str:
    """Format user profile for display."""
    if as_json:
        return json.dumps(profile_data, indent=2)

    lines = [
        "",
        f"  {BOLD}Wardrobe Profile{RESET}",
        f"  {'─' * 40}",
    ]

    sizes = profile_data.get("sizes", {})
    if sizes:
        lines.append(f"  {BOLD}Sizes:{RESET}")
        for cat, size in sorted(sizes.items()):
            lines.append(f"    {cat:<15} {size}")
    else:
        lines.append(f"  {DIM}No sizes configured{RESET}")

    lines.append(f"  {BOLD}Color strict:{RESET}  {profile_data.get('color_strict', False)}")

    max_price = profile_data.get("max_price")
    if max_price:
        lines.append(f"  {BOLD}Max price:{RESET}     ${max_price:.2f}")

    platforms = profile_data.get("enabled_platforms", [])
    lines.append(f"  {BOLD}Platforms:{RESET}     {', '.join(platforms)}")
    lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Watchlist display (Phase 1.0.0)
# ---------------------------------------------------------------------------

def output_watchlist(
    watches: List[WatchEntry],
    as_json: bool = False,
) -> str:
    """Format the watchlist for terminal display or JSON output."""
    if as_json:
        return json.dumps([w.to_dict() for w in watches], indent=2)

    if not watches:
        return f"\n  {DIM}Watchlist is empty. Add items with: wardrobe_finder watch <url>{RESET}\n"

    lines = [
        "",
        f"  {BOLD}Watchlist{RESET} ({len(watches)} items)",
        f"  {'─' * 60}",
    ]

    for w in watches:
        product = w.product
        brand = product.get("brand", "?")
        model = product.get("model", "?")
        retail = product.get("retail_price", 0)

        # Status line
        name_str = f"{BOLD}{w.name}{RESET}"
        id_str = f"{DIM}({w.id}){RESET}"
        lines.append(f"  {name_str} {id_str}")

        # Details
        detail_parts = [f"{brand} {model}"]
        if retail > 0:
            detail_parts.append(f"${retail:.2f} retail")
        if w.max_price is not None:
            detail_parts.append(f"max ${w.max_price:.2f}")
        if w.platforms:
            detail_parts.append(f"on {', '.join(w.platforms)}")
        lines.append(f"    {' | '.join(detail_parts)}")

        # Check history
        if w.last_checked:
            lines.append(
                f"    {DIM}Last checked: {w.last_checked[:19]} "
                f"({w.check_count} checks){RESET}"
            )
        else:
            lines.append(f"    {DIM}Not yet checked{RESET}")

        lines.append("")

    lines.append(f"  {DIM}Use --check to run a check cycle{RESET}")
    lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Stats display (Phase 1.0.0)
# ---------------------------------------------------------------------------

def output_stats(stats_data: dict, as_json: bool = False) -> str:
    """Format analytics data for terminal display or JSON output."""
    if as_json:
        return json.dumps(stats_data, indent=2)

    lines = [
        "",
        f"  {BOLD}Wardrobe Finder Stats{RESET}",
        f"  {'─' * 40}",
    ]

    # Search history stats
    total_searches = stats_data.get("total_searches", 0)
    lines.append(f"  {BOLD}Total searches:{RESET}    {total_searches}")

    total_results = stats_data.get("total_results", 0)
    lines.append(f"  {BOLD}Total results:{RESET}     {total_results}")

    avg_results = stats_data.get("avg_results_per_search", 0)
    lines.append(f"  {BOLD}Avg results:{RESET}       {avg_results:.1f}")

    avg_duration = stats_data.get("avg_duration_ms", 0)
    lines.append(f"  {BOLD}Avg search time:{RESET}   {avg_duration:.0f}ms")

    # Watch stats
    lines.append("")
    watch_count = stats_data.get("watch_count", 0)
    lines.append(f"  {BOLD}Watched items:{RESET}     {watch_count}")

    total_checks = stats_data.get("total_checks", 0)
    lines.append(f"  {BOLD}Total checks:{RESET}      {total_checks}")

    # Top searched brands
    top_brands = stats_data.get("top_brands", [])
    if top_brands:
        lines.append("")
        lines.append(f"  {BOLD}Top Brands:{RESET}")
        for brand, count in top_brands[:5]:
            lines.append(f"    {brand:<20} {count} searches")

    # Platform breakdown
    platform_counts = stats_data.get("platform_results", {})
    if platform_counts:
        lines.append("")
        lines.append(f"  {BOLD}Results by Platform:{RESET}")
        for platform, count in sorted(
            platform_counts.items(), key=lambda x: -x[1]
        ):
            lines.append(f"    {platform:<15} {count} results")

    lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Watch notification formatting (Phase 1.0.0)
# ---------------------------------------------------------------------------

def format_watch_notification(
    watch_name: str,
    new_matches: List[SearchResult],
    price_drops: List[Dict],
    product: dict,
) -> str:
    """Format a Telegram notification for a watched item.

    Combines new matches and price drops into one message per watched item.
    No em dashes, no ANSI escapes, no HTML tags.
    """
    lines: List[str] = []
    retail_price = product.get("retail_price", 0)

    # New matches section
    if new_matches:
        lines.append(f"New match: {watch_name}")
        lines.append("")

        for r in new_matches:
            title = r.title[:60] + "..." if len(r.title) > 63 else r.title
            lines.append(f"[{r.platform}] {title} - ${r.price:.2f}")

            size_str = r.size if r.size else "?"
            cond_str = r.condition.value
            lines.append(
                f"Size: {size_str} | Condition: {cond_str} | "
                f"Match: {r.match_score}%"
            )
            lines.append(r.url)

            if retail_price > 0 and r.price < retail_price:
                savings = retail_price - r.price
                savings_pct = (savings / retail_price) * 100
                lines.append(
                    f"Retail: ${retail_price:.2f} | "
                    f"Save: ${savings:.2f} ({savings_pct:.0f}%)"
                )

            lines.append("")

    # Price drops section
    if price_drops:
        if new_matches:
            # Separator between sections
            lines.append("")
        lines.append(f"Price drop: {watch_name}")
        lines.append("")

        for drop in price_drops:
            title = drop["title"]
            if len(title) > 63:
                title = title[:60] + "..."
            pct = drop["pct"]
            lines.append(f"[{drop['platform']}] {title}")
            lines.append(
                f"Was: ${drop['old_price']:.2f} -> "
                f"Now: ${drop['new_price']:.2f} (-{pct:.0f}%)"
            )
            lines.append(drop["url"])
            lines.append("")

    return "\n".join(lines).rstrip()
