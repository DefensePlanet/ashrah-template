#!/usr/bin/env python3
"""
Strongbox CLI Integration for Catalyst
Simplified wrapper around KeePassXC CLI for credential management
"""

import subprocess
import os
import logging
import json
import secrets
import string
from typing import Optional, Dict, List, Any, Tuple
from pathlib import Path
from dataclasses import dataclass
from datetime import datetime
import getpass

@dataclass
class CredentialEntry:
    """Credential entry information"""
    title: str
    username: str
    password: str
    url: str = ""
    notes: str = ""
    totp_secret: str = ""
    custom_fields: Dict[str, str] = None
    
    def __post_init__(self):
        if self.custom_fields is None:
            self.custom_fields = {}

class StrongboxCLI:
    """Simplified Strongbox/KeePassXC CLI wrapper for Catalyst"""
    
    def __init__(self, db_path: Optional[str] = None, master_password: Optional[str] = ""):
        self.logger = logging.getLogger(__name__)
        self.root_path = Path.home() / "Documents" / "Builder"

        # Find KeePassXC CLI
        self.cli_paths = [
            "keepassxc-cli",
            "/Applications/KeePassXC.app/Contents/MacOS/keepassxc-cli",
            "/usr/local/bin/keepassxc-cli",
            "/opt/homebrew/bin/keepassxc-cli"
        ]
        self.cli_tool = self._find_cli()

        # Database detection
        self.potential_db_paths = [
            "{{HOME_DIR}}/Library/Mobile Documents/iCloud~com~strongbox/Documents/Roth Pass.kdbx",
            "~/Library/Mobile Documents/iCloud~com~strongbox/Documents/Roth Pass.kdbx",
            "~/Library/Application Support/Strongbox/Strongbox.kdbx",
            "~/Documents/Strongbox.kdbx",
            "~/Desktop/Strongbox.kdbx",
            "~/iCloud Drive/Strongbox.kdbx"
        ]

        self.db_path = db_path or self._find_database()
        # Default to empty password (common for Strongbox databases)
        self.master_password = master_password if master_password is not None else ""
        
        # Service folder mappings
        self.service_folders = {
            "github": "Development/GitHub",
            "gitlab": "Development/GitLab", 
            "openai": "AI/OpenAI",
            "anthropic": "AI/Anthropic",
            "shopify": "E-commerce/Shopify",
            "instagram": "Social Media/Instagram",
            "facebook": "Social Media/Facebook",
            "twitter": "Social Media/Twitter",
            "linkedin": "Social Media/LinkedIn",
            "google": "Google Services",
            "microsoft": "Microsoft Services",
            "apple": "Apple Services",
            "simplelogin": "Email/SimpleLogin",
            "n8n": "Automation/n8n",
            "default": "Catalyst/Auto-Created"
        }
        
    def _find_cli(self) -> Optional[str]:
        """Find KeePassXC CLI tool"""
        for cli_path in self.cli_paths:
            try:
                result = subprocess.run([cli_path, "--version"], 
                                      capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    self.logger.info(f"Found KeePassXC CLI: {cli_path}")
                    return cli_path
            except (FileNotFoundError, subprocess.TimeoutExpired):
                continue
        
        self.logger.error("KeePassXC CLI not found")
        return None
        
    def _find_database(self) -> Optional[str]:
        """Find Strongbox database"""
        for db_path in self.potential_db_paths:
            expanded_path = os.path.expanduser(db_path)
            if os.path.exists(expanded_path):
                self.logger.info(f"Found database: {expanded_path}")
                return expanded_path
        
        self.logger.error("Strongbox database not found")
        return None
        
    def _get_master_password(self, prompt_if_not_set: bool = False) -> str:
        """Get master password - defaults to empty string for no-password databases"""
        if self.master_password is None:
            self.master_password = ""

        # Only prompt if explicitly requested and password is empty
        if prompt_if_not_set and not self.master_password:
            self.master_password = getpass.getpass("Enter Strongbox master password (or press Enter for no password): ")

        return self.master_password
        
    def _run_cli_command(self, args: List[str], input_text: str = "", timeout: int = 30, entry_path_position: int = -1) -> Optional[subprocess.CompletedProcess]:
        """Run KeePassXC CLI command with error handling

        Args:
            args: Command arguments (e.g., ["add", "entry_path", "--username", "user"])
            input_text: Input to pipe to command
            timeout: Command timeout in seconds
            entry_path_position: Position of entry path in args (for inserting db_path before it).
                               If -1, db_path is appended at the end (old behavior)
        """
        if not self.cli_tool or not self.db_path:
            self.logger.error("CLI tool or database not available")
            return None

        try:
            # Insert database path in correct position
            # KeePassXC CLI expects: command database entry_path [options]
            if entry_path_position >= 0 and entry_path_position < len(args):
                # Insert db_path before the entry path
                args_with_db = args[:entry_path_position] + [self.db_path] + args[entry_path_position:]
                full_args = [self.cli_tool] + args_with_db
            else:
                # Old behavior: append db_path at end (for commands like ls, generate)
                full_args = [self.cli_tool] + args + [self.db_path]

            result = subprocess.run(
                full_args,
                input=input_text,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            return result

        except subprocess.TimeoutExpired:
            self.logger.error(f"Command timed out: {' '.join(args)}")
            return None
        except Exception as e:
            self.logger.error(f"Command failed: {e}")
            return None
            
    def test_connection(self) -> bool:
        """Test database connection"""
        password = self._get_master_password()
        result = self._run_cli_command(["ls"], f"{password}\n")
        
        if result and result.returncode == 0:
            self.logger.info("✅ Connected to Strongbox database")
            return True
        else:
            self.logger.error("❌ Failed to connect to database")
            return False
            
    def generate_password(self, length: int = 16, include_symbols: bool = True) -> str:
        """
        Request Strongbox to generate a secure password
        Password generation happens within Strongbox itself
        """
        # Strongbox generates the password internally
        # This method would interact with Strongbox's password generation feature
        # For KeePassXC CLI, we can use the generate command
        try:
            keepassxc_cli = "/Applications/KeePassXC.app/Contents/MacOS/keepassxc-cli"
            cmd_args = [keepassxc_cli, "generate"]
            if length:
                cmd_args.extend(["-L", str(length)])
            if not include_symbols:
                cmd_args.append("--no-symbols")
                
            result = subprocess.run(cmd_args, capture_output=True, text=True, timeout=10)
            
            if result and result.returncode == 0:
                password = result.stdout.strip()
                self.logger.info("✅ Strongbox generated secure password")
                return password
            else:
                self.logger.error("Failed to generate password via Strongbox")
                raise RuntimeError("Strongbox password generation failed")
                
        except Exception as e:
            self.logger.error(f"Password generation error: {e}")
            raise
        
    def create_folder(self, folder_path: str) -> bool:
        """Create folder in database, handling nested paths"""
        password = self._get_master_password()

        # Handle nested folders by creating parent folders first
        path_parts = folder_path.split('/')
        for i in range(1, len(path_parts) + 1):
            partial_path = '/'.join(path_parts[:i])

            # mkdir command expects: mkdir database entry_path
            result = self._run_cli_command(["mkdir", partial_path], f"{password}\n", entry_path_position=1)

            if result:
                if result.returncode == 0:
                    self.logger.info(f"✅ Created folder: {partial_path}")
                elif "already exists" in result.stderr.lower() or "already exists" in result.stdout.lower():
                    self.logger.debug(f"Folder already exists: {partial_path}")
                    continue
                else:
                    self.logger.error(f"Failed to create folder {partial_path}: {result.stderr}")
                    return False
            else:
                return False

        return True
        
    def store_credential(self, service: str, purpose: str, username: str, 
                        password: str = None, url: str = "", notes: str = "",
                        totp_secret: str = "", custom_fields: Dict[str, str] = None) -> bool:
        """Store credential in appropriate folder"""
        
        # Generate password if not provided
        if not password:
            password = self.generate_password()
            
        # Determine folder path
        folder_path = self.service_folders.get(service.lower(), self.service_folders["default"])
        
        # Create folder if needed
        self.create_folder(folder_path)
        
        # Create entry path
        entry_title = f"{service.title()} - {purpose}"
        entry_path = f"{folder_path}/{entry_title}"
        
        # Prepare notes with metadata
        timestamp = datetime.now().isoformat()
        full_notes = f"Created by Catalyst - {timestamp}\n"
        if purpose:
            full_notes += f"Purpose: {purpose}\n"
        if notes:
            full_notes += f"\n{notes}"
            
        # Create entry
        master_password = self._get_master_password()
        # Use -p flag to prompt for entry password via stdin
        input_text = f"{master_password}\n{password}\n"

        # Build args: add command expects: add database entry_path [options]
        args = ["add", entry_path, "--username", username, "-p"]
        if url:
            args.extend(["--url", url])
        # Note: keepassxc-cli add command doesn't support --notes parameter
        # Notes would need to be added via a separate mechanism if needed

        result = self._run_cli_command(args, input_text, entry_path_position=1)

        if result and result.returncode == 0:
            self.logger.info(f"✅ Stored credential: {entry_path}")

            # Add TOTP secret if provided
            if totp_secret:
                self._add_totp_secret(entry_path, totp_secret)

            # Add custom fields
            if custom_fields:
                for field_name, field_value in custom_fields.items():
                    self._add_custom_field(entry_path, field_name, field_value)

            return True
        elif result and "Could not create entry" in result.stderr:
            # Entry already exists, try to update it
            self.logger.info(f"Entry already exists, updating: {entry_path}")
            return self._update_credential(entry_path, username, password, url, notes, totp_secret, custom_fields)
        else:
            self.logger.error(f"Failed to store credential: {result.stderr if result else 'Unknown error'}")
            return False

    def _update_credential(self, entry_path: str, username: str, password: str,
                          url: str = "", notes: str = "", totp_secret: str = "",
                          custom_fields: Dict[str, str] = None) -> bool:
        """Update existing credential entry"""
        master_password = self._get_master_password()
        success = True

        # Update username
        result = self._run_cli_command(
            ["edit", entry_path, "--username", username],
            f"{master_password}\n",
            entry_path_position=1
        )
        if not result or result.returncode != 0:
            self.logger.error(f"Failed to update username: {result.stderr if result else 'Unknown error'}")
            success = False

        # Update password
        input_text = f"{master_password}\n{password}\n"
        result = self._run_cli_command(
            ["edit", entry_path, "-p"],
            input_text,
            entry_path_position=1
        )
        if not result or result.returncode != 0:
            self.logger.error(f"Failed to update password: {result.stderr if result else 'Unknown error'}")
            success = False

        # Update URL
        if url:
            result = self._run_cli_command(
                ["edit", entry_path, "--url", url],
                f"{master_password}\n",
                entry_path_position=1
            )
            if not result or result.returncode != 0:
                self.logger.error(f"Failed to update URL: {result.stderr if result else 'Unknown error'}")
                success = False

        # Add TOTP secret if provided
        if totp_secret:
            self._add_totp_secret(entry_path, totp_secret)

        # Add custom fields
        if custom_fields:
            for field_name, field_value in custom_fields.items():
                self._add_custom_field(entry_path, field_name, field_value)

        if success:
            self.logger.info(f"✅ Updated credential: {entry_path}")

        return success

    def _add_totp_secret(self, entry_path: str, totp_secret: str) -> bool:
        """Add TOTP secret to entry"""
        master_password = self._get_master_password()
        result = self._run_cli_command(
            ["edit", entry_path, "--set-totp", totp_secret],
            f"{master_password}\n",
            entry_path_position=1
        )
        
        if result and result.returncode == 0:
            self.logger.info(f"✅ Added TOTP to {entry_path}")
            return True
        else:
            self.logger.error(f"Failed to add TOTP: {result.stderr if result else 'Unknown error'}")
            return False
            
    def _add_custom_field(self, entry_path: str, field_name: str, field_value: str) -> bool:
        """Add custom field to entry using PyKeePass (KeePassXC CLI doesn't support custom attributes)"""
        try:
            from pykeepass import PyKeePass

            master_password = self._get_master_password()

            # Open database with PyKeePass
            kp = PyKeePass(self.db_path, password=master_password)

            # Find the entry
            entry = kp.find_entries(title=entry_path.split('/')[-1], first=True)
            if not entry:
                # Try finding by full path
                parts = entry_path.split('/')
                group = kp.root_group
                for part in parts[:-1]:
                    group = kp.find_groups(name=part, group=group, first=True)
                    if not group:
                        self.logger.error(f"Group not found in path: {entry_path}")
                        return False
                entry = kp.find_entries(title=parts[-1], group=group, first=True)

            if not entry:
                self.logger.error(f"Entry not found: {entry_path}")
                return False

            # Set custom property
            entry.set_custom_property(field_name, field_value)

            # Save database
            kp.save()

            self.logger.info(f"✅ Added custom field '{field_name}' to {entry_path}")
            return True

        except ImportError:
            self.logger.error("PyKeePass not installed. Install with: pip3 install --break-system-packages pykeepass")
            return False
        except Exception as e:
            self.logger.error(f"Failed to add custom field: {e}")
            return False
        
    def get_credential(self, service: str, purpose: str) -> Optional[CredentialEntry]:
        """Retrieve credential from database"""
        folder_path = self.service_folders.get(service.lower(), self.service_folders["default"])
        entry_title = f"{service.title()} - {purpose}"
        entry_path = f"{folder_path}/{entry_title}"
        
        return self._get_entry_by_path(entry_path)
        
    def _get_entry_by_path(self, entry_path: str) -> Optional[CredentialEntry]:
        """Get entry details by path"""
        master_password = self._get_master_password()

        # Get basic fields
        username_result = self._run_cli_command(
            ["show", "-q", "-a", "UserName", entry_path],
            f"{master_password}\n",
            entry_path_position=4
        )

        password_result = self._run_cli_command(
            ["show", "-q", "-a", "Password", entry_path],
            f"{master_password}\n",
            entry_path_position=4
        )

        url_result = self._run_cli_command(
            ["show", "-q", "-a", "URL", entry_path],
            f"{master_password}\n",
            entry_path_position=4
        )

        notes_result = self._run_cli_command(
            ["show", "-q", "-a", "Notes", entry_path],
            f"{master_password}\n",
            entry_path_position=4
        )

        totp_result = self._run_cli_command(
            ["show", "-q", "--totp", entry_path],
            f"{master_password}\n",
            entry_path_position=3
        )

        if not (username_result and password_result and
                username_result.returncode == 0 and password_result.returncode == 0):
            return None

        return CredentialEntry(
            title=entry_path,
            username=username_result.stdout.strip(),
            password=password_result.stdout.strip(),
            url=url_result.stdout.strip() if url_result and url_result.returncode == 0 else "",
            notes=notes_result.stdout.strip() if notes_result and notes_result.returncode == 0 else "",
            totp_secret="",  # We don't expose the secret, only current code
        )

    def get_custom_field(self, entry_path: str, field_name: str) -> Optional[str]:
        """Get a custom field value from an entry using PyKeePass"""
        try:
            from pykeepass import PyKeePass

            master_password = self._get_master_password()

            # Open database with PyKeePass
            kp = PyKeePass(self.db_path, password=master_password)

            # Find the entry
            entry = kp.find_entries(title=entry_path.split('/')[-1], first=True)
            if not entry:
                # Try finding by full path
                parts = entry_path.split('/')
                group = kp.root_group
                for part in parts[:-1]:
                    group = kp.find_groups(name=part, group=group, first=True)
                    if not group:
                        return None
                entry = kp.find_entries(title=parts[-1], group=group, first=True)

            if not entry:
                return None

            # Get custom property
            value = entry.get_custom_property(field_name)
            return value

        except ImportError:
            self.logger.error("PyKeePass not installed. Install with: pip3 install --break-system-packages pykeepass")
            return None
        except Exception as e:
            self.logger.error(f"Failed to get custom field: {e}")
            return None

    def get_api_key(self, service: str, purpose: str, field_name: str = "API_Key") -> Optional[str]:
        """
        Retrieve API key from custom field in credential entry

        Args:
            service: Service name (e.g., 'openai', 'github')
            purpose: Purpose/identifier (e.g., 'production', 'main account')
            field_name: Custom field name (default: 'API_Key')

        Returns:
            API key value or None if not found
        """
        folder_path = self.service_folders.get(service.lower(), self.service_folders["default"])
        entry_title = f"{service.title()} - {purpose}"
        entry_path = f"{folder_path}/{entry_title}"

        api_key = self.get_custom_field(entry_path, field_name)

        if api_key:
            self.logger.info(f"✅ Retrieved API key from {entry_path} ({field_name})")
        else:
            self.logger.warning(f"⚠️  API key not found in {entry_path} ({field_name})")

        return api_key

    def set_api_key(self, service: str, purpose: str, api_key: str, field_name: str = "API_Key") -> bool:
        """
        Store API key in custom field on credential entry

        Args:
            service: Service name (e.g., 'openai', 'github')
            purpose: Purpose/identifier (e.g., 'production', 'main account')
            api_key: The API key value to store
            field_name: Custom field name (default: 'API_Key')

        Returns:
            True if successful, False otherwise
        """
        folder_path = self.service_folders.get(service.lower(), self.service_folders["default"])
        entry_title = f"{service.title()} - {purpose}"
        entry_path = f"{folder_path}/{entry_title}"

        # Check if entry exists, create it if not
        existing = self.get_credential(service, purpose)
        if not existing:
            self.logger.info(f"Entry doesn't exist, creating: {entry_path}")
            # Create a basic entry (API keys don't need usernames/passwords)
            create_success = self.store_credential(
                service=service,
                purpose=purpose,
                username="api-key",  # Standard marker for API key entries
                password="n/a",       # Not applicable for API keys
                notes=f"API Key Storage - {field_name}"
            )
            if not create_success:
                self.logger.error(f"❌ Failed to create entry for API key")
                return False

        success = self._add_custom_field(entry_path, field_name, api_key)

        if success:
            self.logger.info(f"✅ Stored API key in {entry_path} ({field_name})")
        else:
            self.logger.error(f"❌ Failed to store API key in {entry_path} ({field_name})")

        return success
        
    def get_totp_code(self, service: str, purpose: str) -> Optional[str]:
        """Get current TOTP code for entry"""
        folder_path = self.service_folders.get(service.lower(), self.service_folders["default"])
        entry_title = f"{service.title()} - {purpose}"
        entry_path = f"{folder_path}/{entry_title}"

        master_password = self._get_master_password()
        result = self._run_cli_command(
            ["show", "-q", "--totp", entry_path],
            f"{master_password}\n",
            entry_path_position=3
        )
        
        if result and result.returncode == 0:
            return result.stdout.strip()
        return None
        
    def search_entries(self, search_term: str) -> List[str]:
        """Search for entries containing term"""
        master_password = self._get_master_password()
        result = self._run_cli_command(
            ["search", search_term],
            f"{master_password}\n"
        )
        
        if result and result.returncode == 0:
            entries = []
            for line in result.stdout.strip().split('\n'):
                line = line.strip()
                if line:
                    entries.append(line)
            return entries
        return []
        
    def list_service_entries(self, service: str) -> List[str]:
        """List all entries for a service"""
        folder_path = self.service_folders.get(service.lower(), self.service_folders["default"])

        master_password = self._get_master_password()
        result = self._run_cli_command(
            ["ls", "-R", folder_path],
            f"{master_password}\n",
            entry_path_position=2
        )
        
        if result and result.returncode == 0:
            entries = []
            for line in result.stdout.strip().split('\n'):
                line = line.strip()
                if line and not line.endswith('/'):  # Skip folder names
                    entries.append(line)
            return entries
        return []
        
    def create_account_entry(self, service: str, purpose: str, email_alias: str, 
                           additional_notes: str = "", generated_password: str = None,
                           enable_totp: bool = False) -> Tuple[bool, Dict[str, str]]:
        """
        Create complete account entry in Strongbox
        - Email alias is stored as the username
        - Entry title follows format: Service - Purpose 
        - Password generated by Strongbox if not provided
        """
        
        result = {
            "username": email_alias,  # Email alias becomes the username
            "email": email_alias,     # Same for email field
            "password": "",
            "totp_code": "",
            "entry_path": "",
            "title": ""
        }
        
        # Create entry title: "GitHub - API Access" or "Instagram - Brand Account"
        entry_title = f"{service.title()} - {purpose.title()}"
        result["title"] = entry_title
        
        # Generate password via Strongbox if not provided
        if not generated_password:
            try:
                password = self.generate_password()  # Uses Strongbox's generation
                result["password"] = password
            except Exception as e:
                self.logger.error(f"Failed to generate password via Strongbox: {e}")
                return False, result
        else:
            password = generated_password
            result["password"] = password
        
        # Create service URL
        service_urls = {
            "github": "https://github.com",
            "gitlab": "https://gitlab.com", 
            "openai": "https://platform.openai.com",
            "anthropic": "https://console.anthropic.com",
            "shopify": "https://accounts.shopify.com",
            "instagram": "https://instagram.com",
            "google": "https://accounts.google.com",
            "microsoft": "https://login.microsoftonline.com"
        }
        
        url = service_urls.get(service.lower(), f"https://{service.lower()}.com")
        
        # Create comprehensive notes
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        notes = f"Created by Catalyst - {timestamp}\n"
        notes += f"Service: {service}\n"
        notes += f"Purpose: {purpose}\n" 
        notes += f"Email Alias: {email_alias}\n"
        if additional_notes:
            notes += f"\nAdditional Notes:\n{additional_notes}"
        
        # Generate TOTP secret if requested (using Strongbox's capability)
        totp_secret = ""
        if enable_totp:
            # This would use Strongbox's TOTP generation if available
            # For now, we'll use a basic approach but ideally delegate to Strongbox
            import base64
            import secrets
            totp_bytes = secrets.token_bytes(20)
            totp_secret = base64.b32encode(totp_bytes).decode('utf-8').rstrip('=')
            
        # Store credential using proper title and email alias as username
        success = self.store_credential(
            service=service,
            purpose=purpose,
            username=email_alias,  # Email alias is the username
            password=password,
            url=url,
            notes=notes,
            totp_secret=totp_secret,
            custom_fields={"service": service, "purpose": purpose}
        )
        
        if success:
            folder_path = self.service_folders.get(service.lower(), self.service_folders["default"])
            entry_path = f"{folder_path}/{entry_title}"
            result["entry_path"] = entry_path
            
            # Get TOTP code if enabled
            if enable_totp and totp_secret:
                totp_code = self.get_totp_code(service, purpose)
                if totp_code:
                    result["totp_code"] = totp_code
                    
            self.logger.info(f"✅ Created Strongbox entry: {entry_title}")
            self.logger.info(f"   Username (Email Alias): {email_alias}")
            self.logger.info(f"   Entry Path: {entry_path}")
                    
        return success, result
        
    def backup_database(self, backup_path: Optional[Path] = None) -> bool:
        """Create backup of database"""
        if not backup_path:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = self.root_path / "global" / "backups" / f"strongbox_backup_{timestamp}.kdbx"
            
        backup_path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            import shutil
            shutil.copy2(self.db_path, backup_path)
            self.logger.info(f"✅ Database backed up to: {backup_path}")
            return True
        except Exception as e:
            self.logger.error(f"Backup failed: {e}")
            return False

def main():
    """CLI interface for Strongbox integration"""
    import argparse

    parser = argparse.ArgumentParser(description="Catalyst Strongbox CLI")
    parser.add_argument("action", choices=[
        "test", "store", "get", "list", "search", "backup", "create-account", "get-totp", "get-api-key", "set-api-key"
    ])
    parser.add_argument("--service", help="Service name")
    parser.add_argument("--purpose", help="Purpose/identifier")
    parser.add_argument("--username", help="Username")
    parser.add_argument("--email", help="Email address")
    parser.add_argument("--password", help="Password (generated if not provided)")
    parser.add_argument("--url", help="URL")
    parser.add_argument("--notes", help="Notes")
    parser.add_argument("--search-term", help="Search term")
    parser.add_argument("--enable-totp", action="store_true", help="Enable TOTP")
    parser.add_argument("--field", default="API_Key", help="Custom field name for API key (default: API_Key)")
    parser.add_argument("--api-key", help="API key value to store")
    
    args = parser.parse_args()
    
    strongbox = StrongboxCLI()
    
    if args.action == "test":
        success = strongbox.test_connection()
        return 0 if success else 1
        
    elif args.action == "create-account" and args.service and args.purpose and args.username:
        success, result = strongbox.create_account_entry(
            args.service, args.purpose, args.username, 
            args.email or "", args.password, args.enable_totp
        )
        
        if success:
            print(f"✅ Created account entry: {result['entry_path']}")
            print(f"Username: {result['username']}")
            if result['email']:
                print(f"Email: {result['email']}")
            print(f"Password: {result['password']}")
            if result['totp_code']:
                print(f"TOTP Code: {result['totp_code']}")
            return 0
        else:
            print("❌ Failed to create account entry")
            return 1
            
    elif args.action == "store" and args.service and args.purpose and args.username:
        success = strongbox.store_credential(
            args.service, args.purpose, args.username,
            args.password, args.url or "", args.notes or ""
        )
        return 0 if success else 1
        
    elif args.action == "get" and args.service and args.purpose:
        credential = strongbox.get_credential(args.service, args.purpose)
        if credential:
            print(f"Title: {credential.title}")
            print(f"Username: {credential.username}")
            print(f"Password: {credential.password}")
            print(f"URL: {credential.url}")
            if credential.notes:
                print(f"Notes: {credential.notes}")
            return 0
        else:
            print("❌ Credential not found")
            return 1
            
    elif args.action == "get-totp" and args.service and args.purpose:
        code = strongbox.get_totp_code(args.service, args.purpose)
        if code:
            print(f"TOTP Code: {code}")
            return 0
        else:
            print("❌ TOTP not found or not enabled")
            return 1

    elif args.action == "get-api-key" and args.service and args.purpose:
        api_key = strongbox.get_api_key(args.service, args.purpose, args.field)
        if api_key:
            print(api_key)  # Print just the key for easy piping
            return 0
        else:
            print(f"❌ API key not found in custom field '{args.field}'", file=__import__('sys').stderr)
            return 1

    elif args.action == "set-api-key" and args.service and args.purpose and args.api_key:
        success = strongbox.set_api_key(args.service, args.purpose, args.api_key, args.field)
        if success:
            print(f"✅ Stored API key in custom field '{args.field}'")
            return 0
        else:
            print(f"❌ Failed to store API key", file=__import__('sys').stderr)
            return 1

    elif args.action == "list":
        if args.service:
            entries = strongbox.list_service_entries(args.service)
            print(f"Entries for {args.service}:")
            for entry in entries:
                print(f"  {entry}")
        else:
            print("Available services:")
            for service in strongbox.service_folders.keys():
                if service != "default":
                    print(f"  {service}")
        return 0
        
    elif args.action == "search" and args.search_term:
        entries = strongbox.search_entries(args.search_term)
        print(f"Search results for '{args.search_term}':")
        for entry in entries:
            print(f"  {entry}")
        return 0
        
    elif args.action == "backup":
        success = strongbox.backup_database()
        return 0 if success else 1
        
    else:
        parser.print_help()
        return 1

if __name__ == "__main__":
    import sys
    sys.exit(main())