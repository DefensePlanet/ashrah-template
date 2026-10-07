"""Source file scanner for Just Press Record and Voice Memos.

Discovers audio recordings from configured source directories,
parses timestamps, computes dedup hashes, and detects iCloud stubs.
"""

import glob
import hashlib
import logging
import os
import re
import subprocess
from datetime import datetime
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

# Date folder pattern for JPR: YYYY-MM-DD
_DATE_FOLDER_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

# Time-based filename for JPR: HH-MM-SS (inside date folder)
_TIME_FILE_RE = re.compile(r"^(\d{2}-\d{2}-\d{2})(?:\.m4a)?$")

# Voice Memos filename: YYYYMMDD HHMMSS-<hex>.m4a
_VM_FILENAME_RE = re.compile(r"^(\d{8})\s+(\d{6})-[A-Fa-f0-9]+\.m4a$")

# M4A magic bytes: file type box starts with "ftyp"
_M4A_MAGIC = b"ftyp"


def _is_m4a_file(filepath: str) -> bool:
    """Check if a file is an M4A/MP4 container by reading magic bytes.

    The ISO base media file format (M4A, MP4, etc.) has "ftyp" at offset 4.
    """
    try:
        with open(filepath, "rb") as f:
            header = f.read(12)
        # ftyp appears at byte offset 4
        return _M4A_MAGIC in header[:12]
    except (OSError, IOError):
        return False


def _compute_file_hash(filepath: str) -> str:
    """Compute a fast dedup hash: SHA-256 of first 64KB + file size.

    This is not a full-file hash but sufficient for deduplication
    of audio recordings which vary in length.
    """
    try:
        file_size = os.path.getsize(filepath)
        hasher = hashlib.sha256()
        with open(filepath, "rb") as f:
            chunk = f.read(65536)  # 64KB
            hasher.update(chunk)
        hasher.update(str(file_size).encode())
        return hasher.hexdigest()
    except (OSError, IOError):
        return ""


def _is_icloud_stub(filepath: str) -> bool:
    """Check if a file is an iCloud stub (.filename.icloud placeholder)."""
    basename = os.path.basename(filepath)
    return basename.startswith(".") and basename.endswith(".icloud")


def _get_real_path_from_stub(stub_path: str) -> str:
    """Convert an iCloud stub path to the real file path.

    Stubs are named .filename.icloud -> real file is filename (without dot prefix
    and .icloud suffix).
    """
    directory = os.path.dirname(stub_path)
    basename = os.path.basename(stub_path)
    # Remove leading dot and trailing .icloud
    real_name = basename[1:]  # remove leading .
    if real_name.endswith(".icloud"):
        real_name = real_name[:-7]  # remove .icloud
    return os.path.join(directory, real_name)


