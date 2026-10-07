"""Speech-to-text transcription using mlx-whisper.

Uses Apple Silicon MLX acceleration for fast on-device transcription.
Lazy-loads the model on first transcribe() call.
"""

import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)

# Ensure Homebrew bin is in PATH — mlx-whisper shells out to ffmpeg for audio loading
_HOMEBREW_PATHS = ["/opt/homebrew/bin", "/usr/local/bin"]
for _p in _HOMEBREW_PATHS:
    if _p not in os.environ.get("PATH", ""):
        os.environ["PATH"] = _p + ":" + os.environ.get("PATH", "")
        break


class Transcriber:
    """Whisper-based speech-to-text transcriber using Apple Silicon MLX acceleration.

    The model is lazy-loaded on first transcribe() call to avoid slow startup
    when the pipeline is only doing discovery or status checks.
    """

    # Model repo map — local paths for pre-downloaded, HF repos for on-demand
    _LOCAL_CACHE = os.path.expanduser("~/.cache/catalyst-voice-pipeline/models")
    MODEL_REPOS = {
        # Pre-downloaded via curl (HF xet bridge is unreliable for large files)
        "distil-large-v3-4bit": os.path.join(_LOCAL_CACHE, "mlx_models/distil-large-v3-4-bit"),
        "distil-large-v3": os.path.join(_LOCAL_CACHE, "whisper-distil-large-v3"),
        # HF Hub repos (auto-download via snapshot_download)
        "large-v3-turbo": "mlx-community/whisper-large-v3-turbo",
        "large-v3": "mlx-community/whisper-large-v3-mlx",
        "small": "mlx-community/whisper-small-mlx",
        "tiny": "mlx-community/whisper-tiny",
    }

    def __init__(
        self,
        model: str = "large-v3-turbo",
        batch_size: int = 12,
    ):
        self.model = model
        self.batch_size = batch_size
        self._repo_id = self.MODEL_REPOS.get(model, model)
        self._available = None
        self._loaded = False

    def _check_available(self) -> bool:
        """Check if mlx_whisper is importable."""
        if self._available is not None:
            return self._available
        try:
            import mlx_whisper  # noqa: F401
            self._available = True
        except ImportError:
            logger.warning(
                "mlx_whisper not installed. "
                "Install with: pip install mlx-whisper"
            )
            self._available = False
        return self._available

    def transcribe(
        self,
        audio_path: str,
        language: str = "en",
    ) -> Optional[dict]:
        """Transcribe an audio file to text.

        Args:
            audio_path: Path to a WAV file (16kHz mono recommended).
            language: Language code for transcription.

        Returns:
            Dict with 'text', 'segments', and 'language' keys,
            or None if transcription fails.
        """
        if not self._check_available():
            return None

        try:
            import mlx_whisper

            if not self._loaded:
                logger.info(
                    "Loading Whisper model: %s (repo=%s)",
                    self.model, self._repo_id,
                )

            result = mlx_whisper.transcribe(
                audio_path,
                path_or_hf_repo=self._repo_id,
                language=language,
                verbose=False,
            )

            if not self._loaded:
                logger.info("Whisper model loaded successfully")
                self._loaded = True

            text = result.get("text", "").strip()
            segments = result.get("segments", [])
            detected_lang = result.get("language", language)

            word_count = len(text.split()) if text else 0

            logger.info(
                "Transcribed %s: %d words, %d segments",
                audio_path, word_count, len(segments),
            )

            return {
                "text": text,
                "segments": segments,
                "language": detected_lang,
                "word_count": word_count,
            }
        except Exception as e:
            logger.error("Transcription failed for %s: %s", audio_path, e)
            return None
