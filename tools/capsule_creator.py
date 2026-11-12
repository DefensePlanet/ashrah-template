#!/usr/bin/env python3.12
"""
Catalyst Capsule Creator - Fully Automated

Creates a complete capsule with:
1. Directory structure (specs, docs, CLAUDE.md)
2. Telegram supergroup (auto — invites {{ORCHESTRATOR_NAME}}, promotes to admin, registers binding)
3. Navigation shortcut skill
4. CAPSULES_INDEX.md entry

NOTE: Telegram bot creation is NO LONGER automatic due to Telegram's 20-bot limit.
      Use --with-bot flag if you explicitly want to create a bot.
      See: .claude/skills/telegram-bot-setup/ for on-demand bot creation.

Usage:
    python3.12 capsule_creator.py --name "my-project" --purpose "Track project tasks"
    python3.12 capsule_creator.py --name "therapy-notes" --purpose "Personal therapy journal" --privacy high
    python3.12 capsule_creator.py --name "my-project" --purpose "Track tasks" --skip-supergroup
    python3.12 capsule_creator.py --sync-groups  # Bulk-create supergroups for all unregistered capsules
"""

import argparse
import asyncio
import json
import os
import subprocess
import sys
import re
import tempfile
import time
from pathlib import Path
from datetime import datetime


# Paths — derived from script location so it works on any machine
CATALYST_ROOT = Path(__file__).resolve().parent.parent
CAPSULES_DIR = CATALYST_ROOT / 'capsules'
SKILLS_DIR = CATALYST_ROOT / '.claude/skills'
BOT_CREATOR = CATALYST_ROOT / 'tools/bots/telegram_bot_creator.py'
CAPSULES_INDEX = CAPSULES_DIR / 'CAPSULES_INDEX.md'
CAPSULE_REGISTRY = CATALYST_ROOT / 'tools/telegram/TC3/src/config/capsule-registry.json'
TELETHON_SESSION = CATALYST_ROOT / 'tools/builder_session'
# Bot username to invite to new supergroups
# Priority: CATALYST_BOT_USERNAME env var → .catalyst-config BOT_USERNAME → fallback
def _resolve_bot_username() -> str:
    env = os.environ.get('CATALYST_BOT_USERNAME')
    if env:
        return env
    config_file = CATALYST_ROOT / '.catalyst-config'
    if config_file.exists():
        config = {}
        for line in config_file.read_text().splitlines():
            if '=' in line:
                k, v = line.split('=', 1)
                config[k.strip()] = v.strip().strip('"\'')
        # Explicit bot username from setup.sh
        if config.get('BOT_USERNAME'):
            return config['BOT_USERNAME']
        # Fallback: derive from orchestrator name
        if config.get('ORCHESTRATOR_NAME'):
            return f"{config['ORCHESTRATOR_NAME']}CatalystBot"
    return '{{ORCHESTRATOR_NAME}}CatalystBot'

SUPERGROUP_BOT_USERNAME = _resolve_bot_username()


def derive_names(capsule_name: str) -> dict:
    """Derive display name, short name, bot username from capsule name."""
    parts = capsule_name.split('-')
    
    # Display name: Title Case
    display_name = ' '.join(word.capitalize() for word in parts)
    
    # Short name: first distinctive word (skip common prefixes)
    skip_words = {'my', 'the', 'a', 'an', 'personal', 'private'}
    short_name = None
    for part in parts:
        if part.lower() not in skip_words:
            short_name = part.lower()
            break
    short_name = short_name or parts[0].lower()
    
    # Bot username: PascalCase + Bot
    bot_username = ''.join(word.capitalize() for word in parts) + 'Bot'
    
    return {
        'display_name': display_name,
        'short_name': short_name,
        'bot_username': bot_username,
    }


