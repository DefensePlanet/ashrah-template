#!/usr/bin/env python3
"""
Proton Mail CLI for Catalyst

Interfaces with Proton Mail via Proton Mail Bridge (IMAP/SMTP on localhost):
- Read, search, and manage email messages
- Send, reply, and forward emails with attachments
- Manage folders, flags, and message organization
- Download attachments

Proton Mail Bridge must be running for all operations.

Credentials:
    PROTON_EMAIL            - Email address (or macOS Keychain "proton-bridge" account)
    PROTON_BRIDGE_PASSWORD  - Bridge password (or macOS Keychain "proton-bridge" password)

Connection:
    IMAP: 127.0.0.1:1143 (STARTTLS)
    SMTP: 127.0.0.1:1025 (STARTTLS)

Dependencies: Python stdlib only (no pip packages).
"""

import argparse
import base64
import email
import email.encoders
import email.header
import email.mime.application
import email.mime.base
import email.mime.multipart
import email.mime.text
import email.utils
import html.parser
import imaplib
import json
import logging
import mimetypes
import os
import re
import smtplib
import ssl
import subprocess
import sys
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

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
# Constants
# ---------------------------------------------------------------------------
IMAP_HOST = "127.0.0.1"
IMAP_PORT = 1143
SMTP_HOST = "127.0.0.1"
SMTP_PORT = 1025
DEFAULT_TIMEOUT = 30
DEFAULT_LIMIT = 20
KEYCHAIN_SERVICE = "proton-bridge"

# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class ProtonMailError(Exception):
    """Base exception for all Proton Mail errors."""
    pass

class BridgeNotRunningError(ProtonMailError):
    """Proton Mail Bridge is not running or unreachable."""
    pass

class AuthenticationError(ProtonMailError):
    """IMAP/SMTP authentication failed."""
    pass

class FolderNotFoundError(ProtonMailError):
    """Requested folder does not exist."""
    pass

class MessageNotFoundError(ProtonMailError):
    """Requested message UID was not found."""
    pass

class CredentialError(ProtonMailError):
    """Could not load credentials from env or Keychain."""
    pass

class SendError(ProtonMailError):
    """Failed to send an email."""
    pass

# ---------------------------------------------------------------------------
# HTML to text converter (stdlib only)
# ---------------------------------------------------------------------------

class _HTMLTextExtractor(html.parser.HTMLParser):
    """Minimal HTML to text converter using stdlib html.parser."""

    BLOCK_TAGS = {"p", "div", "br", "h1", "h2", "h3", "h4", "h5", "h6",
                  "li", "tr", "blockquote", "pre", "hr", "table"}
    SKIP_TAGS = {"script", "style", "head"}

    def __init__(self):
        super().__init__()
        self._chunks: List[str] = []
        self._skip = False

    def handle_starttag(self, tag: str, attrs: list) -> None:
        tag_lower = tag.lower()
        if tag_lower in self.SKIP_TAGS:
            self._skip = True
        if tag_lower in self.BLOCK_TAGS:
            self._chunks.append("\n")
        if tag_lower == "a":
            for name, val in attrs:
                if name == "href" and val:
                    self._chunks.append(f" [{val}] ")
                    break

    def handle_endtag(self, tag: str) -> None:
        tag_lower = tag.lower()
        if tag_lower in self.SKIP_TAGS:
            self._skip = False
        if tag_lower in self.BLOCK_TAGS:
            self._chunks.append("\n")

    def handle_data(self, data: str) -> None:
        if not self._skip:
            self._chunks.append(data)

    def get_text(self) -> str:
        text = "".join(self._chunks)
        # Collapse multiple blank lines
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()


def html_to_text(html_content: str) -> str:
    """Convert HTML to readable plain text."""
    parser = _HTMLTextExtractor()
    try:
        parser.feed(html_content)
        return parser.get_text()
    except Exception:
        # Fallback: strip tags with regex
        text = re.sub(r"<[^>]+>", " ", html_content)
        return re.sub(r"\s+", " ", text).strip()

# ---------------------------------------------------------------------------
# Structured result types
# ---------------------------------------------------------------------------

@dataclass
class FolderInfo:
    name: str
    total: int
    unread: int

@dataclass
class MessageSummary:
    uid: int
    from_addr: str
    subject: str
    date: str
    is_unread: bool
    has_attachments: bool

@dataclass
class AttachmentInfo:
    index: int
    filename: str
    content_type: str
    size: int

@dataclass
class MessageDetail:
    uid: int
    from_addr: str
    to_addr: str
    cc: str
    date: str
    subject: str
    body_text: str
    body_html: str
    attachments: List[AttachmentInfo]
    headers: Dict[str, str]
    message_id: str
    in_reply_to: str
    references: str
    is_unread: bool

@dataclass
class StatusInfo:
    connected: bool
    email: str
    imap_host: str
    imap_port: int
    smtp_host: str
    smtp_port: int
    folder_count: int
    total_messages: int

# ---------------------------------------------------------------------------
# Credential loading
# ---------------------------------------------------------------------------

def _load_credentials() -> Tuple[str, str]:
    """
    Load Proton Bridge credentials.

    Priority:
        1. Environment variables PROTON_EMAIL / PROTON_BRIDGE_PASSWORD
        2. macOS Keychain entry for service "proton-bridge"

    Returns (username, password). Never logs the password.
    """
    username = os.environ.get("PROTON_EMAIL", "").strip()
    password = os.environ.get("PROTON_BRIDGE_PASSWORD", "").strip()

    if username and password:
        logger.debug("Credentials loaded from environment variables")
        return username, password

    # Try macOS Keychain
    logger.debug("Trying macOS Keychain for credentials")
    try:
        if not username:
            result = subprocess.run(
                ["security", "find-generic-password", "-s", KEYCHAIN_SERVICE, "-g"],
                capture_output=True, text=True, timeout=5,
            )
            # Parse account from output: "acct"<blob>="user@email.com"
            for line in result.stderr.splitlines() + result.stdout.splitlines():
                match = re.search(r'"acct"<blob>="([^"]+)"', line)
                if match:
                    username = match.group(1)
                    break
            if not username:
                # Try "acct" with hex encoding
                for line in result.stderr.splitlines() + result.stdout.splitlines():
                    match = re.search(r'"acct"<blob>=0x([0-9A-Fa-f]+)', line)
                    if match:
                        username = bytes.fromhex(match.group(1)).decode("utf-8")
                        break

        if not password:
            result = subprocess.run(
                ["security", "find-generic-password", "-s", KEYCHAIN_SERVICE, "-w"],
                capture_output=True, text=True, timeout=5,
            )
            if result.returncode == 0:
                password = result.stdout.strip()

    except (subprocess.TimeoutExpired, FileNotFoundError, OSError) as e:
        logger.debug("Keychain lookup failed: %s", e)

    if not username:
        raise CredentialError(
            "No Proton email found. Set PROTON_EMAIL env var or store "
            f"credentials in macOS Keychain under service '{KEYCHAIN_SERVICE}'."
        )
    if not password:
        raise CredentialError(
            "No Proton Bridge password found. Set PROTON_BRIDGE_PASSWORD env var or "
            f"store credentials in macOS Keychain under service '{KEYCHAIN_SERVICE}'."
        )

    logger.debug("Credentials loaded from macOS Keychain (user: %s)", username)
    return username, password

