#!/usr/bin/env python3
"""
TikTok Unified CLI for Catalyst

Covers TikTok Shop, Marketing (Ads), and Content Posting APIs for
multi-brand e-commerce operations.

Three API surfaces:
  - Shop:      Product catalog, orders, inventory, fulfillment
  - Marketing: Campaigns, ad groups, ads, audiences, reporting
  - Content:   Creator info, video posting, upload, status

Credentials:
    Per-brand credentials loaded from:
      1. capsules/ecommerce/brands/{brand}/.env
      2. capsules/ecommerce/.env
      3. Environment variables
      4. macOS Keychain

Dependencies: Python stdlib only (no pip packages).

Version: 0.1.0
"""

import argparse
import hashlib
import hmac
import json
import logging
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
VERSION = "0.1.0"
def _find_catalyst_root() -> Path:
    """Resolve Catalyst root reliably, even when invoked through symlinks."""
    # 1. Explicit env var (highest priority)
    env = os.environ.get("CATALYST_ROOT")
    if env:
        return Path(env)
    # 2. git rev-parse (works from any depth inside the repo)
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode == 0:
            return Path(result.stdout.strip())
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    # 3. Walk up from the *unresolved* script path looking for .git sentinel
    anchor = Path(__file__).parent
    for parent in [anchor, *anchor.parents]:
        if (parent / ".git").exists():
            return parent
    # 4. Last resort — original (broken under symlinks, but better than nothing)
    return Path(__file__).resolve().parent.parent


CATALYST_ROOT = _find_catalyst_root()
ECOMMERCE_DIR = CATALYST_ROOT / "capsules" / "ecommerce"
BRANDS_DIR = ECOMMERCE_DIR / "brands"

# ---------------------------------------------------------------------------
# Terminal colours
# ---------------------------------------------------------------------------
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
BOLD = "\033[1m"
DIM = "\033[2m"
RESET = "\033[0m"

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class TikTokError(Exception):
    """Base exception for all TikTok errors."""


class TikTokCredentialError(TikTokError):
    """Could not load credentials from env, .env, or Keychain."""


class TikTokAuthError(TikTokError):
    """Authentication or token error."""


class TikTokShopAPIError(TikTokError):
    """TikTok Shop API returned an error."""

    def __init__(self, message: str, code: int = 0, request_id: str = ""):
        self.code = code
        self.request_id = request_id
        super().__init__(message)


class TikTokMarketingAPIError(TikTokError):
    """TikTok Marketing API returned an error."""

    def __init__(self, message: str, code: int = 0, request_id: str = ""):
        self.code = code
        self.request_id = request_id
        super().__init__(message)


class TikTokContentAPIError(TikTokError):
    """TikTok Content API returned an error."""


class TikTokRateLimitError(TikTokError):
    """Rate limit exceeded."""

    def __init__(self, message: str, retry_after: int = 0):
        self.retry_after = retry_after
        super().__init__(message)


class TikTokTokenExpiredError(TikTokAuthError):
    """OAuth token has expired and needs refresh."""


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class ShopStatus:
    shop_id: str
    shop_name: str
    region: str
    status: str

@dataclass
class ProductSummary:
    product_id: str
    title: str
    status: str
    create_time: int = 0
    update_time: int = 0

@dataclass
class ProductDetail:
    product_id: str
    title: str
    description: str
    status: str
    category_id: str = ""
    skus: List[Dict[str, Any]] = field(default_factory=list)
    images: List[str] = field(default_factory=list)
    create_time: int = 0
    update_time: int = 0

@dataclass
class OrderSummary:
    order_id: str
    status: str
    total_amount: str
    currency: str = "USD"
    create_time: int = 0

@dataclass
class OrderDetail:
    order_id: str
    status: str
    total_amount: str
    currency: str = "USD"
    buyer_message: str = ""
    shipping_provider: str = ""
    tracking_number: str = ""
    items: List[Dict[str, Any]] = field(default_factory=list)
    create_time: int = 0
    update_time: int = 0

@dataclass
class InventoryItem:
    sku_id: str
    seller_sku: str
    quantity: int
    warehouse_id: str = ""

@dataclass
class CampaignSummary:
    campaign_id: str
    campaign_name: str
    objective_type: str
    status: str
    budget: float = 0.0
    budget_mode: str = ""

@dataclass
class AdGroupSummary:
    adgroup_id: str
    adgroup_name: str
    campaign_id: str
    status: str
    budget: float = 0.0

@dataclass
class AdSummary:
    ad_id: str
    ad_name: str
    adgroup_id: str
    status: str
    ad_format: str = ""

@dataclass
class ReportRow:
    dimensions: Dict[str, str] = field(default_factory=dict)
    metrics: Dict[str, Any] = field(default_factory=dict)

@dataclass
class CreatorInfo:
    creator_nickname: str
    creator_avatar_url: str
    is_union_enabled: bool = False
    max_video_post_duration_sec: int = 0
    privacy_level_options: List[str] = field(default_factory=list)

@dataclass
class PostStatus:
    publish_id: str
    status: str
    uploaded_bytes: int = 0
    error_code: str = ""
    error_message: str = ""

# ---------------------------------------------------------------------------
# Display helpers (from proton_mail.py)
# ---------------------------------------------------------------------------

def _visible_len(s: str) -> int:
    """Length of string excluding ANSI escape codes."""
    return len(re.sub(r"\033\[[0-9;]*m", "", s))


def _format_table(headers: List[str], rows: List[List[str]], separator: str = "\u2502") -> str:
    """Format a table with box-drawing separators."""
    if not rows:
        return "  (no results)"

    col_widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            if i < len(col_widths):
                col_widths[i] = max(col_widths[i], _visible_len(str(cell)))

    def _pad(text: str, width: int) -> str:
        pad = width - _visible_len(text)
        return text + " " * max(0, pad)

    header_parts = [_pad(h, col_widths[i]) for i, h in enumerate(headers)]
    header_line = f" {separator} ".join(header_parts)

    sep_parts = ["\u2500" * (w + 1) for w in col_widths]
    sep_line = f"\u2500{separator}\u2500".join(sep_parts)

    lines = [f" {header_line}", f" {sep_line}"]

    for row in rows:
        parts = []
        for i in range(len(headers)):
            cell = str(row[i] if i < len(row) else "")
            parts.append(_pad(cell, col_widths[i]))
        lines.append(f" {f' {separator} '.join(parts)}")

    return "\n".join(lines)


def _json_output(data: Any) -> None:
    """Print JSON-formatted output."""
    print(json.dumps(data, indent=2, default=str))


def _dc_to_dict(obj) -> dict:
    """Convert a dataclass to a dict for JSON output."""
    return asdict(obj)


def _truncate(s: str, max_len: int) -> str:
    """Truncate string with ellipsis if too long."""
    if _visible_len(s) <= max_len:
        return s
    return s[:max_len - 1] + "\u2026"


def _ts_to_str(ts: int) -> str:
    """Convert Unix timestamp to readable local time string."""
    if not ts:
        return ""
    try:
        dt = datetime.fromtimestamp(ts)
        return dt.strftime("%Y-%m-%d %H:%M")
    except Exception:
        return str(ts)


# ---------------------------------------------------------------------------
# Credential Loading
# ---------------------------------------------------------------------------

class BrandCredentialLoader:
    """
    Multi-source credential loader for per-brand TikTok credentials.

    Resolution order:
      1. Brand .env: capsules/ecommerce/brands/{brand}/.env
      2. Capsule .env: capsules/ecommerce/.env
      3. Environment variables
      4. macOS Keychain via `security find-generic-password`
    """

    def __init__(self, brand: str):
        self.brand = brand
        self._cache: Dict[str, str] = {}
        self._env_loaded = False

    def _load_env_files(self) -> None:
        """Load .env files into cache (brand-specific overrides capsule-level)."""
        if self._env_loaded:
            return
        self._env_loaded = True

        # Capsule .env (lower priority)
        capsule_env = ECOMMERCE_DIR / ".env"
        if capsule_env.is_file():
            self._parse_env(capsule_env)

        # Brand .env (higher priority, overwrites capsule)
        brand_env = BRANDS_DIR / self.brand / ".env"
        if brand_env.is_file():
            self._parse_env(brand_env)

    def _parse_env(self, path: Path) -> None:
        """Parse a .env file into the cache."""
        try:
            with open(path, "r") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    if "=" in line:
                        key, _, value = line.partition("=")
                        key = key.strip()
                        value = value.strip().strip("'\"")
                        self._cache[key] = value
                        logger.debug("Loaded %s from %s", key, path)
        except Exception as e:
            logger.debug("Failed to parse %s: %s", path, e)

    def _keychain_read(self, service: str) -> Optional[str]:
        """Read a password from macOS Keychain."""
        try:
            result = subprocess.run(
                ["security", "find-generic-password", "-s", service, "-w"],
                capture_output=True, text=True, timeout=5,
            )
            if result.returncode == 0 and result.stdout.strip():
                logger.debug("Keychain read OK for service '%s'", service)
                return result.stdout.strip()
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError) as e:
            logger.debug("Keychain lookup failed for '%s': %s", service, e)
        return None

    @staticmethod
    def keychain_write(service: str, account: str, password: str) -> bool:
        """Write or update a password in macOS Keychain."""
        try:
            result = subprocess.run(
                ["security", "add-generic-password",
                 "-s", service, "-a", account, "-w", password, "-U"],
                capture_output=True, text=True, timeout=5,
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError) as e:
            logger.debug("Keychain write failed for '%s': %s", service, e)
            return False

    def get(self, env_key: str, keychain_service: Optional[str] = None) -> Optional[str]:
        """
        Get a credential value from the resolution chain.

        Args:
            env_key: Environment variable name (also checked in .env files).
            keychain_service: Optional Keychain service name to try last.
        """
        self._load_env_files()

        # 1. Brand/capsule .env
        if env_key in self._cache:
            return self._cache[env_key]

        # 2. Environment variables
        val = os.environ.get(env_key, "").strip()
        if val:
            return val

        # 3. macOS Keychain
        if keychain_service:
            kc_val = self._keychain_read(keychain_service)
            if kc_val:
                return kc_val

        return None

    def require(self, env_key: str, keychain_service: Optional[str] = None, label: str = "") -> str:
        """Get a credential or raise TikTokCredentialError."""
        val = self.get(env_key, keychain_service)
        if not val:
            desc = label or env_key
            raise TikTokCredentialError(
                f"Missing credential: {desc}\n"
                f"  Checked: .env files, ${env_key}, "
                f"{'Keychain ' + repr(keychain_service) if keychain_service else 'no Keychain service'}\n"
                f"  Brand: {self.brand}"
            )
        return val


def _resolve_brand(brand_arg: Optional[str]) -> str:
    """
    Resolve brand name from arg, env, or auto-detect.

    Priority:
      1. --brand flag
      2. TIKTOK_DEFAULT_BRAND env
      3. First brand with tiktok_shop.enabled: true in brand.yaml
    """
    if brand_arg:
        return brand_arg

    env_brand = os.environ.get("TIKTOK_DEFAULT_BRAND", "").strip()
    if env_brand:
        return env_brand

    # Scan brands dir for first with TikTok enabled
    if BRANDS_DIR.is_dir():
        for brand_dir in sorted(BRANDS_DIR.iterdir()):
            if not brand_dir.is_dir():
                continue
            brand_yaml = brand_dir / "brand.yaml"
            if brand_yaml.is_file():
                try:
                    with open(brand_yaml, "r") as f:
                        content = f.read()
                    # Simple YAML check without PyYAML
                    if "tiktok_shop" in content and "enabled: true" in content:
                        logger.debug("Auto-detected brand: %s", brand_dir.name)
                        return brand_dir.name
                except Exception:
                    pass

    raise TikTokCredentialError(
        "No brand specified.\n"
        "  Use --brand <name>, set TIKTOK_DEFAULT_BRAND env,\n"
        "  or add tiktok_shop.enabled: true to a brand.yaml."
    )