def create_directory_structure(capsule_path: Path, capsule_name: str, display_name: str, purpose: str, privacy: str):
    """Create capsule directory and standard files."""
    print(f"📁 Creating directory structure...")

    # Create directories
    capsule_path.mkdir(parents=True, exist_ok=True)
    (capsule_path / 'docs').mkdir(exist_ok=True)
    (capsule_path / 'specs').mkdir(exist_ok=True)

    if privacy == 'high':
        (capsule_path / 'notes').mkdir(exist_ok=True)
        (capsule_path / 'notes' / '.gitkeep').touch()

    # Create specs/current.yaml (the source of truth)
    spec_yaml = f'''name: {display_name}
version: 0.1.0
status: active
last_updated: {datetime.now().strftime("%Y-%m-%d")}

purpose:
  what: {purpose}
  why: To be defined
  for_whom: {{USER_NAME}}

current:
  phase: setup
  health: healthy

technical:
  stack:
    - To be defined
  dependencies:
    external: []
    internal: []

capabilities:
  - Initial setup complete

guardrails:
{"""  - All data stays local
  - No external API calls with sensitive data
  - Privacy-first design""" if privacy == "high" else """  - Standard security practices
  - Follow Catalyst conventions"""}

development:
  workflow: Standard Catalyst workflow
  tools:
    - Claude Code
    - Telegram bot for mobile access

vision:
  statement: To be defined
  roadmap: []

relationships:
  feeds_into: []
  consumes_from: []
  shared_with: []
'''
    (capsule_path / 'specs' / 'current.yaml').write_text(spec_yaml)
    print(f"   ✅ Created: specs/current.yaml")

    # Generate CLAUDE.md from specs
    generator_script = CATALYST_ROOT / 'tools' / 'generate_claude_md.py'
    result = subprocess.run(
        ['python3', str(generator_script), str(capsule_path)],
        capture_output=True,
        text=True
    )
    if result.returncode == 0:
        print(f"   ✅ Generated: CLAUDE.md (from specs)")
    else:
        print(f"   ⚠️  CLAUDE.md generation had issues: {result.stderr}")
    
    # Create README.md
    readme = f'''# {display_name}

{purpose}

## Quick Start
1. Review `specs/current.yaml` for detailed specifications
2. Check `docs/` for documentation
3. Message the Telegram bot for mobile access
4. Use `/{capsule_name.split('-')[0]}` to navigate here

## Structure
```
{capsule_path.name}/
├── CLAUDE.md        # Auto-generated from specs (don't edit directly)
├── README.md        # This file
├── specs/
│   └── current.yaml # Source of truth - edit this for context engineering
├── docs/            # Documentation
{"├── notes/           # Personal notes (local-only)" if privacy == "high" else ""}
```

## Context Engineering
Edit `specs/current.yaml` to update capsule context, then regenerate:
```bash
python3 {{CATALYST_ROOT}}/tools/generate_claude_md.py {capsule_path}
```

## Created
{datetime.now().strftime("%Y-%m-%d")}
'''
    (capsule_path / 'README.md').write_text(readme)
    
    # Create .gitignore
    gitignore_content = '''# Sensitive files
*.secret
*.private
.env.local

# Personal notes (if high privacy)
notes/*.md
!notes/.gitkeep

# OS files
.DS_Store
'''
    (capsule_path / '.gitignore').write_text(gitignore_content)
    
    # Create docs README
    docs_readme = f'''# {display_name} Documentation

Documentation for {purpose}.

## Contents
- (Add your docs here)
'''
    (capsule_path / 'docs' / 'README.md').write_text(docs_readme)
    
    print(f"   ✅ Created: CLAUDE.md, README.md, .gitignore, docs/")


def create_telegram_bot(capsule_name: str, display_name: str, purpose: str) -> dict:
    """Create Telegram bot using telegram_bot_creator.py."""
    print(f"📱 Creating Telegram bot...")
    
    result = subprocess.run(
        [
            'python3.12', str(BOT_CREATOR),
            '--capsule', capsule_name,
            '--display-name', display_name,
            '--description', purpose,
            '--json'
        ],
        capture_output=True,
        text=True
    )
    
    if result.returncode != 0:
        print(f"   ⚠️  Bot creation had issues: {result.stderr}")
        return {'error': result.stderr}
    
    # Parse JSON output
    import json
    try:
        # Find JSON in output (skip non-JSON lines)
        for line in result.stdout.split('\n'):
            if line.strip().startswith('{'):
                return json.loads(line)
        # Try parsing whole output
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        print(f"   ⚠️  Could not parse bot output")
        return {'output': result.stdout}


def _get_keychain(service: str) -> str:
    """Read a secret from macOS Keychain. Returns empty string on failure."""
    r = subprocess.run(
        ['security', 'find-generic-password', '-s', service, '-w'],
        capture_output=True, text=True
    )
    if r.returncode != 0:
        reason = r.stderr.strip() or f"exit code {r.returncode}"
        print(f"   ⚠️  Keychain lookup failed for '{service}': {reason}")
        return ''
    return r.stdout.strip()


