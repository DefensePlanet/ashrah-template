#!/usr/bin/env python3
"""
Catalyst Secrets Sync — Bridge macOS Keychain and Strongbox KeePass database.

Two-pass backup strategy:
    Pass 1 (TOML):      Reads keychain.required.toml manifests across capsules.
                         These have rich metadata (env_var names, capsule labels).
    Pass 2 (Discovery): Dumps ALL service names from macOS Keychain, filters for
                         Catalyst-related ones, and backs up anything not already
                         covered by the TOML pass.

Modes:
    --backup   Read secrets from Keychain, write to KeePass database
    --restore  Read secrets from KeePass database, write to Keychain
    --status   Compare Keychain vs KeePass and show sync state

Usage:
    python3 tools/sync-secrets.py --backup
    python3 tools/sync-secrets.py --restore
    python3 tools/sync-secrets.py --status
    python3 tools/sync-secrets.py --help

Security:
    - NEVER prints secret values to stdout
    - Master password retrieved from Keychain (or prompted on new machine)
    - Uses pykeepass for KeePass operations
    - Uses subprocess for Keychain operations (same pattern as secret_provider.py)
"""

from __future__ import annotations

import argparse
import getpass
import re
import subprocess
import sys
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_CATALYST_ROOT = Path(__file__).resolve().parent.parent

DB_PATH = (
    Path.home()
    / "Library"
    / "Mobile Documents"
    / "iCloud~com~strongbox"
    / "Documents"
    / "Catalyst Secrets.kdbx"
)

KEYCHAIN_SERVICE = "Catalyst-Strongbox"
KEYCHAIN_ACCOUNT = "master-password"

_SUBPROCESS_TIMEOUT = 5

# ---------------------------------------------------------------------------
# TOML manifest locations (explicit, matches check-secrets.py)
# ---------------------------------------------------------------------------

TOML_MANIFESTS: List[Tuple[Path, str]] = [
    # (path_to_toml, KeePass_group_name)
    (_CATALYST_ROOT / "keychain.required.toml", "Root"),
    (_CATALYST_ROOT / "capsules" / "example-team-tags" / "keychain.required.toml", "Big Sky Tags"),
    (_CATALYST_ROOT / "capsules" / "example-team-tags" / "portal" / "keychain.required.toml", "Big Sky Tags"),
    (_CATALYST_ROOT / "capsules" / "catalyst-digital" / "keychain.required.toml", "Catalyst Digital"),
    (_CATALYST_ROOT / "capsules" / "catalyst-mobile" / "api" / "keychain.required.toml", "Catalyst Mobile"),
    (_CATALYST_ROOT / "capsules" / "catalyst-mobile" / "deployment" / "cloudflare" / "keychain.required.toml", "Catalyst Mobile"),
    (_CATALYST_ROOT / "tools" / "telegram" / "TC3" / "keychain.required.toml", "Telegram TC3"),
    (_CATALYST_ROOT / "capsules" / "example-partners" / "portal" / "keychain.required.toml", "Mid Partners"),
]

# Shared secrets not in any capsule TOML — these are cross-capsule services
# stored in /Catalyst/Shared. Format: (service, account, env_var_hint)
SHARED_SECRETS: List[Tuple[str, str, str]] = [
    ("openrouter-api", "catalyst", "OPENROUTER_API_KEY"),
    ("openai-api-key", "catalyst", "OPENAI_API_KEY"),
    ("gemini-api-key", "catalyst", "GEMINI_API_KEY"),
    ("simplelogin-api-key", "catalyst", "SIMPLELOGIN_API_KEY"),
    ("virustotal-api-key", "catalyst", "VIRUSTOTAL_API_KEY"),
    ("github-pat", "catalyst", "GITHUB_TOKEN"),
    ("proton-bridge", "catalyst", "PROTON_BRIDGE_PASSWORD"),
    ("njalla-api", "njalla", "NJALLA_API_TOKEN"),
    ("canva-client-id", "canva", "CANVA_CLIENT_ID"),
    ("canva-client-secret", "canva", "CANVA_CLIENT_SECRET"),
    ("huggingface", "catalyst", "HF_TOKEN"),
    ("anthropic-api-key", "catalyst", "ANTHROPIC_API_KEY"),
]