# ---------------------------------------------------------------------------
# TikTok Shop Auth (HMAC-SHA256)
# ---------------------------------------------------------------------------

class TikTokShopAuth:
    """
    TikTok Shop API request signing (HMAC-SHA256).

    Signing algorithm:
      1. Extract all query params EXCEPT 'sign' and 'access_token'
      2. Sort params alphabetically by key
      3. Concatenate: key1value1key2value2...
      4. Prepend API path (e.g., /product/202309/products)
      5. If POST with body, append raw JSON body
      6. Wrap: app_secret + sign_string + app_secret
      7. HMAC-SHA256(key=app_secret, msg=wrapped_string)
      8. Lowercase hex digest
    """

    def __init__(self, app_key: str, app_secret: str):
        self.app_key = app_key
        self.app_secret = app_secret

    def sign(self, path: str, params: Dict[str, str], body: Optional[str] = None) -> str:
        """Generate HMAC-SHA256 signature for a Shop API request."""
        # Filter out 'sign' and 'access_token'
        sign_params = {
            k: v for k, v in params.items()
            if k not in ("sign", "access_token")
        }

        # Sort alphabetically and concatenate
        sorted_pairs = sorted(sign_params.items())
        param_str = "".join(f"{k}{v}" for k, v in sorted_pairs)

        # Build sign string: path + params + body
        sign_string = path + param_str
        if body:
            sign_string += body

        # Wrap with app_secret
        wrapped = self.app_secret + sign_string + self.app_secret

        # HMAC-SHA256
        signature = hmac.new(
            self.app_secret.encode("utf-8"),
            wrapped.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

        return signature


# ---------------------------------------------------------------------------
# TikTok OAuth (Marketing + Content + Shop token exchange)
# ---------------------------------------------------------------------------

class TikTokOAuth:
    """
    OAuth 2.0 flows for TikTok Shop, Marketing, and Content APIs.
    """

    SHOP_AUTH_URL = "https://services.tiktokshop.com/open/authorize"
    SHOP_TOKEN_URL = "https://auth.tiktok-shops.com/api/v2/token/get"
    SHOP_REFRESH_URL = "https://auth.tiktok-shops.com/api/v2/token/refresh"

    MARKETING_AUTH_URL = "https://business-api.tiktok.com/portal/auth"
    MARKETING_TOKEN_URL = "https://business-api.tiktok.com/open_api/v1.3/oauth2/access_token/"

    CONTENT_AUTH_URL = "https://www.tiktok.com/v2/auth/authorize/"
    CONTENT_TOKEN_URL = "https://open.tiktokapis.com/v2/oauth/token/"

    def __init__(self, app_id: str, app_secret: str,
                 redirect_uri: str = "https://localhost/callback"):
        self.app_id = app_id
        self.app_secret = app_secret
        self.redirect_uri = redirect_uri

    # --- Shop OAuth ---

    def get_shop_auth_url(self, state: str = "") -> str:
        params = urllib.parse.urlencode({
            "app_key": self.app_id,
            "state": state or "shop_auth",
        })
        return f"{self.SHOP_AUTH_URL}?{params}"

    def exchange_shop_code(self, auth_code: str) -> Dict[str, Any]:
        """Exchange authorization code for Shop access + refresh tokens."""
        params = urllib.parse.urlencode({
            "app_key": self.app_id,
            "app_secret": self.app_secret,
            "auth_code": auth_code,
            "grant_type": "authorized_code",
        })
        url = f"{self.SHOP_TOKEN_URL}?{params}"
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        if data.get("code") != 0:
            raise TikTokAuthError(f"Shop token exchange failed: {data.get('message', 'unknown')}")
        return data.get("data", {})

    def refresh_shop_token(self, refresh_token: str) -> Dict[str, Any]:
        """Refresh Shop access token."""
        params = urllib.parse.urlencode({
            "app_key": self.app_id,
            "app_secret": self.app_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        })
        url = f"{self.SHOP_REFRESH_URL}?{params}"
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        if data.get("code") != 0:
            raise TikTokAuthError(f"Shop token refresh failed: {data.get('message', 'unknown')}")
        return data.get("data", {})

    # --- Marketing OAuth ---

    def get_marketing_auth_url(self, state: str = "") -> str:
        params = urllib.parse.urlencode({
            "app_id": self.app_id,
            "redirect_uri": self.redirect_uri,
            "state": state or "marketing_auth",
        })
        return f"{self.MARKETING_AUTH_URL}?{params}"

    def exchange_marketing_code(self, auth_code: str) -> Dict[str, Any]:
        """Exchange authorization code for Marketing access token."""
        body = json.dumps({
            "app_id": self.app_id,
            "secret": self.app_secret,
            "auth_code": auth_code,
        }).encode("utf-8")
        req = urllib.request.Request(
            self.MARKETING_TOKEN_URL,
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        if data.get("code") != 0:
            raise TikTokAuthError(f"Marketing token exchange failed: {data.get('message', 'unknown')}")
        return data.get("data", {})

    def refresh_marketing_token(self, refresh_token: str) -> Dict[str, Any]:
        """Refresh Marketing access token (re-exchange or long-lived)."""
        # TikTok Marketing tokens are typically long-lived;
        # re-authorization may be required instead of refresh.
        raise TikTokAuthError(
            "Marketing API tokens are long-lived. Re-authorize via auth-marketing --generate-url."
        )

    # --- Content OAuth ---

    def get_content_auth_url(self, scopes: Optional[List[str]] = None, state: str = "") -> str:
        scope_str = ",".join(scopes or [
            "user.info.basic",
            "video.publish",
            "video.upload",
        ])
        params = urllib.parse.urlencode({
            "client_key": self.app_id,
            "response_type": "code",
            "scope": scope_str,
            "redirect_uri": self.redirect_uri,
            "state": state or "content_auth",
        })
        return f"{self.CONTENT_AUTH_URL}?{params}"

    def exchange_content_code(self, auth_code: str) -> Dict[str, Any]:
        """Exchange authorization code for Content access + refresh tokens."""
        body = urllib.parse.urlencode({
            "client_key": self.app_id,
            "client_secret": self.app_secret,
            "code": auth_code,
            "grant_type": "authorization_code",
            "redirect_uri": self.redirect_uri,
        }).encode("utf-8")
        req = urllib.request.Request(
            self.CONTENT_TOKEN_URL,
            data=body,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        if "access_token" not in data:
            raise TikTokAuthError(f"Content token exchange failed: {data.get('error_description', data)}")
        return data

    def refresh_content_token(self, refresh_token: str) -> Dict[str, Any]:
        """Refresh Content access token."""
        body = urllib.parse.urlencode({
            "client_key": self.app_id,
            "client_secret": self.app_secret,
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
        }).encode("utf-8")
        req = urllib.request.Request(
            self.CONTENT_TOKEN_URL,
            data=body,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        if "access_token" not in data:
            raise TikTokAuthError(f"Content token refresh failed: {data.get('error_description', data)}")
        return data


# ---------------------------------------------------------------------------
# TikTokShopClient
# ---------------------------------------------------------------------------

class TikTokShopClient:
    """
    REST client for TikTok Shop Open API (v202309).

    Handles HMAC-SHA256 signing, rate limiting, retries, and dry-run.
    """

    BASE_URL = "https://open-api.tiktokglobalshop.com"
    API_VERSION = "202309"
    MIN_REQUEST_INTERVAL = 0.5

    def __init__(self, auth: TikTokShopAuth, access_token: str,
                 shop_cipher: str = "", dry_run: bool = False):
        self.auth = auth
        self.access_token = access_token
        self.shop_cipher = shop_cipher
        self.dry_run = dry_run
        self._last_request_time: float = 0.0

    def _request(
        self,
        method: str,
        path: str,
        body: Optional[Dict[str, Any]] = None,
        extra_params: Optional[Dict[str, str]] = None,
        max_retries: int = 3,
    ) -> Dict[str, Any]:
        """Make a signed request to the Shop API."""
        timestamp = str(int(time.time()))
        params: Dict[str, str] = {
            "app_key": self.auth.app_key,
            "timestamp": timestamp,
        }
        if self.shop_cipher:
            params["shop_cipher"] = self.shop_cipher
        if extra_params:
            params.update(extra_params)

        body_str: Optional[str] = None
        if body is not None:
            body_str = json.dumps(body, separators=(",", ":"))

        # Sign the request
        sign = self.auth.sign(path, params, body_str)
        params["sign"] = sign
        params["access_token"] = self.access_token

        query = urllib.parse.urlencode(params)
        url = f"{self.BASE_URL}{path}?{query}"

        for attempt in range(max_retries):
            # Rate limiting
            now = time.time()
            elapsed = now - self._last_request_time
            if elapsed < self.MIN_REQUEST_INTERVAL:
                time.sleep(self.MIN_REQUEST_INTERVAL - elapsed)

            if self.dry_run and method.upper() in ("POST", "PUT", "DELETE"):
                logger.info("[DRY RUN] %s %s body=%s", method.upper(), path,
                            json.dumps(body, indent=2) if body else "null")
                return {"dry_run": True, "method": method, "path": path}

            headers = {"Content-Type": "application/json"}
            data_bytes = body_str.encode("utf-8") if body_str and method.upper() != "GET" else None
            req = urllib.request.Request(url, data=data_bytes, headers=headers, method=method.upper())

            logger.debug("%s %s", method.upper(), url)

            try:
                with urllib.request.urlopen(req, timeout=30) as resp:
                    self._last_request_time = time.time()
                    resp_body = resp.read().decode("utf-8")
                    result = json.loads(resp_body) if resp_body else {}

                code = result.get("code", 0)
                if code != 0:
                    msg = result.get("message", "Unknown Shop API error")
                    req_id = result.get("request_id", "")
                    raise TikTokShopAPIError(msg, code=code, request_id=req_id)

                return result

            except urllib.error.HTTPError as e:
                self._last_request_time = time.time()
                status = e.code
                try:
                    err_body = e.read().decode("utf-8")
                    err_json = json.loads(err_body)
                except Exception:
                    err_json = {}

                if status == 429:
                    backoff = min(2 ** (attempt + 1), 60)
                    logger.warning("429 Rate limited, backing off %ds (attempt %d/%d)",
                                   backoff, attempt + 1, max_retries)
                    time.sleep(backoff)
                    continue

                if status >= 500:
                    backoff = min(2 ** attempt, 30)
                    logger.warning("%d Server error, retrying in %ds (attempt %d/%d)",
                                   status, backoff, attempt + 1, max_retries)
                    time.sleep(backoff)
                    continue

                msg = err_json.get("message", str(e))
                req_id = err_json.get("request_id", "")
                raise TikTokShopAPIError(msg, code=status, request_id=req_id)

            except urllib.error.URLError as e:
                logger.error("Network error: %s", e)
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)
                    continue
                raise TikTokShopAPIError(f"Network error: {e}")

        raise TikTokShopAPIError(f"Max retries ({max_retries}) exhausted for {method} {path}")

    # --- Shop methods ---

    def get_authorized_shops(self) -> List[Dict[str, Any]]:
        """List shops authorized to this app."""
        path = f"/authorization/{self.API_VERSION}/shops"
        result = self._request("GET", path)
        return result.get("data", {}).get("shops", [])

    def get_shop_info(self) -> ShopStatus:
        """Get current shop information."""
        shops = self.get_authorized_shops()
        if not shops:
            return ShopStatus(shop_id="", shop_name="(none)", region="", status="NO_SHOPS")
        shop = shops[0]
        return ShopStatus(
            shop_id=shop.get("id", ""),
            shop_name=shop.get("name", ""),
            region=shop.get("region", ""),
            status="ACTIVE",
        )

    def list_products(self, status: str = "", page_size: int = 20,
                      page_token: str = "") -> Tuple[List[ProductSummary], str]:
        """List products. Returns (products, next_page_token)."""
        path = f"/product/{self.API_VERSION}/products/search"
        body: Dict[str, Any] = {"page_size": page_size}
        if page_token:
            body["page_token"] = page_token
        if status:
            body["filter"] = {"status": [status]}

        result = self._request("POST", path, body=body)
        data = result.get("data", {})
        products = []
        for p in data.get("products", []):
            products.append(ProductSummary(
                product_id=p.get("id", ""),
                title=p.get("title", ""),
                status=p.get("status", ""),
                create_time=p.get("create_time", 0),
                update_time=p.get("update_time", 0),
            ))
        next_token = data.get("next_page_token", "")
        return products, next_token

    def get_product(self, product_id: str) -> ProductDetail:
        """Get product details."""
        path = f"/product/{self.API_VERSION}/products/{product_id}"
        result = self._request("GET", path)
        p = result.get("data", {})
        return ProductDetail(
            product_id=p.get("id", product_id),
            title=p.get("title", ""),
            description=p.get("description", ""),
            status=p.get("status", ""),
            category_id=p.get("category_id", ""),
            skus=p.get("skus", []),
            images=[img.get("url", "") for img in p.get("main_images", [])],
            create_time=p.get("create_time", 0),
            update_time=p.get("update_time", 0),
        )

    def create_product(self, product_data: Dict[str, Any]) -> str:
        """Create a product. Returns product_id."""
        path = f"/product/{self.API_VERSION}/products"
        result = self._request("POST", path, body=product_data)
        return result.get("data", {}).get("product_id", "")

    def update_product(self, product_id: str, updates: Dict[str, Any]) -> bool:
        """Update a product. Returns True on success."""
        path = f"/product/{self.API_VERSION}/products/{product_id}"
        result = self._request("PUT", path, body=updates)
        return result.get("code", -1) == 0 or result.get("dry_run", False)

    def list_orders(self, status: str = "", page_size: int = 20,
                    create_time_from: int = 0, create_time_to: int = 0,
                    page_token: str = "") -> Tuple[List[OrderSummary], str]:
        """List orders. Returns (orders, next_page_token)."""
        path = f"/order/{self.API_VERSION}/orders/search"
        body: Dict[str, Any] = {"page_size": page_size}
        if page_token:
            body["page_token"] = page_token
        if status:
            body["filter"] = {"order_status": [status]}
        if create_time_from or create_time_to:
            time_filter: Dict[str, int] = {}
            if create_time_from:
                time_filter["create_time_from"] = create_time_from
            if create_time_to:
                time_filter["create_time_to"] = create_time_to
            body.setdefault("filter", {}).update(time_filter)

        result = self._request("POST", path, body=body)
        data = result.get("data", {})
        orders = []
        for o in data.get("orders", []):
            payment = o.get("payment", {})
            orders.append(OrderSummary(
                order_id=o.get("id", ""),
                status=o.get("status", ""),
                total_amount=payment.get("total_amount", "0"),
                currency=payment.get("currency", "USD"),
                create_time=o.get("create_time", 0),
            ))
        next_token = data.get("next_page_token", "")
        return orders, next_token

    def get_order(self, order_id: str) -> OrderDetail:
        """Get order details."""
        path = f"/order/{self.API_VERSION}/orders/{order_id}"
        result = self._request("GET", path)
        o = result.get("data", {})
        payment = o.get("payment", {})
        shipping = o.get("shipping_detail", {})
        return OrderDetail(
            order_id=o.get("id", order_id),
            status=o.get("status", ""),
            total_amount=payment.get("total_amount", "0"),
            currency=payment.get("currency", "USD"),
            buyer_message=o.get("buyer_message", ""),
            shipping_provider=shipping.get("shipping_provider_name", ""),
            tracking_number=shipping.get("tracking_number", ""),
            items=o.get("line_items", []),
            create_time=o.get("create_time", 0),
            update_time=o.get("update_time", 0),
        )

    def fulfill_order(self, order_id: str, tracking_number: str,
                      shipping_provider_id: str) -> bool:
        """Mark order as shipped with tracking info."""
        path = f"/fulfillment/{self.API_VERSION}/orders/{order_id}/packages"
        body = {
            "packages": [{
                "tracking_number": tracking_number,
                "shipping_provider_id": shipping_provider_id,
            }]
        }
        result = self._request("POST", path, body=body)
        return result.get("code", -1) == 0 or result.get("dry_run", False)

    def get_inventory(self, product_id: str) -> List[InventoryItem]:
        """Get inventory for a product's SKUs."""
        # First get product SKUs
        product = self.get_product(product_id)
        items = []
        for sku in product.skus:
            inventory = sku.get("inventory", [])
            for inv in inventory:
                items.append(InventoryItem(
                    sku_id=sku.get("id", ""),
                    seller_sku=sku.get("seller_sku", ""),
                    quantity=inv.get("quantity", 0),
                    warehouse_id=inv.get("warehouse_id", ""),
                ))
            if not inventory:
                items.append(InventoryItem(
                    sku_id=sku.get("id", ""),
                    seller_sku=sku.get("seller_sku", ""),
                    quantity=0,
                ))
        return items

    def update_inventory(self, sku_id: str, warehouse_id: str, quantity: int) -> bool:
        """Update inventory quantity for a SKU."""
        path = f"/product/{self.API_VERSION}/inventory/update"
        body = {
            "inventory_updates": [{
                "sku_id": sku_id,
                "warehouse_id": warehouse_id,
                "quantity": quantity,
            }]
        }
        result = self._request("POST", path, body=body)
        return result.get("code", -1) == 0 or result.get("dry_run", False)


# ---------------------------------------------------------------------------
# TikTokMarketingClient
# ---------------------------------------------------------------------------

class TikTokMarketingClient:
    """
    REST client for TikTok Marketing (Ads) API v1.3.

    Uses Access-Token header (TikTok's non-standard name).
    """

    BASE_URL = "https://business-api.tiktok.com/open_api/v1.3"
    MIN_REQUEST_INTERVAL = 0.5

    def __init__(self, access_token: str, advertiser_id: str = "",
                 dry_run: bool = False):
        self.access_token = access_token
        self.advertiser_id = advertiser_id
        self.dry_run = dry_run
        self._last_request_time: float = 0.0

    def _request(
        self,
        method: str,
        path: str,
        body: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, str]] = None,
        max_retries: int = 3,
    ) -> Dict[str, Any]:
        """Make an authenticated request to the Marketing API."""
        url = f"{self.BASE_URL}{path}"
        if params:
            query = urllib.parse.urlencode(params)
            url = f"{url}?{query}"

        for attempt in range(max_retries):
            now = time.time()
            elapsed = now - self._last_request_time
            if elapsed < self.MIN_REQUEST_INTERVAL:
                time.sleep(self.MIN_REQUEST_INTERVAL - elapsed)

            if self.dry_run and method.upper() in ("POST", "PUT", "DELETE"):
                logger.info("[DRY RUN] %s %s body=%s", method.upper(), path,
                            json.dumps(body, indent=2) if body else "null")
                return {"dry_run": True, "method": method, "path": path, "code": 0, "data": {}}

            headers = {
                "Content-Type": "application/json",
                "Access-Token": self.access_token,
            }
            data_bytes = json.dumps(body).encode("utf-8") if body else None
            req = urllib.request.Request(url, data=data_bytes, headers=headers, method=method.upper())

            logger.debug("%s %s", method.upper(), url)

            try:
                with urllib.request.urlopen(req, timeout=30) as resp:
                    self._last_request_time = time.time()
                    resp_body = resp.read().decode("utf-8")
                    result = json.loads(resp_body) if resp_body else {}

                code = result.get("code", 0)
                if code != 0:
                    msg = result.get("message", "Unknown Marketing API error")
                    req_id = result.get("request_id", "")
                    raise TikTokMarketingAPIError(msg, code=code, request_id=req_id)

                return result

            except urllib.error.HTTPError as e:
                self._last_request_time = time.time()
                status = e.code
                try:
                    err_body = e.read().decode("utf-8")
                    err_json = json.loads(err_body)
                except Exception:
                    err_json = {}

                if status == 429:
                    backoff = min(2 ** (attempt + 1), 60)
                    logger.warning("429 Rate limited, backing off %ds", backoff)
                    time.sleep(backoff)
                    continue

                if status >= 500:
                    backoff = min(2 ** attempt, 30)
                    logger.warning("%d Server error, retrying in %ds", status, backoff)
                    time.sleep(backoff)
                    continue

                msg = err_json.get("message", str(e))
                req_id = err_json.get("request_id", "")
                raise TikTokMarketingAPIError(msg, code=status, request_id=req_id)

            except urllib.error.URLError as e:
                logger.error("Network error: %s", e)
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)
                    continue
                raise TikTokMarketingAPIError(f"Network error: {e}")

        raise TikTokMarketingAPIError(f"Max retries ({max_retries}) exhausted for {method} {path}")

    # --- Campaign methods ---

    def list_campaigns(self, status: str = "", page: int = 1,
                       page_size: int = 20) -> List[CampaignSummary]:
        """List advertising campaigns."""
        body: Dict[str, Any] = {
            "advertiser_id": self.advertiser_id,
            "page": page,
            "page_size": page_size,
        }
        if status:
            body["filtering"] = {"status": status}

        result = self._request("GET", "/campaign/get/",
                               params={"advertiser_id": self.advertiser_id,
                                       "page": str(page), "page_size": str(page_size)})
        campaigns = []
        for c in result.get("data", {}).get("list", []):
            campaigns.append(CampaignSummary(
                campaign_id=str(c.get("campaign_id", "")),
                campaign_name=c.get("campaign_name", ""),
                objective_type=c.get("objective_type", ""),
                status=c.get("status", ""),
                budget=float(c.get("budget", 0)),
                budget_mode=c.get("budget_mode", ""),
            ))
        return campaigns

    def get_campaign(self, campaign_id: str) -> Dict[str, Any]:
        """Get campaign details."""
        result = self._request("GET", "/campaign/get/",
                               params={"advertiser_id": self.advertiser_id,
                                       "filtering": json.dumps({"campaign_ids": [campaign_id]})})
        campaigns = result.get("data", {}).get("list", [])
        return campaigns[0] if campaigns else {}

    def create_campaign(self, name: str, objective_type: str,
                        budget: float, budget_mode: str = "BUDGET_MODE_TOTAL") -> str:
        """Create a campaign. Returns campaign_id."""
        body = {
            "advertiser_id": self.advertiser_id,
            "campaign_name": name,
            "objective_type": objective_type,
            "budget": budget,
            "budget_mode": budget_mode,
        }
        result = self._request("POST", "/campaign/create/", body=body)
        return str(result.get("data", {}).get("campaign_id", ""))

    def update_campaign(self, campaign_id: str, updates: Dict[str, Any]) -> bool:
        """Update campaign settings."""
        body = {
            "advertiser_id": self.advertiser_id,
            "campaign_id": campaign_id,
            **updates,
        }
        result = self._request("POST", "/campaign/update/", body=body)
        return result.get("code", -1) == 0 or result.get("dry_run", False)

    # --- Ad Group methods ---

    def list_ad_groups(self, campaign_id: str = "", page: int = 1,
                       page_size: int = 20) -> List[AdGroupSummary]:
        """List ad groups, optionally filtered by campaign."""
        params: Dict[str, str] = {
            "advertiser_id": self.advertiser_id,
            "page": str(page),
            "page_size": str(page_size),
        }
        if campaign_id:
            params["filtering"] = json.dumps({"campaign_ids": [campaign_id]})

        result = self._request("GET", "/adgroup/get/", params=params)
        groups = []
        for g in result.get("data", {}).get("list", []):
            groups.append(AdGroupSummary(
                adgroup_id=str(g.get("adgroup_id", "")),
                adgroup_name=g.get("adgroup_name", ""),
                campaign_id=str(g.get("campaign_id", "")),
                status=g.get("status", ""),
                budget=float(g.get("budget", 0)),
            ))
        return groups

    def create_ad_group(self, campaign_id: str, name: str,
                        placement_type: str, budget: float,
                        schedule_start: str, targeting: Optional[Dict[str, Any]] = None) -> str:
        """Create an ad group. Returns adgroup_id."""
        body: Dict[str, Any] = {
            "advertiser_id": self.advertiser_id,
            "campaign_id": campaign_id,
            "adgroup_name": name,
            "placement_type": placement_type,
            "budget": budget,
            "schedule_start_time": schedule_start,
        }
        if targeting:
            body["targeting"] = targeting

        result = self._request("POST", "/adgroup/create/", body=body)
        return str(result.get("data", {}).get("adgroup_id", ""))

    # --- Ad methods ---

    def list_ads(self, adgroup_id: str = "", page: int = 1,
                 page_size: int = 20) -> List[AdSummary]:
        """List ads, optionally filtered by ad group."""
        params: Dict[str, str] = {
            "advertiser_id": self.advertiser_id,
            "page": str(page),
            "page_size": str(page_size),
        }
        if adgroup_id:
            params["filtering"] = json.dumps({"adgroup_ids": [adgroup_id]})

        result = self._request("GET", "/ad/get/", params=params)
        ads = []
        for a in result.get("data", {}).get("list", []):
            ads.append(AdSummary(
                ad_id=str(a.get("ad_id", "")),
                ad_name=a.get("ad_name", ""),
                adgroup_id=str(a.get("adgroup_id", "")),
                status=a.get("status", ""),
                ad_format=a.get("ad_format", ""),
            ))
        return ads

    def create_ad(self, adgroup_id: str, ad_name: str,
                  ad_format: str, creative: Dict[str, Any]) -> str:
        """Create an ad. Returns ad_id."""
        body = {
            "advertiser_id": self.advertiser_id,
            "adgroup_id": adgroup_id,
            "ad_name": ad_name,
            "ad_format": ad_format,
            "creative": creative,
        }
        result = self._request("POST", "/ad/create/", body=body)
        return str(result.get("data", {}).get("ad_id", ""))

    # --- Audience methods ---

    def list_audiences(self) -> List[Dict[str, Any]]:
        """List custom audiences."""
        result = self._request("GET", "/audience/list/",
                               params={"advertiser_id": self.advertiser_id})
        return result.get("data", {}).get("list", [])

    # --- Reporting ---

    def get_report(self, report_type: str, dimensions: List[str],
                   metrics: List[str], start_date: str, end_date: str,
                   filters: Optional[Dict[str, Any]] = None) -> List[ReportRow]:
        """Get a performance report."""
        body: Dict[str, Any] = {
            "advertiser_id": self.advertiser_id,
            "report_type": report_type,
            "dimensions": dimensions,
            "metrics": metrics,
            "data_level": "AUCTION_" + report_type.upper(),
            "start_date": start_date,
            "end_date": end_date,
        }
        if filters:
            body["filtering"] = filters

        result = self._request("POST", "/report/integrated/get/", body=body)
        rows = []
        for r in result.get("data", {}).get("list", []):
            dim_vals = r.get("dimensions", {})
            met_vals = r.get("metrics", {})
            rows.append(ReportRow(dimensions=dim_vals, metrics=met_vals))
        return rows