def create_telegram_supergroup(capsule_name: str, short_id: str,
                                display_name: str, capsule_path: Path) -> dict:
    """Create a Telegram supergroup, invite {{ORCHESTRATOR_NAME}} bot, promote to admin, register in capsule-registry.json.

    Args:
        capsule_name: Full kebab-case capsule name (e.g. 'financial-untethering')
        short_id: Short nav word used as capsuleId in the registry (e.g. 'finu')
        display_name: Human-readable title for the supergroup
        capsule_path: Absolute path to the capsule directory
    """
    print(f"💬 Creating Telegram supergroup...")

    api_id = _get_keychain('catalyst-telegram-api-id')
    api_hash = _get_keychain('catalyst-telegram-api-hash')

    if not api_id or not api_hash:
        print("   ⚠️  Telegram API credentials not found in Keychain. Skipping supergroup.")
        return {'error': 'missing_credentials'}

    # Pre-flight: verify Telethon session exists
    session_path = Path(str(TELETHON_SESSION) + '.session')
    if not session_path.exists():
        print(f"   ⚠️  Telethon session not found at {session_path}. Skipping supergroup.")
        return {'error': 'missing_session'}

    # Pre-flight: verify registry file is readable and valid
    try:
        registry = json.loads(CAPSULE_REGISTRY.read_text())
        registry.setdefault('chats', {})
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"   ⚠️  Cannot read capsule-registry.json: {e}. Skipping supergroup.")
        return {'error': f'registry_error: {e}'}

    async def _create():
        from telethon import TelegramClient
        from telethon.tl.functions.channels import CreateChannelRequest, InviteToChannelRequest, EditAdminRequest
        from telethon.tl.types import ChatAdminRights

        client = TelegramClient(str(TELETHON_SESSION), int(api_id), api_hash)
        await client.start()

        try:
            # Resolve {{ORCHESTRATOR_NAME}} bot
            {{ORCHESTRATOR_NAME_LOWER}} = await client.get_entity(SUPERGROUP_BOT_USERNAME)

            # Create supergroup
            result = await client(CreateChannelRequest(
                title=display_name,
                about=f"Catalyst capsule: {short_id}",
                megagroup=True
            ))
            channel = result.chats[0]
            chat_id = -(1000000000000 + channel.id)

            # Invite {{ORCHESTRATOR_NAME}}
            await client(InviteToChannelRequest(channel=channel, users=[{{ORCHESTRATOR_NAME_LOWER}}]))

            # Promote {{ORCHESTRATOR_NAME}} to admin
            await client(EditAdminRequest(
                channel=channel,
                user_id={{ORCHESTRATOR_NAME_LOWER}},
                admin_rights=ChatAdminRights(
                    change_info=False, post_messages=False, edit_messages=False,
                    delete_messages=True, ban_users=False, invite_users=False,
                    pin_messages=True, add_admins=False, manage_call=False,
                    anonymous=False, other=True,
                ),
                rank="Bot"
            ))

            return {'chat_id': chat_id, 'display_name': display_name}

        finally:
            await client.disconnect()

    try:
        result = asyncio.run(_create())

        # Register in capsule-registry.json (registry already validated above)
        # Atomic write: temp file + os.replace to prevent corruption on disk errors
        registry['chats'][str(result['chat_id'])] = {
            'capsuleId': short_id,
            'workingDir': str(capsule_path),
            'name': display_name,
            'defaultMode': 'pi'
        }
        try:
            registry_data = json.dumps(registry, indent=2, ensure_ascii=False) + '\n'
            tmp_path = CAPSULE_REGISTRY.with_suffix('.tmp')
            tmp_path.write_text(registry_data, encoding='utf-8')
            os.replace(tmp_path, CAPSULE_REGISTRY)
        except OSError as we:
            print(f"   ⚠️  Registry write failed: {we}")
            print(f"   ⚠️  Orphaned group chat_id={result['chat_id']} — add manually to capsule-registry.json")
            return {'error': f'registry_write_failed: {we}'}

        print(f"   ✅ Supergroup created (chat_id: {result['chat_id']})")
        print(f"   ✅ {{ORCHESTRATOR_NAME}} invited + promoted to admin")
        print(f"   ✅ Registered in capsule-registry.json")
        return result
    except Exception as e:
        print(f"   ⚠️  Supergroup creation failed: {e}")
        return {'error': str(e)}


