"""On-demand speaker diarization using pyannote.audio.

Only invoked when heuristics suggest multiple speakers in a recording.
Requires a Hugging Face token (HF_TOKEN) for model access.
Entirely optional -- the pipeline works without it.
"""

import logging
import os
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

# Cache the availability check
_pyannote_available: Optional[bool] = None


def _check_pyannote() -> bool:
    """Check if pyannote.audio is importable."""
    global _pyannote_available
    if _pyannote_available is not None:
        return _pyannote_available
    try:
        import pyannote.audio  # noqa: F401
        _pyannote_available = True
    except ImportError:
        logger.info(
            "pyannote.audio not installed -- speaker diarization disabled. "
            "Install with: pip install pyannote.audio"
        )
        _pyannote_available = False
    return _pyannote_available


def _get_hf_token() -> Optional[str]:
    """Get Hugging Face token from environment or keychain.

    Checks in order:
    1. HF_TOKEN environment variable
    2. HUGGING_FACE_HUB_TOKEN environment variable
    3. ~/.huggingface/token file
    """
    # Environment variables
    token = os.environ.get("HF_TOKEN") or os.environ.get("HUGGING_FACE_HUB_TOKEN")
    if token:
        return token

    # Token files (old + new standard locations)
    for token_path in [
        os.path.expanduser("~/.cache/huggingface/token"),
        os.path.expanduser("~/.huggingface/token"),
    ]:
        if os.path.exists(token_path):
            try:
                with open(token_path, "r") as f:
                    token = f.read().strip()
                if token:
                    return token
            except OSError:
                pass

    # macOS Keychain (Catalyst pattern)
    try:
        import subprocess
        result = subprocess.run(
            ["security", "find-generic-password", "-s", "huggingface", "-w"],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except Exception:
        pass

    return None


def should_diarize(
    transcript_text: str,
    duration_secs: float,
    segments: list,
) -> bool:
    """Heuristic: should we run diarization on this recording?

    Checks multiple signals to determine if a recording likely contains
    multiple speakers.

    Args:
        transcript_text: Full transcript text.
        duration_secs: Recording duration in seconds.
        segments: Whisper segments list.

    Returns:
        True if diarization is recommended.
    """
    # Cannot diarize if pyannote is not installed
    if not _check_pyannote():
        return False

    # Need a HF token
    if not _get_hf_token():
        logger.debug("No HF_TOKEN found -- skipping diarization check")
        return False

    # Skip short recordings (< 60 seconds)
    if duration_secs < 60:
        return False

    # Strong signal: question-response patterns in longer recordings
    if "?" in transcript_text and duration_secs > 120:
        return True

    # Check for dialogue indicators
    dialogue_markers = [
        "he said", "she said", "they said",
        "I asked", "they asked",
        "you know what", "let me tell you",
        "yeah", "right", "exactly",
    ]
    marker_count = sum(
        1 for marker in dialogue_markers
        if marker.lower() in transcript_text.lower()
    )
    if marker_count >= 3 and duration_secs > 180:
        return True

    return False


def diarize(
    audio_path: str,
    num_speakers: Optional[int] = None,
) -> Optional[List[Dict]]:
    """Run speaker diarization on an audio file.

    Args:
        audio_path: Path to WAV audio file.
        num_speakers: Expected number of speakers (None for auto-detection).

    Returns:
        List of speaker-labeled segments:
        [{"start": 0.0, "end": 5.2, "speaker": "SPEAKER_00"}, ...]
        Returns None if diarization fails or is unavailable.
    """
    if not _check_pyannote():
        return None

    token = _get_hf_token()
    if not token:
        logger.warning("No HF_TOKEN available -- cannot run diarization")
        return None

    try:
        from pyannote.audio import Pipeline

        logger.info("Loading diarization pipeline...")
        pipeline = Pipeline.from_pretrained(
            "pyannote/speaker-diarization-3.1",
            token=token,
        )

        # Run diarization
        kwargs = {}
        if num_speakers is not None:
            kwargs["num_speakers"] = num_speakers

        logger.info("Running diarization on: %s", audio_path)
        diarization_result = pipeline(audio_path, **kwargs)

        # Convert to list of segments
        segments = []
        for turn, _, speaker in diarization_result.itertracks(yield_label=True):
            segments.append({
                "start": round(turn.start, 2),
                "end": round(turn.end, 2),
                "speaker": speaker,
            })

        # Count unique speakers
        unique_speakers = set(seg["speaker"] for seg in segments)
        logger.info(
            "Diarization complete: %d segments, %d speakers",
            len(segments), len(unique_speakers),
        )

        return segments

    except Exception as e:
        logger.error("Diarization failed: %s", e)
        return None


def count_speakers(diarization_segments: List[Dict]) -> int:
    """Count unique speakers from diarization results.

    Args:
        diarization_segments: Output from diarize().

    Returns:
        Number of unique speakers.
    """
    if not diarization_segments:
        return 1
    speakers = set(seg.get("speaker", "") for seg in diarization_segments)
    return max(len(speakers), 1)
