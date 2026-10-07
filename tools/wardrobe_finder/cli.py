"""
CLI argument parser for Wardrobe Finder.

Subcommands:
    search          Search resale marketplaces for a product
    watch           Manage watchlist for persistent monitoring
    stats           View search analytics and watch statistics
    config          View/update user profile (sizes, preferences)
    test-extractor  Test product extraction from a URL
    test-searcher   Test if a marketplace searcher is operational
    history         View recent search history
"""

import argparse
import sys

from . import VERSION


def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser with all subcommands."""
    parser = argparse.ArgumentParser(
        prog="wardrobe_finder",
        description=(
            "Secondhand clothing finder — takes a retail URL, "
            "extracts product details, searches resale marketplaces, "
            "returns matches sorted by price."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  %(prog)s search https://nike.com/t/air-force-1 --dry-run\n"
            "  %(prog)s search https://nike.com/t/air-force-1 --json\n"
            "  %(prog)s watch https://nike.com/t/air-force-1 --max-price 80\n"
            "  %(prog)s watch --list\n"
            "  %(prog)s watch --check\n"
            "  %(prog)s stats\n"
            "  %(prog)s config --tops M --bottoms 32x32 --shoes 10.5\n"
            "  %(prog)s config --show\n"
            "  %(prog)s test-extractor https://nike.com/t/air-force-1\n"
            "  %(prog)s test-searcher ebay\n"
            "  %(prog)s history --limit 5\n"
        ),
    )
    parser.add_argument(
        "--version", action="version", version=f"%(prog)s {VERSION}"
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true",
        help="Enable debug logging",
    )

    subparsers = parser.add_subparsers(
        dest="command", help="Available commands"
    )

    # -------------------------------------------------------------------
    # search
    # -------------------------------------------------------------------
    search_parser = subparsers.add_parser(
        "search",
        help="Search resale marketplaces for a product",
        description="Extract product details from a retail URL and search secondhand marketplaces.",
    )
    search_parser.add_argument(
        "url",
        help="Retail product URL to search for secondhand",
    )
    search_parser.add_argument(
        "--platforms", "-p",
        help="Comma-separated list of platforms to search (default: all enabled)",
    )
    search_parser.add_argument(
        "--json", action="store_true",
        help="Output results as JSON",
    )
    search_parser.add_argument(
        "--telegram", action="store_true",
        help="Output results in Telegram-friendly format (compact, no tables, top 5)",
    )
    search_parser.add_argument(
        "--limit", "-n", type=int, default=20,
        help="Max results to display (default: 20)",
    )
    search_parser.add_argument(
        "--max-price", type=float,
        help="Filter results to this maximum price",
    )
    search_parser.add_argument(
        "--color-strict", action="store_true",
        help="Only show results matching the exact color",
    )
    search_parser.add_argument(
        "--dry-run", action="store_true",
        help="Extract product details only, don't search",
    )
    search_parser.add_argument(
        "--no-expand", action="store_true",
        help="Skip AI query expansion (faster, no Gemini API call)",
    )
    search_parser.add_argument(
        "--no-vision", action="store_true",
        help="Skip vision matching (faster, no image comparison API call)",
    )
    search_parser.add_argument(
        "--no-resolve", action="store_true",
        help="Skip URL resolution (don't unwrap Pinterest pins or short links)",
    )
    search_parser.add_argument(
        "--gender", "-g",
        choices=["mens", "womens", "unisex", "any"],
        default="any",
        help="Filter results by gender (default: any)",
    )
    search_parser.add_argument(
        "--size-strict",
        action="store_true",
        default=True,
        help="Only show exact size matches (default: True)",
    )
    search_parser.add_argument(
        "--size-fuzzy",
        action="store_true",
        help="Allow fuzzy size matching (overrides --size-strict)",
    )
    search_parser.add_argument(
        "--min-score",
        type=int,
        default=0,
        help="Minimum match score (0-100) to show results (default: 0)",
    )

    # -------------------------------------------------------------------
    # config
    # -------------------------------------------------------------------
    config_parser = subparsers.add_parser(
        "config",
        help="View or update wardrobe profile",
        description="Manage your size profile and marketplace preferences.",
    )
    config_parser.add_argument(
        "--show", action="store_true",
        help="Display current profile",
    )
    config_parser.add_argument(
        "--tops",
        help="Your top/shirt size (e.g., M, L, XL)",
    )
    config_parser.add_argument(
        "--bottoms",
        help="Your bottom/pants size (e.g., 32x32, M)",
    )
    config_parser.add_argument(
        "--shoes",
        help="Your shoe size (e.g., 10.5)",
    )
    config_parser.add_argument(
        "--outerwear",
        help="Your outerwear size (e.g., L)",
    )
    config_parser.add_argument(
        "--accessories",
        help="Your accessories size (e.g., OS)",
    )
    config_parser.add_argument(
        "--dresses",
        help="Your dress size (e.g., 8, M)",
    )
    config_parser.add_argument(
        "--max-price", type=float,
        help="Default maximum price filter",
    )
    config_parser.add_argument(
        "--color-strict",
        action=argparse.BooleanOptionalAction,
        help="Require exact color match",
    )
    config_parser.add_argument(
        "--platforms",
        help="Comma-separated list of enabled platforms",
    )
    config_parser.add_argument(
        "--json", action="store_true",
        help="Output as JSON",
    )

    # -------------------------------------------------------------------
    # test-extractor
    # -------------------------------------------------------------------
    test_ext_parser = subparsers.add_parser(
        "test-extractor",
        help="Test product extraction from a URL",
        description="Extract and display product details without searching.",
    )
    test_ext_parser.add_argument(
        "url",
        help="Retail product URL to extract from",
    )
    test_ext_parser.add_argument(
        "--json", action="store_true",
        help="Output as JSON",
    )
    test_ext_parser.add_argument(
        "--no-resolve", action="store_true",
        help="Skip URL resolution (don't unwrap Pinterest pins or short links)",
    )

    # -------------------------------------------------------------------
    # test-searcher
    # -------------------------------------------------------------------
    test_search_parser = subparsers.add_parser(
        "test-searcher",
        help="Test if a marketplace searcher is operational",
        description="Check if a specific platform's searcher is configured and available.",
    )
    test_search_parser.add_argument(
        "platform",
        help="Platform name to test (e.g., ebay, poshmark, depop)",
    )
    test_search_parser.add_argument(
        "--json", action="store_true",
        help="Output as JSON",
    )

    # -------------------------------------------------------------------
    # history
    # -------------------------------------------------------------------
    history_parser = subparsers.add_parser(
        "history",
        help="View recent search history",
        description="Show recent searches from ~/.wardrobe/history/.",
    )
    history_parser.add_argument(
        "--limit", "-n", type=int, default=10,
        help="Number of recent searches to show (default: 10)",
    )
    history_parser.add_argument(
        "--json", action="store_true",
        help="Output as JSON",
    )

    # -------------------------------------------------------------------
    # watch (Phase 1.0.0 — Persistent Watching)
    # -------------------------------------------------------------------
    watch_parser = subparsers.add_parser(
        "watch",
        help="Manage watchlist for persistent monitoring",
        description=(
            "Add products to a watchlist for background monitoring. "
            "Check cycles search resale platforms and send Telegram "
            "notifications for new matches and price drops."
        ),
    )
    watch_parser.add_argument(
        "url", nargs="?",
        help="Retail product URL to add to watchlist",
    )
    watch_parser.add_argument(
        "--name",
        help="Custom display name for the watch entry",
    )
    watch_parser.add_argument(
        "--max-price", type=float,
        help="Maximum price for notifications (overrides profile default)",
    )
    watch_parser.add_argument(
        "--platforms", "-p",
        help="Comma-separated platforms to search (overrides profile default)",
    )
    watch_parser.add_argument(
        "--list", action="store_true",
        help="List all watched items",
    )
    watch_parser.add_argument(
        "--remove", metavar="ID",
        help="Remove a watch entry by ID",
    )
    watch_parser.add_argument(
        "--check", action="store_true",
        help="Run one check cycle for all watched items",
    )
    watch_parser.add_argument(
        "--json", action="store_true",
        help="Output as JSON",
    )
    watch_parser.add_argument(
        "--no-resolve", action="store_true",
        help="Skip URL resolution when adding a watch",
    )
    watch_parser.add_argument(
        "--verbose", action="store_true",
        help="Show detailed output during check cycles",
    )

    # -------------------------------------------------------------------
    # stats (Phase 1.0.0 — Analytics)
    # -------------------------------------------------------------------
    stats_parser = subparsers.add_parser(
        "stats",
        help="View search analytics and watch statistics",
        description="Aggregate stats from search history and watchlist.",
    )
    stats_parser.add_argument(
        "--json", action="store_true",
        help="Output as JSON",
    )

    return parser


def main(argv=None) -> int:
    """CLI entry point."""
    import logging

    parser = build_parser()
    args = parser.parse_args(argv)

    # Configure logging
    log_level = logging.DEBUG if args.verbose else logging.WARNING
    logging.basicConfig(
        level=log_level,
        format="%(name)s: %(message)s",
        stream=sys.stderr,
    )

    if not args.command:
        parser.print_help()
        return 0

    # Route to handler
    from . import handlers

    handler_map = {
        "search": handlers.handle_search,
        "watch": handlers.handle_watch,
        "stats": handlers.handle_stats,
        "config": handlers.handle_config,
        "test-extractor": handlers.handle_test_extractor,
        "test-searcher": handlers.handle_test_searcher,
        "history": handlers.handle_history,
    }

    handler = handler_map.get(args.command)
    if handler:
        return handler(args)
    else:
        parser.print_help()
        return 1