# ---------------------------------------------------------------------------
# TikTokContentClient
# ---------------------------------------------------------------------------

class TikTokContentClient:
    """
    REST client for TikTok Content Posting API v2.

    Auth: Bearer token in Authorization header.
    Rate limit: 6 req/min -- enforce 10s minimum interval.
    """

    BASE_URL = "https://open.tiktokapis.com/v2"
    MIN_REQUEST_INTERVAL = 10.0  # 6 req/min safety margin

    def __init__(self, access_token: str, dry_run: bool = False):
        self.access_token = access_token
        self.dry_run = dry_run
        self._last_request_time: float = 0.0

    def _request(
        self,
        method: str,
        path: str,
        body: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, str]] = None,
        max_retries: int = 3,
    ) -> Dict[str, Any]:
        """Make an authenticated request to the Content API."""
        url = f"{self.BASE_URL}{path}"
        if params:
            query = urllib.parse.urlencode(params)
            url = f"{url}?{query}"

        for attempt in range(max_retries):
            now = time.time()
            elapsed = now - self._last_request_time
            if elapsed < self.MIN_REQUEST_INTERVAL:
                wait = self.MIN_REQUEST_INTERVAL - elapsed
                logger.debug("Content API rate limit: waiting %.1fs", wait)
                time.sleep(wait)

            if self.dry_run and method.upper() in ("POST", "PUT", "DELETE"):
                logger.info("[DRY RUN] %s %s body=%s", method.upper(), path,
                            json.dumps(body, indent=2) if body else "null")
                return {"dry_run": True, "method": method, "path": path, "data": {}}

            headers = {
                "Content-Type": "application/json; charset=UTF-8",
                "Authorization": f"Bearer {self.access_token}",
            }
            data_bytes = json.dumps(body).encode("utf-8") if body else None
            req = urllib.request.Request(url, data=data_bytes, headers=headers, method=method.upper())

            logger.debug("%s %s", method.upper(), url)

            try:
                with urllib.request.urlopen(req, timeout=30) as resp:
                    self._last_request_time = time.time()
                    resp_body = resp.read().decode("utf-8")
                    result = json.loads(resp_body) if resp_body else {}

                error = result.get("error", {})
                if error.get("code", "ok") != "ok":
                    raise TikTokContentAPIError(
                        f"{error.get('code', 'unknown')}: {error.get('message', 'Unknown error')}"
                    )

                return result

            except urllib.error.HTTPError as e:
                self._last_request_time = time.time()
                status = e.code
                try:
                    err_body = e.read().decode("utf-8")
                    err_json = json.loads(err_body)
                except Exception:
                    err_json = {}

                if status == 429:
                    retry_after = int(e.headers.get("Retry-After", 60))
                    raise TikTokRateLimitError(
                        "Content API rate limited", retry_after=retry_after
                    )

                if status >= 500:
                    backoff = min(2 ** attempt, 30)
                    logger.warning("%d Server error, retrying in %ds", status, backoff)
                    time.sleep(backoff)
                    continue

                error = err_json.get("error", {})
                raise TikTokContentAPIError(
                    f"HTTP {status}: {error.get('message', str(e))}"
                )

            except urllib.error.URLError as e:
                logger.error("Network error: %s", e)
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)
                    continue
                raise TikTokContentAPIError(f"Network error: {e}")

        raise TikTokContentAPIError(f"Max retries ({max_retries}) exhausted for {method} {path}")

    # --- Content methods ---

    def get_creator_info(self) -> CreatorInfo:
        """Get creator info and posting capabilities."""
        result = self._request("POST", "/post/publish/creator_info/query/")
        data = result.get("data", {})
        return CreatorInfo(
            creator_nickname=data.get("creator_nickname", ""),
            creator_avatar_url=data.get("creator_avatar_url", ""),
            is_union_enabled=data.get("is_union_enabled", False),
            max_video_post_duration_sec=data.get("max_video_post_duration_sec", 0),
            privacy_level_options=data.get("privacy_level_options", []),
        )

    def direct_post_video(
        self,
        video_url: str,
        title: str,
        privacy_level: str = "SELF_ONLY",
        disable_comment: bool = False,
        disable_duet: bool = True,
        disable_stitch: bool = True,
        is_aigc: bool = False,
    ) -> str:
        """Post a video by URL. Returns publish_id."""
        body: Dict[str, Any] = {
            "post_info": {
                "title": title,
                "privacy_level": privacy_level,
                "disable_comment": disable_comment,
                "disable_duet": disable_duet,
                "disable_stitch": disable_stitch,
            },
            "source_info": {
                "source": "PULL_FROM_URL",
                "video_url": video_url,
            },
        }
        if is_aigc:
            body["post_info"]["is_aigc"] = True

        result = self._request("POST", "/post/publish/video/init/", body=body)
        return result.get("data", {}).get("publish_id", "")

    def init_file_upload(self, video_size: int,
                         chunk_size: int = 10_000_000) -> Tuple[str, str]:
        """Initialize a chunked file upload. Returns (publish_id, upload_url)."""
        body = {
            "post_info": {
                "title": "",
                "privacy_level": "SELF_ONLY",
            },
            "source_info": {
                "source": "FILE_UPLOAD",
                "video_size": video_size,
                "chunk_size": chunk_size,
                "total_chunk_count": (video_size + chunk_size - 1) // chunk_size,
            },
        }
        result = self._request("POST", "/post/publish/video/init/", body=body)
        data = result.get("data", {})
        return data.get("publish_id", ""), data.get("upload_url", "")

    def upload_video_chunk(self, upload_url: str, file_path: str,
                           chunk_index: int, chunk_size: int,
                           total_size: int) -> bool:
        """Upload a single video chunk."""
        path = Path(file_path)
        if not path.is_file():
            raise TikTokContentAPIError(f"File not found: {file_path}")

        offset = chunk_index * chunk_size
        read_size = min(chunk_size, total_size - offset)

        with open(path, "rb") as f:
            f.seek(offset)
            chunk_data = f.read(read_size)

        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/octet-stream",
            "Content-Range": f"bytes {offset}-{offset + len(chunk_data) - 1}/{total_size}",
        }

        req = urllib.request.Request(upload_url, data=chunk_data, headers=headers, method="PUT")
        with urllib.request.urlopen(req, timeout=120) as resp:
            return resp.status in (200, 201, 206)

    def get_post_status(self, publish_id: str) -> PostStatus:
        """Check the status of a video post."""
        body = {"publish_id": publish_id}
        result = self._request("POST", "/post/publish/status/fetch/", body=body)
        data = result.get("data", {})
        return PostStatus(
            publish_id=publish_id,
            status=data.get("status", "UNKNOWN"),
            uploaded_bytes=data.get("uploaded_bytes", 0),
            error_code=data.get("fail_reason", ""),
            error_message=data.get("publicaly_available_post_id", [{}])[0].get("id", "")
            if isinstance(data.get("publicaly_available_post_id"), list) else "",
        )


