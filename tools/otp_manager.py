#!/usr/bin/env python3
"""
Catalyst OTP Manager
TOTP secret generation, QR codes, and Strongbox integration
"""

import secrets
import base64
import qrcode
import io
import logging
from typing import Optional, Tuple, Dict, List
from pathlib import Path
from dataclasses import dataclass
import pyotp
import json
from datetime import datetime

from strongbox_hub import StrongboxHub, CredentialEntry, CredentialType

@dataclass
class OTPConfig:
    """OTP configuration for a service"""
    service: str
    account: str
    secret: str
    issuer: str
    algorithm: str = "SHA1"
    digits: int = 6
    period: int = 30
    backup_codes: List[str] = None
    
    def __post_init__(self):
        if self.backup_codes is None:
            self.backup_codes = []

class OTPManager:
    """Manages TOTP secrets, QR codes, and Strongbox storage"""
    
    def __init__(self, strongbox_hub: Optional[StrongboxHub] = None):
        self.logger = logging.getLogger(__name__)
        self.root_path = Path.home() / "Documents" / "Builder"
        
        # Initialize Strongbox integration
        self.strongbox = strongbox_hub or StrongboxHub()
        if not self.strongbox.initialize():
            self.logger.warning("Strongbox not available - OTP storage disabled")
            
        # QR code storage
        self.qr_storage_path = self.root_path / "global" / "security" / "qr_codes"
        self.qr_storage_path.mkdir(parents=True, exist_ok=True)
        
        # Backup codes storage 
        self.backup_storage_path = self.root_path / "global" / "security" / "backup_codes"
        self.backup_storage_path.mkdir(parents=True, exist_ok=True)
        
    def generate_secret(self, length: int = 32) -> str:
        """Generate cryptographically secure TOTP secret"""
        # Generate random bytes and encode as base32
        secret_bytes = secrets.token_bytes(length)
        secret = base64.b32encode(secret_bytes).decode('utf-8')
        
        # Remove padding for cleaner secret
        return secret.rstrip('=')
        
    def generate_backup_codes(self, count: int = 10) -> List[str]:
        """Generate backup codes for account recovery"""
        codes = []
        for _ in range(count):
            # 8-character alphanumeric codes
            code = ''.join(secrets.choice('ABCDEFGHJKLMNPQRSTUVWXYZ23456789') for _ in range(8))
            codes.append(code)
        return codes
        
    def create_otp_config(self, service: str, account: str, issuer: str = None) -> OTPConfig:
        """Create new OTP configuration"""
        secret = self.generate_secret()
        backup_codes = self.generate_backup_codes()
        
        if issuer is None:
            issuer = service.title()
            
        config = OTPConfig(
            service=service,
            account=account,
            secret=secret,
            issuer=issuer,
            backup_codes=backup_codes
        )
        
        self.logger.info(f"✅ Generated OTP config for {service}:{account}")
        return config
        
    def generate_qr_code(self, otp_config: OTPConfig, save_to_file: bool = True) -> Optional[str]:
        """Generate QR code for TOTP setup"""
        try:
            # Create TOTP URL
            totp = pyotp.TOTP(otp_config.secret)
            provisioning_uri = totp.provisioning_uri(
                name=otp_config.account,
                issuer_name=otp_config.issuer
            )
            
            # Generate QR code
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )
            qr.add_data(provisioning_uri)
            qr.make(fit=True)
            
            # Create image
            img = qr.make_image(fill_color="black", back_color="white")
            
            if save_to_file:
                # Save to file
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"{otp_config.service}_{otp_config.account}_{timestamp}.png"
                filepath = self.qr_storage_path / filename
                
                img.save(filepath)
                self.logger.info(f"✅ QR code saved: {filepath}")
                return str(filepath)
            else:
                # Return as base64 for display
                buffer = io.BytesIO()
                img.save(buffer, format='PNG')
                buffer.seek(0)
                img_data = base64.b64encode(buffer.getvalue()).decode()
                return f"data:image/png;base64,{img_data}"
                
        except Exception as e:
            self.logger.error(f"QR code generation failed: {e}")
            return None
            
    def save_backup_codes(self, otp_config: OTPConfig) -> bool:
        """Save backup codes to secure file"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{otp_config.service}_{otp_config.account}_{timestamp}_backup.json"
            filepath = self.backup_storage_path / filename
            
            backup_data = {
                "service": otp_config.service,
                "account": otp_config.account,
                "issuer": otp_config.issuer,
                "created": datetime.now().isoformat(),
                "backup_codes": otp_config.backup_codes,
                "instructions": [
                    "These codes can be used if you lose access to your authenticator app",
                    "Each code can only be used once",
                    "Store these codes in a secure location separate from your device"
                ]
            }
            
            with open(filepath, 'w') as f:
                json.dump(backup_data, f, indent=2)
                
            # Secure file permissions (owner read/write only)
            filepath.chmod(0o600)
            
            self.logger.info(f"✅ Backup codes saved: {filepath}")
            return True
            
        except Exception as e:
            self.logger.error(f"Backup code storage failed: {e}")
            return False
            
    def store_in_strongbox(self, otp_config: OTPConfig, qr_code_path: Optional[str] = None) -> bool:
        """Store OTP configuration in Strongbox"""
        if not self.strongbox:
            self.logger.error("Strongbox not available")
            return False
            
        try:
            # Create credential entry
            custom_fields = {
                "otp_secret": otp_config.secret,
                "issuer": otp_config.issuer,
                "algorithm": otp_config.algorithm,
                "digits": str(otp_config.digits),
                "period": str(otp_config.period),
                "backup_codes": ",".join(otp_config.backup_codes),
                "created": datetime.now().isoformat(),
                "type": "TOTP"
            }
            
            if qr_code_path:
                custom_fields["qr_code_path"] = qr_code_path
                
            notes = f"""TOTP Configuration for {otp_config.service}