# ---------------------------------------------------------------------------
# MIME header decoding
# ---------------------------------------------------------------------------

def _decode_header(raw: Optional[str]) -> str:
    """Decode RFC 2047 encoded email header into a UTF-8 string."""
    if not raw:
        return ""
    parts = email.header.decode_header(raw)
    decoded = []
    for data, charset in parts:
        if isinstance(data, bytes):
            decoded.append(data.decode(charset or "utf-8", errors="replace"))
        else:
            decoded.append(str(data))
    return " ".join(decoded)


def _parse_date(raw: Optional[str]) -> str:
    """Parse email date header into local time string."""
    if not raw:
        return ""
    try:
        parsed = email.utils.parsedate_to_datetime(raw)
        local = parsed.astimezone()
        return local.strftime("%Y-%m-%d %H:%M")
    except Exception:
        return raw.strip()


def _format_size(size_bytes: int) -> str:
    """Format byte size to human-readable string."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.0f} KB"
    else:
        return f"{size_bytes / (1024 * 1024):.1f} MB"

# ---------------------------------------------------------------------------
# ProtonBridgeClient - IMAP/SMTP operations
# ---------------------------------------------------------------------------

class ProtonBridgeClient:
    """
    Handles all IMAP and SMTP operations against Proton Mail Bridge.

    Maintains a reusable IMAP connection for the duration of a CLI invocation.
    SMTP connections are created per-send (short-lived).
    """

    def __init__(
        self,
        timeout: int = DEFAULT_TIMEOUT,
        dry_run: bool = False,
    ):
        self._timeout = timeout
        self._dry_run = dry_run
        self._imap: Optional[imaplib.IMAP4] = None
        self._username: Optional[str] = None
        self._email: Optional[str] = None
        self._ssl_ctx = self._create_ssl_context()

    @staticmethod
    def _create_ssl_context() -> ssl.SSLContext:
        """Create SSL context for Proton Bridge self-signed cert."""
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        return ctx

    # --- Connection management ---

    def _connect_imap(self) -> imaplib.IMAP4:
        """Establish IMAP connection with STARTTLS."""
        if self._imap is not None:
            try:
                self._imap.noop()
                return self._imap
            except Exception:
                self._imap = None

        username, password = _load_credentials()
        self._username = username
        self._email = username

        logger.debug("Connecting to IMAP %s:%d", IMAP_HOST, IMAP_PORT)
        try:
            imap = imaplib.IMAP4(IMAP_HOST, IMAP_PORT)
            imap.socket().settimeout(self._timeout)
        except (ConnectionRefusedError, OSError) as e:
            raise BridgeNotRunningError(
                f"Cannot connect to Proton Mail Bridge IMAP at {IMAP_HOST}:{IMAP_PORT}.\n"
                "Ensure Proton Mail Bridge is running and logged in."
            ) from e

        try:
            imap.starttls(ssl_context=self._ssl_ctx)
        except Exception as e:
            raise BridgeNotRunningError(
                f"STARTTLS failed on IMAP connection: {e}\n"
                "Ensure Proton Mail Bridge is running correctly."
            ) from e

        try:
            imap.login(username, password)
        except imaplib.IMAP4.error as e:
            raise AuthenticationError(
                "IMAP authentication failed. Check your Bridge password.\n"
                f"IMAP error: {e}"
            ) from e

        self._imap = imap
        logger.debug("IMAP connected and authenticated as %s", username)
        return imap

    def _connect_smtp(self) -> smtplib.SMTP:
        """Establish SMTP connection with STARTTLS."""
        username, password = _load_credentials()

        logger.debug("Connecting to SMTP %s:%d", SMTP_HOST, SMTP_PORT)
        try:
            server = smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=self._timeout)
        except (ConnectionRefusedError, OSError) as e:
            raise BridgeNotRunningError(
                f"Cannot connect to Proton Mail Bridge SMTP at {SMTP_HOST}:{SMTP_PORT}.\n"
                "Ensure Proton Mail Bridge is running and logged in."
            ) from e

        try:
            server.starttls(context=self._ssl_ctx)
        except Exception as e:
            raise BridgeNotRunningError(
                f"STARTTLS failed on SMTP connection: {e}\n"
                "Ensure Proton Mail Bridge is running correctly."
            ) from e

        try:
            server.login(username, password)
        except smtplib.SMTPAuthenticationError as e:
            raise AuthenticationError(
                "SMTP authentication failed. Check your Bridge password."
            ) from e

        logger.debug("SMTP connected and authenticated")
        return server

    def close(self) -> None:
        """Close IMAP connection gracefully."""
        if self._imap:
            try:
                self._imap.close()
            except Exception:
                pass
            try:
                self._imap.logout()
            except Exception:
                pass
            self._imap = None

    # --- Folder operations ---

    def list_folders(self) -> List[FolderInfo]:
        """List all IMAP folders with message counts."""
        imap = self._connect_imap()
        status, data = imap.list()
        if status != "OK":
            raise ProtonMailError("Failed to list folders")

        folders = []
        for item in data:
            if item is None:
                continue
            decoded = item.decode("utf-8") if isinstance(item, bytes) else str(item)
            # Parse: (\HasNoChildren) "/" "FolderName"
            match = re.search(r'"([^"]*)"$|(\S+)$', decoded)
            if not match:
                continue
            folder_name = match.group(1) or match.group(2)

            # Get status for each folder
            try:
                st, st_data = imap.status(
                    f'"{folder_name}"', "(MESSAGES UNSEEN)"
                )
                total = 0
                unread = 0
                if st == "OK" and st_data and st_data[0]:
                    info = st_data[0].decode("utf-8") if isinstance(st_data[0], bytes) else str(st_data[0])
                    m_total = re.search(r"MESSAGES\s+(\d+)", info)
                    m_unseen = re.search(r"UNSEEN\s+(\d+)", info)
                    if m_total:
                        total = int(m_total.group(1))
                    if m_unseen:
                        unread = int(m_unseen.group(1))
                folders.append(FolderInfo(name=folder_name, total=total, unread=unread))
            except Exception as e:
                logger.debug("Failed to get status for folder %s: %s", folder_name, e)
                folders.append(FolderInfo(name=folder_name, total=0, unread=0))

        return folders

    def _select_folder(self, folder: str, readonly: bool = True) -> int:
        """Select an IMAP folder. Returns message count."""
        imap = self._connect_imap()
        status, data = imap.select(f'"{folder}"', readonly=readonly)
        if status != "OK":
            raise FolderNotFoundError(f"Folder not found: {folder}")
        count = int(data[0]) if data and data[0] else 0
        logger.debug("Selected folder '%s' (%d messages, readonly=%s)", folder, count, readonly)
        return count

    # --- Search / fetch ---

    def _search(self, folder: str, criteria: str) -> List[int]:
        """Search a folder and return list of UIDs matching criteria."""
        self._select_folder(folder, readonly=True)
        imap = self._connect_imap()
        status, data = imap.uid("SEARCH", None, criteria)
        if status != "OK":
            return []
        if not data or not data[0]:
            return []
        uid_list = [int(uid) for uid in data[0].split()]
        return uid_list

    def _fetch_envelope(self, uid: int) -> Optional[MessageSummary]:
        """Fetch envelope data for a single UID (lightweight)."""
        imap = self._connect_imap()
        status, data = imap.uid("FETCH", str(uid), "(FLAGS BODY.PEEK[HEADER.FIELDS (FROM SUBJECT DATE)])")
        if status != "OK" or not data or data[0] is None:
            return None

        # Parse flags and header
        flags_str = ""
        header_bytes = b""
        for part in data:
            if isinstance(part, tuple):
                meta = part[0].decode("utf-8", errors="replace") if isinstance(part[0], bytes) else str(part[0])
                flags_match = re.search(r"FLAGS \(([^)]*)\)", meta)
                if flags_match:
                    flags_str = flags_match.group(1)
                header_bytes = part[1] if len(part) > 1 else b""

        msg = email.message_from_bytes(header_bytes)
        is_unread = "\\Seen" not in flags_str

        from_addr = _decode_header(msg.get("From", ""))
        subject = _decode_header(msg.get("Subject", "(no subject)"))
        date_str = _parse_date(msg.get("Date", ""))

        return MessageSummary(
            uid=uid,
            from_addr=from_addr,
            subject=subject,
            date=date_str,
            is_unread=is_unread,
            has_attachments=False,  # Would need full fetch to determine
        )

    def _fetch_full(self, uid: int, folder: str = "INBOX") -> MessageDetail:
        """Fetch full message by UID."""
        self._select_folder(folder, readonly=True)
        imap = self._connect_imap()
        status, data = imap.uid("FETCH", str(uid), "(FLAGS RFC822)")
        if status != "OK" or not data or data[0] is None:
            raise MessageNotFoundError(f"Message UID {uid} not found in folder '{folder}'")

        # Extract raw message and flags
        flags_str = ""
        raw_bytes = b""
        for part in data:
            if isinstance(part, tuple):
                meta = part[0].decode("utf-8", errors="replace") if isinstance(part[0], bytes) else str(part[0])
                flags_match = re.search(r"FLAGS \(([^)]*)\)", meta)
                if flags_match:
                    flags_str = flags_match.group(1)
                raw_bytes = part[1] if len(part) > 1 else b""

        if not raw_bytes:
            raise MessageNotFoundError(f"Message UID {uid}: empty message data")

        msg = email.message_from_bytes(raw_bytes)

        # Extract headers
        from_addr = _decode_header(msg.get("From", ""))
        to_addr = _decode_header(msg.get("To", ""))
        cc = _decode_header(msg.get("Cc", ""))
        subject = _decode_header(msg.get("Subject", "(no subject)"))
        date_str = _parse_date(msg.get("Date", ""))
        message_id = msg.get("Message-ID", "")
        in_reply_to = msg.get("In-Reply-To", "")
        references = msg.get("References", "")
        is_unread = "\\Seen" not in flags_str

        # Extract all headers
        all_headers = {}
        for key in msg.keys():
            all_headers[key] = _decode_header(msg.get(key, ""))

        # Extract body and attachments
        body_text = ""
        body_html = ""
        attachments: List[AttachmentInfo] = []
        att_index = 0

        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                disposition = str(part.get("Content-Disposition", ""))

                if "attachment" in disposition.lower():
                    filename = part.get_filename()
                    if filename:
                        filename = _decode_header(filename)
                    else:
                        ext = mimetypes.guess_extension(content_type) or ".bin"
                        filename = f"attachment_{att_index}{ext}"
                    payload = part.get_payload(decode=True)
                    size = len(payload) if payload else 0
                    attachments.append(AttachmentInfo(
                        index=att_index,
                        filename=filename,
                        content_type=content_type,
                        size=size,
                    ))
                    att_index += 1
                elif content_type == "text/plain" and not body_text:
                    payload = part.get_payload(decode=True)
                    if payload:
                        charset = part.get_content_charset() or "utf-8"
                        body_text = payload.decode(charset, errors="replace")
                elif content_type == "text/html" and not body_html:
                    payload = part.get_payload(decode=True)
                    if payload:
                        charset = part.get_content_charset() or "utf-8"
                        body_html = payload.decode(charset, errors="replace")
                # Inline images count as attachments too
                elif "inline" in disposition.lower() and content_type.startswith("image/"):
                    filename = part.get_filename()
                    if filename:
                        filename = _decode_header(filename)
                    else:
                        ext = mimetypes.guess_extension(content_type) or ".bin"
                        filename = f"inline_{att_index}{ext}"
                    payload = part.get_payload(decode=True)
                    size = len(payload) if payload else 0
                    attachments.append(AttachmentInfo(
                        index=att_index,
                        filename=filename,
                        content_type=content_type,
                        size=size,
                    ))
                    att_index += 1
        else:
            content_type = msg.get_content_type()
            payload = msg.get_payload(decode=True)
            if payload:
                charset = msg.get_content_charset() or "utf-8"
                decoded = payload.decode(charset, errors="replace")
                if content_type == "text/html":
                    body_html = decoded
                else:
                    body_text = decoded

        return MessageDetail(
            uid=uid,
            from_addr=from_addr,
            to_addr=to_addr,
            cc=cc,
            date=date_str,
            subject=subject,
            body_text=body_text,
            body_html=body_html,
            attachments=attachments,
            headers=all_headers,
            message_id=message_id,
            in_reply_to=in_reply_to,
            references=references,
            is_unread=is_unread,
        )

    def _get_attachment_payload(self, uid: int, att_index: int, folder: str = "INBOX") -> Tuple[str, bytes]:
        """Fetch a specific attachment's raw data. Returns (filename, data)."""
        self._select_folder(folder, readonly=True)
        imap = self._connect_imap()
        status, data = imap.uid("FETCH", str(uid), "(RFC822)")
        if status != "OK" or not data or data[0] is None:
            raise MessageNotFoundError(f"Message UID {uid} not found")

        raw_bytes = b""
        for part in data:
            if isinstance(part, tuple) and len(part) > 1:
                raw_bytes = part[1]

        if not raw_bytes:
            raise MessageNotFoundError(f"Message UID {uid}: empty data")

        msg = email.message_from_bytes(raw_bytes)
        current_index = 0

        for part in msg.walk():
            disposition = str(part.get("Content-Disposition", ""))
            content_type = part.get_content_type()
            is_attachment = (
                "attachment" in disposition.lower()
                or ("inline" in disposition.lower() and content_type.startswith("image/"))
            )
            if is_attachment:
                if current_index == att_index:
                    filename = part.get_filename()
                    if filename:
                        filename = _decode_header(filename)
                    else:
                        ext = mimetypes.guess_extension(content_type) or ".bin"
                        filename = f"attachment_{att_index}{ext}"
                    payload = part.get_payload(decode=True) or b""
                    return filename, payload
                current_index += 1

        raise ProtonMailError(f"Attachment index {att_index} not found in message UID {uid}")

    # --- High-level operations ---

    def get_status(self) -> StatusInfo:
        """Check Bridge connection and return account status."""
        imap = self._connect_imap()
        folders = self.list_folders()
        total_messages = sum(f.total for f in folders)
        return StatusInfo(
            connected=True,
            email=self._email or "",
            imap_host=IMAP_HOST,
            imap_port=IMAP_PORT,
            smtp_host=SMTP_HOST,
            smtp_port=SMTP_PORT,
            folder_count=len(folders),
            total_messages=total_messages,
        )

    def list_messages(
        self,
        folder: str = "INBOX",
        unread_only: bool = False,
        from_filter: Optional[str] = None,
        subject_filter: Optional[str] = None,
        since: Optional[str] = None,
        before: Optional[str] = None,
        limit: int = DEFAULT_LIMIT,
    ) -> List[MessageSummary]:
        """List messages in a folder with optional filters."""
        # Build IMAP SEARCH criteria
        criteria_parts = []
        if unread_only:
            criteria_parts.append("UNSEEN")
        if from_filter:
            from_filter = from_filter.replace('\\', '').replace('"', '')
            criteria_parts.append(f'FROM "{from_filter}"')
        if subject_filter:
            subject_filter = subject_filter.replace('\\', '').replace('"', '')
            criteria_parts.append(f'SUBJECT "{subject_filter}"')
        if since:
            try:
                dt = datetime.strptime(since, "%Y-%m-%d")
                criteria_parts.append(f'SINCE {dt.strftime("%d-%b-%Y")}')
            except ValueError:
                logger.warning("Invalid --since date format: %s (expected YYYY-MM-DD)", since)
        if before:
            try:
                dt = datetime.strptime(before, "%Y-%m-%d")
                criteria_parts.append(f'BEFORE {dt.strftime("%d-%b-%Y")}')
            except ValueError:
                logger.warning("Invalid --before date format: %s (expected YYYY-MM-DD)", before)

        criteria = " ".join(criteria_parts) if criteria_parts else "ALL"

        uids = self._search(folder, criteria)
        # Most recent first
        uids.reverse()
        uids = uids[:limit]

        messages = []
        for uid in uids:
            summary = self._fetch_envelope(uid)
            if summary:
                messages.append(summary)

        return messages

    def read_message(self, uid: int, folder: str = "INBOX") -> MessageDetail:
        """Fetch and return full message detail."""
        return self._fetch_full(uid, folder)

    def search_messages(
        self,
        query: Optional[str] = None,
        body_query: Optional[str] = None,
        from_filter: Optional[str] = None,
        to_filter: Optional[str] = None,
        since: Optional[str] = None,
        folder: str = "INBOX",
        all_folders: bool = False,
        limit: int = DEFAULT_LIMIT,
    ) -> List[MessageSummary]:
        """Search messages across one or all folders."""
        criteria_parts = []
        if query:
            # Proton Bridge doesn't handle multi-word SUBJECT searches well;
            # split into individual SUBJECT criteria (IMAP ANDs them).
            words = query.split()
            for word in words:
                word = word.replace('\\', '').replace('"', '')
                criteria_parts.append(f'SUBJECT "{word}"')
        if body_query:
            words = body_query.split()
            for word in words:
                word = word.replace('\\', '').replace('"', '')
                criteria_parts.append(f'BODY "{word}"')
        if from_filter:
            from_filter = from_filter.replace('\\', '').replace('"', '')
            criteria_parts.append(f'FROM "{from_filter}"')
        if to_filter:
            to_filter = to_filter.replace('\\', '').replace('"', '')
            criteria_parts.append(f'TO "{to_filter}"')
        if since:
            try:
                dt = datetime.strptime(since, "%Y-%m-%d")
                criteria_parts.append(f'SINCE {dt.strftime("%d-%b-%Y")}')
            except ValueError:
                pass

        criteria = " ".join(criteria_parts) if criteria_parts else "ALL"

        results: List[MessageSummary] = []

        if all_folders:
            folders = self.list_folders()
            for fi in folders:
                try:
                    uids = self._search(fi.name, criteria)
                    uids.reverse()
                    for uid in uids[:limit - len(results)]:
                        summary = self._fetch_envelope(uid)
                        if summary:
                            results.append(summary)
                        if len(results) >= limit:
                            break
                except Exception as e:
                    logger.debug("Search failed in folder %s: %s", fi.name, e)
                if len(results) >= limit:
                    break
        else:
            uids = self._search(folder, criteria)
            uids.reverse()
            for uid in uids[:limit]:
                summary = self._fetch_envelope(uid)
                if summary:
                    results.append(summary)

        return results

    def send_message(
        self,
        to: List[str],
        subject: str,
        body: str,
        cc: Optional[List[str]] = None,
        bcc: Optional[List[str]] = None,
        is_html: bool = False,
        attachments: Optional[List[str]] = None,
        in_reply_to: Optional[str] = None,
        references: Optional[str] = None,
        from_addr: Optional[str] = None,
    ) -> bool:
        """Send an email via SMTP. Returns True on success.

        Args:
            from_addr: Optional sender address (e.g. SimpleLogin alias).
                       Defaults to the Proton account email.
        """
        if self._dry_run:
            logger.info("[DRY RUN] Would send email to %s", ", ".join(to))
            return True

        # Build message
        if attachments:
            msg = email.mime.multipart.MIMEMultipart()
            if is_html:
                msg.attach(email.mime.text.MIMEText(body, "html", "utf-8"))
            else:
                msg.attach(email.mime.text.MIMEText(body, "plain", "utf-8"))

            for filepath in attachments:
                path = Path(filepath)
                if not path.exists():
                    raise SendError(f"Attachment not found: {filepath}")
                content_type, _ = mimetypes.guess_type(str(path))
                if content_type is None:
                    content_type = "application/octet-stream"
                maintype, subtype = content_type.split("/", 1)

                with open(path, "rb") as f:
                    attachment_data = f.read()

                att = email.mime.base.MIMEBase(maintype, subtype)
                att.set_payload(attachment_data)
                email.encoders.encode_base64(att)
                att.add_header(
                    "Content-Disposition", "attachment",
                    filename=path.name,
                )
                msg.attach(att)
        else:
            subtype = "html" if is_html else "plain"
            msg = email.mime.text.MIMEText(body, subtype, "utf-8")

        # Set headers
        username, _ = _load_credentials()
        msg["From"] = from_addr if from_addr else username
        msg["To"] = ", ".join(to)
        if cc:
            msg["Cc"] = ", ".join(cc)
        msg["Subject"] = subject
        msg["Date"] = email.utils.formatdate(localtime=True)
        msg["Message-ID"] = email.utils.make_msgid()

        if in_reply_to:
            msg["In-Reply-To"] = in_reply_to
        if references:
            msg["References"] = references

        # Determine all recipients
        all_recipients = list(to)
        if cc:
            all_recipients.extend(cc)
        if bcc:
            all_recipients.extend(bcc)

        # Send via SMTP
        server = self._connect_smtp()
        try:
            server.sendmail(username, all_recipients, msg.as_string())
            logger.debug("Email sent to %s", ", ".join(all_recipients))
            return True
        except smtplib.SMTPException as e:
            raise SendError(f"Failed to send email: {e}") from e
        finally:
            try:
                server.quit()
            except Exception:
                pass

    def move_message(self, uid: int, target_folder: str, source_folder: str = "INBOX") -> bool:
        """Move a message to another folder via COPY + delete."""
        if self._dry_run:
            logger.info("[DRY RUN] Would move UID %d from '%s' to '%s'", uid, source_folder, target_folder)
            return True

        self._select_folder(source_folder, readonly=False)
        imap = self._connect_imap()

        # Copy to target
        status, _ = imap.uid("COPY", str(uid), f'"{target_folder}"')
        if status != "OK":
            raise FolderNotFoundError(f"Failed to copy to folder '{target_folder}' (does it exist?)")

        # Mark original as deleted
        imap.uid("STORE", str(uid), "+FLAGS", "(\\Deleted)")
        imap.expunge()

        logger.debug("Moved UID %d from '%s' to '%s'", uid, source_folder, target_folder)
        return True

    def mark_message(
        self,
        uid: int,
        folder: str = "INBOX",
        read: Optional[bool] = None,
        starred: Optional[bool] = None,
    ) -> bool:
        """Mark a message as read/unread or starred/unstarred."""
        if self._dry_run:
            logger.info("[DRY RUN] Would update flags on UID %d", uid)
            return True

        self._select_folder(folder, readonly=False)
        imap = self._connect_imap()

        if read is True:
            imap.uid("STORE", str(uid), "+FLAGS", "(\\Seen)")
        elif read is False:
            imap.uid("STORE", str(uid), "-FLAGS", "(\\Seen)")

        if starred is True:
            imap.uid("STORE", str(uid), "+FLAGS", "(\\Flagged)")
        elif starred is False:
            imap.uid("STORE", str(uid), "-FLAGS", "(\\Flagged)")

        return True

    def delete_message(self, uid: int, folder: str = "INBOX", permanent: bool = False) -> bool:
        """Delete a message (move to Trash, or permanently delete)."""
        if self._dry_run:
            action = "permanently delete" if permanent else "move to Trash"
            logger.info("[DRY RUN] Would %s UID %d", action, uid)
            return True

        if permanent:
            self._select_folder(folder, readonly=False)
            imap = self._connect_imap()
            imap.uid("STORE", str(uid), "+FLAGS", "(\\Deleted)")
            imap.expunge()
            logger.debug("Permanently deleted UID %d from '%s'", uid, folder)
        else:
            self.move_message(uid, "Trash", source_folder=folder)
            logger.debug("Moved UID %d to Trash", uid)

        return True