# ---------------------------------------------------------------------------
# Client Container
# ---------------------------------------------------------------------------

@dataclass
class TikTokClients:
    """Lazy container for all three TikTok API clients."""
    shop: Optional[TikTokShopClient] = None
    marketing: Optional[TikTokMarketingClient] = None
    content: Optional[TikTokContentClient] = None
    brand: str = ""
    dry_run: bool = False


# ---------------------------------------------------------------------------
# Command Handlers - Shop
# ---------------------------------------------------------------------------

def cmd_status(clients: TikTokClients, args: argparse.Namespace) -> int:
    """Show Shop status and connection info."""
    assert clients.shop is not None
    info = clients.shop.get_shop_info()

    if args.json:
        _json_output(_dc_to_dict(info))
        return 0

    print(f"\n{BOLD}TikTok Shop Status{RESET} (brand: {clients.brand})\n")
    print(f"  Shop ID:    {info.shop_id}")
    print(f"  Shop Name:  {info.shop_name}")
    print(f"  Region:     {info.region}")
    print(f"  Status:     {GREEN}{info.status}{RESET}")
    print()
    return 0


def cmd_products(clients: TikTokClients, args: argparse.Namespace) -> int:
    """List products."""
    assert clients.shop is not None
    products, next_token = clients.shop.list_products(
        status=getattr(args, "status", ""),
        page_size=getattr(args, "limit", 20),
        page_token=getattr(args, "page_token", ""),
    )

    if args.json:
        _json_output({
            "products": [_dc_to_dict(p) for p in products],
            "next_page_token": next_token,
        })
        return 0

    if not products:
        print(f"\n  {DIM}No products found{RESET}\n")
        return 0

    print(f"\n{BOLD}Products{RESET} ({len(products)} shown)\n")
    rows = []
    for p in products:
        rows.append([
            p.product_id,
            _truncate(p.title, 35),
            p.status,
            _ts_to_str(p.create_time),
        ])
    print(_format_table(["Product ID", "Title", "Status", "Created"], rows))
    if next_token:
        print(f"\n  {DIM}Next page: --page-token {next_token}{RESET}")
    print()
    return 0


