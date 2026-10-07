#!/usr/bin/env python3
"""
Persistent TTS Server - Keeps Kokoro model loaded in memory

Solves the performance issue where model loads fresh on every TTS call.
The server loads the model once at startup and reuses it for all requests.

Expected speedup: 3-5 seconds → <1 second per TTS call
"""

import json
import os
import socket
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

import numpy as np

# Import mlx_audio
try:
    from mlx_audio.tts.generate import remove_silence_on_both_ends
    from mlx_audio.tts.utils import load_model
    import mlx.core as mx
except ImportError as e:
    print(f"Failed to import mlx_audio: {e}", file=sys.stderr)
    print("Make sure mlx_audio is installed for Python 3.11", file=sys.stderr)
    sys.exit(1)


def audio_volume_normalize(audio: np.ndarray, coeff: float = 0.5) -> np.ndarray:
    """Normalize audio volume (replacement for removed mlx_audio function)."""
    peak = np.max(np.abs(audio))
    if peak > 0:
        target = coeff
        audio = audio * (target / peak)
    return audio

# Configuration
SERVER_HOST = "127.0.0.1"
SERVER_PORT = 9876
MODEL_PATH = "prince-canuma/Kokoro-82M"
VOICE = "af_nova"
SPEED = 1.1
OUTPUT_DIR = Path.home() / '.mlx_audio' / 'outputs'
LOG_FILE = Path.home() / '.claude' / 'tts_server.log'
PID_FILE = Path.home() / '.claude' / 'tts_server.pid'