def _download_icloud_file(filepath: str) -> bool:
    """Request iCloud download for a stub file using brctl.

    Args:
        filepath: Path to the actual file (not the stub).

    Returns:
        True if download was initiated, False on error.
    """
    try:
        result = subprocess.run(
            ["brctl", "download", filepath],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode == 0:
            logger.info("Initiated iCloud download for: %s", filepath)
            return True
        else:
            logger.warning("brctl download failed for %s: %s", filepath, result.stderr.strip())
            return False
    except FileNotFoundError:
        logger.warning("brctl not found -- cannot download iCloud files")
        return False
    except subprocess.TimeoutExpired:
        logger.warning("brctl download timed out for %s", filepath)
        return False


def _parse_cutoff(cutoff_str: Optional[str]) -> Optional[datetime]:
    """Parse cutoff date string to datetime."""
    if not cutoff_str:
        return None
    try:
        return datetime.fromisoformat(cutoff_str)
    except (ValueError, TypeError):
        logger.warning("Invalid cutoff date: %s", cutoff_str)
        return None


# ---------------------------------------------------------------------------
# JPR Scanner
# ---------------------------------------------------------------------------

def scan_jpr(source_config: dict, cutoff: Optional[datetime] = None) -> List[dict]:
    """Scan Just Press Record source directory for audio files.

    JPR stores recordings in date-based folders:
        Documents/YYYY-MM-DD/HH-MM-SS (extensionless M4A)
        Documents/YYYY-MM-DD/HH-MM-SS.m4a

    Args:
        source_config: Source config dict with 'path' and 'is_icloud' keys.
        cutoff: Only return files recorded after this datetime.

    Returns:
        List of discovery dicts with source_path, source_app, recorded_at,
        file_size, file_hash.
    """
    base_path = source_config.get("path", "")
    is_icloud = source_config.get("is_icloud", False)

    if not base_path or not os.path.isdir(base_path):
        logger.warning("JPR source path does not exist: %s", base_path)
        return []

    results = []

    # Walk date folders
    try:
        entries = sorted(os.listdir(base_path))
    except OSError as e:
        logger.error("Cannot list JPR directory %s: %s", base_path, e)
        return []

    for date_folder in entries:
        if not _DATE_FOLDER_RE.match(date_folder):
            continue

        date_path = os.path.join(base_path, date_folder)
        if not os.path.isdir(date_path):
            continue

        # List files in the date folder
        try:
            files = sorted(os.listdir(date_path))
        except OSError:
            continue

        for filename in files:
            filepath = os.path.join(date_path, filename)

            # Handle iCloud stubs
            if _is_icloud_stub(filepath):
                real_path = _get_real_path_from_stub(filepath)
                if is_icloud:
                    _download_icloud_file(real_path)
                logger.debug("Skipping iCloud stub (download initiated): %s", filepath)
                continue

            if not os.path.isfile(filepath):
                continue

            # Match time-based filenames (with or without .m4a)
            match = _TIME_FILE_RE.match(filename)
            if not match:
                continue

            # For extensionless files, verify M4A format
            if not filename.endswith(".m4a"):
                if not _is_m4a_file(filepath):
                    logger.debug("Skipping non-M4A file: %s", filepath)
                    continue

            # Parse timestamp: folder date + filename time
            time_str = match.group(1)  # HH-MM-SS
            try:
                recorded_at = datetime.strptime(
                    f"{date_folder} {time_str}", "%Y-%m-%d %H-%M-%S"
                )
            except ValueError:
                logger.warning("Cannot parse timestamp for: %s/%s", date_folder, filename)
                continue

            # Apply cutoff filter
            if cutoff and recorded_at < cutoff:
                continue

            file_size = os.path.getsize(filepath)
            file_hash = _compute_file_hash(filepath)

            results.append({
                "source_path": filepath,
                "source_app": "jpr",
                "recorded_at": recorded_at.isoformat(),
                "file_size": file_size,
                "file_hash": file_hash,
            })

    logger.info("JPR scan found %d recordings", len(results))
    return results


# ---------------------------------------------------------------------------
# Voice Memos Scanner
# ---------------------------------------------------------------------------

def scan_voice_memos(source_config: dict, cutoff: Optional[datetime] = None) -> List[dict]:
    """Scan Voice Memos source directory for audio files.

    Voice Memos stores recordings as:
        Recordings/YYYYMMDD HHMMSS-<hex>.m4a

    Args:
        source_config: Source config dict with 'path' key.
        cutoff: Only return files recorded after this datetime.

    Returns:
        List of discovery dicts.
    """
    base_path = source_config.get("path", "")

    if not base_path or not os.path.isdir(base_path):
        logger.warning("Voice Memos source path does not exist: %s", base_path)
        return []

    results = []

    # Glob for .m4a files
    pattern = os.path.join(base_path, "*.m4a")
    for filepath in sorted(glob.glob(pattern)):
        filename = os.path.basename(filepath)

        # Skip auxiliary files
        if ".waveform" in filename.lower():
            continue

        # Parse Voice Memos filename
        match = _VM_FILENAME_RE.match(filename)
        if not match:
            # Try a more permissive match: any .m4a that starts with digits
            if not filename[0].isdigit():
                continue
            # Use file modification time as fallback
            try:
                mtime = os.path.getmtime(filepath)
                recorded_at = datetime.fromtimestamp(mtime)
            except OSError:
                continue
        else:
            date_str = match.group(1)  # YYYYMMDD
            time_str = match.group(2)  # HHMMSS
            try:
                recorded_at = datetime.strptime(
                    f"{date_str} {time_str}", "%Y%m%d %H%M%S"
                )
            except ValueError:
                logger.warning("Cannot parse timestamp for: %s", filename)
                continue

        # Apply cutoff filter
        if cutoff and recorded_at < cutoff:
            continue

        file_size = os.path.getsize(filepath)
        file_hash = _compute_file_hash(filepath)

        results.append({
            "source_path": filepath,
            "source_app": "voice_memos",
            "recorded_at": recorded_at.isoformat(),
            "file_size": file_size,
            "file_hash": file_hash,
        })

    logger.info("Voice Memos scan found %d recordings", len(results))
    return results


# ---------------------------------------------------------------------------
# Unified discovery
# ---------------------------------------------------------------------------

def discover(config: dict) -> List[dict]:
    """Discover all new recordings from configured sources.

    Args:
        config: Full pipeline config dict.

    Returns:
        Combined list of discovery dicts from all enabled sources,
        sorted by recorded_at ascending.
    """
    sources = config.get("sources", {})
    watcher_cfg = config.get("watcher", {})
    cutoff = _parse_cutoff(watcher_cfg.get("cutoff_date"))

    all_recordings = []

    # JPR
    jpr_config = sources.get("jpr", {})
    if jpr_config.get("enabled", False):
        all_recordings.extend(scan_jpr(jpr_config, cutoff))

    # Voice Memos
    vm_config = sources.get("voice_memos", {})
    if vm_config.get("enabled", False):
        all_recordings.extend(scan_voice_memos(vm_config, cutoff))

    # Sort by recorded_at
    all_recordings.sort(key=lambda r: r.get("recorded_at", ""))

    logger.info("Total recordings discovered: %d", len(all_recordings))
    return all_recordings