def cmd_product_detail(clients: TikTokClients, args: argparse.Namespace) -> int:
    """Show product details."""
    assert clients.shop is not None
    product = clients.shop.get_product(args.product_id)

    if args.json:
        _json_output(_dc_to_dict(product))
        return 0

    print(f"\n{BOLD}Product: {product.title}{RESET}\n")
    print(f"  ID:          {product.product_id}")
    print(f"  Status:      {product.status}")
    print(f"  Category:    {product.category_id}")
    print(f"  Created:     {_ts_to_str(product.create_time)}")
    print(f"  Updated:     {_ts_to_str(product.update_time)}")
    if product.description:
        desc = _truncate(product.description, 100)
        print(f"  Description: {desc}")
    if product.skus:
        print(f"\n  {BOLD}SKUs ({len(product.skus)}):{RESET}")
        for sku in product.skus:
            print(f"    - {sku.get('id', 'N/A')}: {sku.get('seller_sku', 'N/A')}")
    if product.images:
        print(f"\n  {BOLD}Images ({len(product.images)}):{RESET}")
        for img in product.images[:5]:
            print(f"    - {_truncate(img, 60)}")
    print()
    return 0


def cmd_create_product(clients: TikTokClients, args: argparse.Namespace) -> int:
    """Create a product from JSON file or inline."""
    assert clients.shop is not None
    if args.from_file:
        with open(args.from_file, "r") as f:
            product_data = json.load(f)
    else:
        print(f"{RED}Provide product data via --from-file <path.json>{RESET}")
        return 2

    product_id = clients.shop.create_product(product_data)

    if args.json:
        _json_output({"product_id": product_id})
    else:
        if product_id:
            print(f"\n{GREEN}Product created: {product_id}{RESET}\n")
        else:
            print(f"\n{YELLOW}Product creation returned (dry-run or pending){RESET}\n")
    return 0


def cmd_update_product(clients: TikTokClients, args: argparse.Namespace) -> int:
    """Update a product from JSON file."""
    assert clients.shop is not None
    if args.from_file:
        with open(args.from_file, "r") as f:
            updates = json.load(f)
    else:
        print(f"{RED}Provide update data via --from-file <path.json>{RESET}")
        return 2

    ok = clients.shop.update_product(args.product_id, updates)

    if args.json:
        _json_output({"success": ok, "product_id": args.product_id})
    else:
        if ok:
            print(f"\n{GREEN}Product {args.product_id} updated{RESET}\n")
        else:
            print(f"\n{RED}Failed to update product{RESET}\n")
    return 0 if ok else 1


def cmd_orders(clients: TikTokClients, args: argparse.Namespace) -> int:
    """List orders."""
    assert clients.shop is not None
    orders, next_token = clients.shop.list_orders(
        status=getattr(args, "status", ""),
        page_size=getattr(args, "limit", 20),
        page_token=getattr(args, "page_token", ""),
    )

    if args.json:
        _json_output({
            "orders": [_dc_to_dict(o) for o in orders],
            "next_page_token": next_token,
        })
        return 0

    if not orders:
        print(f"\n  {DIM}No orders found{RESET}\n")
        return 0

    print(f"\n{BOLD}Orders{RESET} ({len(orders)} shown)\n")
    rows = []
    for o in orders:
        rows.append([
            o.order_id,
            o.status,
            f"{o.currency} {o.total_amount}",
            _ts_to_str(o.create_time),
        ])
    print(_format_table(["Order ID", "Status", "Total", "Created"], rows))
    if next_token:
        print(f"\n  {DIM}Next page: --page-token {next_token}{RESET}")
    print()
    return 0


def cmd_order_detail(clients: TikTokClients, args: argparse.Namespace) -> int:
    """Show order details."""
    assert clients.shop is not None
    order = clients.shop.get_order(args.order_id)

    if args.json:
        _json_output(_dc_to_dict(order))
        return 0

    print(f"\n{BOLD}Order: {order.order_id}{RESET}\n")
    print(f"  Status:     {order.status}")
    print(f"  Total:      {order.currency} {order.total_amount}")
    print(f"  Created:    {_ts_to_str(order.create_time)}")
    print(f"  Updated:    {_ts_to_str(order.update_time)}")
    if order.buyer_message:
        print(f"  Buyer Msg:  {order.buyer_message}")
    if order.tracking_number:
        print(f"  Tracking:   {order.tracking_number} ({order.shipping_provider})")
    if order.items:
        print(f"\n  {BOLD}Items ({len(order.items)}):{RESET}")
        for item in order.items:
            print(f"    - {item.get('product_name', 'N/A')} x{item.get('quantity', 1)}")
    print()
    return 0


def cmd_fulfill_order(clients: TikTokClients, args: argparse.Namespace) -> int:
    """Fulfill an order with tracking info."""
    assert clients.shop is not None
    ok = clients.shop.fulfill_order(
        args.order_id, args.tracking_number, args.shipping_provider_id,
    )

    if args.json:
        _json_output({"success": ok, "order_id": args.order_id})
    else:
        if ok:
            print(f"\n{GREEN}Order {args.order_id} fulfilled (tracking: {args.tracking_number}){RESET}\n")
        else:
            print(f"\n{RED}Failed to fulfill order{RESET}\n")
    return 0 if ok else 1


def cmd_inventory(clients: TikTokClients, args: argparse.Namespace) -> int:
    """Show inventory for a product."""
    assert clients.shop is not None
    items = clients.shop.get_inventory(args.product_id)

    if args.json:
        _json_output([_dc_to_dict(i) for i in items])
        return 0

    if not items:
        print(f"\n  {DIM}No inventory found for {args.product_id}{RESET}\n")
        return 0

    print(f"\n{BOLD}Inventory for {args.product_id}{RESET}\n")
    rows = []
    for item in items:
        rows.append([
            item.sku_id,
            item.seller_sku,
            str(item.quantity),
            item.warehouse_id or "(default)",
        ])
    print(_format_table(["SKU ID", "Seller SKU", "Qty", "Warehouse"], rows))
    print()
    return 0


def cmd_update_inventory(clients: TikTokClients, args: argparse.Namespace) -> int:
    """Update inventory quantity for a SKU."""
    assert clients.shop is not None
    ok = clients.shop.update_inventory(
        args.sku_id, args.warehouse_id, args.quantity,
    )

    if args.json:
        _json_output({"success": ok, "sku_id": args.sku_id, "quantity": args.quantity})
    else:
        if ok:
            print(f"\n{GREEN}Inventory updated: SKU {args.sku_id} -> {args.quantity}{RESET}\n")
        else:
            print(f"\n{RED}Failed to update inventory{RESET}\n")
    return 0 if ok else 1


# ---------------------------------------------------------------------------
# Command Handlers - Shop Auth
# ---------------------------------------------------------------------------

def cmd_auth_shop(clients: TikTokClients, args: argparse.Namespace) -> int:
    """Manage Shop OAuth tokens."""
    creds = BrandCredentialLoader(clients.brand)
    app_key = creds.require("TIKTOK_SHOP_APP_KEY",
                            f"ecommerce/{clients.brand}/tiktok-shop",
                            "TikTok Shop App Key")
    app_secret = creds.require("TIKTOK_SHOP_APP_SECRET",
                               f"ecommerce/{clients.brand}/tiktok-shop",
                               "TikTok Shop App Secret")
    oauth = TikTokOAuth(app_key, app_secret)

    if getattr(args, "generate_url", False):
        url = oauth.get_shop_auth_url()
        print(f"\n{BOLD}Shop Authorization URL:{RESET}\n")
        print(f"  {CYAN}{url}{RESET}\n")
        print(f"  After authorizing, run:")
        print(f"  {DIM}tiktok auth-shop --code <AUTH_CODE> --brand {clients.brand}{RESET}\n")
        return 0

    if getattr(args, "code", None):
        data = oauth.exchange_shop_code(args.code)
        access_token = data.get("access_token", "")
        refresh_token = data.get("refresh_token", "")

        # Store in Keychain
        svc_token = f"ecommerce/{clients.brand}/tiktok-shop-token"
        svc_refresh = f"ecommerce/{clients.brand}/tiktok-shop-refresh"
        BrandCredentialLoader.keychain_write(svc_token, clients.brand, access_token)
        BrandCredentialLoader.keychain_write(svc_refresh, clients.brand, refresh_token)

        if args.json:
            _json_output({"success": True, "access_token_prefix": access_token[:12] + "..."})
        else:
            print(f"\n{GREEN}Shop tokens stored in Keychain{RESET}")
            print(f"  Access token:  {access_token[:12]}...")
            print(f"  Refresh token: {refresh_token[:12]}...")
            print(f"  Keychain svc:  {svc_token}\n")
        return 0

    if getattr(args, "refresh", False):
        svc_refresh = f"ecommerce/{clients.brand}/tiktok-shop-refresh"
        refresh_token = creds.get("TIKTOK_SHOP_REFRESH_TOKEN", svc_refresh)
        if not refresh_token:
            print(f"{RED}No refresh token found. Run auth-shop --generate-url first.{RESET}")
            return 1

        data = oauth.refresh_shop_token(refresh_token)
        new_access = data.get("access_token", "")
        new_refresh = data.get("refresh_token", "")

        svc_token = f"ecommerce/{clients.brand}/tiktok-shop-token"
        BrandCredentialLoader.keychain_write(svc_token, clients.brand, new_access)
        if new_refresh:
            BrandCredentialLoader.keychain_write(svc_refresh, clients.brand, new_refresh)

        if args.json:
            _json_output({"success": True, "access_token_prefix": new_access[:12] + "..."})
        else:
            print(f"\n{GREEN}Shop tokens refreshed and stored{RESET}")
            print(f"  New access token: {new_access[:12]}...\n")
        return 0

    print(f"{YELLOW}Use --generate-url, --code <AUTH_CODE>, or --refresh{RESET}")
    return 2


