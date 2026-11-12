"""Output writer for the voice recording pipeline.

Writes three files per recording to the iCloud Drive archive:
1. WAV file (denoised audio)
2. Transcript (.txt) with metadata header
3. Metadata (.json) with full processing details

Also handles Finder tagging on the original source file.
Follows the xattr + plistlib pattern from Catalyst's file-organizer/tagger.py.
"""

import json
import logging
import os
import plistlib
import shutil
import subprocess
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)

PIPELINE_VERSION = "1.0.0"

# Friendly names for source apps
SOURCE_APP_NAMES = {
    "jpr": "Just Press Record",
    "voice_memos": "Voice Memos",
}

# Friendly names for categories
CATEGORY_NAMES = {
    "prayer": "Prayer",
    "daily-log": "Daily Log",
    "meditation": "Meditation",
    "ambient": "Ambient",
    "uncategorized": "Uncategorized",
}


def _format_duration(seconds: float) -> str:
    """Format seconds to MM:SS or H:MM:SS."""
    total = int(seconds)
    hours = total // 3600
    minutes = (total % 3600) // 60
    secs = total % 60
    if hours > 0:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes}:{secs:02d}"


def _format_date_header(recorded_at: str) -> str:
    """Format recorded_at ISO string to a human-readable header date.

    Example: 'February 8, 2026 (9:53 PM)'
    """
    try:
        dt = datetime.fromisoformat(recorded_at)
        hour = dt.strftime("%-I:%M %p")
        return f"{dt.strftime('%B')} {dt.day}, {dt.year} ({hour})"
    except (ValueError, TypeError):
        return recorded_at


def _build_output_filename(recorded_at: str, category: str) -> str:
    """Build output filename: YYYY-MM-DD-HHMM-{category}

    Args:
        recorded_at: ISO format datetime string.
        category: Category name.

    Returns:
        Base filename without extension.
    """
    try:
        dt = datetime.fromisoformat(recorded_at)
        return f"{dt.strftime('%Y-%m-%d-%H%M')}-{category}"
    except (ValueError, TypeError):
        # Fallback
        ts = datetime.now().strftime("%Y-%m-%d-%H%M")
        return f"{ts}-{category}"


def _resolve_collision(base_path: str, extension: str) -> str:
    """Resolve filename collisions by appending -2, -3, etc.

    Args:
        base_path: Full path without extension.
        extension: File extension including dot (e.g., '.wav').

    Returns:
        Final path with collision resolution.
    """
    full_path = f"{base_path}{extension}"
    if not os.path.exists(full_path):
        return full_path

    counter = 2
    while True:
        candidate = f"{base_path}-{counter}{extension}"
        if not os.path.exists(candidate):
            return candidate
        counter += 1
        if counter > 100:
            # Safety valve
            raise RuntimeError(f"Too many filename collisions for: {base_path}")


def _write_transcript_file(
    output_path: str,
    recording: dict,
) -> bool:
    """Write the transcript text file with metadata header.

    Format:
        Category - Month Day, Year (Time)
        Duration: MM:SS | Source: App Name

        ---

        [Full transcript text]

        ---
        Summary: One-line summary
    """
    category_name = CATEGORY_NAMES.get(recording["category"], recording["category"].title())
    source_name = SOURCE_APP_NAMES.get(recording["source_app"], recording["source_app"])
    date_header = _format_date_header(recording["recorded_at"])
    duration_str = _format_duration(recording["duration_secs"])
    transcript = recording.get("transcript", "")
    summary = recording.get("summary", "")

    lines = [
        f"{category_name} - {date_header}",
        f"Duration: {duration_str} | Source: {source_name}",
        "",
        "---",
        "",
    ]

    # Add transcript with paragraph breaks (split on long pauses/double newlines)
    if transcript.strip():
        lines.append(transcript.strip())
    else:
        lines.append("[No transcript available]")

    lines.extend(["", "---"])

    if summary:
        lines.append(f"Summary: {summary}")

    try:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
        return True
    except OSError as e:
        logger.error("Failed to write transcript file %s: %s", output_path, e)
        return False


def _write_metadata_file(
    output_path: str,
    recording: dict,
) -> bool:
    """Write the JSON metadata file."""
    try:
        dt = datetime.fromisoformat(recording["recorded_at"])
        date_str = dt.strftime("%Y-%m-%d")
        time_str = dt.strftime("%H:%M:%S")
    except (ValueError, TypeError):
        date_str = ""
        time_str = ""

    metadata = {
        "date": date_str,
        "time": time_str,
        "category": recording.get("category", ""),
        "confidence": recording.get("confidence", 0.0),
        "source_app": recording.get("source_app", ""),
        "source_file": recording.get("source_path", ""),
        "duration_secs": recording.get("duration_secs", 0.0),
        "duration_formatted": _format_duration(recording.get("duration_secs", 0)),
        "word_count": recording.get("word_count", 0),
        "speakers": recording.get("speakers", 1),
        "diarized": recording.get("diarized", False),
        "summary": recording.get("summary", ""),
        "processed_at": datetime.now().isoformat(),
        "pipeline_version": PIPELINE_VERSION,
    }

    try:
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
            f.write("\n")
        return True
    except OSError as e:
        logger.error("Failed to write metadata file %s: %s", output_path, e)
        return False


