#!/Library/Frameworks/Python.framework/Versions/3.11/bin/python3
"""
Catalyst Account Creator
Unified workflow for automated account creation using Simple Login + Strongbox + Playwright
"""

import logging
import json
from typing import Optional, Dict, Any, Tuple, List
from pathlib import Path
from dataclasses import dataclass
from datetime import datetime

from simple_login_api import SimpleLoginAPI, AliasInfo
from strongbox_cli import StrongboxCLI, CredentialEntry

# Import async support
import asyncio

# Optional: CAPTCHA solver (may not be available in Python 3.14+ due to aifc removal)
try:
    from universal_captcha_solver import UniversalCaptchaSolver, CaptchaType
    CAPTCHA_SOLVER_AVAILABLE = True
except (ImportError, ModuleNotFoundError) as e:
    logging.warning(f"CAPTCHA solver not available (Python 3.14+ compatibility issue): {e}")
    CAPTCHA_SOLVER_AVAILABLE = False
    # Create dummy types for compatibility
    class CaptchaType:
        RECAPTCHA_V2 = "recaptcha_v2"
        RECAPTCHA_V3 = "recaptcha_v3"
    UniversalCaptchaSolver = None

# Import hybrid browser for Playwright + SeleniumBase
from hybrid_browser import HybridBrowser, BrowserConfig

@dataclass
class AccountCreationResult:
    """Result of account creation process"""
    success: bool
    service: str
    purpose: str
    username: str = ""
    email: str = ""
    password: str = ""
    totp_code: str = ""
    strongbox_path: str = ""
    alias_id: Optional[int] = None
    error_message: str = ""
    playwright_used: bool = False