# ---------------------------------------------------------------------------
# Command Handlers - Marketing
# ---------------------------------------------------------------------------

def cmd_campaigns(clients: TikTokClients, args: argparse.Namespace) -> int:
    """List campaigns."""
    assert clients.marketing is not None
    campaigns = clients.marketing.list_campaigns(
        status=getattr(args, "status", ""),
        page=getattr(args, "page", 1),
        page_size=getattr(args, "limit", 20),
    )

    if args.json:
        _json_output([_dc_to_dict(c) for c in campaigns])
        return 0

    if not campaigns:
        print(f"\n  {DIM}No campaigns found{RESET}\n")
        return 0

    print(f"\n{BOLD}Campaigns{RESET} ({len(campaigns)} shown)\n")
    rows = []
    for c in campaigns:
        rows.append([
            c.campaign_id,
            _truncate(c.campaign_name, 25),
            c.objective_type,
            c.status,
            f"${c.budget:.2f}",
        ])
    print(_format_table(["Campaign ID", "Name", "Objective", "Status", "Budget"], rows))
    print()
    return 0


def cmd_campaign_detail(clients: TikTokClients, args: argparse.Namespace) -> int:
    """Show campaign details."""
    assert clients.marketing is not None
    campaign = clients.marketing.get_campaign(args.campaign_id)

    if args.json:
        _json_output(campaign)
    else:
        if not campaign:
            print(f"\n  {DIM}Campaign {args.campaign_id} not found{RESET}\n")
            return 1
        print(f"\n{BOLD}Campaign: {campaign.get('campaign_name', 'N/A')}{RESET}\n")
        for k, v in sorted(campaign.items()):
            print(f"  {k}: {v}")
        print()
    return 0


def cmd_create_campaign(clients: TikTokClients, args: argparse.Namespace) -> int:
    """Create a campaign."""
    assert clients.marketing is not None
    campaign_id = clients.marketing.create_campaign(
        name=args.name,
        objective_type=args.objective,
        budget=float(args.budget),
        budget_mode=getattr(args, "budget_mode", "BUDGET_MODE_TOTAL"),
    )

    if args.json:
        _json_output({"campaign_id": campaign_id})
    else:
        if campaign_id:
            print(f"\n{GREEN}Campaign created: {campaign_id}{RESET}\n")
        else:
            print(f"\n{YELLOW}Campaign creation returned (dry-run or pending){RESET}\n")
    return 0


def cmd_ad_groups(clients: TikTokClients, args: argparse.Namespace) -> int:
    """List ad groups."""
    assert clients.marketing is not None
    groups = clients.marketing.list_ad_groups(
        campaign_id=getattr(args, "campaign_id", ""),
        page=getattr(args, "page", 1),
        page_size=getattr(args, "limit", 20),
    )

    if args.json:
        _json_output([_dc_to_dict(g) for g in groups])
        return 0

    if not groups:
        print(f"\n  {DIM}No ad groups found{RESET}\n")
        return 0

    print(f"\n{BOLD}Ad Groups{RESET} ({len(groups)} shown)\n")
    rows = []
    for g in groups:
        rows.append([
            g.adgroup_id,
            _truncate(g.adgroup_name, 25),
            g.campaign_id,
            g.status,
            f"${g.budget:.2f}",
        ])
    print(_format_table(["AdGroup ID", "Name", "Campaign", "Status", "Budget"], rows))
    print()
    return 0


def cmd_create_ad_group(clients: TikTokClients, args: argparse.Namespace) -> int:
    """Create an ad group."""
    assert clients.marketing is not None
    adgroup_id = clients.marketing.create_ad_group(
        campaign_id=args.campaign_id,
        name=args.name,
        placement_type=getattr(args, "placement", "PLACEMENT_TYPE_AUTOMATIC"),
        budget=float(args.budget),
        schedule_start=args.schedule_start,
    )

    if args.json:
        _json_output({"adgroup_id": adgroup_id})
    else:
        if adgroup_id:
            print(f"\n{GREEN}Ad group created: {adgroup_id}{RESET}\n")
        else:
            print(f"\n{YELLOW}Ad group creation returned (dry-run or pending){RESET}\n")
    return 0


def cmd_ads(clients: TikTokClients, args: argparse.Namespace) -> int:
    """List ads."""
    assert clients.marketing is not None
    ads = clients.marketing.list_ads(
        adgroup_id=getattr(args, "adgroup_id", ""),
        page=getattr(args, "page", 1),
        page_size=getattr(args, "limit", 20),
    )

    if args.json:
        _json_output([_dc_to_dict(a) for a in ads])
        return 0

    if not ads:
        print(f"\n  {DIM}No ads found{RESET}\n")
        return 0

    print(f"\n{BOLD}Ads{RESET} ({len(ads)} shown)\n")
    rows = []
    for a in ads:
        rows.append([a.ad_id, _truncate(a.ad_name, 25), a.adgroup_id, a.status, a.ad_format])
    print(_format_table(["Ad ID", "Name", "AdGroup", "Status", "Format"], rows))
    print()
    return 0


def cmd_create_ad(clients: TikTokClients, args: argparse.Namespace) -> int:
    """Create an ad from JSON creative file."""
    assert clients.marketing is not None
    if args.creative_file:
        with open(args.creative_file, "r") as f:
            creative = json.load(f)
    else:
        print(f"{RED}Provide creative data via --creative-file <path.json>{RESET}")
        return 2

    ad_id = clients.marketing.create_ad(
        adgroup_id=args.adgroup_id,
        ad_name=args.name,
        ad_format=getattr(args, "format", "SINGLE_VIDEO"),
        creative=creative,
    )

    if args.json:
        _json_output({"ad_id": ad_id})
    else:
        if ad_id:
            print(f"\n{GREEN}Ad created: {ad_id}{RESET}\n")
        else:
            print(f"\n{YELLOW}Ad creation returned (dry-run or pending){RESET}\n")
    return 0


def cmd_audiences(clients: TikTokClients, args: argparse.Namespace) -> int:
    """List custom audiences."""
    assert clients.marketing is not None
    audiences = clients.marketing.list_audiences()

    if args.json:
        _json_output(audiences)
        return 0

    if not audiences:
        print(f"\n  {DIM}No audiences found{RESET}\n")
        return 0

    print(f"\n{BOLD}Audiences{RESET} ({len(audiences)} shown)\n")
    rows = []
    for a in audiences:
        rows.append([
            str(a.get("audience_id", "")),
            a.get("name", ""),
            str(a.get("audience_size", 0)),
        ])
    print(_format_table(["Audience ID", "Name", "Size"], rows))
    print()
    return 0


def cmd_reports(clients: TikTokClients, args: argparse.Namespace) -> int:
    """Generate a performance report."""
    assert clients.marketing is not None
    dimensions = [d.strip() for d in args.dimensions.split(",")]
    metrics = [m.strip() for m in args.metrics.split(",")]

    rows = clients.marketing.get_report(
        report_type=getattr(args, "report_type", "BASIC"),
        dimensions=dimensions,
        metrics=metrics,
        start_date=args.start_date,
        end_date=args.end_date,
    )

    if args.json:
        _json_output([_dc_to_dict(r) for r in rows])
        return 0

    if not rows:
        print(f"\n  {DIM}No report data{RESET}\n")
        return 0

    print(f"\n{BOLD}Report{RESET} ({len(rows)} rows)\n")
    # Build dynamic table from first row
    if rows:
        dim_keys = sorted(rows[0].dimensions.keys())
        met_keys = sorted(rows[0].metrics.keys())
        headers = dim_keys + met_keys
        table_rows = []
        for r in rows:
            table_row = [str(r.dimensions.get(k, "")) for k in dim_keys]
            table_row += [str(r.metrics.get(k, "")) for k in met_keys]
            table_rows.append(table_row)
        print(_format_table(headers, table_rows))
    print()
    return 0


# ---------------------------------------------------------------------------
# Command Handlers - Marketing Auth
# ---------------------------------------------------------------------------

def cmd_auth_marketing(clients: TikTokClients, args: argparse.Namespace) -> int:
    """Manage Marketing OAuth tokens."""
    creds = BrandCredentialLoader(clients.brand)
    app_id = creds.require("TIKTOK_ADS_APP_ID",
                           f"ecommerce/{clients.brand}/tiktok-ads",
                           "TikTok Ads App ID")
    app_secret = creds.require("TIKTOK_ADS_APP_SECRET",
                               f"ecommerce/{clients.brand}/tiktok-ads",
                               "TikTok Ads App Secret")
    oauth = TikTokOAuth(app_id, app_secret)

    if getattr(args, "generate_url", False):
        url = oauth.get_marketing_auth_url()
        print(f"\n{BOLD}Marketing Authorization URL:{RESET}\n")
        print(f"  {CYAN}{url}{RESET}\n")
        print(f"  After authorizing, run:")
        print(f"  {DIM}tiktok auth-marketing --code <AUTH_CODE> --brand {clients.brand}{RESET}\n")
        return 0

    if getattr(args, "code", None):
        data = oauth.exchange_marketing_code(args.code)
        access_token = data.get("access_token", "")

        svc = f"ecommerce/{clients.brand}/tiktok-ads"
        BrandCredentialLoader.keychain_write(svc, clients.brand, access_token)

        if args.json:
            _json_output({"success": True, "access_token_prefix": access_token[:12] + "..."})
        else:
            print(f"\n{GREEN}Marketing token stored in Keychain{RESET}")
            print(f"  Access token: {access_token[:12]}...")
            print(f"  Keychain svc: {svc}\n")
        return 0

    print(f"{YELLOW}Use --generate-url or --code <AUTH_CODE>{RESET}")
    return 2


# ---------------------------------------------------------------------------
# Command Handlers - Content
# ---------------------------------------------------------------------------

def cmd_creator_info(clients: TikTokClients, args: argparse.Namespace) -> int:
    """Show creator info."""
    assert clients.content is not None
    info = clients.content.get_creator_info()

    if args.json:
        _json_output(_dc_to_dict(info))
        return 0

    print(f"\n{BOLD}Creator Info{RESET}\n")
    print(f"  Nickname:       {info.creator_nickname}")
    print(f"  Avatar:         {_truncate(info.creator_avatar_url, 50)}")
    print(f"  Union Enabled:  {info.is_union_enabled}")
    print(f"  Max Duration:   {info.max_video_post_duration_sec}s")
    print(f"  Privacy Opts:   {', '.join(info.privacy_level_options)}")
    print()
    return 0


def cmd_post_video(clients: TikTokClients, args: argparse.Namespace) -> int:
    """Post a video by URL."""
    assert clients.content is not None
    publish_id = clients.content.direct_post_video(
        video_url=args.video_url,
        title=args.title,
        privacy_level=getattr(args, "privacy", "SELF_ONLY"),
        disable_comment=getattr(args, "disable_comment", False),
        disable_duet=getattr(args, "disable_duet", True),
        disable_stitch=getattr(args, "disable_stitch", True),
        is_aigc=getattr(args, "aigc", False),
    )

    if args.json:
        _json_output({"publish_id": publish_id})
    else:
        if publish_id:
            print(f"\n{GREEN}Video posted! publish_id: {publish_id}{RESET}")
            print(f"  Check status: tiktok post-status {publish_id}\n")
        else:
            print(f"\n{YELLOW}Post returned (dry-run or pending){RESET}\n")
    return 0


