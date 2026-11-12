# Proton Mail Integration

Direct Proton Mail access via Proton Bridge (IMAP/SMTP). Stdlib-only Python CLI.

## Tool Location
`tools/proton_mail.py`

## Prerequisites
- Proton Mail Bridge running on localhost (IMAP 1143, SMTP 1025)
- Credentials in macOS Keychain (service: `proton-bridge`) or env vars (`PROTON_EMAIL`, `PROTON_BRIDGE_PASSWORD`)

## Quick Reference

### Check connection
```bash
python3 tools/proton_mail.py status
```

### Read inbox
```bash
python3 tools/proton_mail.py inbox                        # Last 20 messages
python3 tools/proton_mail.py inbox --unread                # Unread only
python3 tools/proton_mail.py inbox --limit 50              # More messages
python3 tools/proton_mail.py inbox --from "someone@x.com"  # Filter by sender
python3 tools/proton_mail.py inbox --subject "invoice"      # Filter by subject
python3 tools/proton_mail.py inbox --since 2026-02-01      # Since date
python3 tools/proton_mail.py inbox --folder "Sent"         # Different folder
```

### Read a message
```bash
python3 tools/proton_mail.py read <uid>
python3 tools/proton_mail.py read <uid> --html      # Raw HTML body
python3 tools/proton_mail.py read <uid> --headers    # All headers
```

### Search
```bash
python3 tools/proton_mail.py search "query"                  # Subject search
python3 tools/proton_mail.py search --body "payment"         # Body search
python3 tools/proton_mail.py search --from "bank@x.com"      # From search
python3 tools/proton_mail.py search "invoice" --all-folders   # All folders
```

### Send email
```bash
python3 tools/proton_mail.py send --to "a@x.com" --subject "Hello" --body "Message"
python3 tools/proton_mail.py send --to "a@x.com" --subject "Files" --body "See attached" --attach /path/to/file.pdf
python3 tools/proton_mail.py send --to "a@x.com" --subject "Test" --body "msg" --dry-run
```

### Reply / Forward
```bash
python3 tools/proton_mail.py reply <uid> --body "Thanks!"
python3 tools/proton_mail.py reply <uid> --body "Noted." --reply-all
python3 tools/proton_mail.py forward <uid> --to "colleague@x.com" --body "FYI"
```

### Folder management
```bash
python3 tools/proton_mail.py folders                  # List all folders
python3 tools/proton_mail.py move <uid> "Archive"     # Move message
python3 tools/proton_mail.py move <uid> "Trash"       # Trash message
```

### Message actions
```bash
python3 tools/proton_mail.py mark <uid> --read
python3 tools/proton_mail.py mark <uid> --unread
python3 tools/proton_mail.py mark <uid> --starred
python3 tools/proton_mail.py attachments <uid>                    # List attachments
python3 tools/proton_mail.py attachments <uid> --download /tmp/   # Download all
python3 tools/proton_mail.py delete <uid>                         # Move to Trash
```

### Global flags
- `--json` — Machine-readable JSON output
- `--verbose` — Debug info (never shows password)
- `--dry-run` — Preview without executing (send/reply/forward)
- `--timeout <seconds>` — Connection timeout (default: 30)

## Security
- Credentials stored in macOS Keychain, never in files
- Password never printed or logged, even in verbose mode
- Bridge connection is local only (127.0.0.1)
- All email encryption/decryption handled by Bridge transparently

## Sending Guidelines
- **Always use `--dry-run` first** when composing emails on behalf of {{USER_NAME}}
- Get explicit approval before sending any email
- Never send emails without {{USER_NAME}}'s confirmation unless pre-authorized for a specific workflow