class AccountCreator:
    """Unified account creation workflow"""
    
    def __init__(self, simple_login_api_key: Optional[str] = None,
                 strongbox_password: Optional[str] = None):
        self.logger = logging.getLogger(__name__)
        self.root_path = Path.home() / "Documents" / "Builder"

        # Initialize integrations
        try:
            self.simple_login = SimpleLoginAPI(simple_login_api_key)
        except ValueError as e:
            self.logger.warning(f"Simple Login not available: {e}")
            self.simple_login = None

        self.strongbox = StrongboxCLI(master_password=strongbox_password)

        # Hybrid browser automation (Playwright + SeleniumBase)
        self.hybrid_browser = HybridBrowser()

        # Playwright integration (if available)
        self.playwright_available = self._check_playwright_mcp()
        
        # Service configuration for account creation
        self.service_configs = {
            "github": {
                "signup_url": "https://github.com/signup",
                "username_field": "user[login]",
                "email_field": "user[email]",
                "password_field": "user[password]",
                "requires_verification": True,
                "supports_totp": True,
                "use_stealth": False  # GitHub is cooperative
            },
            "gitlab": {
                "signup_url": "https://gitlab.com/users/sign_up",
                "username_field": "new_user[username]",
                "email_field": "new_user[email]",
                "password_field": "new_user[password]",
                "requires_verification": True,
                "supports_totp": True,
                "use_stealth": False  # GitLab is cooperative
            },
            "openai": {
                "signup_url": "https://platform.openai.com/signup",
                "email_field": "email",
                "password_field": "password",
                "requires_verification": True,
                "supports_totp": False,
                "use_stealth": False  # OpenAI is cooperative
            },
            "shopify": {
                "signup_url": "https://accounts.shopify.com/signup",
                "email_field": "account[email]",
                "password_field": "account[password]",
                "requires_verification": True,
                "supports_totp": True,
                "use_stealth": False  # Shopify is cooperative
            },
            "instagram": {
                "signup_url": "https://www.instagram.com/accounts/emailsignup/",
                "username_field": "username",
                "email_field": "emailOrPhone",
                "password_field": "password",
                "requires_verification": True,
                "supports_totp": True,
                "use_stealth": True  # Instagram needs stealth + anti-detection
            }
        }
        
    def _check_playwright_mcp(self) -> bool:
        """Check if Playwright MCP is available"""
        # This would check MCP configuration
        # For now, assume it's available if we're in Catalyst
        mcp_config_path = self.root_path / "global" / "claude-config" / "playwright-mcp-config.json"
        return mcp_config_path.exists()

    def _get_browser_mode(self, service: str) -> str:
        """Determine which browser mode to use for service"""
        config = self.service_configs.get(service.lower(), {})

        # Check if service explicitly requires stealth
        if config.get('use_stealth', False):
            self.logger.info(f"🔒 Using SeleniumBase stealth mode for {service}")
            return "seleniumbase"

        # Auto-detect based on URL
        signup_url = config.get('signup_url', '')
        if signup_url and self.hybrid_browser.should_use_stealth(signup_url):
            self.logger.info(f"🔒 Auto-detected stealth needed for {service}")
            return "seleniumbase"

        # Default to Playwright
        self.logger.info(f"⚡ Using Playwright for {service}")
        return "playwright"
        
    def create_account_manual(self, service: str, purpose: str, username: str = "", 
                            custom_email: str = "", enable_totp: bool = False) -> AccountCreationResult:
        """Create account with manual credential entry (no Playwright)"""
        
        result = AccountCreationResult(
            success=False,
            service=service,
            purpose=purpose,
            username=username
        )
        
        try:
            # Step 1: Create Simple Login alias
            email_to_use = custom_email
            alias_info = None
            
            if not custom_email and self.simple_login:
                self.logger.info(f"Creating Simple Login alias for {service}:{purpose}")
                alias_info = self.simple_login.create_alias_for_service(service, purpose)
                
                if alias_info:
                    email_to_use = alias_info.email
                    result.alias_id = alias_info.id
                    self.logger.info(f"✅ Created alias: {email_to_use}")
                else:
                    result.error_message = "Failed to create Simple Login alias"
                    return result
            elif not custom_email:
                result.error_message = "No email provided and Simple Login not available"
                return result
                
            result.email = email_to_use
            
            # Step 2: Create account entry in Strongbox
            self.logger.info(f"Creating Strongbox entry for {service}:{purpose}")
            
            success, strongbox_result = self.strongbox.create_account_entry(
                service=service,
                purpose=purpose,
                email_alias=email_to_use,  # Email alias becomes the username in Strongbox
                additional_notes=f"Created for {service} {purpose} via Catalyst",
                enable_totp=enable_totp
            )
            
            if success:
                result.username = strongbox_result["username"]
                result.password = strongbox_result["password"]
                result.strongbox_path = strongbox_result["entry_path"]
                result.totp_code = strongbox_result.get("totp_code", "")
                result.success = True
                
                self.logger.info(f"✅ Account creation complete")
                self.logger.info(f"   Email: {result.email}")
                self.logger.info(f"   Username: {result.username}")
                self.logger.info(f"   Strongbox: {result.strongbox_path}")
                
            else:
                result.error_message = "Failed to create Strongbox entry"
                
        except Exception as e:
            self.logger.error(f"Account creation failed: {e}")
            result.error_message = str(e)
            
        return result
        
    def create_account_automated(self, service: str, purpose: str, username: str = "",
                               enable_totp: bool = False) -> AccountCreationResult:
        """Create account with Playwright automation"""

        result = AccountCreationResult(
            success=False,
            service=service,
            purpose=purpose,
            username=username,
            playwright_used=True
        )

        if not self.playwright_available:
            self.logger.warning("Playwright not available, falling back to manual creation")
            return self.create_account_manual(service, purpose, username, "", enable_totp)

        # Note: Even without CAPTCHA solver, we can use SeleniumBase UC mode which bypasses most CAPTCHAs
        if not CAPTCHA_SOLVER_AVAILABLE:
            self.logger.info("Using SeleniumBase UC mode for CAPTCHA bypass (playwright-recaptcha not available)")
            
        if service.lower() not in self.service_configs:
            result.error_message = f"Automated signup not supported for {service}"
            return result
            
        try:
            # Step 1: Create Simple Login alias
            alias_info = None
            if self.simple_login:
                self.logger.info(f"Creating Simple Login alias for {service}:{purpose}")
                alias_info = self.simple_login.create_alias_for_service(service, purpose)
                
                if not alias_info:
                    result.error_message = "Failed to create Simple Login alias"
                    return result
                    
                result.email = alias_info.email
                result.alias_id = alias_info.id
                self.logger.info(f"✅ Created alias: {result.email}")
            else:
                result.error_message = "Simple Login not available for automated signup"
                return result
                
            # Step 2: Create Strongbox entry with Strongbox-generated password
            username_to_use = username or result.email.split('@')[0]
            
            # Let Strongbox generate the password internally
            success, strongbox_result = self.strongbox.create_account_entry(
                service=service,
                purpose=purpose,
                email_alias=result.email,  # Email alias becomes the username in Strongbox
                additional_notes=f"Automated account creation for {service} {purpose}",
                generated_password=None,  # Let Strongbox generate it
                enable_totp=enable_totp
            )
            
            if not success:
                result.error_message = "Failed to create Strongbox entry"
                return result
                
            result.username = strongbox_result["username"]
            result.password = strongbox_result["password"]
            result.strongbox_path = strongbox_result["entry_path"]
            result.totp_code = strongbox_result.get("totp_code", "")
            
            # Step 3: Use Playwright to create account
            signup_success = self._playwright_signup(service, result)
            
            if signup_success:
                result.success = True
                self.logger.info(f"✅ Automated account creation complete")
                self.logger.info(f"   Service: {service}")
                self.logger.info(f"   Email: {result.email}")
                self.logger.info(f"   Username: {result.username}")
                self.logger.info(f"   Strongbox: {result.strongbox_path}")
            else:
                result.error_message = "Playwright signup automation failed"
                
        except Exception as e:
            self.logger.error(f"Automated account creation failed: {e}")
            result.error_message = str(e)
            
        return result
        
    def _playwright_signup(self, service: str, account_info: AccountCreationResult) -> bool:
        """
        Use hybrid browser automation for signup

        Strategy:
        - Playwright MCP: Cooperative sites (GitHub, GitLab, OpenAI, Shopify)
        - SeleniumBase: Anti-bot sites (Instagram, Facebook, Twitter)
        """

        config = self.service_configs.get(service.lower())
        if not config:
            self.logger.error(f"No configuration found for service: {service}")
            return False

        # Determine which browser mode to use
        browser_mode = self._get_browser_mode(service)

        self.logger.info(f"🚀 Starting automated signup for {service} using {browser_mode}")

        if browser_mode == "seleniumbase":
            # Use SeleniumBase for stealth/CAPTCHA scenarios
            return self._seleniumbase_signup(service, config, account_info)
        else:
            # Use Playwright MCP for cooperative sites
            try:
                result = asyncio.run(self._async_playwright_signup(service, config, account_info))
                return result
            except Exception as e:
                self.logger.error(f"Playwright automation failed: {e}")
                return False

    def _seleniumbase_signup(self, service: str, config: Dict[str, Any],
                            account_info: AccountCreationResult) -> bool:
        """
        Use SeleniumBase for stealth account creation

        This handles sites with aggressive bot detection:
        - Instagram, Facebook, Twitter, etc.
        - Built-in stealth mode (UC mode)
        - CAPTCHA solving capabilities
        """

        self.logger.info(f"🔒 Using SeleniumBase stealth mode for {service}")

        # Prepare account data
        account_data = {
            'email': account_info.email,
            'password': account_info.password,
            'username': account_info.username or account_info.email.split('@')[0]
        }

        # Use hybrid browser to execute signup
        result = self.hybrid_browser.create_account(
            url=config['signup_url'],
            account_data=account_data,
            mode="seleniumbase"
        )

        if result.get('success'):
            self.logger.info(f"✅ SeleniumBase signup successful for {service}")
            return True
        else:
            self.logger.error(f"❌ SeleniumBase signup failed: {result.get('error', 'Unknown error')}")
            return False

    async def _async_playwright_signup(
        self,
        service: str,
        config: Dict[str, Any],
        account_info: AccountCreationResult
    ) -> bool:
        """
        Async Playwright automation with universal CAPTCHA solving

        This is the real implementation that:
        1. Creates stealth browser
        2. Navigates to signup page
        3. Fills form with human-like behavior
        4. Detects and solves any CAPTCHA (reCAPTCHA v2/v3, hCaptcha, Turnstile)
        5. Submits form and verifies success
        """

        # Initialize CAPTCHA solver with Chromium (best for bot detection)
        captcha_solver = UniversalCaptchaSolver(
            headless=False,  # Visible browser for better success
            stealth_enabled=True,
            timeout=30,
            max_retries=2,
            browser="chromium"  # Chromium best for stealth (no Brave shields interference)
        )

        browser, page = await captcha_solver.create_stealth_browser()

        try:
            # Step 1: Navigate to signup page
            self.logger.info(f"📍 Navigating to {config['signup_url']}")
            await page.goto(config['signup_url'], wait_until='networkidle')
            await asyncio.sleep(random.uniform(1, 3))  # Human-like delay

            # Step 2: Fill form fields with human-like typing
            self.logger.info("✍️  Filling signup form...")

            # Email field
            if 'email_field' in config:
                try:
                    await captcha_solver.human_type(
                        page,
                        f'input[name="{config["email_field"]}"], input[type="email"], #email',
                        account_info.email
                    )
                    await asyncio.sleep(random.uniform(0.5, 1.5))
                except Exception as e:
                    self.logger.warning(f"Email field fill error: {e}")

            # Username field (if required)
            if 'username_field' in config and account_info.username:
                try:
                    await captcha_solver.human_type(
                        page,
                        f'input[name="{config["username_field"]}"], #username',
                        account_info.username
                    )
                    await asyncio.sleep(random.uniform(0.5, 1.5))
                except Exception as e:
                    self.logger.warning(f"Username field fill error: {e}")

            # Password field
            if 'password_field' in config:
                try:
                    await captcha_solver.human_type(
                        page,
                        f'input[name="{config["password_field"]}"], input[type="password"], #password',
                        account_info.password
                    )
                    await asyncio.sleep(random.uniform(0.5, 1.5))
                except Exception as e:
                    self.logger.warning(f"Password field fill error: {e}")

            # Step 3: Detect and solve CAPTCHA
            self.logger.info("🔍 Checking for CAPTCHA...")
            captcha_result = await captcha_solver.solve(page)

            if captcha_result.captcha_type != CaptchaType.NONE:
                if captcha_result.success:
                    self.logger.info(f"✓ {captcha_result.captcha_type.value} solved in {captcha_result.time_taken:.1f}s")
                else:
                    self.logger.error(f"✗ CAPTCHA solve failed: {captcha_result.error}")
                    # Take screenshot for debugging
                    screenshot_path = f"/tmp/{service}_captcha_failed.png"
                    await page.screenshot(path=screenshot_path)
                    self.logger.info(f"📸 Screenshot saved to {screenshot_path}")
                    return False
            else:
                self.logger.info("✓ No CAPTCHA detected")

            # Step 4: Submit form
            self.logger.info("📤 Submitting signup form...")
            try:
                # Try common submit button selectors
                submit_selectors = [
                    'button[type="submit"]',
                    'input[type="submit"]',
                    'button:has-text("Sign up")',
                    'button:has-text("Create")',
                    'button:has-text("Continue")',
                    '.btn-primary'
                ]

                for selector in submit_selectors:
                    try:
                        await page.click(selector, timeout=2000)
                        self.logger.info(f"✓ Clicked submit: {selector}")
                        break
                    except:
                        continue
                else:
                    # If no button found, try Enter key
                    await page.keyboard.press('Enter')
                    self.logger.info("⌨️  Submitted via Enter key")

            except Exception as e:
                self.logger.error(f"Submit error: {e}")
                return False

            # Step 5: Wait for navigation and verify success
            self.logger.info("⏳ Waiting for account creation confirmation...")
            await asyncio.sleep(5)  # Allow time for processing

            # Check for success indicators
            current_url = page.url
            success_patterns = {
                'github': ['/welcome', '/dashboard', 'session'],
                'gitlab': ['/users/confirmation', '/dashboard'],
                'openai': ['/playground', '/usage', 'api-keys'],
                'shopify': ['/admin', '/store', 'myshopify'],
                'instagram': ['/accounts/onetap', '/']
            }

            patterns = success_patterns.get(service.lower(), [])
            success = any(pattern in current_url.lower() for pattern in patterns)

            if success:
                self.logger.info(f"✅ Account creation appears successful! URL: {current_url}")
            else:
                # Check for error messages
                error_text = await page.evaluate("""
                    () => {
                        const errors = document.querySelectorAll('.error, .alert-error, [role="alert"]');
                        return Array.from(errors).map(e => e.textContent.trim()).join('; ');
                    }
                """)

                if error_text:
                    self.logger.warning(f"⚠ Possible errors on page: {error_text}")

                # Take screenshot for manual review
                screenshot_path = f"/tmp/{service}_signup_result.png"
                await page.screenshot(path=screenshot_path)
                self.logger.info(f"📸 Result screenshot: {screenshot_path}")

                self.logger.warning(f"⚠ Account creation uncertain. Current URL: {current_url}")
                success = False

            # Wait to allow user to see result
            if not success:
                await asyncio.sleep(10)

            return success

        except Exception as e:
            self.logger.exception(f"Automation error: {e}")
            # Take error screenshot
            try:
                screenshot_path = f"/tmp/{service}_error.png"
                await page.screenshot(path=screenshot_path)
                self.logger.info(f"📸 Error screenshot: {screenshot_path}")
            except:
                pass
            return False

        finally:
            await browser.close()
        
    def verify_account_access(self, service: str, purpose: str) -> bool:
        """Verify we can access the created account"""
        credential = self.strongbox.get_credential(service, purpose)
        
        if not credential:
            self.logger.error(f"No credentials found for {service}:{purpose}")
            return False
            
        # TODO: Implement service-specific verification
        # This could involve:
        # - API calls to verify credentials
        # - Login attempts via Playwright
        # - Email verification checks
        
        self.logger.info(f"Credentials exist for {service}:{purpose}")
        return True
        
    def cleanup_failed_creation(self, result: AccountCreationResult):
        """Clean up resources from failed account creation"""
        self.logger.info(f"Cleaning up failed account creation for {result.service}:{result.purpose}")
        
        # Delete Simple Login alias if created
        if result.alias_id and self.simple_login:
            try:
                self.simple_login.delete_alias(result.alias_id)
                self.logger.info(f"✅ Deleted Simple Login alias: {result.email}")
            except Exception as e:
                self.logger.error(f"Failed to delete alias: {e}")
                
        # TODO: Remove Strongbox entry if created
        # KeePassXC CLI doesn't have a simple delete command
        # Would need to implement this separately
        
    def list_created_accounts(self, service: Optional[str] = None) -> List[Dict[str, str]]:
        """List accounts created by this system"""
        accounts = []
        
        if service:
            services_to_check = [service]
        else:
            services_to_check = list(self.service_configs.keys())
            
        for svc in services_to_check:
            entries = self.strongbox.list_service_entries(svc)
            for entry in entries:
                # Parse entry to extract purpose
                if " - " in entry:
                    title_part = entry.split(" - ", 1)[1]
                    accounts.append({
                        "service": svc,
                        "purpose": title_part,
                        "entry_path": entry
                    })
                    
        return accounts
        
    def get_account_info(self, service: str, purpose: str) -> Optional[Dict[str, Any]]:
        """Get complete account information"""
        credential = self.strongbox.get_credential(service, purpose)
        
        if not credential:
            return None
            
        info = {
            "service": service,
            "purpose": purpose,
            "username": credential.username,
            "email": credential.custom_fields.get("email", ""),
            "password": credential.password,
            "url": credential.url,
            "notes": credential.notes,
            "strongbox_path": credential.title,
            "has_totp": bool(credential.totp_secret),
            "created_via_builder": "Catalyst" in credential.notes
        }
        
        # Get current TOTP code if available
        totp_code = self.strongbox.get_totp_code(service, purpose)
        if totp_code:
            info["current_totp_code"] = totp_code
            
        return info