def cmd_upload_video(clients: TikTokClients, args: argparse.Namespace) -> int:
    """Upload a local video file in chunks."""
    assert clients.content is not None
    file_path = Path(args.file)
    if not file_path.is_file():
        print(f"{RED}File not found: {args.file}{RESET}")
        return 1

    total_size = file_path.stat().st_size
    chunk_size = getattr(args, "chunk_size", 10_000_000)
    total_chunks = (total_size + chunk_size - 1) // chunk_size

    print(f"\n{BOLD}Uploading{RESET}: {file_path.name} ({total_size:,} bytes, {total_chunks} chunks)\n")

    publish_id, upload_url = clients.content.init_file_upload(total_size, chunk_size)
    if not upload_url:
        print(f"{RED}Failed to initialize upload{RESET}")
        return 1

    for i in range(total_chunks):
        ok = clients.content.upload_video_chunk(
            upload_url, str(file_path), i, chunk_size, total_size,
        )
        status = f"{GREEN}OK{RESET}" if ok else f"{RED}FAIL{RESET}"
        print(f"  Chunk {i + 1}/{total_chunks}: {status}")
        if not ok:
            print(f"\n{RED}Upload failed at chunk {i + 1}{RESET}\n")
            return 1

    if args.json:
        _json_output({"publish_id": publish_id, "chunks": total_chunks})
    else:
        print(f"\n{GREEN}Upload complete! publish_id: {publish_id}{RESET}")
        print(f"  Check status: tiktok post-status {publish_id}\n")
    return 0


def cmd_post_status(clients: TikTokClients, args: argparse.Namespace) -> int:
    """Check status of a video post."""
    assert clients.content is not None
    status = clients.content.get_post_status(args.publish_id)

    if args.json:
        _json_output(_dc_to_dict(status))
        return 0

    color = GREEN if status.status == "PUBLISH_COMPLETE" else YELLOW
    print(f"\n{BOLD}Post Status{RESET}\n")
    print(f"  Publish ID:  {status.publish_id}")
    print(f"  Status:      {color}{status.status}{RESET}")
    if status.uploaded_bytes:
        print(f"  Uploaded:    {status.uploaded_bytes:,} bytes")
    if status.error_code:
        print(f"  Error:       {RED}{status.error_code}{RESET}")
    if status.error_message:
        print(f"  Message:     {status.error_message}")
    print()
    return 0


# ---------------------------------------------------------------------------
# Command Handlers - Content Auth
# ---------------------------------------------------------------------------

def cmd_auth_content(clients: TikTokClients, args: argparse.Namespace) -> int:
    """Manage Content OAuth tokens."""
    creds = BrandCredentialLoader(clients.brand)
    app_id = creds.require("TIKTOK_CONTENT_APP_ID",
                           f"ecommerce/{clients.brand}/tiktok-content",
                           "TikTok Content App ID")
    app_secret = creds.require("TIKTOK_CONTENT_APP_SECRET",
                               f"ecommerce/{clients.brand}/tiktok-content",
                               "TikTok Content App Secret")
    oauth = TikTokOAuth(app_id, app_secret)

    if getattr(args, "generate_url", False):
        scopes = None
        if getattr(args, "scopes", None):
            scopes = [s.strip() for s in args.scopes.split(",")]
        url = oauth.get_content_auth_url(scopes=scopes)
        print(f"\n{BOLD}Content Authorization URL:{RESET}\n")
        print(f"  {CYAN}{url}{RESET}\n")
        print(f"  After authorizing, run:")
        print(f"  {DIM}tiktok auth-content --code <AUTH_CODE> --brand {clients.brand}{RESET}\n")
        return 0

    if getattr(args, "code", None):
        data = oauth.exchange_content_code(args.code)
        access_token = data.get("access_token", "")
        refresh_token = data.get("refresh_token", "")

        svc_token = f"ecommerce/{clients.brand}/tiktok-content"
        svc_refresh = f"ecommerce/{clients.brand}/tiktok-content-refresh"
        BrandCredentialLoader.keychain_write(svc_token, clients.brand, access_token)
        if refresh_token:
            BrandCredentialLoader.keychain_write(svc_refresh, clients.brand, refresh_token)

        if args.json:
            _json_output({"success": True, "access_token_prefix": access_token[:12] + "..."})
        else:
            print(f"\n{GREEN}Content tokens stored in Keychain{RESET}")
            print(f"  Access token:  {access_token[:12]}...")
            if refresh_token:
                print(f"  Refresh token: {refresh_token[:12]}...")
            print(f"  Keychain svc:  {svc_token}\n")
        return 0

    if getattr(args, "refresh", False):
        svc_refresh = f"ecommerce/{clients.brand}/tiktok-content-refresh"
        refresh_token = creds.get("TIKTOK_CONTENT_REFRESH_TOKEN", svc_refresh)
        if not refresh_token:
            print(f"{RED}No refresh token found. Run auth-content --generate-url first.{RESET}")
            return 1

        data = oauth.refresh_content_token(refresh_token)
        new_access = data.get("access_token", "")
        new_refresh = data.get("refresh_token", "")

        svc_token = f"ecommerce/{clients.brand}/tiktok-content"
        BrandCredentialLoader.keychain_write(svc_token, clients.brand, new_access)
        if new_refresh:
            BrandCredentialLoader.keychain_write(svc_refresh, clients.brand, new_refresh)

        if args.json:
            _json_output({"success": True, "access_token_prefix": new_access[:12] + "..."})
        else:
            print(f"\n{GREEN}Content tokens refreshed and stored{RESET}")
            print(f"  New access token: {new_access[:12]}...\n")
        return 0

    print(f"{YELLOW}Use --generate-url, --code <AUTH_CODE>, or --refresh{RESET}")
    return 2