def create_navigation_skill(capsule_name: str, short_name: str, display_name: str,
                            purpose: str, privacy: str):
    """Create navigation shortcut skill."""
    print(f"🔗 Creating navigation shortcut /{short_name}...")
    
    # Single-word shortcut name - no "navigation" suffix
    skill_dir = SKILLS_DIR / short_name
    skill_dir.mkdir(parents=True, exist_ok=True)
    
    skill_content = f'''---
name: {short_name}
description: Navigate to {display_name} capsule - {purpose}
when: User types /{short_name} or mentions {capsule_name}
allowed-tools:
  - Bash
metadata:
  version: "1.0.0"
  capsule: "{capsule_name}"
  privacy: "{privacy}"
  last_updated: "{datetime.now().strftime("%Y-%m-%d")}"
---

# /{short_name} - Navigate to {display_name}

## Purpose
Quick navigation to the {display_name} capsule.

**Capsule purpose:** {purpose}

## Trigger Conditions
- User types `/{short_name}`
- User mentions "{capsule_name}"
- User wants to work on {display_name.lower()}

## What This Skill Does

1. **Navigates to capsule:**
   ```bash
   cd {{CATALYST_ROOT}}/capsules/{capsule_name}
   ```

2. **Confirms navigation:**
   - Reports current location
   - Shows available next steps
   {"- Reminds user of privacy protections" if privacy == "high" else ""}

## Navigation Command

```bash
cd {{CATALYST_ROOT}}/capsules/{capsule_name} && pwd
```

## Response Template

When this skill is invoked, respond with:

```
✓ Navigated to {display_name}

📍 {{CATALYST_ROOT}}/capsules/{capsule_name}

**What would you like to work on?**

- Review README.md for overview
- Check docs/ for documentation
- Start working on your task

{"🔒 Privacy: High - personal notes stay local-only" if privacy == "high" else ""}
```

## Mobile Access

Telegram bot: Use /telegram-bot-setup to create one if needed
'''
    
    (skill_dir / 'skill.md').write_text(skill_content)
    print(f"   ✅ Created: .claude/skills/{short_name}/skill.md")


def update_capsules_index(capsule_name: str, display_name: str, purpose: str,
                          short_name: str, bot_username: str, privacy: str, has_bot: bool):
    """Add entry to CAPSULES_INDEX.md."""
    print(f"📋 Updating CAPSULES_INDEX.md...")

    bot_line = f"**Bot:** @{bot_username}  " if has_bot else "**Bot:** (use /telegram-bot-setup)  "
    entry = f'''
### {capsule_name}/
**Purpose:** {purpose}
**Nav:** /{short_name}
{bot_line}
{"**Privacy:** High - local-only by default" if privacy == "high" else ""}
'''

    with open(CAPSULES_INDEX, 'a') as f:
        f.write(entry)

    print(f"   ✅ Added entry to CAPSULES_INDEX.md")


# ─── Sync-groups helpers ──────────────────────────────────────────────────────


def _is_real_capsule(capsule_path: Path) -> bool:
    """Return True for substantive capsule directories (skip templates, hidden, empty)."""
    if not capsule_path.is_dir():
        return False
    name = capsule_path.name
    if name.startswith('.') or name.startswith('_'):
        return False
    has_specs = (capsule_path / 'specs' / 'current.yaml').exists()
    has_claude = (capsule_path / 'CLAUDE.md').exists()
    return has_specs or has_claude


def _derive_display_name(capsule_name: str, capsule_path: Path) -> str:
    """Derive human-readable display name from specs or directory name."""
    spec_path = capsule_path / 'specs' / 'current.yaml'
    if spec_path.exists():
        try:
            for line in spec_path.read_text().splitlines():
                if line.startswith('name:'):
                    raw = line.split(':', 1)[1].strip().strip('"\'')
                    if raw and raw != capsule_name:
                        return raw
        except Exception:
            pass
    return ' '.join(w.capitalize() for w in capsule_name.replace('-', ' ').split())


