#!/usr/bin/env python3
"""
Sync .env files from Strongbox for capsules
Hybrid approach: Strongbox = source of truth, .env = local convenience
"""

import argparse
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional
import logging

# Import StrongboxCLI
sys.path.insert(0, str(Path(__file__).parent))
from strongbox_cli import StrongboxCLI

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)


class EnvSyncer:
    """Sync capsule .env files from Strongbox"""

    def __init__(self, builder_root: Path):
        self.builder_root = builder_root
        self.capsules_dir = builder_root / "capsules"
        self.strongbox = StrongboxCLI()

    def parse_env_template(self, template_path: Path) -> Dict[str, Dict]:
        """
        Parse .env.template file for Strongbox mappings

        Format:
        OPENAI_API_KEY=  # strongbox:openai:main account
        GITHUB_TOKEN=    # strongbox:github:production:API_Key_Production
        """
        mappings = {}

        if not template_path.exists():
            return mappings

        with open(template_path, 'r') as f:
            for line in f:
                line = line.strip()

                # Look for lines with strongbox mapping comments
                if '#' in line and 'strongbox:' in line:
                    parts = line.split('#')
                    var_name = parts[0].split('=')[0].strip()

                    # Parse strongbox:service:purpose[:field]
                    mapping = parts[1].strip()
                    if mapping.startswith('strongbox:'):
                        mapping_parts = mapping.replace('strongbox:', '').split(':')

                        service = mapping_parts[0]
                        purpose = mapping_parts[1] if len(mapping_parts) > 1 else ""
                        field = mapping_parts[2] if len(mapping_parts) > 2 else "API_Key"

                        mappings[var_name] = {
                            'service': service,
                            'purpose': purpose,
                            'field': field
                        }

        return mappings

    def fetch_keys_from_strongbox(self, mappings: Dict[str, Dict]) -> Dict[str, str]:
        """Fetch all mapped keys from Strongbox"""
        env_vars = {}

        for var_name, mapping in mappings.items():
            try:
                api_key = self.strongbox.get_api_key(
                    mapping['service'],
                    mapping['purpose'],
                    mapping['field']
                )

                if api_key:
                    env_vars[var_name] = api_key
                    logger.info(f"✅ {var_name}: Retrieved from Strongbox")
                else:
                    logger.warning(f"⚠️  {var_name}: Not found in Strongbox")

            except Exception as e:
                logger.error(f"❌ {var_name}: Failed to retrieve - {e}")

        return env_vars

    def write_env_file(self, env_path: Path, env_vars: Dict[str, str],
                       template_path: Optional[Path] = None):
        """Write .env file with variables from Strongbox"""

        lines = []
        lines.append("# Auto-generated from Strongbox")
        lines.append("# DO NOT COMMIT THIS FILE")
        lines.append("# Source: Strongbox credential store")
        lines.append(f"# Generated: {Path(__file__).name}")
        lines.append("")

        # If template exists, preserve structure and comments
        if template_path and template_path.exists():
            with open(template_path, 'r') as f:
                for line in f:
                    line = line.rstrip()

                    # Skip empty lines and pure comments at start
                    if not line or line.startswith('#'):
                        continue

                    # Extract variable name
                    var_name = line.split('=')[0].strip()

                    # Write with value if we have it
                    if var_name in env_vars:
                        lines.append(f"{var_name}={env_vars[var_name]}")
                    else:
                        # Preserve line as-is if no value
                        lines.append(line)
        else:
            # No template, just write all variables
            for var_name, value in env_vars.items():
                lines.append(f"{var_name}={value}")

        # Write file
        with open(env_path, 'w') as f:
            f.write('\n'.join(lines) + '\n')

        logger.info(f"✅ Wrote {len(env_vars)} variables to {env_path}")

    def ensure_gitignore(self, capsule_dir: Path):
        """Ensure .env is in capsule's .gitignore"""
        gitignore_path = capsule_dir / ".gitignore"

        # Read existing .gitignore
        existing_lines = []
        if gitignore_path.exists():
            with open(gitignore_path, 'r') as f:
                existing_lines = [line.strip() for line in f.readlines()]

        # Add .env if not already present
        if '.env' not in existing_lines and '*.env' not in existing_lines:
            with open(gitignore_path, 'a') as f:
                f.write('\n# Environment variables (never commit)\n')
                f.write('.env\n')
            logger.info(f"✅ Added .env to {gitignore_path}")

    def sync_capsule(self, capsule_name: str):
        """Sync .env for a specific capsule"""
        capsule_dir = self.capsules_dir / capsule_name

        if not capsule_dir.exists():
            logger.error(f"❌ Capsule not found: {capsule_name}")
            return False

        template_path = capsule_dir / ".env.template"
        env_path = capsule_dir / ".env"

        logger.info(f"🔄 Syncing environment for capsule: {capsule_name}")

        # Parse template for Strongbox mappings
        mappings = self.parse_env_template(template_path)

        if not mappings:
            logger.warning(f"⚠️  No Strongbox mappings found in {template_path}")
            logger.info("Add comments like: # strongbox:service:purpose[:field]")
            return False

        logger.info(f"📋 Found {len(mappings)} API key mappings")

        # Fetch keys from Strongbox
        env_vars = self.fetch_keys_from_strongbox(mappings)

        if not env_vars:
            logger.error("❌ No API keys retrieved from Strongbox")
            return False

        # Write .env file
        self.write_env_file(env_path, env_vars, template_path)

        # Ensure .env is gitignored
        self.ensure_gitignore(capsule_dir)

        logger.info(f"✅ Environment sync complete for {capsule_name}")
        return True

    def list_capsules(self) -> List[str]:
        """List all available capsules"""
        if not self.capsules_dir.exists():
            return []

        capsules = []
        for item in self.capsules_dir.iterdir():
            if item.is_dir() and not item.name.startswith('.'):
                capsules.append(item.name)

        return sorted(capsules)


def main():
    parser = argparse.ArgumentParser(
        description="Sync capsule .env files from Strongbox",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Sync specific capsule
  %(prog)s my-project

  # Sync all capsules
  %(prog)s --all

  # List available capsules
  %(prog)s --list

.env.template format:
  OPENAI_API_KEY=  # strongbox:openai:main account
  GITHUB_TOKEN=    # strongbox:github:production:API_Key_Production
        """
    )

    parser.add_argument('capsule', nargs='?', help='Capsule name to sync')
    parser.add_argument('--all', action='store_true', help='Sync all capsules')
    parser.add_argument('--list', action='store_true', help='List available capsules')
    parser.add_argument('--root', help='Builder root directory',
                       default='{{CATALYST_ROOT}}')

    args = parser.parse_args()

    builder_root = Path(args.root)
    syncer = EnvSyncer(builder_root)

    # List capsules
    if args.list:
        capsules = syncer.list_capsules()
        print("Available capsules:")
        for capsule in capsules:
            print(f"  {capsule}")
        return 0

    # Sync all capsules
    if args.all:
        capsules = syncer.list_capsules()
        logger.info(f"🔄 Syncing all {len(capsules)} capsules...")

        success_count = 0
        for capsule in capsules:
            if syncer.sync_capsule(capsule):
                success_count += 1
            print()  # Blank line between capsules

        logger.info(f"✅ Synced {success_count}/{len(capsules)} capsules")
        return 0 if success_count == len(capsules) else 1

    # Sync specific capsule
    if args.capsule:
        success = syncer.sync_capsule(args.capsule)
        return 0 if success else 1

    # No arguments
    parser.print_help()
    return 1


if __name__ == '__main__':
    sys.exit(main())
