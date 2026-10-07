#!/usr/bin/env python3
"""
Catalyst Secrets Vault Creator — Bootstrap a KeePass database for Keychain backup.

Creates a new KeePass database at the Strongbox iCloud path with the correct
group structure for all Catalyst capsules. Generates a strong master password
and stores it in macOS Keychain.

Usage:
    python3 tools/create-secrets-vault.py
    python3 tools/create-secrets-vault.py --help

The database is created at:
    ~/Library/Mobile Documents/iCloud~com~strongbox/Documents/Catalyst Secrets.kdbx

The master password is stored in Keychain:
    service="Catalyst-Strongbox"  account="master-password"

This script is idempotent — it will not overwrite an existing database.
"""

from __future__ import annotations

import argparse
import os
import secrets
import string
import subprocess
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DB_PATH = Path.home() / "Library" / "Mobile Documents" / "iCloud~com~strongbox" / "Documents" / "Catalyst Secrets.kdbx"
KEYCHAIN_SERVICE = "Catalyst-Strongbox"
KEYCHAIN_ACCOUNT = "master-password"
PASSWORD_LENGTH = 32

# Group structure: top-level group "Catalyst", subgroups underneath
GROUPS = [
    "Root",
    "Big Sky Tags",
    "Catalyst Digital",
    "Catalyst Mobile",
    "Telegram TC3",
    "Mid Partners",
    "Shared",
    "Google",
    "Telegram Bots",
    "Proton",
    "Cloudflare",
    "Financial",
    "Catalyst Design System",
    "Legacy Duplicates",
]

_SUBPROCESS_TIMEOUT = 5


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def generate_master_password(length: int = PASSWORD_LENGTH) -> str:
    """Generate a cryptographically strong password.

    Uses secrets module for CSPRNG. Character set includes uppercase,
    lowercase, digits, and punctuation (excluding characters that cause
    shell escaping issues: ', ", \\, `).
    """
    safe_punctuation = "!@#$%^&*()-_=+[]{}|;:,.<>?/"
    alphabet = string.ascii_letters + string.digits + safe_punctuation

    # Ensure at least one of each category
    while True:
        password = "".join(secrets.choice(alphabet) for _ in range(length))
        has_upper = any(c in string.ascii_uppercase for c in password)
        has_lower = any(c in string.ascii_lowercase for c in password)
        has_digit = any(c in string.digits for c in password)
        has_symbol = any(c in safe_punctuation for c in password)
        if has_upper and has_lower and has_digit and has_symbol:
            return password


def store_password_in_keychain(password: str) -> None:
    """Store the master password in macOS Keychain.

    Deletes any existing entry first (idempotent update pattern).
    """
    # Delete existing entry (ignore errors if it doesn't exist)
    subprocess.run(
        ["security", "delete-generic-password", "-s", KEYCHAIN_SERVICE, "-a", KEYCHAIN_ACCOUNT],
        capture_output=True, text=True, timeout=_SUBPROCESS_TIMEOUT,
    )

    # Add the new entry
    result = subprocess.run(
        ["security", "add-generic-password", "-s", KEYCHAIN_SERVICE, "-a", KEYCHAIN_ACCOUNT, "-w", password],
        capture_output=True, text=True, timeout=_SUBPROCESS_TIMEOUT,
    )

    if result.returncode != 0:
        print(f"ERROR: Failed to store master password in Keychain: {result.stderr.strip()}", file=sys.stderr)
        sys.exit(1)


def create_database(password: str) -> None:
    """Create the KeePass database with the Catalyst group structure."""
    from pykeepass import create_database as kp_create

    # Ensure parent directory exists
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    # Create database
    kp = kp_create(str(DB_PATH), password=password)

    # Create top-level "Catalyst" group
    catalyst_group = kp.add_group(kp.root_group, "Catalyst")

    # Create subgroups
    for group_name in GROUPS:
        kp.add_group(catalyst_group, group_name)

    kp.save()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Create the Catalyst Secrets KeePass database for Strongbox backup",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Creates a new KeePass database at:\n"
            f"  {DB_PATH}\n"
            "\n"
            "Master password is stored in macOS Keychain:\n"
            f"  service=\"{KEYCHAIN_SERVICE}\"  account=\"{KEYCHAIN_ACCOUNT}\"\n"
            "\n"
            "After creation, run:\n"
            "  python3 tools/sync-secrets.py --backup\n"
            "to populate the database with current Keychain secrets."
        ),
    )
    parser.parse_args()

    # Check if database already exists
    if DB_PATH.exists():
        print(f"Database already exists: {DB_PATH}")
        print("To recreate, delete the existing file first.")
        print("Existing database was NOT modified.")
        return 0

    # Check that the iCloud Strongbox directory exists
    if not DB_PATH.parent.exists():
        print(f"ERROR: Strongbox iCloud directory not found: {DB_PATH.parent}", file=sys.stderr)
        print("Ensure Strongbox is installed and iCloud sync is enabled.", file=sys.stderr)
        return 1

    print("Creating Catalyst Secrets vault...")
    print()

    # Step 1: Generate master password
    password = generate_master_password()
    print(f"  [1/3] Generated {PASSWORD_LENGTH}-character master password")

    # Step 2: Create the database FIRST (reversible — just delete the file on failure)
    try:
        create_database(password)
        print(f"  [2/3] Created KeePass database with {len(GROUPS)} groups")
    except Exception as e:
        # Clean up partial database file if creation failed
        if DB_PATH.exists():
            DB_PATH.unlink()
        print(f"ERROR: Failed to create database: {e}", file=sys.stderr)
        return 1

    # Step 3: Store in Keychain AFTER database exists (ensures consistency)
    store_password_in_keychain(password)
    print(f"  [3/3] Stored master password in Keychain (service={KEYCHAIN_SERVICE!r})")

    print()
    print(f"Database: {DB_PATH}")
    print(f"Keychain: service={KEYCHAIN_SERVICE!r}, account={KEYCHAIN_ACCOUNT!r}")
    print()
    print("Groups created:")
    for group_name in GROUPS:
        print(f"  /Catalyst/{group_name}")
    print()
    print("IMPORTANT: The master password is ONLY stored in Keychain.")
    print("           It was NEVER printed to the screen.")
    print()
    print("Next step:")
    print("  python3 tools/sync-secrets.py --backup")

    return 0


if __name__ == "__main__":
    sys.exit(main())
