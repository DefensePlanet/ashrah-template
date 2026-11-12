#!/usr/bin/env python3
"""
Simple Login API Integration for Catalyst
Creates email aliases programmatically for account creation
"""

import requests
import logging
import json
from typing import Optional, Dict, List, Any
from pathlib import Path
from dataclasses import dataclass
from datetime import datetime
import os

@dataclass
class AliasInfo:
    """Information about a created alias"""
    email: str
    id: int
    enabled: bool
    note: str
    mailbox_id: int
    created_at: str
    nb_forward: int
    nb_block: int
    nb_reply: int

class SimpleLoginAPI:
    """Simple Login API integration"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.logger = logging.getLogger(__name__)
        self.base_url = "https://app.simplelogin.io/api"
        
        # Get API key from parameter or environment
        self.api_key = api_key or os.environ.get('SIMPLELOGIN_API_KEY')
        
        if not self.api_key:
            raise ValueError("Simple Login API key required. Set SIMPLELOGIN_API_KEY environment variable or pass api_key parameter.")
        
        # Set up session with headers
        self.session = requests.Session()
        self.session.headers.update({
            'Authentication': self.api_key,
            'Content-Type': 'application/json'
        })
        
        # Rate limiting
        self._last_request = 0
        self._min_interval = 1.0  # Minimum seconds between requests
        
    def _make_request(self, method: str, endpoint: str, **kwargs) -> Optional[Dict[str, Any]]:
        """Make API request with rate limiting and error handling"""
        import time
        
        # Rate limiting
        now = time.time()
        if now - self._last_request < self._min_interval:
            time.sleep(self._min_interval - (now - self._last_request))
        
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        
        try:
            response = self.session.request(method, url, **kwargs)
            self._last_request = time.time()
            
            # Handle rate limiting
            if response.status_code == 429:
                self.logger.warning("Rate limited, waiting 60 seconds...")
                time.sleep(60)
                return self._make_request(method, endpoint, **kwargs)
            
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 201:
                return response.json()
            else:
                self.logger.error(f"API request failed: {response.status_code} - {response.text}")
                return None
                
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Request failed: {e}")
            return None
            
    def test_connection(self) -> bool:
        """Test API connection by getting user info"""
        print(f"Testing connection with API key: {self.api_key[:10]}...")
        result = self._make_request('GET', '/user_info')
        if result:
            print(f"✅ Connected to Simple Login as: {result.get('name', 'Unknown')}")
            return True
        else:
            print("❌ Failed to connect to Simple Login API")
            return False
            
    def get_user_info(self) -> Optional[Dict[str, Any]]:
        """Get user account information"""
        return self._make_request('GET', '/user_info')

    def get_mailboxes(self) -> Optional[List[Dict[str, Any]]]:
        """Get all mailboxes for the account"""
        result = self._make_request('GET', '/mailboxes')
        if result and 'mailboxes' in result:
            return result['mailboxes']
        return None

    def find_mailbox_by_email(self, email: str) -> Optional[int]:
        """Find mailbox ID by email address"""
        mailboxes = self.get_mailboxes()
        if mailboxes:
            for mailbox in mailboxes:
                if mailbox.get('email', '').lower() == email.lower():
                    return mailbox.get('id')
        return None

    def create_random_alias(self, note: str = "", hostname: str = "", mode: str = "word", mailbox_id: Optional[int] = None) -> Optional[AliasInfo]:
        """Create random alias with optional hostname and mode

        Args:
            note: Note to attach to alias
            hostname: Service hostname to influence alias generation (e.g., 'radar', 'github')
            mode: 'word' for readable aliases (radar.reference759) or 'uuid' for random strings
            mailbox_id: Mailbox ID to forward emails to (defaults to {{USER_EMAIL}} if not specified)
        """
        # Default to {{USER_EMAIL}} mailbox if not specified
        if mailbox_id is None:
            mailbox_id = self.find_mailbox_by_email('{{USER_EMAIL}}')
            if mailbox_id:
                self.logger.info(f"Using default mailbox: {{USER_EMAIL}} (ID: {mailbox_id})")

        # Build query parameters
        params = {}
        if mode:
            params['mode'] = mode
        if hostname:
            params['hostname'] = hostname

        data = {}
        if note:
            data['note'] = note
        if mailbox_id:
            data['mailbox_id'] = mailbox_id

        result = self._make_request('POST', '/alias/random/new', json=data, params=params)
        
        if result:
            alias_info = AliasInfo(
                email=result['email'],
                id=result['id'],
                enabled=result['enabled'],
                note=result.get('note', ''),
                mailbox_id=result.get('mailbox_id', 0),
                created_at=result.get('created_at', ''),
                nb_forward=result.get('nb_forward', 0),
                nb_block=result.get('nb_block', 0),
                nb_reply=result.get('nb_reply', 0)
            )
            self.logger.info(f"✅ Created random alias: {alias_info.email}")
            return alias_info
        
        return None
        
    def create_custom_alias(self, alias_prefix: str, suffix: str, note: str = "", mailbox_id: Optional[int] = None) -> Optional[AliasInfo]:
        """Create custom alias with specific prefix and suffix

        Args:
            alias_prefix: Prefix for the alias
            suffix: Domain suffix for the alias
            note: Note to attach to alias
            mailbox_id: Mailbox ID to forward emails to (defaults to {{USER_EMAIL}} if not specified)
        """
        # Default to {{USER_EMAIL}} mailbox if not specified
        if mailbox_id is None:
            mailbox_id = self.find_mailbox_by_email('{{USER_EMAIL}}')
            if mailbox_id:
                self.logger.info(f"Using default mailbox: {{USER_EMAIL}} (ID: {mailbox_id})")

        data = {
            'alias_prefix': alias_prefix,
            'signed_suffix': suffix
        }
        if note:
            data['note'] = note
        if mailbox_id:
            data['mailbox_id'] = mailbox_id

        result = self._make_request('POST', '/alias/custom/new', json=data)
        
        if result:
            alias_info = AliasInfo(
                email=result['email'],
                id=result['id'],
                enabled=result['enabled'],
                note=result.get('note', ''),
                mailbox_id=result.get('mailbox_id', 0),
                created_at=result.get('created_at', ''),
                nb_forward=result.get('nb_forward', 0),
                nb_block=result.get('nb_block', 0),
                nb_reply=result.get('nb_reply', 0)
            )
            self.logger.info(f"✅ Created custom alias: {alias_info.email}")
            return alias_info
            
        return None
        
    def get_aliases(self, page_id: int = 0) -> Optional[List[Dict[str, Any]]]:
        """Get list of aliases"""
        params = {'page_id': page_id}
        result = self._make_request('GET', '/aliases', params=params)
        
        if result and 'aliases' in result:
            return result['aliases']
        return None
        
    def get_alias_info(self, alias_id: int) -> Optional[Dict[str, Any]]:
        """Get detailed info about specific alias"""
        return self._make_request('GET', f'/aliases/{alias_id}')
        
    def update_alias_note(self, alias_id: int, note: str) -> bool:
        """Update alias note/description"""
        data = {'note': note}
        result = self._make_request('PATCH', f'/aliases/{alias_id}', json=data)
        return result is not None
        
    def toggle_alias(self, alias_id: int) -> bool:
        """Enable/disable alias"""
        result = self._make_request('POST', f'/aliases/{alias_id}/toggle')
        return result is not None
        
    def delete_alias(self, alias_id: int) -> bool:
        """Delete alias"""
        result = self._make_request('DELETE', f'/aliases/{alias_id}')
        return result is not None
        
    def create_alias_for_service(self, service_name: str, purpose: str = None) -> Optional[AliasInfo]:
        """Create alias specifically for a service/account"""
        # Generate descriptive note
        timestamp = datetime.now().strftime("%Y-%m-%d")
        
        if purpose:
            note = f"Catalyst - {service_name} ({purpose}) - {timestamp}"
        else:
            note = f"Catalyst - {service_name} - {timestamp}"
        
        # Try to create custom alias first, fallback to random
        alias_prefix = f"{service_name.lower().replace(' ', '-')}"
        
        # Get available suffixes for custom alias
        suffixes = self.get_custom_domains()
        if suffixes:
            # Use first available suffix
            suffix = suffixes[0]
            alias = self.create_custom_alias(alias_prefix, suffix, note)
            if alias:
                return alias
        
        # Fallback to random alias with service-based naming
        self.logger.info("Custom alias failed, creating random alias with hostname")
        return self.create_random_alias(note=note, hostname=service_name, mode="word")
        
    def get_custom_domains(self) -> Optional[List[str]]:
        """Get available custom domains/suffixes"""
        result = self._make_request('GET', '/alias/options')
        
        if result and 'suffixes' in result:
            return [suffix['suffix'] for suffix in result['suffixes']]
        return None
        
    def search_aliases_by_note(self, search_term: str) -> List[Dict[str, Any]]:
        """Search aliases by note content"""
        all_aliases = []
        page = 0
        
        while True:
            aliases = self.get_aliases(page)
            if not aliases:
                break
                
            # Filter by note content
            matching_aliases = [
                alias for alias in aliases 
                if search_term.lower() in alias.get('note', '').lower()
            ]
            all_aliases.extend(matching_aliases)
            
            # Check if there are more pages
            if len(aliases) < 20:  # Assuming page size is 20
                break
            page += 1
            
        return all_aliases
        
    def get_service_aliases(self, service_name: str) -> List[Dict[str, Any]]:
        """Get all aliases for a specific service"""
        return self.search_aliases_by_note(service_name)
        
    def cleanup_old_aliases(self, days_old: int = 365, dry_run: bool = True) -> List[str]:
        """Clean up old unused aliases"""
        from datetime import datetime, timedelta
        
        cutoff_date = datetime.now() - timedelta(days=days_old)
        deleted_aliases = []
        
        # Get all aliases
        page = 0
        while True:
            aliases = self.get_aliases(page)
            if not aliases:
                break
                
            for alias in aliases:
                created_at = datetime.fromisoformat(alias['created_at'].replace('Z', '+00:00'))
                
                # Check if old and unused
                if (created_at < cutoff_date and 
                    alias.get('nb_forward', 0) == 0 and 
                    alias.get('nb_reply', 0) == 0):
                    
                    self.logger.info(f"Would delete old unused alias: {alias['email']}")
                    deleted_aliases.append(alias['email'])
                    
                    if not dry_run:
                        self.delete_alias(alias['id'])
                        
            if len(aliases) < 20:
                break
            page += 1
            
        return deleted_aliases

def main():
    """CLI interface for Simple Login API"""
    import argparse

    parser = argparse.ArgumentParser(description="Simple Login API Integration")
    parser.add_argument("action", choices=[
        "test", "create", "list", "info", "search", "cleanup", "mailboxes"
    ])
    parser.add_argument("--service", help="Service name")
    parser.add_argument("--purpose", help="Purpose/description")
    parser.add_argument("--note", help="Note/description")
    parser.add_argument("--hostname", help="Hostname for alias generation (e.g., 'radar', 'github')")
    parser.add_argument("--mode", choices=["word", "uuid"], default="word",
                        help="Alias generation mode: 'word' for readable (default) or 'uuid' for random")
    parser.add_argument("--alias-id", type=int, help="Alias ID")
    parser.add_argument("--search", help="Search term")
    parser.add_argument("--days", type=int, default=365, help="Days old for cleanup")
    parser.add_argument("--dry-run", action="store_true", help="Dry run for cleanup")
    
    args = parser.parse_args()
    
    try:
        api = SimpleLoginAPI()
    except ValueError as e:
        print(f"❌ {e}")
        return 1
        
    if args.action == "test":
        success = api.test_connection()
        return 0 if success else 1
        
    elif args.action == "create":
        if args.service:
            alias = api.create_alias_for_service(args.service, args.purpose)
        else:
            note = args.note or "Created via Catalyst CLI"
            hostname = args.hostname or ""
            mode = args.mode or "word"
            alias = api.create_random_alias(note=note, hostname=hostname, mode=mode)
            
        if alias:
            print(f"✅ Created alias: {alias.email}")
            print(f"   ID: {alias.id}")
            print(f"   Note: {alias.note}")
            return 0
        else:
            print("❌ Failed to create alias")
            return 1
            
    elif args.action == "list":
        if args.service:
            aliases = api.get_service_aliases(args.service)
            print(f"Aliases for {args.service}:")
        else:
            aliases = api.get_aliases()
            print("All aliases:")
            
        if aliases:
            for alias in aliases:
                print(f"  {alias['email']} - {alias.get('note', 'No note')}")
        else:
            print("  No aliases found")
        return 0
        
    elif args.action == "info" and args.alias_id:
        info = api.get_alias_info(args.alias_id)
        if info:
            print(f"Alias: {info['email']}")
            print(f"ID: {info['id']}")
            print(f"Enabled: {info['enabled']}")
            print(f"Note: {info.get('note', 'No note')}")
            print(f"Forwards: {info.get('nb_forward', 0)}")
            print(f"Blocks: {info.get('nb_block', 0)}")
            print(f"Replies: {info.get('nb_reply', 0)}")
            return 0
        else:
            print("❌ Alias not found")
            return 1
            
    elif args.action == "search" and args.search:
        aliases = api.search_aliases_by_note(args.search)
        print(f"Search results for '{args.search}':")
        for alias in aliases:
            print(f"  {alias['email']} - {alias.get('note', 'No note')}")
        return 0
        
    elif args.action == "cleanup":
        deleted = api.cleanup_old_aliases(args.days, args.dry_run)
        if args.dry_run:
            print(f"Would delete {len(deleted)} old aliases")
        else:
            print(f"Deleted {len(deleted)} old aliases")
        for email in deleted:
            print(f"  {email}")
        return 0

    elif args.action == "mailboxes":
        mailboxes = api.get_mailboxes()
        if mailboxes:
            print("Available mailboxes:")
            for mailbox in mailboxes:
                verified = "✅" if mailbox.get('verified', False) else "❌"
                default = " (default)" if mailbox.get('default', False) else ""
                print(f"  {verified} {mailbox['email']} (ID: {mailbox['id']}){default}")

            # Check for {{USER_EMAIL}}
            target_id = api.find_mailbox_by_email('{{USER_EMAIL}}')
            if target_id:
                print(f"\n✅ Configured default mailbox found: {{USER_EMAIL}} (ID: {target_id})")
            else:
                print(f"\n⚠️  Configured default mailbox '{{USER_EMAIL}}' not found")
            return 0
        else:
            print("❌ Failed to retrieve mailboxes")
            return 1

    else:
        parser.print_help()
        return 1

if __name__ == "__main__":
    import sys
    sys.exit(main())