# ---------------------------------------------------------------------------
# CLI Parser
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser with all subcommands."""
    shared = argparse.ArgumentParser(add_help=False)
    shared.add_argument("-v", "--verbose", action="store_true", help="Enable verbose logging")
    shared.add_argument("--json", action="store_true", help="Output results as JSON")
    shared.add_argument("--dry-run", action="store_true",
                        help="Preview write operations without making changes")
    shared.add_argument("--brand", help="Brand name (from capsules/ecommerce/brands/)")

    parser = argparse.ArgumentParser(
        prog="tiktok",
        parents=[shared],
        description=(
            f"TikTok Unified CLI v{VERSION}\n"
            "Shop, Marketing, and Content Posting APIs for multi-brand e-commerce."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Shop examples:\n"
            "  %(prog)s status --brand rawhide-organics\n"
            "  %(prog)s products --limit 10\n"
            "  %(prog)s product-detail <PRODUCT_ID>\n"
            "  %(prog)s orders --status AWAITING_SHIPMENT\n"
            "  %(prog)s fulfill-order <ORDER_ID> --tracking TRK123 --provider-id 1234\n"
            "  %(prog)s auth-shop --generate-url\n"
            "\n"
            "Marketing examples:\n"
            "  %(prog)s campaigns --brand asset-labs\n"
            "  %(prog)s create-campaign --name 'Summer Sale' --objective CONVERSIONS --budget 500\n"
            "  %(prog)s reports --dimensions campaign_id --metrics spend,impressions \\\n"
            "             --start-date 2026-01-01 --end-date 2026-01-31\n"
            "  %(prog)s auth-marketing --generate-url\n"
            "\n"
            "Content examples:\n"
            "  %(prog)s creator-info\n"
            "  %(prog)s post-video --url https://example.com/video.mp4 --title 'Check this out'\n"
            "  %(prog)s upload-video --file /path/to/video.mp4\n"
            "  %(prog)s post-status <PUBLISH_ID>\n"
            "  %(prog)s auth-content --generate-url\n"
            "\n"
            "Credentials are loaded per-brand from .env files and macOS Keychain.\n"
        ),
    )

    sub = parser.add_subparsers(dest="command", help="Available commands")

    # === Shop commands ===

    sub.add_parser("status", parents=[shared], help="Show Shop connection status")

    p = sub.add_parser("products", parents=[shared], help="List products")
    p.add_argument("--status", default="", help="Filter by status (LIVE, DRAFT, etc.)")
    p.add_argument("--limit", type=int, default=20, help="Max results (default: 20)")
    p.add_argument("--page-token", default="", help="Pagination token")

    p = sub.add_parser("product-detail", parents=[shared], help="Show product details")
    p.add_argument("product_id", help="Product ID")

    p = sub.add_parser("create-product", parents=[shared], help="Create a product")
    p.add_argument("--from-file", required=True, help="JSON file with product data")

    p = sub.add_parser("update-product", parents=[shared], help="Update a product")
    p.add_argument("product_id", help="Product ID to update")
    p.add_argument("--from-file", required=True, help="JSON file with update data")

    p = sub.add_parser("orders", parents=[shared], help="List orders")
    p.add_argument("--status", default="", help="Filter by status")
    p.add_argument("--limit", type=int, default=20, help="Max results (default: 20)")
    p.add_argument("--page-token", default="", help="Pagination token")

    p = sub.add_parser("order-detail", parents=[shared], help="Show order details")
    p.add_argument("order_id", help="Order ID")

    p = sub.add_parser("fulfill-order", parents=[shared], help="Fulfill order with tracking")
    p.add_argument("order_id", help="Order ID")
    p.add_argument("--tracking-number", required=True, help="Tracking number")
    p.add_argument("--shipping-provider-id", required=True, help="Shipping provider ID")

    p = sub.add_parser("inventory", parents=[shared], help="Show inventory for a product")
    p.add_argument("product_id", help="Product ID")

    p = sub.add_parser("update-inventory", parents=[shared], help="Update SKU inventory")
    p.add_argument("--sku-id", required=True, help="SKU ID")
    p.add_argument("--warehouse-id", required=True, help="Warehouse ID")
    p.add_argument("--quantity", type=int, required=True, help="New quantity")

    p = sub.add_parser("auth-shop", parents=[shared], help="Manage Shop OAuth tokens")
    auth_grp = p.add_mutually_exclusive_group()
    auth_grp.add_argument("--generate-url", action="store_true", help="Print authorization URL")
    auth_grp.add_argument("--code", help="Exchange authorization code for tokens")
    auth_grp.add_argument("--refresh", action="store_true", help="Refresh access token")

    # === Marketing commands ===

    p = sub.add_parser("campaigns", parents=[shared], help="List ad campaigns")
    p.add_argument("--status", default="", help="Filter by status")
    p.add_argument("--page", type=int, default=1, help="Page number")
    p.add_argument("--limit", type=int, default=20, help="Page size")

    p = sub.add_parser("campaign-detail", parents=[shared], help="Show campaign details")
    p.add_argument("campaign_id", help="Campaign ID")

    p = sub.add_parser("create-campaign", parents=[shared], help="Create a campaign")
    p.add_argument("--name", required=True, help="Campaign name")
    p.add_argument("--objective", required=True,
                   help="Objective type (CONVERSIONS, TRAFFIC, REACH, etc.)")
    p.add_argument("--budget", required=True, help="Budget amount")
    p.add_argument("--budget-mode", default="BUDGET_MODE_TOTAL",
                   help="Budget mode (default: BUDGET_MODE_TOTAL)")

    p = sub.add_parser("ad-groups", parents=[shared], help="List ad groups")
    p.add_argument("--campaign-id", default="", help="Filter by campaign ID")
    p.add_argument("--page", type=int, default=1, help="Page number")
    p.add_argument("--limit", type=int, default=20, help="Page size")

    p = sub.add_parser("create-ad-group", parents=[shared], help="Create an ad group")
    p.add_argument("--campaign-id", required=True, help="Parent campaign ID")
    p.add_argument("--name", required=True, help="Ad group name")
    p.add_argument("--budget", required=True, help="Budget amount")
    p.add_argument("--schedule-start", required=True, help="Start time (YYYY-MM-DD HH:MM:SS)")
    p.add_argument("--placement", default="PLACEMENT_TYPE_AUTOMATIC",
                   help="Placement type (default: PLACEMENT_TYPE_AUTOMATIC)")

    p = sub.add_parser("ads", parents=[shared], help="List ads")
    p.add_argument("--adgroup-id", default="", help="Filter by ad group ID")
    p.add_argument("--page", type=int, default=1, help="Page number")
    p.add_argument("--limit", type=int, default=20, help="Page size")

    p = sub.add_parser("create-ad", parents=[shared], help="Create an ad")
    p.add_argument("--adgroup-id", required=True, help="Parent ad group ID")
    p.add_argument("--name", required=True, help="Ad name")
    p.add_argument("--format", default="SINGLE_VIDEO", help="Ad format (default: SINGLE_VIDEO)")
    p.add_argument("--creative-file", required=True, help="JSON file with creative data")

    sub.add_parser("audiences", parents=[shared], help="List custom audiences")

    p = sub.add_parser("reports", parents=[shared], help="Generate performance report")
    p.add_argument("--report-type", default="BASIC", help="Report type (default: BASIC)")
    p.add_argument("--dimensions", required=True, help="Comma-separated dimension keys")
    p.add_argument("--metrics", required=True, help="Comma-separated metric keys")
    p.add_argument("--start-date", required=True, help="Start date (YYYY-MM-DD)")
    p.add_argument("--end-date", required=True, help="End date (YYYY-MM-DD)")

    p = sub.add_parser("auth-marketing", parents=[shared], help="Manage Marketing OAuth tokens")
    auth_grp = p.add_mutually_exclusive_group()
    auth_grp.add_argument("--generate-url", action="store_true", help="Print authorization URL")
    auth_grp.add_argument("--code", help="Exchange authorization code for tokens")

    # === Content commands ===

    sub.add_parser("creator-info", parents=[shared], help="Show creator info and capabilities")

    p = sub.add_parser("post-video", parents=[shared], help="Post a video by URL")
    p.add_argument("--url", dest="video_url", required=True, help="Public video URL")
    p.add_argument("--title", required=True, help="Video title/caption")
    p.add_argument("--privacy", default="SELF_ONLY",
                   help="Privacy level (SELF_ONLY, MUTUAL_FOLLOW_FRIENDS, FOLLOWER_OF_CREATOR, PUBLIC_TO_EVERYONE)")
    p.add_argument("--disable-comment", action="store_true", help="Disable comments")
    p.add_argument("--disable-duet", action="store_true", help="Disable duets")
    p.add_argument("--disable-stitch", action="store_true", help="Disable stitches")
    p.add_argument("--aigc", action="store_true", help="Mark as AI-generated content")

    p = sub.add_parser("upload-video", parents=[shared], help="Upload a local video file")
    p.add_argument("--file", required=True, help="Path to video file")
    p.add_argument("--chunk-size", type=int, default=10_000_000, help="Chunk size in bytes (default: 10MB)")

    p = sub.add_parser("post-status", parents=[shared], help="Check video post status")
    p.add_argument("publish_id", help="Publish ID from post or upload")

    p = sub.add_parser("auth-content", parents=[shared], help="Manage Content OAuth tokens")
    auth_grp = p.add_mutually_exclusive_group()
    auth_grp.add_argument("--generate-url", action="store_true", help="Print authorization URL")
    auth_grp.add_argument("--code", help="Exchange authorization code for tokens")
    auth_grp.add_argument("--refresh", action="store_true", help="Refresh access token")
    p.add_argument("--scopes", help="Comma-separated scopes (for --generate-url)")

    return parser


# ---------------------------------------------------------------------------
# Command Dispatch
# ---------------------------------------------------------------------------

SHOP_COMMANDS = {
    "status": cmd_status,
    "products": cmd_products,
    "product-detail": cmd_product_detail,
    "create-product": cmd_create_product,
    "update-product": cmd_update_product,
    "orders": cmd_orders,
    "order-detail": cmd_order_detail,
    "fulfill-order": cmd_fulfill_order,
    "inventory": cmd_inventory,
    "update-inventory": cmd_update_inventory,
    "auth-shop": cmd_auth_shop,
}

MARKETING_COMMANDS = {
    "campaigns": cmd_campaigns,
    "campaign-detail": cmd_campaign_detail,
    "create-campaign": cmd_create_campaign,
    "ad-groups": cmd_ad_groups,
    "create-ad-group": cmd_create_ad_group,
    "ads": cmd_ads,
    "create-ad": cmd_create_ad,
    "audiences": cmd_audiences,
    "reports": cmd_reports,
    "auth-marketing": cmd_auth_marketing,
}

CONTENT_COMMANDS = {
    "creator-info": cmd_creator_info,
    "post-video": cmd_post_video,
    "upload-video": cmd_upload_video,
    "post-status": cmd_post_status,
    "auth-content": cmd_auth_content,
}

ALL_COMMANDS = {**SHOP_COMMANDS, **MARKETING_COMMANDS, **CONTENT_COMMANDS}

# Auth commands that skip client initialization
AUTH_COMMANDS = {"auth-shop", "auth-marketing", "auth-content"}


# ---------------------------------------------------------------------------
# Client initialization (lazy)
# ---------------------------------------------------------------------------

def _init_shop_client(brand: str, dry_run: bool) -> TikTokShopClient:
    """Initialize TikTok Shop client with brand credentials."""
    creds = BrandCredentialLoader(brand)
    app_key = creds.require("TIKTOK_SHOP_APP_KEY",
                            f"ecommerce/{brand}/tiktok-shop",
                            "TikTok Shop App Key")
    app_secret = creds.require("TIKTOK_SHOP_APP_SECRET",
                               f"ecommerce/{brand}/tiktok-shop",
                               "TikTok Shop App Secret")
    access_token = creds.require("TIKTOK_SHOP_ACCESS_TOKEN",
                                 f"ecommerce/{brand}/tiktok-shop-token",
                                 "TikTok Shop Access Token")
    shop_cipher = creds.get("TIKTOK_SHOP_CIPHER") or ""

    auth = TikTokShopAuth(app_key, app_secret)
    return TikTokShopClient(auth, access_token, shop_cipher, dry_run=dry_run)


def _init_marketing_client(brand: str, dry_run: bool) -> TikTokMarketingClient:
    """Initialize TikTok Marketing client with brand credentials."""
    creds = BrandCredentialLoader(brand)
    access_token = creds.require("TIKTOK_ADS_ACCESS_TOKEN",
                                 f"ecommerce/{brand}/tiktok-ads",
                                 "TikTok Ads Access Token")
    advertiser_id = creds.require("TIKTOK_ADS_ADVERTISER_ID",
                                  label="TikTok Ads Advertiser ID")
    return TikTokMarketingClient(access_token, advertiser_id, dry_run=dry_run)


def _init_content_client(brand: str, dry_run: bool) -> TikTokContentClient:
    """Initialize TikTok Content client with brand credentials."""
    creds = BrandCredentialLoader(brand)
    access_token = creds.require("TIKTOK_CONTENT_ACCESS_TOKEN",
                                 f"ecommerce/{brand}/tiktok-content",
                                 "TikTok Content Access Token")
    return TikTokContentClient(access_token, dry_run=dry_run)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> int:
    """CLI entry point."""
    parser = build_parser()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    # Configure logging
    log_level = logging.DEBUG if args.verbose else logging.WARNING
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    command = args.command
    handler = ALL_COMMANDS.get(command)
    if not handler:
        parser.print_help()
        return 1

    try:
        # Resolve brand (auth commands still need it for credential lookup)
        brand = _resolve_brand(getattr(args, "brand", None))
        dry_run = getattr(args, "dry_run", False)

        # Build clients container with lazy init
        clients = TikTokClients(brand=brand, dry_run=dry_run)

        # Only init the needed client (skip for auth commands)
        if command not in AUTH_COMMANDS:
            if command in SHOP_COMMANDS:
                clients.shop = _init_shop_client(brand, dry_run)
            elif command in MARKETING_COMMANDS:
                clients.marketing = _init_marketing_client(brand, dry_run)
            elif command in CONTENT_COMMANDS:
                clients.content = _init_content_client(brand, dry_run)

        return handler(clients, args)

    except TikTokCredentialError as e:
        if args.json:
            _json_output({"error": str(e), "type": "credential_error"})
        else:
            print(f"\n{RED}Credential error.{RESET}\n")
            print(f"{e}")
            print(f"\n{YELLOW}Set credentials in brand .env or macOS Keychain.{RESET}")
        return 1

    except TikTokTokenExpiredError as e:
        if args.json:
            _json_output({"error": str(e), "type": "token_expired"})
        else:
            print(f"\n{RED}Token expired.{RESET}\n")
            print(f"{e}")
            print(f"\n{YELLOW}Refresh with: tiktok auth-shop --refresh --brand <brand>{RESET}")
        return 1

    except TikTokAuthError as e:
        if args.json:
            _json_output({"error": str(e), "type": "auth_error"})
        else:
            print(f"\n{RED}Authentication error.{RESET}\n")
            print(f"{e}")
        return 1

    except TikTokRateLimitError as e:
        if args.json:
            _json_output({"error": str(e), "type": "rate_limit",
                          "retry_after": e.retry_after})
        else:
            print(f"\n{YELLOW}Rate limited.{RESET}")
            print(f"{e}")
            if e.retry_after:
                print(f"Retry after {e.retry_after}s")
        return 1

    except TikTokShopAPIError as e:
        if args.json:
            _json_output({"error": str(e), "type": "shop_api_error",
                          "code": e.code, "request_id": e.request_id})
        else:
            print(f"\n{RED}Shop API error (code={e.code}).{RESET}")
            print(f"{e}")
            if e.request_id:
                print(f"{DIM}Request ID: {e.request_id}{RESET}")
        return 1

    except TikTokMarketingAPIError as e:
        if args.json:
            _json_output({"error": str(e), "type": "marketing_api_error",
                          "code": e.code, "request_id": e.request_id})
        else:
            print(f"\n{RED}Marketing API error (code={e.code}).{RESET}")
            print(f"{e}")
            if e.request_id:
                print(f"{DIM}Request ID: {e.request_id}{RESET}")
        return 1

    except TikTokContentAPIError as e:
        if args.json:
            _json_output({"error": str(e), "type": "content_api_error"})
        else:
            print(f"\n{RED}Content API error.{RESET}")
            print(f"{e}")
        return 1

    except KeyboardInterrupt:
        print(f"\n{YELLOW}Interrupted{RESET}")
        return 130

    except Exception as e:
        logger.debug("Unhandled exception", exc_info=True)
        if args.json:
            _json_output({"error": str(e), "type": "unexpected_error"})
        else:
            print(f"\n{RED}Error: {e}{RESET}")
            if args.verbose:
                import traceback
                traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