# ---------------------------------------------------------------------------
# Keychain Discovery — prefixes and exclusions
# ---------------------------------------------------------------------------

# Prefixes/patterns that identify Catalyst-related Keychain services
CATALYST_PREFIXES: List[str] = [
    "bst-",
    "catalyst-",
    "cm-",
    "example-partners-",
    "tc3-",
    "telegram-",
    "cd-",
    "meta-",
    "tiktok-",
    "openai-",
    "openrouter-",
    "gemini-",
    "anthropic-",
    "simplelogin-",
    "virustotal-",
    "github-",
    "proton-",
    "njalla-",
    "canva-",
    "huggingface",
    "cloudflare-",
    "google-",
    "exampleco-",
    "lithic-",
    "Mailgun-",
    "Wise-",
    "resolve-script",
    "ios_signing",
    "instagram_scraper",
]

# Exact service names to exclude (system/browser items that match prefixes)
EXCLUDE_SERVICES: Set[str] = {
    "Catalyst-Strongbox",       # Our own master password — never back up recursively
    "MetadataKeychain",         # Apple system
}

# Patterns to exclude (substring match)
EXCLUDE_PATTERNS: List[str] = [
    "Safe Storage",
    "com.apple.",
    "com.adobe.",
    "com.facebook.",
    "com.reincubate.",
    "Adobe ",
    "iCloud",
    "ProtectedCloudStorage",
    "TelephonyUtilities",
    "TMASecureStorage",
    "Safari ",
    "AirPlay ",
    "Apple ",
]

# Service name prefix -> KeePass group routing
# Order matters: first match wins. More specific prefixes come first.
GROUP_ROUTING: List[Tuple[str, str]] = [
    ("bst-", "Big Sky Tags"),
    ("catalyst-design-", "Catalyst Design System"),
    ("catalyst-digital-", "Catalyst Digital"),
    ("catalyst-", "Root"),
    ("cm-", "Catalyst Mobile"),
    ("example-partners-", "Mid Partners"),
    ("tc3-", "Telegram TC3"),
    ("telegram-bot-", "Telegram Bots"),
    ("telegram-{{ORCHESTRATOR_NAME_LOWER}}-", "Telegram Bots"),
    ("telegram-openai-", "Telegram TC3"),
    ("telegram-telegram-", "Telegram TC3"),
    ("telegram-", "Telegram TC3"),
    ("meta-", "Catalyst Digital"),
    ("tiktok-", "Catalyst Digital"),
    ("google-", "Google"),
    ("proton-", "Proton"),
    ("Proton", "Proton"),
    ("cloudflare-", "Cloudflare"),
    ("lithic-", "Financial"),
    ("Wise-", "Financial"),
    ("Mailgun-", "Big Sky Tags"),
    ("exampleco-", "Mid Partners"),
    ("openai-", "Shared"),
    ("openrouter-", "Shared"),
    ("gemini-", "Shared"),
    ("anthropic-", "Shared"),
    ("simplelogin-", "Shared"),
    ("virustotal-", "Shared"),
    ("github-", "Shared"),
    ("njalla-", "Shared"),
    ("canva-", "Shared"),
    ("huggingface", "Shared"),
    ("resolve-script", "Shared"),
    ("ios_signing", "Shared"),
    ("instagram_scraper", "Shared"),
    ("cd-", "Catalyst Digital"),
]

# Suffixes that route to Legacy Duplicates (regardless of prefix routing)
LEGACY_SUFFIXES: List[str] = [
    "-zshrc",
    "-env",
]


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


@dataclass
class SecretEntry:
    """A secret to sync between Keychain and KeePass."""

    service: str  # Keychain service name (also KeePass entry title)
    account: str  # Keychain account name (also KeePass entry username)
    env_var: str  # Environment variable name (stored as custom field)
    group_name: str  # KeePass group under /Catalyst/
    capsule: str  # Capsule label for metadata
    source: str = "toml"  # "toml" or "keychain-discovery"
    in_keychain: bool = False
    in_strongbox: bool = False


