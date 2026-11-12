#!/usr/bin/env python3
"""
Catalyst Strongbox Integration Hub
Unified credential management for all capsules via Strongbox/KeePassXC CLI
"""

import subprocess
import os
import logging
import json
from typing import Optional, Tuple, List, Dict, Any
from pathlib import Path
from dataclasses import dataclass
from enum import Enum
import getpass

class CredentialType(Enum):
    """Types of credentials we manage"""
    API_KEY = "api_key"
    PASSWORD = "password"
    OTP_SECRET = "otp_secret"
    SSH_KEY = "ssh_key"
    CERTIFICATE = "certificate"
    EMAIL_ALIAS = "email_alias"

@dataclass
class CredentialEntry:
    """Structured credential entry"""
    title: str
    username: str
    password: str
    url: str = ""
    notes: str = ""
    custom_fields: Dict[str, str] = None
    
    def __post_init__(self):
        if self.custom_fields is None:
            self.custom_fields = {}

@dataclass 
class ServiceConfig:
    """Configuration for service-specific credential management"""
    name: str
    folder_path: str
    entry_template: str
    required_fields: List[str]
    api_key_field: str = "api_key"

class StrongboxHub:
    """Unified Strongbox integration for Catalyst"""
    
    def __init__(self, config_path: Optional[Path] = None):
        self.logger = logging.getLogger(__name__)
        self.root_path = Path.home() / "Documents" / "Builder"
        
        # Service configurations
        self.service_configs = {
            "github": ServiceConfig(
                name="GitHub",
                folder_path="Development/GitHub",
                entry_template="GitHub - {purpose}",
                required_fields=["api_key", "username"],
                api_key_field="api_key"
            ),
            "openai": ServiceConfig(
                name="OpenAI", 
                folder_path="AI/OpenAI",
                entry_template="OpenAI - {purpose}",
                required_fields=["api_key"],
                api_key_field="api_key"
            ),
            "anthropic": ServiceConfig(
                name="Anthropic",
                folder_path="AI/Anthropic", 
                entry_template="Anthropic - {purpose}",
                required_fields=["api_key"],
                api_key_field="api_key"
            ),
            "simplelogin": ServiceConfig(
                name="SimpleLogin",
                folder_path="Email/SimpleLogin",
                entry_template="SimpleLogin - {alias}",
                required_fields=["email", "api_key"],
                api_key_field="api_key"
            ),
            "n8n": ServiceConfig(
                name="n8n",
                folder_path="Automation/n8n",
                entry_template="n8n - {instance}",
                required_fields=["username", "password", "webhook_url"],
            ),
            "shopify": ServiceConfig(
                name="Shopify",
                folder_path="E-commerce/Shopify",
                entry_template="Shopify - {store_name}",
                required_fields=["api_key", "api_secret", "store_url"],
                api_key_field="api_key"
            )
        }
        
        # KeePassXC CLI detection
        self.cli_paths = [
            "keepassxc-cli",
            "/Applications/KeePassXC.app/Contents/MacOS/keepassxc-cli",
            "/usr/local/bin/keepassxc-cli", 
            "/opt/homebrew/bin/keepassxc-cli"
        ]
        self.cli_tool = None
        
        # Database path detection
        self.potential_db_paths = [
            "{{HOME_DIR}}/Library/Mobile Documents/iCloud~com~strongbox/Documents/Roth Pass.kdbx",
            "~/Library/Mobile Documents/iCloud~com~strongbox/Documents/Roth Pass.kdbx",
            "~/Library/Application Support/Strongbox/Strongbox.kdbx",
            "~/Documents/Strongbox.kdbx",
            "~/Desktop/Strongbox.kdbx",
            "~/iCloud Drive/Strongbox.kdbx"
        ]
        
        self.db_path = None
        self.master_password = None
        
    def initialize(self) -> bool:
        """Initialize Strongbox connection"""
        if not self._check_keepassxc_cli():
            self.logger.error("KeePassXC CLI not available")
            return False
            
        self.db_path = self._find_database()
        if not self.db_path:
            self.logger.error("Strongbox database not found")
            return False
            
        # Test connection
        if not self._test_connection():
            self.logger.error("Failed to connect to Strongbox database")
            return False
            
        self.logger.info(f"✅ Strongbox Hub initialized with database: {os.path.basename(self.db_path)}")
        return True
        
    def _check_keepassxc_cli(self) -> bool:
        """Check for KeePassXC CLI availability"""
        for cli_path in self.cli_paths:
            try:
                result = subprocess.run([cli_path, "--version"], capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    self.cli_tool = cli_path
                    version = result.stdout.strip()
                    self.logger.info(f"Found KeePassXC CLI: {cli_path} ({version})")
                    return True
            except (FileNotFoundError, subprocess.TimeoutExpired):
                continue
        return False
        
    def _find_database(self) -> Optional[str]:
        """Find Strongbox database file"""
        for db_path in self.potential_db_paths:
            expanded_path = os.path.expanduser(db_path)
            if os.path.exists(expanded_path):
                self.logger.info(f"Found database: {expanded_path}")
                return expanded_path
        return None
        
    def _test_connection(self) -> bool:
        """Test database connection"""
        if not self.master_password:
            self.master_password = getpass.getpass("Enter Strongbox master password: ")
            
        try:
            result = subprocess.run(
                [self.cli_tool, "ls", self.db_path],
                input=self.master_password + "\n",
                capture_output=True,
                text=True,
                timeout=10
            )
            return result.returncode == 0
        except subprocess.TimeoutExpired:
            self.logger.error("Database connection timed out")
            return False
            
    def create_service_folder(self, service: str) -> bool:
        """Create folder structure for a service"""
        if service not in self.service_configs:
            self.logger.error(f"Unknown service: {service}")
            return False
            
        config = self.service_configs[service]
        
        try:
            # Create folder path
            result = subprocess.run(
                [self.cli_tool, "mkdir", self.db_path, config.folder_path],
                input=self.master_password + "\n",
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                self.logger.info(f"✅ Created folder: {config.folder_path}")
                return True
            else:
                # Folder might already exist, which is fine
                if "already exists" in result.stderr.lower():
                    self.logger.info(f"Folder already exists: {config.folder_path}")
                    return True
                self.logger.error(f"Failed to create folder: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            self.logger.error("Folder creation timed out")
            return False
            
    def store_credential(self, service: str, purpose: str, credential: CredentialEntry) -> bool:
        """Store credential in appropriate service folder"""
        if service not in self.service_configs:
            self.logger.error(f"Unknown service: {service}")
            return False
            
        config = self.service_configs[service]
        
        # Ensure folder exists
        self.create_service_folder(service)
        
        # Format entry title
        entry_title = config.entry_template.format(purpose=purpose)
        entry_path = f"{config.folder_path}/{entry_title}"
        
        try:
            # Create entry
            result = subprocess.run(
                [self.cli_tool, "add", self.db_path, entry_path, 
                 "--username", credential.username,
                 "--url", credential.url,
                 "--notes", credential.notes],
                input=f"{self.master_password}\n{credential.password}\n{credential.password}\n",
                capture_output=True,
                text=True,
                timeout=15
            )
            
            if result.returncode == 0:
                # Add custom fields
                for field_name, field_value in credential.custom_fields.items():
                    self._add_custom_field(entry_path, field_name, field_value)
                    
                self.logger.info(f"✅ Stored credential: {entry_path}")
                return True
            else:
                self.logger.error(f"Failed to store credential: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            self.logger.error("Credential storage timed out")
            return False
            
    def _add_custom_field(self, entry_path: str, field_name: str, field_value: str) -> bool:
        """Add custom field to existing entry"""
        try:
            result = subprocess.run(
                [self.cli_tool, "edit", self.db_path, entry_path, "--set-attribute", field_name, field_value],
                input=self.master_password + "\n",
                capture_output=True,
                text=True,
                timeout=10
            )
            return result.returncode == 0
        except subprocess.TimeoutExpired:
            return False
            
    def retrieve_credential(self, service: str, purpose: str) -> Optional[CredentialEntry]:
        """Retrieve credential from Strongbox"""
        if service not in self.service_configs:
            self.logger.error(f"Unknown service: {service}")
            return None
            
        config = self.service_configs[service]
        entry_title = config.entry_template.format(purpose=purpose) 
        entry_path = f"{config.folder_path}/{entry_title}"
        
        return self._get_entry_details(entry_path)
        
    def _get_entry_details(self, entry_path: str) -> Optional[CredentialEntry]:
        """Get full details for an entry"""
        try:
            # Get basic fields
            username_result = subprocess.run(
                [self.cli_tool, "show", "-q", "-a", "UserName", self.db_path, entry_path],
                input=self.master_password + "\n",
                capture_output=True,
                text=True,
                timeout=10
            )
            
            password_result = subprocess.run(
                [self.cli_tool, "show", "-q", "-a", "Password", self.db_path, entry_path],
                input=self.master_password + "\n", 
                capture_output=True,
                text=True,
                timeout=10
            )
            
            url_result = subprocess.run(
                [self.cli_tool, "show", "-q", "-a", "URL", self.db_path, entry_path],
                input=self.master_password + "\n",
                capture_output=True,
                text=True,
                timeout=10
            )
            
            notes_result = subprocess.run(
                [self.cli_tool, "show", "-q", "-a", "Notes", self.db_path, entry_path],
                input=self.master_password + "\n",
                capture_output=True,
                text=True, 
                timeout=10
            )
            
            if all(r.returncode == 0 for r in [username_result, password_result]):
                return CredentialEntry(
                    title=entry_path,
                    username=username_result.stdout.strip(),
                    password=password_result.stdout.strip(),
                    url=url_result.stdout.strip() if url_result.returncode == 0 else "",
                    notes=notes_result.stdout.strip() if notes_result.returncode == 0 else ""
                )
                
        except subprocess.TimeoutExpired:
            self.logger.error("Credential retrieval timed out")
            
        return None
        
    def list_service_entries(self, service: str) -> List[str]:
        """List all entries for a service"""
        if service not in self.service_configs:
            return []
            
        config = self.service_configs[service]
        
        try:
            result = subprocess.run(
                [self.cli_tool, "ls", "-R", self.db_path, config.folder_path],
                input=self.master_password + "\n",
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                entries = []
                for line in result.stdout.strip().split('\n'):
                    line = line.strip()
                    if line and not line.endswith('/'):  # Skip folders
                        entries.append(line)
                return entries
                
        except subprocess.TimeoutExpired:
            self.logger.error("Entry listing timed out")
            
        return []
        
    def generate_api_key_entry(self, service: str, purpose: str, api_key: str, 
                              username: str = "", additional_fields: Dict[str, str] = None) -> CredentialEntry:
        """Generate properly formatted API key entry"""
        if additional_fields is None:
            additional_fields = {}
            
        config = self.service_configs.get(service)
        if config:
            additional_fields[config.api_key_field] = api_key
            
        entry = CredentialEntry(
            title=f"{service} - {purpose}",
            username=username,
            password=api_key,  # Store API key as password for easy retrieval
            url=f"https://{service}.com" if not additional_fields.get("url") else additional_fields["url"],
            notes=f"API key for {purpose}\nCreated: {self._get_timestamp()}",
            custom_fields=additional_fields
        )
        
        return entry
        
    def _get_timestamp(self) -> str:
        """Get current timestamp"""
        from datetime import datetime
        return datetime.now().isoformat()
        
    def search_entries(self, search_term: str) -> List[str]:
        """Search for entries by term"""
        try:
            result = subprocess.run(
                [self.cli_tool, "search", self.db_path, search_term],
                input=self.master_password + "\n",
                capture_output=True,
                text=True,
                timeout=15
            )
            
            if result.returncode == 0:
                entries = []
                for line in result.stdout.strip().split('\n'):
                    line = line.strip()
                    if line:
                        entries.append(line)
                return entries
                
        except subprocess.TimeoutExpired:
            self.logger.error("Search timed out")
            
        return []
        
    def backup_database(self, backup_path: Optional[Path] = None) -> bool:
        """Create backup of Strongbox database"""
        if backup_path is None:
            backup_path = self.root_path / "global" / "backups" / f"strongbox_backup_{self._get_timestamp().replace(':', '-')}.kdbx"
            
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
    """CLI interface for Strongbox Hub"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Catalyst Strongbox Hub")
    parser.add_argument("action", choices=["init", "store", "get", "list", "search", "backup"])
    parser.add_argument("--service", help="Service name")
    parser.add_argument("--purpose", help="Purpose/identifier")
    parser.add_argument("--username", help="Username")
    parser.add_argument("--api-key", help="API key")
    parser.add_argument("--search-term", help="Search term")
    
    args = parser.parse_args()
    
    hub = StrongboxHub()
    
    if args.action == "init":
        success = hub.initialize()
        return 0 if success else 1
        
    elif args.action == "store" and args.service and args.purpose:
        if not hub.initialize():
            return 1
            
        # Create API key entry
        api_key = args.api_key or getpass.getpass("Enter API key: ")
        username = args.username or input("Username (optional): ")
        
        entry = hub.generate_api_key_entry(args.service, args.purpose, api_key, username)
        success = hub.store_credential(args.service, args.purpose, entry)
        return 0 if success else 1
        
    elif args.action == "get" and args.service and args.purpose:
        if not hub.initialize():
            return 1
            
        credential = hub.retrieve_credential(args.service, args.purpose)
        if credential:
            print(f"Username: {credential.username}")
            print(f"API Key: {credential.password}")
            if credential.custom_fields:
                print("Additional fields:")
                for k, v in credential.custom_fields.items():
                    print(f"  {k}: {v}")
            return 0
        else:
            print("Credential not found")
            return 1
            
    elif args.action == "list":
        if not hub.initialize():
            return 1
            
        if args.service:
            entries = hub.list_service_entries(args.service)
            print(f"Entries for {args.service}:")
            for entry in entries:
                print(f"  {entry}")
        else:
            print("Available services:")
            for service in hub.service_configs.keys():
                print(f"  {service}")
        return 0
        
    elif args.action == "search" and args.search_term:
        if not hub.initialize():
            return 1
            
        entries = hub.search_entries(args.search_term)
        print(f"Search results for '{args.search_term}':")
        for entry in entries:
            print(f"  {entry}")
        return 0
        
    elif args.action == "backup":
        if not hub.initialize():
            return 1
            
        success = hub.backup_database()
        return 0 if success else 1
        
    else:
        parser.print_help()
        return 1

if __name__ == "__main__":
    import sys
    sys.exit(main())