# ---------------------------------------------------------------------------
# Display helpers
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

    # Header
    header_parts = [_pad(h, col_widths[i]) for i, h in enumerate(headers)]
    header_line = f" {separator} ".join(header_parts)

    # Separator line
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

# ---------------------------------------------------------------------------
# Command handlers
# ---------------------------------------------------------------------------

def cmd_status(client: ProtonBridgeClient, args: argparse.Namespace) -> int:
    """Check Bridge connection and show account info."""
    status = client.get_status()

    if args.json:
        _json_output(_dc_to_dict(status))
        return 0

    print(f"\n{BOLD}Proton Mail Bridge Status{RESET}\n")
    print(f"  {GREEN}Connected{RESET}")
    print(f"  Account:     {status.email}")
    print(f"  IMAP:        {status.imap_host}:{status.imap_port}")
    print(f"  SMTP:        {status.smtp_host}:{status.smtp_port}")
    print(f"  Folders:     {status.folder_count}")
    print(f"  Messages:    {status.total_messages:,}")
    print()
    return 0


def cmd_inbox(client: ProtonBridgeClient, args: argparse.Namespace) -> int:
    """List recent messages with filters."""
    folder = getattr(args, "folder", None) or "INBOX"
    messages = client.list_messages(
        folder=folder,
        unread_only=getattr(args, "unread", False),
        from_filter=getattr(args, "from_addr", None),
        subject_filter=getattr(args, "subject", None),
        since=getattr(args, "since", None),
        before=getattr(args, "before", None),
        limit=getattr(args, "limit", DEFAULT_LIMIT),
    )

    if args.json:
        _json_output([_dc_to_dict(m) for m in messages])
        return 0

    if not messages:
        print(f"\n  {DIM}No messages found{RESET}\n")
        return 0

    print(f"\n{BOLD}{folder}{RESET} ({len(messages)} shown)\n")
    rows = []
    for m in messages:
        status_icon = f"{BOLD}\u25cf{RESET}" if m.is_unread else f"{DIM}\u25cb{RESET}"
        from_display = _truncate(m.from_addr, 25)
        subject_display = _truncate(m.subject, 35)
        rows.append([str(m.uid), from_display, subject_display, m.date, status_icon])

    print(_format_table(["UID", "From", "Subject", "Date", "Status"], rows))
    print()
    return 0


