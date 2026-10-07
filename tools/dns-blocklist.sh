#!/bin/bash
# dns-blocklist.sh — Manage dnscrypt-proxy ad/tracker blocking
# Usage:
#   dns-blocklist.sh status       — Show blocking stats
#   dns-blocklist.sh blocked      — Show recently blocked domains
#   dns-blocklist.sh check <domain> — Check if a domain is blocked
#   dns-blocklist.sh allow <domain> — Allowlist a domain (unblock it)
#   dns-blocklist.sh update       — Update blocklist from OISD

BLOCKLIST="/opt/homebrew/etc/blocked-names.txt"
ALLOWLIST="/opt/homebrew/etc/allowed-names.txt"
BLOCK_LOG="/opt/homebrew/etc/blocked-names.log"

case "${1}" in
  status)
    echo "=== DNS Blocklist Status ==="
    blocked=$(grep -c -v "^#" "$BLOCKLIST" 2>/dev/null || echo 0)
    allowed=$(grep -c -v "^#" "$ALLOWLIST" 2>/dev/null || echo 0)
    echo "Blocked domains: $blocked"
    echo "Allowlisted: $allowed"
    if [ -f "$BLOCK_LOG" ]; then
      today=$(date +%Y-%m-%d)
      today_count=$(grep -c "$today" "$BLOCK_LOG" 2>/dev/null || echo 0)
      total_count=$(wc -l < "$BLOCK_LOG" 2>/dev/null || echo 0)
      echo "Blocked queries today: $today_count"
      echo "Blocked queries total: $total_count"
    else
      echo "Block log: not yet created (will appear after first blocked query)"
    fi
    echo ""
    echo "Blocklist: $BLOCKLIST"
    echo "Allowlist: $ALLOWLIST"
    echo "Block log: $BLOCK_LOG"
    ;;

  blocked)
    if [ ! -f "$BLOCK_LOG" ]; then
      echo "No block log yet. Queries haven't been blocked yet or dnscrypt-proxy needs a restart."
      exit 0
    fi
    lines="${2:-30}"
    echo "=== Last $lines blocked queries ==="
    tail -n "$lines" "$BLOCK_LOG"
    ;;

  check)
    if [ -z "$2" ]; then
      echo "Usage: dns-blocklist.sh check <domain>"
      exit 1
    fi
    domain="$2"
    if grep -qiF "$domain" "$ALLOWLIST" 2>/dev/null; then
      echo "ALLOWED — $domain is in the allowlist"
    elif grep -qiF "$domain" "$BLOCKLIST" 2>/dev/null; then
      echo "BLOCKED — $domain matched in blocklist:"
      grep -iF "$domain" "$BLOCKLIST" | head -5
    else
      echo "NOT BLOCKED — $domain is not in the blocklist"
    fi
    ;;

  allow)
    if [ -z "$2" ]; then
      echo "Usage: dns-blocklist.sh allow <domain>"
      exit 1
    fi
    domain="$2"
    echo "$domain" >> "$ALLOWLIST"
    echo "Added $domain to allowlist. Restarting dnscrypt-proxy..."
    brew services restart dnscrypt-proxy 2>/dev/null
    echo "Done. $domain is now unblocked."
    ;;

  update)
    echo "Updating OISD blocklist..."
    curl -sL "https://big.oisd.nl/domainswild" -o "$BLOCKLIST.tmp"
    new_count=$(grep -c -v "^#" "$BLOCKLIST.tmp" 2>/dev/null || echo 0)
    if [ "$new_count" -gt 100000 ]; then
      mv "$BLOCKLIST.tmp" "$BLOCKLIST"
      echo "Updated: $new_count domains"
      echo "Restarting dnscrypt-proxy..."
      brew services restart dnscrypt-proxy 2>/dev/null
      echo "Done."
    else
      rm -f "$BLOCKLIST.tmp"
      echo "ERROR: Downloaded list seems too small ($new_count domains). Keeping existing list."
      exit 1
    fi
    ;;

  *)
    echo "dns-blocklist.sh — Manage DNS ad/tracker blocking"
    echo ""
    echo "Commands:"
    echo "  status          Show blocking stats"
    echo "  blocked [N]     Show last N blocked queries (default 30)"
    echo "  check <domain>  Check if a domain is blocked"
    echo "  allow <domain>  Unblock a domain (add to allowlist)"
    echo "  update          Update blocklist from OISD"
    ;;
esac
