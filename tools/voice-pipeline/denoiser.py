"""Two-stage audio denoising for the voice recording pipeline.

Stage 1: ffmpeg bandpass filter + adaptive noise reduction + dynamic normalization
Stage 2: noisereduce library for ML-based spectral gating

Output: 16kHz mono WAV optimized for Whisper transcription.
"""

import logging
import os
import subprocess
import tempfile
from typing import Optional

logger = logging.getLogger(__name__)

# Resolve ffmpeg path once at module load — handles Homebrew locations
_FFMPEG_PATH: Optional[str] = None


def _find_ffmpeg() -> Optional[str]:
    """Find ffmpeg binary, checking common Homebrew paths."""
    global _FFMPEG_PATH
    if _FFMPEG_PATH is not None:
        return _FFMPEG_PATH if _FFMPEG_PATH else None

    import shutil
    # Check PATH first, then common Homebrew locations
    candidates = [
        shutil.which("ffmpeg"),
        "/opt/homebrew/bin/ffmpeg",
        "/usr/local/bin/ffmpeg",
    ]
    for path in candidates:
        if path and os.path.isfile(path):
            _FFMPEG_PATH = path
            logger.debug("Found ffmpeg at: %s", path)
            return path

    _FFMPEG_PATH = ""  # Cache negative result
    return None


def _ffmpeg_available() -> bool:
    """Check if ffmpeg is available on the system."""
    return _find_ffmpeg() is not None


def _run_ffmpeg_denoise(
    input_path: str,
    output_path: str,
    highpass_hz: int = 80,
    lowpass_hz: int = 8000,
    noise_floor: int = -25,
) -> bool:
    """Run ffmpeg Stage 1 denoising.

    Applies: highpass -> lowpass -> adaptive FFT denoise -> dynamic normalization
    Outputs: 16kHz mono WAV (Whisper's native format)

    Args:
        input_path: Path to input audio file (M4A, WAV, etc.).
        output_path: Path for output WAV file.
        highpass_hz: High-pass filter cutoff frequency.
        lowpass_hz: Low-pass filter cutoff frequency.
        noise_floor: FFT denoise noise floor in dB.

    Returns:
        True if successful, False on error.
    """
    af_chain = (
        f"highpass=f={highpass_hz},"
        f"lowpass=f={lowpass_hz},"
        f"afftdn=nf={noise_floor},"
        f"dynaudnorm"
    )

    cmd = [
        _find_ffmpeg(),
        "-i", input_path,
        "-af", af_chain,
        "-ar", "16000",
        "-ac", "1",
        output_path,
        "-y",
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120,
        )
        if result.returncode != 0:
            logger.error("ffmpeg denoise failed: %s", result.stderr[-500:] if result.stderr else "unknown error")
            return False
        return True
    except subprocess.TimeoutExpired:
        logger.error("ffmpeg denoise timed out for: %s", input_path)
        return False