def cmd_read(client: ProtonBridgeClient, args: argparse.Namespace) -> int:
    """Read a specific message."""
    folder = getattr(args, "folder", None) or "INBOX"
    msg = client.read_message(args.message_id, folder)

    if args.json:
        d = _dc_to_dict(msg)
        # Remove HTML body from JSON unless requested
        if not getattr(args, "html_body", False):
            d.pop("body_html", None)
        _json_output(d)
        return 0

    # Show all headers if requested
    if getattr(args, "all_headers", False):
        print(f"\n{BOLD}Headers{RESET}\n")
        for key, val in msg.headers.items():
            print(f"  {DIM}{key}:{RESET} {val}")
        print()

    print(f"\n{BOLD}From:{RESET}    {msg.from_addr}")
    print(f"{BOLD}To:{RESET}      {msg.to_addr}")
    if msg.cc:
        print(f"{BOLD}Cc:{RESET}      {msg.cc}")
    print(f"{BOLD}Date:{RESET}    {msg.date}")
    print(f"{BOLD}Subject:{RESET} {msg.subject}")
    print()

    # Body
    if getattr(args, "html_body", False) and msg.body_html:
        print(msg.body_html)
    elif msg.body_text:
        print(msg.body_text)
    elif msg.body_html:
        print(html_to_text(msg.body_html))
    else:
        print(f"  {DIM}(empty message body){RESET}")

    # Attachments
    if msg.attachments:
        print(f"\n{BOLD}Attachments:{RESET}")
        for att in msg.attachments:
            print(f"  [{att.index}] {att.filename} ({_format_size(att.size)})")

    print()
    return 0