Account: {otp_config.account}
Issuer: {otp_config.issuer}
Secret: {otp_config.secret}

Setup Instructions:
1. Scan QR code with authenticator app
2. Or manually enter secret: {otp_config.secret}
3. Save backup codes separately

Created: {datetime.now().isoformat()}"""
            
            credential = CredentialEntry(
                title=f"TOTP - {otp_config.service}",
                username=otp_config.account,
                password=otp_config.secret,
                url=f"otpauth://totp/{otp_config.issuer}:{otp_config.account}",
                notes=notes,
                custom_fields=custom_fields
            )
            
            # Store in appropriate service folder or OTP folder
            service_key = otp_config.service.lower()
            if service_key in self.strongbox.service_configs:
                success = self.strongbox.store_credential(service_key, f"OTP-{otp_config.account}", credential)
            else:
                # Create generic OTP entry structure
                folder_path = f"Authentication/TOTP/{otp_config.service}"
                # Note: This would require extending StrongboxHub to support custom folder paths
                success = self.strongbox.store_credential("generic", f"{otp_config.service}-OTP", credential)
                
            if success:
                self.logger.info(f"✅ OTP stored in Strongbox: {otp_config.service}:{otp_config.account}")
            return success
            
        except Exception as e:
            self.logger.error(f"Strongbox storage failed: {e}")
            return False
            
    def retrieve_otp_secret(self, service: str, account: str) -> Optional[str]:
        """Retrieve OTP secret from Strongbox"""
        if not self.strongbox:
            return None
            
        try:
            service_key = service.lower()
            if service_key in self.strongbox.service_configs:
                credential = self.strongbox.retrieve_credential(service_key, f"OTP-{account}")
            else:
                credential = self.strongbox.retrieve_credential("generic", f"{service}-OTP")
                
            if credential and credential.custom_fields:
                return credential.custom_fields.get("otp_secret")
                
        except Exception as e:
            self.logger.error(f"OTP retrieval failed: {e}")
            
        return None
        
    def generate_current_code(self, secret: str) -> Optional[str]:
        """Generate current TOTP code from secret"""
        try:
            totp = pyotp.TOTP(secret)
            return totp.now()
        except Exception as e:
            self.logger.error(f"TOTP generation failed: {e}")
            return None
            
    def verify_code(self, secret: str, code: str, window: int = 1) -> bool:
        """Verify TOTP code"""
        try:
            totp = pyotp.TOTP(secret)
            return totp.verify(code, window=window)
        except Exception as e:
            self.logger.error(f"TOTP verification failed: {e}")
            return False
            
    def setup_service_otp(self, service: str, account: str, issuer: str = None) -> Tuple[bool, Dict[str, str]]:
        """Complete OTP setup for a service"""
        result = {
            "secret": "",
            "qr_code_path": "",
            "backup_codes_path": "",
            "strongbox_stored": False
        }
        
        try:
            # Generate OTP config
            otp_config = self.create_otp_config(service, account, issuer)
            result["secret"] = otp_config.secret
            
            # Generate and save QR code
            qr_path = self.generate_qr_code(otp_config, save_to_file=True)
            if qr_path:
                result["qr_code_path"] = qr_path
                
            # Save backup codes
            if self.save_backup_codes(otp_config):
                result["backup_codes_path"] = str(self.backup_storage_path)
                
            # Store in Strongbox
            if self.store_in_strongbox(otp_config, qr_path):
                result["strongbox_stored"] = True
                
            self.logger.info(f"✅ Complete OTP setup for {service}:{account}")
            return True, result
            
        except Exception as e:
            self.logger.error(f"OTP setup failed: {e}")
            return False, result
            
    def list_otp_entries(self) -> List[Dict[str, str]]:
        """List all OTP entries"""
        entries = []
        
        if not self.strongbox:
            return entries
            
        try:
            # Search for TOTP entries
            otp_entries = self.strongbox.search_entries("TOTP")
            
            for entry_path in otp_entries:
                # Parse entry details
                parts = entry_path.split("/")
                if len(parts) >= 2:
                    service = parts[-2] if len(parts) > 2 else "Unknown"
                    account = parts[-1].replace("TOTP - ", "")
                    
                    entries.append({
                        "service": service,
                        "account": account,
                        "path": entry_path
                    })
                    
        except Exception as e:
            self.logger.error(f"Failed to list OTP entries: {e}")
            
        return entries
        
    def cleanup_old_files(self, days: int = 30) -> bool:
        """Clean up old QR codes and backup files"""
        try:
            from datetime import timedelta
            cutoff_date = datetime.now() - timedelta(days=days)
            
            cleaned_count = 0
            
            # Clean QR codes
            for qr_file in self.qr_storage_path.glob("*.png"):
                if datetime.fromtimestamp(qr_file.stat().st_mtime) < cutoff_date:
                    qr_file.unlink()
                    cleaned_count += 1
                    
            # Clean backup code files  
            for backup_file in self.backup_storage_path.glob("*_backup.json"):
                if datetime.fromtimestamp(backup_file.stat().st_mtime) < cutoff_date:
                    backup_file.unlink()
                    cleaned_count += 1
                    
            self.logger.info(f"✅ Cleaned up {cleaned_count} old OTP files")
            return True
            
        except Exception as e:
            self.logger.error(f"Cleanup failed: {e}")
            return False

def main():
    """CLI interface for OTP Manager"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Catalyst OTP Manager")
    parser.add_argument("action", choices=["setup", "get-code", "verify", "list", "cleanup"])
    parser.add_argument("--service", help="Service name")
    parser.add_argument("--account", help="Account/username") 
    parser.add_argument("--issuer", help="Issuer name (optional)")
    parser.add_argument("--code", help="Code to verify")
    parser.add_argument("--secret", help="TOTP secret")
    parser.add_argument("--days", type=int, default=30, help="Days for cleanup")
    
    args = parser.parse_args()
    
    otp_manager = OTPManager()
    
    if args.action == "setup" and args.service and args.account:
        success, result = otp_manager.setup_service_otp(args.service, args.account, args.issuer)
        if success:
            print(f"✅ OTP setup complete for {args.service}:{args.account}")
            print(f"Secret: {result['secret']}")
            print(f"QR Code: {result['qr_code_path']}")
            print(f"Backup Codes: {result['backup_codes_path']}")
            print(f"Strongbox: {'✅' if result['strongbox_stored'] else '❌'}")
            return 0
        else:
            print("❌ OTP setup failed")
            return 1
            
    elif args.action == "get-code":
        if args.secret:
            code = otp_manager.generate_current_code(args.secret)
        elif args.service and args.account:
            secret = otp_manager.retrieve_otp_secret(args.service, args.account)
            code = otp_manager.generate_current_code(secret) if secret else None
        else:
            print("❌ Need either --secret or --service and --account")
            return 1
            
        if code:
            print(f"Current TOTP code: {code}")
            return 0
        else:
            print("❌ Failed to generate code")
            return 1
            
    elif args.action == "verify" and args.secret and args.code:
        if otp_manager.verify_code(args.secret, args.code):
            print("✅ Code is valid")
            return 0
        else:
            print("❌ Code is invalid")
            return 1
            
    elif args.action == "list":
        entries = otp_manager.list_otp_entries()
        print("OTP Entries:")
        for entry in entries:
            print(f"  {entry['service']}:{entry['account']} - {entry['path']}")
        return 0
        
    elif args.action == "cleanup":
        if otp_manager.cleanup_old_files(args.days):
            print(f"✅ Cleaned up files older than {args.days} days")
            return 0
        else:
            print("❌ Cleanup failed")
            return 1
            
    else:
        parser.print_help()
        return 1

if __name__ == "__main__":
    import sys
    sys.exit(main())