def _run_ffmpeg_convert(input_path: str, output_path: str) -> bool:
    """Convert audio to 16kHz mono WAV without denoising (fallback when ffmpeg filters fail)."""
    cmd = [
        _find_ffmpeg(),
        "-i", input_path,
        "-ar", "16000",
        "-ac", "1",
        output_path,
        "-y",
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60,
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


def _run_noisereduce(
    input_wav: str,
    output_wav: str,
    stationary: bool = False,
    prop_decrease: float = 0.75,
) -> bool:
    """Run noisereduce Stage 2 ML-based spectral gating.

    Args:
        input_wav: Path to input WAV file (from Stage 1).
        output_wav: Path for output denoised WAV.
        stationary: If True, use stationary noise reduction.
        prop_decrease: Proportion of noise to reduce (0.0-1.0).

    Returns:
        True if successful, False on error.
    """
    try:
        import noisereduce as nr
        import soundfile as sf
    except ImportError:
        logger.warning("noisereduce or soundfile not installed -- skipping Stage 2")
        return False

    try:
        data, rate = sf.read(input_wav)
        reduced = nr.reduce_noise(
            y=data,
            sr=rate,
            stationary=stationary,
            prop_decrease=prop_decrease,
        )
        sf.write(output_wav, reduced, rate)
        return True
    except Exception as e:
        logger.error("noisereduce failed: %s", e)
        return False


def denoise(
    input_path: str,
    config: dict,
) -> Optional[str]:
    """Run the full two-stage denoising pipeline on an audio file.

    Stage 1 (ffmpeg): bandpass + FFT denoise + dynamic normalization -> 16kHz WAV
    Stage 2 (noisereduce): ML spectral gating on the WAV

    Args:
        input_path: Path to the source audio file.
        config: Denoiser config dict from config.yaml.

    Returns:
        Path to the final denoised WAV file, or None on total failure.
    """
    output_dir = config.get("output_dir", "/tmp/voice-pipeline-denoised")
    os.makedirs(output_dir, exist_ok=True)

    # Build output filename: source basename + .wav
    basename = os.path.splitext(os.path.basename(input_path))[0]
    # Handle extensionless JPR files
    if not basename or basename == input_path:
        basename = os.path.basename(input_path)
    final_output = os.path.join(output_dir, f"{basename}.wav")

    # Read config values
    highpass_hz = config.get("ffmpeg_highpass_hz", 80)
    lowpass_hz = config.get("ffmpeg_lowpass_hz", 8000)
    noise_floor = config.get("ffmpeg_afftdn_noise_floor", -25)
    stationary = config.get("noisereduce_stationary", False)
    prop_decrease = config.get("noisereduce_prop_decrease", 0.75)

    has_ffmpeg = _ffmpeg_available()

    # Stage 1: ffmpeg
    stage1_output = None
    if has_ffmpeg:
        stage1_path = os.path.join(output_dir, f"{basename}_stage1.wav")
        if _run_ffmpeg_denoise(input_path, stage1_path, highpass_hz, lowpass_hz, noise_floor):
            stage1_output = stage1_path
            logger.debug("Stage 1 (ffmpeg denoise) complete: %s", stage1_path)
        else:
            # Try plain conversion
            logger.info("ffmpeg denoise failed, trying plain conversion")
            if _run_ffmpeg_convert(input_path, stage1_path):
                stage1_output = stage1_path
                logger.debug("Stage 1 (ffmpeg convert) complete: %s", stage1_path)
    else:
        logger.warning("ffmpeg not found -- skipping Stage 1, attempting raw conversion")
        # Without ffmpeg, we cannot convert M4A to WAV at all.
        # noisereduce needs WAV input.
        # Try soundfile directly if the input is already WAV.
        if input_path.lower().endswith(".wav"):
            stage1_output = input_path
        else:
            logger.error("Cannot process non-WAV file without ffmpeg: %s", input_path)
            return None

    if stage1_output is None:
        logger.error("Stage 1 failed completely for: %s", input_path)
        return None

    # Stage 2: noisereduce
    if _run_noisereduce(stage1_output, final_output, stationary, prop_decrease):
        logger.debug("Stage 2 (noisereduce) complete: %s", final_output)
        # Clean up Stage 1 intermediate file
        if stage1_output != input_path and stage1_output != final_output:
            try:
                os.remove(stage1_output)
            except OSError:
                pass
        return final_output
    else:
        # Stage 2 failed; use Stage 1 output directly
        logger.info("Stage 2 skipped/failed, using Stage 1 output")
        if stage1_output != final_output:
            try:
                os.rename(stage1_output, final_output)
            except OSError:
                # If rename fails (cross-device), copy
                import shutil
                shutil.copy2(stage1_output, final_output)
                try:
                    os.remove(stage1_output)
                except OSError:
                    pass
        return final_output


def cleanup_orphaned(output_dir: str, max_age_hours: int = 24) -> int:
    """Remove orphaned denoised files older than max_age_hours.

    Called periodically by the daemon to prevent temp file accumulation.
    Returns count of files removed.
    """
    import time

    if not os.path.isdir(output_dir):
        return 0

    cutoff = time.time() - (max_age_hours * 3600)
    removed = 0
    for filename in os.listdir(output_dir):
        filepath = os.path.join(output_dir, filename)
        if not os.path.isfile(filepath):
            continue
        try:
            if os.path.getmtime(filepath) < cutoff:
                os.remove(filepath)
                removed += 1
                logger.debug("Removed orphaned temp file: %s", filepath)
        except OSError:
            pass

    if removed:
        logger.info("Cleaned up %d orphaned denoised file(s)", removed)
    return removed