def _derive_short_id(capsule_name: str) -> str:
    """Derive short capsule ID from nav skill metadata or capsule name."""
    # Priority 1: search nav skills (must be a navigation skill, not a functional one)
    if SKILLS_DIR.exists():
        for skill_dir in SKILLS_DIR.iterdir():
            skill_file = skill_dir / 'skill.md'
            if not skill_file.exists():
                continue
            try:
                content = skill_file.read_text()
                # Must match capsule AND be a nav skill (description contains "Navigate to")
                has_capsule = re.search(
                    r'capsule:\s*["\']' + re.escape(capsule_name) + r'["\']',
                    content
                )
                is_nav = 'Navigate to' in content
                if has_capsule and is_nav:
                    return skill_dir.name
            except Exception:
                continue

    # Priority 2: derive_names() fallback (first distinctive word)
    return derive_names(capsule_name)['short_name']


def _build_registered_paths(registry: dict) -> set:
    """Extract set of workingDir paths currently in the TC3 registry."""
    return {entry.get('workingDir', '') for entry in registry.get('chats', {}).values()}


def sync_telegram_groups() -> None:
    """Scan capsules/ and create Telegram supergroups for any capsule not already registered.

    Idempotent: re-running produces no duplicates.
    Non-interactive: errors are reported but do not halt the scan.
    """
    print()
    print("=" * 60)
    print("  Syncing Telegram Supergroups")
    print("=" * 60)

    # Pre-flight: check credentials
    api_id = _get_keychain('catalyst-telegram-api-id')
    api_hash = _get_keychain('catalyst-telegram-api-hash')
    session_path = Path(str(TELETHON_SESSION) + '.session')

    if not api_id or not api_hash:
        print("[skip] Telegram credentials not found in Keychain.")
        print("       Add: security add-generic-password -s catalyst-telegram-api-id -w <ID>")
        print("       Add: security add-generic-password -s catalyst-telegram-api-hash -w <HASH>")
        return

    if not session_path.exists():
        print(f"[skip] Telethon session not found at {session_path}")
        print("       Authenticate first: python3.12 tools/bots/authenticate_telethon.py")
        return

    # Load TC3 registry (create stub if missing — fresh install)
    try:
        if CAPSULE_REGISTRY.exists():
            registry = json.loads(CAPSULE_REGISTRY.read_text())
        else:
            registry = {
                "defaultCapsule": {
                    "workingDir": str(CATALYST_ROOT),
                    "name": "Catalyst",
                    "defaultMode": "pi"
                },
                "chats": {}
            }
        registry.setdefault('chats', {})
    except (json.JSONDecodeError, OSError) as e:
        print(f"[error] Cannot read capsule-registry.json: {e}")
        return

    registered_paths = _build_registered_paths(registry)

    # Scan capsules/
    candidates = sorted(
        p for p in CAPSULES_DIR.iterdir()
        if _is_real_capsule(p)
    )

    created = []
    skipped = []
    failed = []

    for capsule_path in candidates:
        capsule_name = capsule_path.name

        if str(capsule_path) in registered_paths:
            skipped.append(capsule_name)
            continue

        short_id = _derive_short_id(capsule_name)
        display_name = _derive_display_name(capsule_name, capsule_path)
        print(f"\n  [{capsule_name}] -> \"{display_name}\" (id: {short_id})")

        result = create_telegram_supergroup(capsule_name, short_id, display_name, capsule_path)

        if 'error' in result:
            failed.append((capsule_name, result['error']))
        else:
            created.append(capsule_name)
            registered_paths.add(str(capsule_path))  # prevent duplicates within this run

        # Rate limit: 2s between Telegram API calls (even on failure — API was still hit)
        time.sleep(2)

    # Summary
    print()
    print("=" * 60)
    print(f"  Supergroup sync complete")
    print("=" * 60)
    print(f"  Created : {len(created)}")
    for name in created:
        print(f"    + {name}")
    print(f"  Skipped : {len(skipped)} (already registered)")
    print(f"  Failed  : {len(failed)}")
    for name, err in failed:
        print(f"    x {name}: {err}")
    print()