def main():
    """CLI interface for Account Creator"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Catalyst Account Creator")
    parser.add_argument("action", choices=[
        "create", "create-auto", "verify", "list", "info", "cleanup"
    ])
    parser.add_argument("--service", required=True, help="Service name")
    parser.add_argument("--purpose", required=True, help="Purpose/identifier")
    parser.add_argument("--username", help="Username (optional)")
    parser.add_argument("--email", help="Custom email (skips Simple Login)")
    parser.add_argument("--enable-totp", action="store_true", help="Enable TOTP")
    
    args = parser.parse_args()
    
    creator = AccountCreator()
    
    if args.action == "create":
        result = creator.create_account_manual(
            args.service, args.purpose, args.username or "",
            args.email or "", args.enable_totp
        )
        
        if result.success:
            print(f"✅ Account created successfully")
            print(f"Service: {result.service}")
            print(f"Purpose: {result.purpose}")  
            print(f"Email: {result.email}")
            print(f"Username: {result.username}")
            print(f"Password: {result.password}")
            if result.totp_code:
                print(f"TOTP Code: {result.totp_code}")
            print(f"Strongbox: {result.strongbox_path}")
            return 0
        else:
            print(f"❌ Account creation failed: {result.error_message}")
            return 1
            
    elif args.action == "create-auto":
        result = creator.create_account_automated(
            args.service, args.purpose, args.username or "", args.enable_totp
        )
        
        if result.success:
            print(f"✅ Automated account creation successful")
            print(f"Service: {result.service}")
            print(f"Email: {result.email}")
            print(f"Username: {result.username}")
            if result.totp_code:
                print(f"TOTP Code: {result.totp_code}")
            print(f"Strongbox: {result.strongbox_path}")
            return 0
        else:
            print(f"❌ Automated creation failed: {result.error_message}")
            if not result.playwright_used:
                print("Fell back to manual creation")
            return 1
            
    elif args.action == "verify":
        success = creator.verify_account_access(args.service, args.purpose)
        return 0 if success else 1
        
    elif args.action == "list":
        accounts = creator.list_created_accounts(args.service)
        print(f"Created accounts:")
        for account in accounts:
            print(f"  {account['service']} - {account['purpose']}")
        return 0
        
    elif args.action == "info":
        info = creator.get_account_info(args.service, args.purpose)
        if info:
            print(f"Account Info:")
            for key, value in info.items():
                if key != "password":  # Don't print password in CLI
                    print(f"  {key}: {value}")
            return 0
        else:
            print(f"❌ No account found for {args.service}:{args.purpose}")
            return 1
            
    else:
        parser.print_help()
        return 1

if __name__ == "__main__":
    import sys
    sys.exit(main())