def cmd_search(client: ProtonBridgeClient, args: argparse.Namespace) -> int:
    """Search messages."""
    folder = getattr(args, "folder", None) or "INBOX"
    messages = client.search_messages(
        query=getattr(args, "query", None),
        body_query=getattr(args, "body", None),
        from_filter=getattr(args, "from_addr", None),
        to_filter=getattr(args, "to_addr", None),
        since=getattr(args, "since", None),
        folder=folder,
        all_folders=getattr(args, "all_folders", False),
        limit=getattr(args, "limit", DEFAULT_LIMIT),
    )

    if args.json:
        _json_output([_dc_to_dict(m) for m in messages])
        return 0

    if not messages:
        print(f"\n  {DIM}No messages found{RESET}\n")
        return 0

    print(f"\n{BOLD}Search Results{RESET} ({len(messages)} found)\n")
    rows = []
    for m in messages:
        status_icon = f"{BOLD}\u25cf{RESET}" if m.is_unread else f"{DIM}\u25cb{RESET}"
        from_display = _truncate(m.from_addr, 25)
        subject_display = _truncate(m.subject, 35)
        rows.append([str(m.uid), from_display, subject_display, m.date, status_icon])

    print(_format_table(["UID", "From", "Subject", "Date", "Status"], rows))
    print()
    return 0