def _copy_audio_file(source_wav: str, dest_path: str) -> bool:
    """Copy the denoised WAV to the archive."""
    try:
        shutil.copy2(source_wav, dest_path)
        return True
    except (OSError, shutil.Error) as e:
        logger.error("Failed to copy audio file to %s: %s", dest_path, e)
        return False


# ---------------------------------------------------------------------------
# Finder tagging (follows file-organizer/tagger.py pattern)
# ---------------------------------------------------------------------------

def _set_finder_tag(
    filepath: str,
    tag_name: str,
    color: int = 6,
) -> bool:
    """Set a Finder tag on a file using xattr + plistlib.

    Each tag entry is "tagname\\nN" where N is the color code:
    0=None, 1=Red, 2=Orange, 3=Yellow, 4=Green, 5=Blue, 6=Purple, 7=Gray

    Args:
        filepath: Path to the file to tag.
        tag_name: Tag name string.
        color: macOS Finder color code (0-7).

    Returns:
        True if tag was set successfully.
    """
    try:
        # Read existing tags first
        existing_tags = []
        try:
            result = subprocess.run(
                ["xattr", "-px", "com.apple.metadata:_kMDItemUserTags", filepath],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0 and result.stdout.strip():
                hex_str = result.stdout.strip().replace(" ", "").replace("\n", "")
                plist_bytes = bytes.fromhex(hex_str)
                existing_tags = plistlib.loads(plist_bytes)
                if not isinstance(existing_tags, list):
                    existing_tags = []
        except Exception:
            existing_tags = []

        # Check if tag already exists
        tag_entry = f"{tag_name}\n{color}"
        tag_names_only = [t.split("\n")[0] for t in existing_tags if isinstance(t, str)]
        if tag_name in tag_names_only:
            logger.debug("Tag '%s' already present on: %s", tag_name, filepath)
            return True

        # Add new tag
        existing_tags.append(tag_entry)

        # Encode as binary plist
        plist_data = plistlib.dumps(existing_tags, fmt=plistlib.FMT_BINARY)
        hex_str = plist_data.hex(" ")

        result = subprocess.run(
            ["xattr", "-wx", "com.apple.metadata:_kMDItemUserTags",
             hex_str, filepath],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            logger.debug("Tagged '%s' on: %s", tag_name, filepath)
            return True
        else:
            logger.warning("xattr write failed for %s: %s", filepath, result.stderr)
            return False
    except Exception as e:
        logger.error("Finder tag failed for %s: %s", filepath, e)
        return False


# ---------------------------------------------------------------------------
# Main write function
# ---------------------------------------------------------------------------

def write_output(
    recording: dict,
    config: dict,
) -> Optional[str]:
    """Write all output files for a processed recording.

    Writes three files to the archive:
    1. {name}.wav  - Denoised audio
    2. {name}.txt  - Transcript with metadata header
    3. {name}.json - Machine-readable metadata

    Args:
        recording: Full recording dict with all processed fields.
        config: Output config dict from config.yaml.

    Returns:
        The output directory path where files were written,
        or None on failure.
    """
    output_cfg = config.get("output", {})
    base_path = output_cfg.get("base_path", "")
    structure = output_cfg.get("structure", {})

    if not base_path:
        logger.error("No output.base_path configured")
        return None

    # Determine output subdirectory from category
    category = recording.get("category", "uncategorized")
    subdir = structure.get(category, structure.get("uncategorized", "uncategorized/"))
    output_dir = os.path.join(base_path, subdir)

    # Create output directory
    os.makedirs(output_dir, exist_ok=True)

    # Build filename
    base_name = _build_output_filename(recording["recorded_at"], category)
    base_file = os.path.join(output_dir, base_name)

    # Resolve collisions for all three files
    wav_path = _resolve_collision(base_file, ".wav")
    # Use the same resolved base for txt and json
    resolved_base = wav_path[:-4]  # strip .wav
    txt_path = f"{resolved_base}.txt"
    json_path = f"{resolved_base}.json"

    success = True

    # 1. Copy denoised WAV
    denoised_path = recording.get("denoised_path", "")
    if denoised_path and os.path.exists(denoised_path):
        if not _copy_audio_file(denoised_path, wav_path):
            success = False
    else:
        logger.warning("No denoised audio available for: %s", recording.get("source_path", ""))

    # 2. Write transcript
    if not _write_transcript_file(txt_path, recording):
        success = False

    # 3. Write metadata
    if not _write_metadata_file(json_path, recording):
        success = False

    if success:
        logger.info("Output written to: %s", output_dir)
        return output_dir
    else:
        logger.error("Partial write failure for: %s", recording.get("source_path", ""))
        return output_dir  # Return dir even on partial failure for status tracking


def tag_source_file(
    source_path: str,
    config: dict,
) -> bool:
    """Apply Finder tag to the original source file.

    Args:
        source_path: Path to the original recording file.
        config: Output config dict from config.yaml.

    Returns:
        True if tagging succeeded.
    """
    output_cfg = config.get("output", {})
    if not output_cfg.get("finder_tag", False):
        return True  # Tagging disabled, consider it "success"

    tag_name = output_cfg.get("finder_tag_name", "Voice-Processed")
    tag_color = output_cfg.get("finder_tag_color", 6)

    if not os.path.exists(source_path):
        logger.warning("Source file no longer exists for tagging: %s", source_path)
        return False

    return _set_finder_tag(source_path, tag_name, tag_color)