# ---------------------------------------------------------------------------
# Keychain helpers (subprocess, same pattern as secret_provider.py)
# ---------------------------------------------------------------------------


def _keychain_get(service: str, account: str) -> Optional[str]:
    """Read a secret from macOS Keychain. Returns None if not found."""
    try:
        result = subprocess.run(
            ["security", "find-generic-password", "-s", service, "-a", account, "-w"],
            capture_output=True,
            text=True,
            timeout=_SUBPROCESS_TIMEOUT,
        )
        if result.returncode == 0:
            value = result.stdout.strip()
            return value if value else None
        return None
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return None


def _keychain_get_by_service(service: str, account: str = "catalyst") -> Optional[str]:
    """Read a secret from macOS Keychain by service AND account name.

    Always specifies both -s (service) and -a (account) to avoid triggering
    macOS Keychain Access prompts for items created by other applications
    (e.g., gh CLI, browsers) that have restrictive ACLs.

    Returns None if not found.
    """
    try:
        result = subprocess.run(
            ["security", "find-generic-password", "-s", service, "-a", account, "-w"],
            capture_output=True,
            text=True,
            timeout=_SUBPROCESS_TIMEOUT,
        )
        if result.returncode == 0:
            value = result.stdout.strip()
            return value if value else None
        return None
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return None


def _keychain_get_account(service: str) -> Optional[str]:
    """Get the account name for a Keychain service. Returns None if not found."""
    try:
        result = subprocess.run(
            ["security", "find-generic-password", "-s", service],
            capture_output=True,
            text=True,
            timeout=_SUBPROCESS_TIMEOUT,
        )
        if result.returncode != 0:
            return None
        # Parse "acct" from output like:  "acct"<blob>="catalyst"
        for line in result.stdout.splitlines():
            if '"acct"' in line:
                match = re.search(r'"acct"<blob>="([^"]*)"', line)
                if match:
                    return match.group(1)
        return None
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return None


def _keychain_exists(service: str, account: str) -> bool:
    """Check whether a secret exists in Keychain."""
    return _keychain_get(service, account) is not None