def cmd_send(client: ProtonBridgeClient, args: argparse.Namespace) -> int:
    """Send an email."""
    to_list = [addr.strip() for addr in args.to.split(",")]
    cc_list = [addr.strip() for addr in args.cc.split(",")] if getattr(args, "cc", None) else None
    bcc_list = [addr.strip() for addr in args.bcc.split(",")] if getattr(args, "bcc", None) else None
    attachments = getattr(args, "attach", None) or []

    sender = getattr(args, "from_addr", None)

    if getattr(args, "dry_run", False) or client._dry_run:
        print(f"\n{YELLOW}[DRY RUN] Would send:{RESET}")
        if sender:
            print(f"  From:    {sender} (SimpleLogin alias)")
        print(f"  To:      {', '.join(to_list)}")
        if cc_list:
            print(f"  Cc:      {', '.join(cc_list)}")
        if bcc_list:
            print(f"  Bcc:     {', '.join(bcc_list)}")
        print(f"  Subject: {args.subject}")
        print(f"  Body:    {_truncate(args.body, 80)}")
        if attachments:
            print(f"  Attach:  {', '.join(attachments)}")
        print()
        return 0

    success = client.send_message(
        to=to_list,
        subject=args.subject,
        body=args.body,
        cc=cc_list,
        bcc=bcc_list,
        is_html=getattr(args, "html_body", False),
        attachments=attachments if attachments else None,
        from_addr=sender,
    )

    if args.json:
        _json_output({"success": success})
    else:
        if success:
            print(f"\n{GREEN}Email sent to {', '.join(to_list)}{RESET}\n")
        else:
            print(f"\n{RED}Failed to send email{RESET}\n")

    return 0 if success else 1


def cmd_reply(client: ProtonBridgeClient, args: argparse.Namespace) -> int:
    """Reply to a message."""
    folder = getattr(args, "folder", None) or "INBOX"
    original = client.read_message(args.message_id, folder)

    # Determine recipients
    if getattr(args, "reply_all", False):
        # Reply all: original From + original To + Cc, minus self
        username, _ = _load_credentials()
        all_addrs = set()
        for addr_str in [original.from_addr, original.to_addr, original.cc]:
            if addr_str:
                for part in addr_str.split(","):
                    part = part.strip()
                    if part and username.lower() not in part.lower():
                        all_addrs.add(part)
        to_list = list(all_addrs) if all_addrs else [original.from_addr]
    else:
        to_list = [original.from_addr]

    # Build subject
    subject = original.subject
    if not subject.lower().startswith("re:"):
        subject = f"Re: {subject}"

    # Build quoted body
    quote_body = original.body_text or html_to_text(original.body_html) if original.body_html else ""
    quoted_lines = "\n".join(f"> {line}" for line in quote_body.splitlines())
    full_body = f"{args.body}\n\nOn {original.date}, {original.from_addr} wrote:\n{quoted_lines}"

    attachments = getattr(args, "attach", None) or []
    sender = getattr(args, "from_addr", None)

    if client._dry_run:
        print(f"\n{YELLOW}[DRY RUN] Would reply:{RESET}")
        if sender:
            print(f"  From:    {sender} (SimpleLogin alias)")
        print(f"  To:      {', '.join(to_list)}")
        print(f"  Subject: {subject}")
        print(f"  Body:    {_truncate(args.body, 80)}")
        print()
        return 0

    success = client.send_message(
        to=to_list,
        subject=subject,
        body=full_body,
        attachments=attachments if attachments else None,
        in_reply_to=original.message_id,
        references=f"{original.references} {original.message_id}".strip(),
        from_addr=sender,
    )

    if args.json:
        _json_output({"success": success, "to": to_list, "subject": subject})
    else:
        if success:
            print(f"\n{GREEN}Reply sent to {', '.join(to_list)}{RESET}\n")
        else:
            print(f"\n{RED}Failed to send reply{RESET}\n")

    return 0 if success else 1


def cmd_forward(client: ProtonBridgeClient, args: argparse.Namespace) -> int:
    """Forward a message."""
    folder = getattr(args, "folder", None) or "INBOX"
    original = client.read_message(args.message_id, folder)

    to_list = [addr.strip() for addr in args.to.split(",")]

    # Build subject
    subject = original.subject
    if not subject.lower().startswith("fwd:"):
        subject = f"Fwd: {subject}"

    # Build forwarded body
    orig_body = original.body_text or (html_to_text(original.body_html) if original.body_html else "")
    full_body = (
        f"{args.body}\n\n"
        f"---------- Forwarded message ----------\n"
        f"From: {original.from_addr}\n"
        f"Date: {original.date}\n"
        f"Subject: {original.subject}\n"
        f"To: {original.to_addr}\n"
        f"\n{orig_body}"
    )

    # Forward original attachments
    attach_paths: List[str] = []
    if original.attachments:
        import tempfile
        tmp_dir = tempfile.mkdtemp(prefix="proton_fwd_")
        for att in original.attachments:
            filename, data = client._get_attachment_payload(args.message_id, att.index, folder)
            out_path = os.path.join(tmp_dir, filename)
            with open(out_path, "wb") as f:
                f.write(data)
            attach_paths.append(out_path)

    sender = getattr(args, "from_addr", None)

    if client._dry_run:
        print(f"\n{YELLOW}[DRY RUN] Would forward:{RESET}")
        if sender:
            print(f"  From:    {sender} (SimpleLogin alias)")
        print(f"  To:      {', '.join(to_list)}")
        print(f"  Subject: {subject}")
        if attach_paths:
            print(f"  Attach:  {len(attach_paths)} original attachment(s)")
        print()
        return 0

    success = client.send_message(
        to=to_list,
        subject=subject,
        body=full_body,
        attachments=attach_paths if attach_paths else None,
        from_addr=sender,
    )

    if args.json:
        _json_output({"success": success, "to": to_list, "subject": subject})
    else:
        if success:
            print(f"\n{GREEN}Forwarded to {', '.join(to_list)}{RESET}\n")
        else:
            print(f"\n{RED}Failed to forward{RESET}\n")

    return 0 if success else 1


def cmd_folders(client: ProtonBridgeClient, args: argparse.Namespace) -> int:
    """List all folders with message counts."""
    folders = client.list_folders()

    if args.json:
        _json_output([_dc_to_dict(f) for f in folders])
        return 0

    print(f"\n{BOLD}Folders{RESET}\n")
    rows = []
    for f in folders:
        unread_display = f"{BOLD}{f.unread}{RESET}" if f.unread > 0 else str(f.unread)
        rows.append([f.name, f"{f.total:,}", unread_display])

    print(_format_table(["Folder", "Total", "Unread"], rows))
    print()
    return 0


def cmd_move(client: ProtonBridgeClient, args: argparse.Namespace) -> int:
    """Move a message to another folder."""
    source = getattr(args, "folder", None) or "INBOX"
    success = client.move_message(args.message_id, args.target_folder, source_folder=source)

    if args.json:
        _json_output({"success": success, "uid": args.message_id, "target": args.target_folder})
    else:
        if success:
            print(f"\n{GREEN}Moved UID {args.message_id} to '{args.target_folder}'{RESET}\n")
        else:
            print(f"\n{RED}Failed to move message{RESET}\n")

    return 0 if success else 1