class TTSServer:
    """Persistent TTS server with pre-loaded model."""

    def __init__(self):
        self.model = None
        self.model_loaded = False
        self.request_count = 0
        self.log_file = LOG_FILE
        self.log_file.parent.mkdir(parents=True, exist_ok=True)
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    def log(self, message: str) -> None:
        """Log to both stdout and file."""
        timestamp = datetime.now().isoformat()
        log_line = f"[{timestamp}] {message}\n"
        print(log_line.strip())
        try:
            with open(self.log_file, 'a') as f:
                f.write(log_line)
        except Exception:
            pass

    def load_model_once(self) -> None:
        """Load the Kokoro model into memory once."""
        if self.model_loaded:
            return

        self.log(f"Loading model: {MODEL_PATH}")
        start_time = time.time()

        try:
            self.model = load_model(model_path=MODEL_PATH)
            load_time = time.time() - start_time
            self.model_loaded = True
            self.log(f"✅ Model loaded successfully in {load_time:.2f}s")
        except Exception as e:
            self.log(f"❌ Failed to load model: {e}")
            raise

    def _post_process_audio(self, audio: mx.array) -> tuple[np.ndarray, int]:
        """Minimal processing that preserves speech quality while fixing sample rate.

        Returns:
            Tuple of (processed_audio, sample_rate)
        """
        audio_np = np.array(audio, dtype=np.float32)
        output_sr = self.model.sample_rate  # Track the output sample rate

        if audio_np.size == 0:
            return audio_np, output_sr

        # Ensure we do not carry NaNs/Infs through the pipeline
        audio_np = np.nan_to_num(audio_np, nan=0.0, posinf=0.0, neginf=0.0)

        # 1. Remove DC offset (keeps voice centered)
        audio_np -= np.mean(audio_np)

        # 2. Gentle silence trim (preserve quiet speech)
        try:
            trimmed = remove_silence_on_both_ends(
                audio_np,
                self.model.sample_rate,
                window_duration=0.08,
                volume_threshold=0.003,  # Gentler threshold
            )
            if trimmed.size >= int(0.1 * self.model.sample_rate):
                audio_np = trimmed.astype(np.float32, copy=False)
        except Exception as exc:
            self.log(f"Silence trim skipped: {exc}")

        # 3. Pre-resample spike removal (only extreme artifacts)
        diffs = np.abs(np.diff(audio_np))
        if diffs.size > 0:
            candidate_indices = np.where(diffs > 0.5)[0] + 1
            repaired = 0
            for idx in candidate_indices:
                if idx <= 0 or idx >= audio_np.size - 1:
                    continue
                centre = audio_np[idx]
                left = audio_np[idx - 1]
                right = audio_np[idx + 1]
                if (
                    abs(centre) > 0.5
                    and abs(centre - left) > 0.5
                    and abs(centre - right) > 0.5
                ):
                    audio_np[idx] = 0.5 * (left + right)
                    repaired += 1
            if repaired:
                self.log(f"Pre-resample: smoothed {repaired} extreme spikes")

        # 4. Resample to 44.1kHz to match Mac output (prevents CoreAudio artifacts)
        target_sr = 44100
        if self.model.sample_rate != target_sr:
            try:
                # Use soxr for high-quality, artifact-free resampling
                import soxr
                audio_np = soxr.resample(
                    audio_np,
                    self.model.sample_rate,
                    target_sr,
                    quality='VHQ'  # Very High Quality - no transient artifacts
                )
                output_sr = target_sr  # Update output sample rate
                self.log(f"Resampled to {target_sr}Hz using soxr (VHQ)")
            except ImportError:
                # Fallback to librosa with safer settings
                try:
                    import librosa
                    audio_np = librosa.resample(
                        audio_np,
                        orig_sr=self.model.sample_rate,
                        target_sr=target_sr,
                        res_type='soxr_vhq'  # Use soxr backend if available
                    )
                    output_sr = target_sr
                    self.log(f"Resampled to {target_sr}Hz using librosa")
                except Exception as exc:
                    self.log(f"Resampling failed: {exc}")
            except Exception as exc:
                self.log(f"Resampling failed: {exc}")

        # 5. Post-resample de-clicking: remove clicks/pops from resampling artifacts
        diffs_post = np.abs(np.diff(audio_np))
        if diffs_post.size > 0:
            # Detect transients (sharp changes that sound like clicks)
            click_threshold = 0.15
            click_indices = np.where(diffs_post > click_threshold)[0] + 1
            clicks_removed = 0

            for idx in click_indices:
                if idx <= 1 or idx >= audio_np.size - 2:
                    continue

                # Check if this is an isolated transient (click) vs natural speech
                centre = audio_np[idx]
                left1 = audio_np[idx - 1]
                left2 = audio_np[idx - 2]
                right1 = audio_np[idx + 1]
                right2 = audio_np[idx + 2]

                # Click detection: center value significantly different from neighbors
                left_avg = (left1 + left2) / 2
                right_avg = (right1 + right2) / 2
                expected = (left_avg + right_avg) / 2

                if abs(centre - expected) > 0.15:
                    # Interpolate using cubic smoothing for natural sound
                    audio_np[idx] = 0.5 * (left1 + right1)
                    clicks_removed += 1

            if clicks_removed > 0:
                self.log(f"De-clicked: removed {clicks_removed} transient artifacts")

        # 6. Apply short fades at start/end to prevent edge clicks
        fade_samples = min(int(0.005 * output_sr), audio_np.size // 2)
        if fade_samples > 0:
            fade = np.linspace(0.0, 1.0, fade_samples, dtype=np.float32)
            audio_np[:fade_samples] *= fade
            audio_np[-fade_samples:] *= fade[::-1]

        # 7. Very gentle volume normalization (avoid amplifying artifacts)
        audio_np = audio_volume_normalize(audio_np, coeff=0.4).astype(np.float32)

        # 8. Soft limiting (prevent only extreme peaks)
        max_val = np.max(np.abs(audio_np))
        if max_val > 0.98:
            compression_ratio = 0.98 / max_val
            audio_np *= compression_ratio
            self.log(f"Soft limit applied: {compression_ratio:.2f}x")

        # 9. Final safety clip
        np.clip(audio_np, -0.99, 0.99, out=audio_np)

        # Log audio quality metrics
        rms = np.sqrt(np.mean(audio_np**2))
        peak = np.max(np.abs(audio_np))
        crest = peak / (rms + 1e-10)
        self.log(f"Quality - RMS: {rms:.4f}, Peak: {peak:.4f}, Crest: {crest:.2f}")

        return audio_np, output_sr

    def generate_tts(self, text: str, speed: float = SPEED) -> Optional[Path]:
        """Generate TTS audio using pre-loaded model."""
        if not self.model_loaded:
            self.log("Model not loaded, loading now...")
            self.load_model_once()

        try:
            # Generate unique filename
            file_prefix = f"tts_server_{int(time.time())}_{self.request_count}"
            self.request_count += 1

            # Change to output directory (Kokoro saves to CWD)
            original_dir = Path.cwd()
            os.chdir(OUTPUT_DIR)

            start_time = time.time()
            try:
                # Generate using pre-loaded model (much faster!)
                results = self.model.generate(
                    text=text,
                    voice=VOICE,
                    speed=speed,
                    lang_code="a",
                    temperature=0.7,
                    max_tokens=1200,
                    verbose=False,
                    stream=False,
                    streaming_interval=2.0,
                )

                # Save audio file
                import soundfile as sf
                for i, result in enumerate(results):
                    audio_np, sample_rate = self._post_process_audio(result.audio)
                    if audio_np.size == 0:
                        raise ValueError("Generated audio is empty after processing")

                    file_name = f"{file_prefix}.wav"
                    sf.write(
                        file_name,
                        audio_np,
                        sample_rate,
                        subtype="PCM_16",
                    )
                    audio_path = OUTPUT_DIR / file_name

                    generation_time = time.time() - start_time
                    self.log(f"Generated audio in {generation_time:.2f}s @ {sample_rate}Hz: {audio_path}")

                    return audio_path

            finally:
                os.chdir(original_dir)
                # Clear MLX cache to prevent memory bloat
                mx.clear_cache()

        except Exception as e:
            self.log(f"TTS generation error: {e}")
            return None

    def handle_request(self, data: dict) -> dict:
        """Handle incoming TTS request."""
        text = data.get("text", "").strip()
        try:
            speed = float(data.get("speed", SPEED))
            speed = max(0.5, min(speed, 2.0))
        except (TypeError, ValueError):
            speed = SPEED

        if not text or len(text) < 10:
            return {"status": "error", "message": "Text too short"}

        self.log(f"Request #{self.request_count}: {len(text)} chars (speed={speed})")

        audio_path = self.generate_tts(text, speed=speed)

        if audio_path and audio_path.exists():
            return {
                "status": "success",
                "audio_path": str(audio_path),
                "request_count": self.request_count
            }
        else:
            return {"status": "error", "message": "Failed to generate audio"}

    def run(self) -> None:
        """Start the TTS server."""
        # Write PID file
        PID_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(PID_FILE, 'w') as f:
            f.write(str(os.getpid()))

        self.log(f"🚀 TTS Server starting on {SERVER_HOST}:{SERVER_PORT}")

        # Pre-load model at startup
        self.load_model_once()

        # Create socket server
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        try:
            server_socket.bind((SERVER_HOST, SERVER_PORT))
            server_socket.listen(5)
            self.log(f"✅ Server listening (model ready for fast inference)")

            while True:
                client_socket, address = server_socket.accept()

                try:
                    # Receive request
                    data = b""
                    while True:
                        chunk = client_socket.recv(4096)
                        if not chunk:
                            break
                        data += chunk
                        if b"\n\n" in data:  # End marker
                            break

                    if not data:
                        continue

                    request = json.loads(data.decode('utf-8').strip())
                    response = self.handle_request(request)

                    # Send response
                    client_socket.sendall(json.dumps(response).encode('utf-8'))

                except Exception as e:
                    self.log(f"Request handling error: {e}")
                    try:
                        error_response = {"status": "error", "message": str(e)}
                        client_socket.sendall(json.dumps(error_response).encode('utf-8'))
                    except:
                        pass
                finally:
                    client_socket.close()

        except KeyboardInterrupt:
            self.log("Server shutting down...")
        except Exception as e:
            self.log(f"Server error: {e}")
        finally:
            server_socket.close()
            if PID_FILE.exists():
                PID_FILE.unlink()
            self.log("Server stopped")


def main():
    """Entry point."""
    server = TTSServer()
    server.run()


if __name__ == "__main__":
    main()