def main():
    parser = argparse.ArgumentParser(description='Create a new Catalyst capsule or sync Telegram groups')

    # Sync mode (alternative to capsule creation)
    parser.add_argument('--sync-groups', action='store_true',
                        help='Bulk-create Telegram supergroups for all unregistered capsules')

    parser.add_argument('--name', help='Capsule name (kebab-case)')
    parser.add_argument('--purpose', help='Brief description of purpose')
    parser.add_argument('--privacy', default='normal', choices=['normal', 'high'],
                        help='Privacy level (default: normal)')
    parser.add_argument('--with-bot', action='store_true',
                        help='Create Telegram bot (disabled by default due to 20-bot limit)')
    parser.add_argument('--skip-nav', action='store_true', help='Skip navigation skill creation')
    parser.add_argument('--skip-supergroup', action='store_true',
                        help='Skip Telegram supergroup creation')

    args = parser.parse_args()

    # Route to sync mode
    if args.sync_groups:
        sync_telegram_groups()
        return

    # Validate required args for capsule creation mode
    if not args.name:
        parser.error("--name is required when not using --sync-groups")
    if not args.purpose:
        parser.error("--purpose is required when not using --sync-groups")

    # Normalize capsule name
    capsule_name = args.name.lower().replace(' ', '-').replace('_', '-')
    capsule_path = CAPSULES_DIR / capsule_name
    
    # Check if exists
    if capsule_path.exists():
        print(f"❌ Capsule already exists: {capsule_path}")
        sys.exit(1)
    
    # Derive names
    names = derive_names(capsule_name)
    display_name = names['display_name']
    short_name = names['short_name']
    bot_username = names['bot_username']
    
    print("=" * 60)
    print(f"Creating Capsule: {display_name}")
    print("=" * 60)
    print(f"  Name:     {capsule_name}")
    print(f"  Purpose:  {args.purpose}")
    print(f"  Privacy:  {args.privacy}")
    print(f"  Nav:      /{short_name}")
    print(f"  Bot:      @{bot_username}")
    print("=" * 60)
    print()
    
    # Step 1: Directory structure with specs/current.yaml
    create_directory_structure(capsule_path, capsule_name, display_name, args.purpose, args.privacy)
    
    # Step 2: Telegram bot (opt-in due to 20-bot limit)
    bot_result = {}
    if args.with_bot:
        bot_result = create_telegram_bot(capsule_name, display_name, args.purpose)
        if 'error' not in bot_result:
            print(f"   ✅ Bot created: @{bot_result.get('bot_username', bot_username)}")
    else:
        print("   ⏭️  Telegram bot skipped (use --with-bot to create, or /telegram-bot-setup later)")

    # Step 3: Telegram supergroup (auto, opt-out with --skip-supergroup)
    supergroup_result = {}
    if not args.skip_supergroup:
        supergroup_result = create_telegram_supergroup(
            capsule_name, short_name, display_name, capsule_path
        )
    else:
        print("   ⏭️  Telegram supergroup skipped (use /capsule bind in Telegram to add later)")

    # Step 4: Navigation skill
    if not args.skip_nav:
        create_navigation_skill(capsule_name, short_name, display_name,
                               args.purpose, args.privacy)
    else:
        print("   ⏭️  Skipping navigation skill")

    # Step 5: Update index
    has_bot = args.with_bot and 'error' not in bot_result
    update_capsules_index(capsule_name, display_name, args.purpose,
                          short_name, bot_result.get('bot_username', bot_username),
                          args.privacy, has_bot)
    
    # Summary
    print()
    print("=" * 60)
    print("✅ Capsule Created Successfully!")
    print("=" * 60)
    print(f"📁 Location:   {capsule_path}")
    if 'chat_id' in supergroup_result:
        print(f"💬 Supergroup: {supergroup_result['display_name']} (chat_id: {supergroup_result['chat_id']})")
    if args.with_bot:
        print(f"📱 Telegram:   @{bot_result.get('bot_username', bot_username)}")
    print(f"🔗 Navigation: /{short_name}")
    if args.privacy == 'high':
        print(f"🔒 Privacy:    High - notes stay local-only")
    print()
    print("Next steps:")
    print(f"  1. Edit specs/current.yaml to customize context (then regenerate CLAUDE.md)")
    if 'chat_id' in supergroup_result:
        print(f"  2. Message {{ORCHESTRATOR_NAME}} in the '{supergroup_result['display_name']}' Telegram group")
    elif args.with_bot:
        print(f"  2. Message @{bot_result.get('bot_username', bot_username)} in Telegram")
    else:
        print(f"  2. (Optional) Create Telegram bot later with: /telegram-bot-setup")
    print(f"  3. Use /{short_name} to navigate here")


if __name__ == '__main__':
    main()