def cmd_mark(client: ProtonBridgeClient, args: argparse.Namespace) -> int:
    """Mark message flags."""
    folder = getattr(args, "folder", None) or "INBOX"

    read_flag = None
    starred_flag = None
    actions = []

    if getattr(args, "read", False):
        read_flag = True
        actions.append("read")
    elif getattr(args, "unread", False):
        read_flag = False
        actions.append("unread")

    if getattr(args, "starred", False):
        starred_flag = True
        actions.append("starred")
    elif getattr(args, "unstarred", False):
        starred_flag = False
        actions.append("unstarred")

    if not actions:
        print(f"{RED}Specify at least one flag: --read, --unread, --starred, --unstarred{RESET}")
        return 2

    success = client.mark_message(args.message_id, folder, read=read_flag, starred=starred_flag)

    if args.json:
        _json_output({"success": success, "uid": args.message_id, "actions": actions})
    else:
        if success:
            print(f"\n{GREEN}UID {args.message_id} marked as: {', '.join(actions)}{RESET}\n")
        else:
            print(f"\n{RED}Failed to update flags{RESET}\n")

    return 0 if success else 1


def cmd_attachments(client: ProtonBridgeClient, args: argparse.Namespace) -> int:
    """List or download attachments."""
    folder = getattr(args, "folder", None) or "INBOX"
    msg = client.read_message(args.message_id, folder)

    if not msg.attachments:
        if args.json:
            _json_output({"uid": args.message_id, "attachments": []})
        else:
            print(f"\n  {DIM}No attachments in UID {args.message_id}{RESET}\n")
        return 0

    download_dir = getattr(args, "download", None)

    if download_dir:
        # Download mode
        download_path = Path(download_dir)
        if not download_path.is_dir():
            print(f"{RED}Download directory does not exist: {download_dir}{RESET}")
            return 1

        specific_index = getattr(args, "index", None)
        downloaded = []

        for att in msg.attachments:
            if specific_index is not None and att.index != specific_index:
                continue

            filename, data = client._get_attachment_payload(args.message_id, att.index, folder)
            out_path = download_path / filename
            # Avoid overwriting
            if out_path.exists():
                stem = out_path.stem
                suffix = out_path.suffix
                counter = 1
                while out_path.exists():
                    out_path = download_path / f"{stem}_{counter}{suffix}"
                    counter += 1

            with open(out_path, "wb") as f:
                f.write(data)
            downloaded.append({"filename": filename, "path": str(out_path), "size": len(data)})

            if not args.json:
                print(f"  {GREEN}Downloaded:{RESET} {out_path} ({_format_size(len(data))})")

        if args.json:
            _json_output({"uid": args.message_id, "downloaded": downloaded})
        elif not downloaded:
            print(f"\n  {YELLOW}Attachment index {specific_index} not found{RESET}\n")
            return 1
        else:
            print()

        return 0

    # List mode
    if args.json:
        _json_output({
            "uid": args.message_id,
            "attachments": [_dc_to_dict(a) for a in msg.attachments],
        })
        return 0

    print(f"\n{BOLD}Attachments for UID {args.message_id}{RESET}\n")
    rows = []
    for att in msg.attachments:
        rows.append([str(att.index), att.filename, att.content_type, _format_size(att.size)])

    print(_format_table(["Index", "Filename", "Type", "Size"], rows))
    print()
    return 0


def cmd_delete(client: ProtonBridgeClient, args: argparse.Namespace) -> int:
    """Delete a message."""
    folder = getattr(args, "folder", None) or "INBOX"
    permanent = getattr(args, "permanent", False)

    if permanent and not client._dry_run:
        # Require confirmation for permanent delete
        try:
            answer = input(
                f"{YELLOW}Permanently delete UID {args.message_id}? "
                f"This cannot be undone. [y/N]: {RESET}"
            )
            if answer.lower() not in ("y", "yes"):
                print("Cancelled.")
                return 0
        except (EOFError, KeyboardInterrupt):
            print("\nCancelled.")
            return 0

    success = client.delete_message(args.message_id, folder, permanent=permanent)

    action = "permanently deleted" if permanent else "moved to Trash"

    if args.json:
        _json_output({"success": success, "uid": args.message_id, "action": action})
    else:
        if success:
            print(f"\n{GREEN}UID {args.message_id} {action}{RESET}\n")
        else:
            print(f"\n{RED}Failed to delete message{RESET}\n")

    return 0 if success else 1