def _keychain_set(service: str, account: str, value: str) -> bool:
    """Write a secret to macOS Keychain (delete-then-add pattern)."""
    try:
        # Delete existing (ignore errors)
        subprocess.run(
            ["security", "delete-generic-password", "-s", service, "-a", account],
            capture_output=True,
            text=True,
            timeout=_SUBPROCESS_TIMEOUT,
        )
        # Add new
        result = subprocess.run(
            ["security", "add-generic-password", "-s", service, "-a", account, "-w", value],
            capture_output=True,
            text=True,
            timeout=_SUBPROCESS_TIMEOUT,
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


def _keychain_dump_services() -> List[str]:
    """Dump all service names from the login Keychain.

    Returns a deduplicated, sorted list of service name strings.
    """
    return sorted(_keychain_dump_services_with_accounts().keys())


def _keychain_dump_services_with_accounts() -> Dict[str, str]:
    """Dump all service names and their accounts from the login Keychain.

    Returns a dict of {service_name: account_name}. This avoids needing
    to call find-generic-password per item (which triggers ACL prompts
    for items created by other applications).
    """
    keychain_path = Path.home() / "Library" / "Keychains" / "login.keychain-db"
    try:
        result = subprocess.run(
            ["security", "dump-keychain", str(keychain_path)],
            capture_output=True,
            text=True,
            timeout=30,  # dump can be slow on large keychains
        )
        if result.returncode != 0:
            return {}

        services: Dict[str, str] = {}
        current_service: Optional[str] = None
        current_account: Optional[str] = None

        for line in result.stdout.splitlines():
            if '"svce"' in line:
                match = re.search(r'"svce"<blob>="([^"]*)"', line)
                if match:
                    # Save previous entry if complete
                    if current_service and current_service not in services:
                        services[current_service] = current_account or ""
                    current_service = match.group(1)
                    current_account = None
            elif '"acct"' in line and current_service:
                match = re.search(r'"acct"<blob>="([^"]*)"', line)
                if match:
                    current_account = match.group(1)

        # Don't forget the last entry
        if current_service and current_service not in services:
            services[current_service] = current_account or ""

        return services
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return {}


# ---------------------------------------------------------------------------
# Master password retrieval
# ---------------------------------------------------------------------------


def get_master_password(allow_prompt: bool = False) -> str:
    """Get the Catalyst Secrets vault master password.

    Tries Keychain first. If not found and allow_prompt is True (restore mode
    on a new machine), prompts the user.
    """
    password = _keychain_get(KEYCHAIN_SERVICE, KEYCHAIN_ACCOUNT)
    if password:
        return password

    if allow_prompt:
        print("Master password not found in Keychain (new machine?).")
        print("Enter the Catalyst Secrets vault master password:")
        password = getpass.getpass("  Master password: ")
        if not password:
            print("ERROR: No password provided.", file=sys.stderr)
            sys.exit(1)
        # Store it in Keychain for future use
        if _keychain_set(KEYCHAIN_SERVICE, KEYCHAIN_ACCOUNT, password):
            print("  Stored master password in Keychain for future use.")
        return password

    print("ERROR: Master password not found in Keychain.", file=sys.stderr)
    print(f"  Expected: service={KEYCHAIN_SERVICE!r}, account={KEYCHAIN_ACCOUNT!r}", file=sys.stderr)
    print("  Run: python3 tools/create-secrets-vault.py", file=sys.stderr)
    sys.exit(1)


# ---------------------------------------------------------------------------
# TOML parsing
# ---------------------------------------------------------------------------


def _capsule_label(group_name: str) -> str:
    """Map group name to a capsule label for metadata."""
    mapping = {
        "Root": "catalyst-root",
        "Big Sky Tags": "example-team-tags",
        "Catalyst Digital": "catalyst-digital",
        "Catalyst Mobile": "catalyst-mobile",
        "Telegram TC3": "telegram-tc3",
        "Mid Partners": "example-partners",
        "Shared": "shared",
        "Google": "google",
        "Telegram Bots": "telegram-bots",
        "Proton": "proton",
        "Cloudflare": "cloudflare",
        "Financial": "financial",
        "Catalyst Design System": "catalyst-design-system",
        "Legacy Duplicates": "legacy-duplicates",
    }
    return mapping.get(group_name, group_name.lower().replace(" ", "-"))


def parse_toml_manifest(toml_path: Path, group_name: str) -> List[SecretEntry]:
    """Parse a keychain.required.toml file into SecretEntry objects.

    Reads both [secrets] and [keychain_reference] sections.
    """
    entries: List[SecretEntry] = []

    if not toml_path.exists():
        return entries

    with open(toml_path, "rb") as f:
        data = tomllib.load(f)

    capsule = _capsule_label(group_name)

    # Process both [secrets] and [keychain_reference] sections
    for section_name in ("secrets", "keychain_reference"):
        section = data.get(section_name, {})
        if not isinstance(section, dict):
            continue

        for env_var, config in section.items():
            if not isinstance(config, dict):
                continue

            service = config.get("service", "")
            account = config.get("account", "catalyst")

            if not service:
                continue

            entries.append(SecretEntry(
                service=service,
                account=account,
                env_var=env_var,
                group_name=group_name,
                capsule=capsule,
                source="toml",
            ))

    return entries


def collect_toml_entries() -> Tuple[List[SecretEntry], Dict[str, SecretEntry]]:
    """Collect all secret entries from TOML manifests and shared secrets.

    Returns:
        (entries_list, seen_dict) where seen_dict is keyed by service name
        for deduplication with the discovery pass.
    """
    seen: Dict[str, SecretEntry] = {}
    entries: List[SecretEntry] = []

    # Parse TOML manifests
    for toml_path, group_name in TOML_MANIFESTS:
        for entry in parse_toml_manifest(toml_path, group_name):
            if entry.service not in seen:
                seen[entry.service] = entry
                entries.append(entry)

    # Add shared secrets (only if not already covered by TOML manifests)
    for service, account, env_var in SHARED_SECRETS:
        if service not in seen:
            entry = SecretEntry(
                service=service,
                account=account,
                env_var=env_var,
                group_name="Shared",
                capsule="shared",
                source="toml",
            )
            seen[service] = entry
            entries.append(entry)

    return entries, seen


# ---------------------------------------------------------------------------
# Keychain Discovery
# ---------------------------------------------------------------------------


def _is_catalyst_service(service: str) -> bool:
    """Check if a Keychain service name belongs to Catalyst."""
    # Exact exclusions
    if service in EXCLUDE_SERVICES:
        return False

    # Pattern exclusions
    for pattern in EXCLUDE_PATTERNS:
        if pattern in service:
            return False

    # Check if it matches any Catalyst prefix
    service_lower = service.lower()
    for prefix in CATALYST_PREFIXES:
        if service_lower.startswith(prefix.lower()):
            return True

    return False


def _route_to_group(service: str) -> str:
    """Route a Keychain service name to the correct KeePass group.

    Checks for legacy suffixes first, then prefix-based routing.
    """
    # Legacy suffix check (-zshrc, -env variants)
    for suffix in LEGACY_SUFFIXES:
        if service.endswith(suffix):
            return "Legacy Duplicates"

    # Prefix-based routing (first match wins)
    for prefix, group in GROUP_ROUTING:
        if service.startswith(prefix):
            return group

    # Fallback
    return "Shared"


_KNOWN_CATALYST_ACCOUNTS = {"catalyst", "njalla", "canva", "master-password", ""}

def discover_keychain_secrets(already_seen: Dict[str, SecretEntry]) -> List[SecretEntry]:
    """Discover Catalyst secrets in Keychain not covered by TOML manifests.

    Uses the dump-based account lookup to avoid triggering ACL prompts
    for items created by other applications. Only includes items with
    known Catalyst accounts.

    Args:
        already_seen: Dict of service_name -> SecretEntry from the TOML pass.

    Returns:
        List of newly discovered SecretEntry objects.
    """
    services_with_accounts = _keychain_dump_services_with_accounts()
    discovered: List[SecretEntry] = []

    for service, account in sorted(services_with_accounts.items()):
        # Skip if already covered by TOML pass
        if service in already_seen:
            continue

        # Skip non-Catalyst services
        if not _is_catalyst_service(service):
            continue

        # Skip items with non-Catalyst accounts (these trigger ACL prompts)
        if account not in _KNOWN_CATALYST_ACCOUNTS:
            continue

        # Default empty account to "catalyst"
        if not account:
            account = "catalyst"

        # Route to the correct group
        group_name = _route_to_group(service)
        capsule = _capsule_label(group_name)

        discovered.append(SecretEntry(
            service=service,
            account=account,
            env_var="",  # No env_var hint for discovered secrets
            group_name=group_name,
            capsule=capsule,
            source="keychain-discovery",
        ))

    return discovered


def collect_all_entries() -> Tuple[List[SecretEntry], int, int]:
    """Collect entries from TOML manifests + Keychain discovery.

    Returns:
        (all_entries, toml_count, discovered_count)
    """
    toml_entries, seen = collect_toml_entries()
    discovered_entries = discover_keychain_secrets(seen)

    all_entries = toml_entries + discovered_entries
    return all_entries, len(toml_entries), len(discovered_entries)


# ---------------------------------------------------------------------------
# KeePass helpers
# ---------------------------------------------------------------------------


def open_database(password: str):
    """Open the Catalyst Secrets KeePass database."""
    from pykeepass import PyKeePass
    from pykeepass.exceptions import CredentialsError

    if not DB_PATH.exists():
        print(f"ERROR: Database not found: {DB_PATH}", file=sys.stderr)
        print("  Run: python3 tools/create-secrets-vault.py", file=sys.stderr)
        sys.exit(1)

    try:
        return PyKeePass(str(DB_PATH), password=password)
    except CredentialsError:
        print("ERROR: Incorrect master password.", file=sys.stderr)
        print("  Check Keychain service 'Catalyst-Strongbox' or re-enter manually.", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: Failed to open database: {e}", file=sys.stderr)
        print("  The file may be corrupted or mid-iCloud-sync. Try again in a moment.", file=sys.stderr)
        sys.exit(1)


def find_or_create_group(kp, group_name: str):
    """Find the /Catalyst/{group_name} group, or create it if missing."""
    # Find the Catalyst top-level group
    catalyst_groups = [g for g in kp.find_groups(name="Catalyst")
                       if g.parentgroup == kp.root_group]

    if not catalyst_groups:
        # Create if missing
        catalyst_group = kp.add_group(kp.root_group, "Catalyst")
    else:
        catalyst_group = catalyst_groups[0]

    # Find or create the subgroup
    subgroups = [g for g in kp.find_groups(name=group_name)
                 if g.parentgroup == catalyst_group]

    if not subgroups:
        return kp.add_group(catalyst_group, group_name)

    return subgroups[0]


def ensure_new_groups(kp) -> List[str]:
    """Ensure all required groups exist in the database.

    Returns list of newly created group names.
    """
    new_groups = [
        "Google",
        "Telegram Bots",
        "Proton",
        "Cloudflare",
        "Financial",
        "Catalyst Design System",
        "Legacy Duplicates",
    ]

    created = []
    for group_name in new_groups:
        # Check if it already exists
        catalyst_groups = [g for g in kp.find_groups(name="Catalyst")
                           if g.parentgroup == kp.root_group]
        if not catalyst_groups:
            catalyst_group = kp.add_group(kp.root_group, "Catalyst")
        else:
            catalyst_group = catalyst_groups[0]

        existing = [g for g in kp.find_groups(name=group_name)
                     if g.parentgroup == catalyst_group]
        if not existing:
            kp.add_group(catalyst_group, group_name)
            created.append(group_name)

    return created


def find_entry_in_group(kp, group, service: str):
    """Find an entry by title within a specific group."""
    entries = kp.find_entries(title=service, group=group, regex=False)
    if entries:
        return entries[0]
    return None


def entry_exists_anywhere(kp, service: str, account: str) -> bool:
    """Check if an entry with this service/account exists anywhere in the database."""
    entries = [e for e in kp.find_entries(title=service, regex=False)
               if "Recycle Bin" not in str(getattr(e, 'path', []))]
    for entry in entries:
        if entry.username == account:
            return True
    return False


# ---------------------------------------------------------------------------
# Mode: --backup
# ---------------------------------------------------------------------------


def do_backup(password: str) -> int:
    """Backup Keychain secrets to the KeePass database.

    Two-pass strategy:
        Pass 1: TOML manifests (rich metadata: env_var, capsule)
        Pass 2: Keychain discovery (fills gaps with source=keychain-discovery)
    """
    from pykeepass import PyKeePass

    print("Backing up Keychain secrets to Strongbox...")
    print()

    kp = open_database(password)

    # Ensure all groups exist (including new ones)
    new_groups = ensure_new_groups(kp)
    if new_groups:
        print(f"  Created {len(new_groups)} new group(s): {', '.join(new_groups)}")
        print()

    all_entries, toml_count, discovered_count = collect_all_entries()

    backed_up = 0
    updated = 0
    skipped = 0
    toml_backed = 0
    discovered_backed = 0

    for entry in all_entries:
        # Read from Keychain — use account-specific lookup for TOML entries,
        # service-only for discovered (account was already resolved)
        if entry.source == "toml":
            value = _keychain_get(entry.service, entry.account)
        else:
            value = _keychain_get(entry.service, entry.account)
            if value is None:
                # Try service-only lookup as fallback (with account to avoid ACL prompts)
                value = _keychain_get_by_service(entry.service, entry.account)

        if value is None:
            skipped += 1
            print(f"  SKIP  {entry.service} (not in Keychain)")
            continue

        # Find or create group
        group = find_or_create_group(kp, entry.group_name)

        # Find existing entry in the group
        existing = find_entry_in_group(kp, group, entry.service)

        if existing:
            # Update existing entry
            existing.username = entry.account
            existing.password = value
            if entry.env_var:
                existing.set_custom_property("env_var", entry.env_var, protect=False)
            existing.set_custom_property("capsule", entry.capsule, protect=False)
            existing.set_custom_property("source", entry.source, protect=False)
            updated += 1
            print(f"  UPDATE  /Catalyst/{entry.group_name}/{entry.service}")
        else:
            # Create new entry
            new_entry = kp.add_entry(
                group,
                title=entry.service,
                username=entry.account,
                password=value,
            )
            if entry.env_var:
                new_entry.set_custom_property("env_var", entry.env_var, protect=False)
            new_entry.set_custom_property("capsule", entry.capsule, protect=False)
            new_entry.set_custom_property("source", entry.source, protect=False)
            backed_up += 1
            tag = "TOML" if entry.source == "toml" else "DISC"
            print(f"  NEW [{tag}]  /Catalyst/{entry.group_name}/{entry.service}")

        # Track per-source counts
        if entry.source == "toml":
            toml_backed += 1
        else:
            discovered_backed += 1

    try:
        kp.save()
    except Exception as e:
        print(f"\nERROR: Failed to save database: {e}", file=sys.stderr)
        print("  The backup may be incomplete. Check that iCloud sync is not in progress.", file=sys.stderr)
        return 1

    total_processed = backed_up + updated
    print()
    print("=" * 60)
    print(f"  Pass 1 (TOML manifests):     {toml_count} declared, {toml_backed} backed up")
    print(f"  Pass 2 (Keychain discovery):  {discovered_count} found, {discovered_backed} backed up")
    print(f"  -----------------------------------------------")
    print(f"  Total: {total_processed} backed up ({backed_up} new, {updated} updated), {skipped} skipped")
    print("=" * 60)
    print(f"Database saved: {DB_PATH}")

    return 0


# ---------------------------------------------------------------------------
# Mode: --restore
# ---------------------------------------------------------------------------


def do_restore(password: str) -> int:
    """Restore secrets from KeePass database to Keychain."""
    from pykeepass import PyKeePass

    print("Restoring secrets from Strongbox to Keychain...")
    print()

    kp = open_database(password)

    restored = 0
    failed = 0

    # Walk all entries under /Catalyst/
    catalyst_groups = [g for g in kp.find_groups(name="Catalyst")
                       if g.parentgroup == kp.root_group]

    if not catalyst_groups:
        print("ERROR: No /Catalyst group found in database.", file=sys.stderr)
        return 1

    catalyst_group = catalyst_groups[0]

    for subgroup in catalyst_group.subgroups:
        for entry in subgroup.entries:
            if not entry.title or not entry.password:
                continue

            service = entry.title
            account = entry.username or "catalyst"
            value = entry.password

            success = _keychain_set(service, account, value)
            if success:
                restored += 1
                print(f"  RESTORE  {service} (account={account})")
            else:
                failed += 1
                print(f"  FAIL     {service} (could not write to Keychain)")

    print()
    print(f"Summary: {restored} secrets restored to Keychain, {failed} failed")

    return 0 if failed == 0 else 1


# ---------------------------------------------------------------------------
# Mode: --status
# ---------------------------------------------------------------------------


def do_status(password: str) -> int:
    """Show sync status between Keychain and Strongbox.

    Includes both TOML-declared and Keychain-discovered secrets.
    """
    from pykeepass import PyKeePass

    print("Checking sync status: Keychain vs Strongbox")
    print()

    kp = open_database(password)
    all_entries, toml_count, discovered_count = collect_all_entries()

    # Check Keychain and Strongbox for each entry
    for entry in all_entries:
        entry.in_keychain = _keychain_exists(entry.service, entry.account)
        if not entry.in_keychain and entry.source == "keychain-discovery":
            # Discovered secrets — also check with account to avoid ACL prompts
            entry.in_keychain = _keychain_get_by_service(entry.service, entry.account) is not None
        entry.in_strongbox = entry_exists_anywhere(kp, entry.service, entry.account)

    # Print table
    header = f"  {'Service':<50} {'Src':<6} {'KC':<5} {'SB':<5} {'Status'}"
    print(header)
    print("  " + "-" * 90)

    current_group = ""
    in_sync = 0
    needs_backup = 0
    needs_restore = 0
    missing_both = 0

    for entry in all_entries:
        # Group separator
        if entry.group_name != current_group:
            if current_group:
                print()
            current_group = entry.group_name
            print(f"  [{entry.group_name}]")

        src_tag = "TOML" if entry.source == "toml" else "DISC"
        kc_icon = "Y" if entry.in_keychain else "-"
        sb_icon = "Y" if entry.in_strongbox else "-"

        if entry.in_keychain and entry.in_strongbox:
            status = "in sync"
            in_sync += 1
        elif entry.in_keychain and not entry.in_strongbox:
            status = "needs --backup"
            needs_backup += 1
        elif not entry.in_keychain and entry.in_strongbox:
            status = "needs --restore"
            needs_restore += 1
        else:
            status = "MISSING"
            missing_both += 1

        print(f"  {entry.service:<50} {src_tag:<6} {kc_icon:<5} {sb_icon:<5} {status}")

    total = len(all_entries)
    print()
    print("=" * 60)
    print(f"  Sources: {toml_count} from TOML, {discovered_count} from Keychain discovery")
    print(f"  Total:   {total} secrets tracked")
    print(f"  -----------------------------------------------")
    print(f"  In sync:        {in_sync}")
    if needs_backup > 0:
        print(f"  Needs backup:   {needs_backup}  (run --backup)")
    if needs_restore > 0:
        print(f"  Needs restore:  {needs_restore}  (run --restore)")
    if missing_both > 0:
        print(f"  Missing both:   {missing_both}  (need to be added)")
    print("=" * 60)

    if needs_backup == 0 and needs_restore == 0 and missing_both == 0:
        print()
        print("All secrets are in sync.")

    return 0


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Catalyst Secrets Sync — Bridge macOS Keychain and Strongbox KeePass",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Modes:\n"
            "  --backup   Keychain -> KeePass (backup secrets to Strongbox)\n"
            "             Pass 1: TOML manifests (rich metadata)\n"
            "             Pass 2: Keychain discovery (fills gaps)\n"
            "  --restore  KeePass -> Keychain (restore secrets on new machine)\n"
            "  --status   Compare and show sync state\n"
            "\n"
            "Database location:\n"
            f"  {DB_PATH}\n"
            "\n"
            "Master password stored in Keychain:\n"
            f"  service=\"{KEYCHAIN_SERVICE}\"  account=\"{KEYCHAIN_ACCOUNT}\"\n"
        ),
    )

    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--backup", action="store_true", help="Backup Keychain secrets to Strongbox")
    mode.add_argument("--restore", action="store_true", help="Restore secrets from Strongbox to Keychain")
    mode.add_argument("--status", action="store_true", help="Show sync status between Keychain and Strongbox")

    args = parser.parse_args()

    # Check database exists (except for restore where we always need it)
    if not DB_PATH.exists():
        print(f"ERROR: Database not found: {DB_PATH}", file=sys.stderr)
        print("  Run: python3 tools/create-secrets-vault.py", file=sys.stderr)
        return 1

    # Get master password (allow prompt only in restore mode — new machine case)
    allow_prompt = args.restore
    password = get_master_password(allow_prompt=allow_prompt)

    if args.backup:
        return do_backup(password)
    elif args.restore:
        return do_restore(password)
    elif args.status:
        return do_status(password)

    return 0


if __name__ == "__main__":
    sys.exit(main())