# ---------------------------------------------------------------------------
# CLI Parser
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser with all subcommands."""
    # Shared parent parser for global flags (inherited by all subcommands)
    shared = argparse.ArgumentParser(add_help=False)
    shared.add_argument(
        "-v", "--verbose", action="store_true", help="Enable verbose logging"
    )
    shared.add_argument(
        "--json", action="store_true", help="Output results as JSON"
    )
    shared.add_argument(
        "--dry-run", action="store_true",
        help="Preview write operations without making changes",
    )
    shared.add_argument(
        "--timeout", type=int, default=DEFAULT_TIMEOUT,
        help=f"Connection timeout in seconds (default: {DEFAULT_TIMEOUT})",
    )

    parser = argparse.ArgumentParser(
        prog="proton_mail",
        parents=[shared],
        description=(
            "Proton Mail CLI via Bridge\n"
            "Read, send, search, and manage email through Proton Mail Bridge\n"
            "on localhost (IMAP 1143 / SMTP 1025)."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  %(prog)s status\n"
            "  %(prog)s inbox --unread --limit 10\n"
            "  %(prog)s read 1542\n"
            "  %(prog)s search \"invoice\" --since 2026-01-01\n"
            "  %(prog)s send --to user@example.com --subject \"Hello\" --body \"Hi there\"\n"
            "  %(prog)s reply 1542 --body \"Thanks!\"\n"
            "  %(prog)s forward 1542 --to colleague@example.com --body \"FYI\"\n"
            "  %(prog)s folders\n"
            "  %(prog)s move 1542 Archive\n"
            "  %(prog)s mark 1542 --read\n"
            "  %(prog)s attachments 1542 --download /tmp/\n"
            "  %(prog)s delete 1542\n"
            "\n"
            "Proton Mail Bridge must be running for all operations.\n"
            "Credentials: PROTON_EMAIL + PROTON_BRIDGE_PASSWORD env vars,\n"
            "or macOS Keychain service 'proton-bridge'.\n"
        ),
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # --- status ---
    subparsers.add_parser("status", parents=[shared], help="Check Bridge connection and show account info")

    # --- inbox ---
    p_inbox = subparsers.add_parser("inbox", parents=[shared], help="List recent messages")
    p_inbox.add_argument("--unread", action="store_true", help="Show unread messages only")
    p_inbox.add_argument("--from", dest="from_addr", help="Filter by sender address")
    p_inbox.add_argument("--subject", help="Filter by subject text")
    p_inbox.add_argument("--since", help="Messages since date (YYYY-MM-DD)")
    p_inbox.add_argument("--before", help="Messages before date (YYYY-MM-DD)")
    p_inbox.add_argument("--limit", type=int, default=DEFAULT_LIMIT, help=f"Max messages to show (default: {DEFAULT_LIMIT})")
    p_inbox.add_argument("--folder", default="INBOX", help="Folder to list (default: INBOX)")

    # --- read ---
    p_read = subparsers.add_parser("read", parents=[shared], help="Read a specific message")
    p_read.add_argument("message_id", type=int, help="Message UID to read")
    p_read.add_argument("--html", dest="html_body", action="store_true", help="Show raw HTML body")
    p_read.add_argument("--headers", dest="all_headers", action="store_true", help="Show all headers")
    p_read.add_argument("--folder", default="INBOX", help="Folder containing the message")

    # --- search ---
    p_search = subparsers.add_parser("search", parents=[shared], help="Search messages")
    p_search.add_argument("query", nargs="?", help="Subject search query")
    p_search.add_argument("--body", help="Search in message body")
    p_search.add_argument("--from", dest="from_addr", help="Search by sender")
    p_search.add_argument("--to", dest="to_addr", help="Search by recipient")
    p_search.add_argument("--since", help="Messages since date (YYYY-MM-DD)")
    p_search.add_argument("--folder", default="INBOX", help="Folder to search (default: INBOX)")
    p_search.add_argument("--all-folders", action="store_true", help="Search across all folders")
    p_search.add_argument("--limit", type=int, default=DEFAULT_LIMIT, help=f"Max results (default: {DEFAULT_LIMIT})")

    # --- send ---
    p_send = subparsers.add_parser("send", parents=[shared], help="Send an email")
    p_send.add_argument("--to", required=True, help="Recipient(s), comma-separated")
    p_send.add_argument("--subject", required=True, help="Email subject")
    p_send.add_argument("--body", required=True, help="Email body text")
    p_send.add_argument("--cc", help="CC recipient(s), comma-separated")
    p_send.add_argument("--bcc", help="BCC recipient(s), comma-separated")
    p_send.add_argument("--html", dest="html_body", action="store_true", help="Send body as HTML")
    p_send.add_argument("--attach", action="append", help="Attach file (can be repeated)")
    p_send.add_argument("--from", dest="from_addr", help="Sender address (e.g. SimpleLogin alias)")

    # --- reply ---
    p_reply = subparsers.add_parser("reply", parents=[shared], help="Reply to a message")
    p_reply.add_argument("message_id", type=int, help="UID of message to reply to")
    p_reply.add_argument("--body", required=True, help="Reply body text")
    p_reply.add_argument("--reply-all", action="store_true", help="Reply to all recipients")
    p_reply.add_argument("--attach", action="append", help="Attach file (can be repeated)")
    p_reply.add_argument("--from", dest="from_addr", help="Sender address (e.g. SimpleLogin alias)")
    p_reply.add_argument("--folder", default="INBOX", help="Folder containing the message")

    # --- forward ---
    p_forward = subparsers.add_parser("forward", parents=[shared], help="Forward a message")
    p_forward.add_argument("message_id", type=int, help="UID of message to forward")
    p_forward.add_argument("--to", required=True, help="Forward to recipient(s), comma-separated")
    p_forward.add_argument("--body", default="", help="Additional message text")
    p_forward.add_argument("--from", dest="from_addr", help="Sender address (e.g. SimpleLogin alias)")
    p_forward.add_argument("--folder", default="INBOX", help="Folder containing the message")

    # --- folders ---
    subparsers.add_parser("folders", parents=[shared], help="List all folders with message counts")

    # --- move ---
    p_move = subparsers.add_parser("move", parents=[shared], help="Move a message to another folder")
    p_move.add_argument("message_id", type=int, help="Message UID to move")
    p_move.add_argument("target_folder", help="Destination folder name")
    p_move.add_argument("--folder", default="INBOX", help="Source folder (default: INBOX)")

    # --- mark ---
    p_mark = subparsers.add_parser("mark", parents=[shared], help="Mark message read/unread/starred/unstarred")
    p_mark.add_argument("message_id", type=int, help="Message UID")
    p_mark.add_argument("--read", action="store_true", help="Mark as read")
    p_mark.add_argument("--unread", action="store_true", help="Mark as unread")
    p_mark.add_argument("--starred", action="store_true", help="Mark as starred")
    p_mark.add_argument("--unstarred", action="store_true", help="Mark as unstarred")
    p_mark.add_argument("--folder", default="INBOX", help="Folder containing the message")

    # --- attachments ---
    p_attach = subparsers.add_parser("attachments", parents=[shared], help="List or download attachments")
    p_attach.add_argument("message_id", type=int, help="Message UID")
    p_attach.add_argument("--download", metavar="DIR", help="Download attachments to directory")
    p_attach.add_argument("--index", type=int, help="Download specific attachment by index")
    p_attach.add_argument("--folder", default="INBOX", help="Folder containing the message")

    # --- delete ---
    p_delete = subparsers.add_parser("delete", parents=[shared], help="Delete a message (move to Trash)")
    p_delete.add_argument("message_id", type=int, help="Message UID to delete")
    p_delete.add_argument("--permanent", action="store_true", help="Permanently delete (skip Trash)")
    p_delete.add_argument("--folder", default="INBOX", help="Source folder (default: INBOX)")

    return parser

# ---------------------------------------------------------------------------
# Command dispatch
# ---------------------------------------------------------------------------

COMMANDS = {
    "status": cmd_status,
    "inbox": cmd_inbox,
    "read": cmd_read,
    "search": cmd_search,
    "send": cmd_send,
    "reply": cmd_reply,
    "forward": cmd_forward,
    "folders": cmd_folders,
    "move": cmd_move,
    "mark": cmd_mark,
    "attachments": cmd_attachments,
    "delete": cmd_delete,
}

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

    # Create client
    client = ProtonBridgeClient(
        timeout=args.timeout,
        dry_run=args.dry_run,
    )

    handler = COMMANDS.get(args.command)
    if not handler:
        parser.print_help()
        return 1

    try:
        return handler(client, args)
    except BridgeNotRunningError as e:
        if args.json:
            _json_output({"error": str(e), "type": "bridge_not_running"})
        else:
            print(f"\n{RED}Proton Mail Bridge is not reachable.{RESET}\n")
            print(f"{e}")
            print(f"\n{YELLOW}Ensure Proton Mail Bridge is running and logged in.{RESET}")
        return 1
    except AuthenticationError as e:
        if args.json:
            _json_output({"error": str(e), "type": "authentication_failed"})
        else:
            print(f"\n{RED}Authentication failed.{RESET}\n")
            print(f"{e}")
            print(f"\n{YELLOW}Check PROTON_BRIDGE_PASSWORD or Keychain entry.{RESET}")
        return 1
    except CredentialError as e:
        if args.json:
            _json_output({"error": str(e), "type": "credential_error"})
        else:
            print(f"\n{RED}Credential error.{RESET}\n")
            print(f"{e}")
        return 1
    except FolderNotFoundError as e:
        if args.json:
            _json_output({"error": str(e), "type": "folder_not_found"})
        else:
            print(f"\n{RED}Folder not found.{RESET}")
            print(f"{e}")
        return 1
    except MessageNotFoundError as e:
        if args.json:
            _json_output({"error": str(e), "type": "message_not_found"})
        else:
            print(f"\n{RED}Message not found.{RESET}")
            print(f"{e}")
        return 1
    except SendError as e:
        if args.json:
            _json_output({"error": str(e), "type": "send_error"})
        else:
            print(f"\n{RED}Send failed.{RESET}")
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
    finally:
        client.close()


if __name__ == "__main__":
    sys.exit(main())
