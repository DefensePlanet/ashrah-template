#!/usr/bin/env python3
"""
Codex Summary TTS (Alloy)

Dedicated TTS pipeline for Codex only. Creates a concise summary of the
assistant's last reply and speaks it using OpenAI TTS with the 'alloy' voice.

This keeps Codex voice separate from Claude Code's TTS configuration.
"""

import json
import os
import re
import sys
import tempfile
import subprocess
import requests
import importlib.util
from typing import Callable
from types import ModuleType
from datetime import datetime
from pathlib import Path
import time

# Kokoro TTS imports (replacing OpenAI TTS)
from mlx_audio.tts.generate import generate_audio


def log_debug(message: str) -> None:
    try:
        with open('/tmp/codex_tts_debug.log', 'a') as f:
            f.write(f"{datetime.now()}: {message}\n")
    except Exception:
        pass


def _local_conceptual_summary(text: str) -> str:
    """Deterministic, template-based summary to avoid hallucinations.

    Extracts structured elements (Actions, Findings, Files, Next) and composes
    a fixed-format, 1–3 clause summary. Falls back to a single clear sentence
    if patterns not found. Always shorter than input.
    """
    # Normalize/clean
    t = re.sub(r'<[^>]+>', '', text)
    t = re.sub(r'```[\s\S]*?```', ' ', t)
    t = re.sub(r'`([^`]+)`', r'\1', t)
    t = re.sub(r'\*\*(.*?)\*\*', r'\1', t)
    t = re.sub(r'\*(.*?)\*', r'\1', t)
    t = re.sub(r'https?://\S+', ' ', t)
    t = t.replace('•', ' ').replace('–', ' ').replace('- ', ' ')
    t = re.sub(r'\n+', ' ', t)
    t = re.sub(r'\s+', ' ', t).strip()

    # Pattern extraction
    def cap(s: str) -> str:
        s = s.strip().strip('.;,:- ')
        if not s:
            return s
        return s[0].upper() + s[1:]

    actions = re.findall(r'(?:I will|I\'m going to|Let me|I\'ll|I am|We will|Next I|Proceed to)\s+([^.!?]*[.!?])', t, re.IGNORECASE)
    findings = re.findall(r'(?:I found|I discovered|I identified|The issue is|The problem is|It appears|We observed)\s+([^.!?]*[.!?])', t, re.IGNORECASE)
    file_ops = re.findall(r'(?:created|updated|modified|edited|wrote|read|added|removed)\s+([^.!?]*[.!?])', t, re.IGNORECASE)
    nexts = re.findall(r'(?:You should|I recommend|Next steps?|To fix|To resolve|Consider)\s+([^.!?]*[.!?])', t, re.IGNORECASE)

    A = cap(actions[0]) if actions else ''
    F = cap(findings[0]) if findings else ''
    O = cap(file_ops[0]) if file_ops else ''
    N = cap(nexts[0]) if nexts else ''

    parts = []
    if A:
        parts.append(f"Actions: {A}")
    if F:
        parts.append(f"Findings: {F}")
    if O:
        parts.append(f"Files: {O}")
    if N:
        parts.append(f"Next: {N}")

    if not parts:
        # Fallback: take the first reasonably short sentence as the headline
        sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', t) if 8 < len(s.strip()) < 160]
        headline = sentences[0] if sentences else t[:140]
        summary = headline.strip()
    else:
        summary = ' '.join(parts)

    # Tone and spacing
    summary = re.sub(r'[!]+', '.', summary)
    summary = re.sub(r'[🙂😀😄🚀🔥✨✅🟢🔧💡⭐️📦📊⚠️🥳🙌👍👋🧠]', '', summary)
    summary = re.sub(r'\s+\.', '. ', summary)
    summary = re.sub(r'\s+,', ', ', summary)
    summary = re.sub(r'\s{2,}', ' ', summary).strip()

    # Strict cap (max ~260 chars, end cleanly)
    if len(summary) > 260:
        cut = summary[:260].rstrip()
        m = re.search(r'[.!?](?=[^.!?]*$)', cut)
        summary = (cut[:m.end()] if m else cut)

    if summary and summary[-1] not in '.!?':
        summary += '.'
    return summary


def _load_claude_summarizer() -> Callable | None:
    """Load Claude Code's summary function for parity, if available."""
    _repo_root = Path(__file__).resolve().parents[2]
    path = str(_repo_root / "tools" / "codex-tts" / "tts_hook_client.py")
    try:
        if not os.path.exists(path):
            log_debug("TTS hook client not found; using local summarizer")
            return None
        spec = importlib.util.spec_from_file_location("tts_hook_client", path)
        if spec and spec.loader:
            mod = importlib.util.module_from_spec(spec)  # type: ignore
            spec.loader.exec_module(mod)  # type: ignore
            func = getattr(mod, "create_conceptual_summary", None)
            if callable(func):
                log_debug("Using Claude summary function for parity")
                return func
    except Exception as e:
        log_debug(f"Failed loading Claude summarizer: {e}")
    return None


def create_conceptual_summary(text: str) -> str:
    """Produce summary; prefer Claude's summarizer to match behavior exactly."""
    use_parity = os.environ.get("CODEX_TTS_USE_CLAUDE_SUMMARY", "1").lower() in ("1","true","on","yes")
    if use_parity:
        func = _load_claude_summarizer()
        if func:
            try:
                return func(text)  # type: ignore
            except Exception as e:
                log_debug(f"Claude summarizer error, falling back: {e}")
    return _local_conceptual_summary(text)


def delegate_tts_to_claude(text: str) -> bool:
    """Delegate both summary and playback to Claude's TTS hook for full parity.

    Returns True if delegation was attempted (regardless of success), False if
    not applicable.
    """
    # Default OFF to keep Codex's own voice (ash) while reusing Claude summary
    use_delegate = os.environ.get("CODEX_TTS_PARITY_TTS", "0").lower() in ("1","true","on","yes")
    _repo_root = Path(__file__).resolve().parents[2]
    path = str(_repo_root / "tools" / "codex-tts" / "tts_hook_client.py")
    if not use_delegate:
        return False
    if not os.path.exists(path):
        log_debug("Claude TTS hook not found; using local TTS")
        return False
    try:
        payload = json.dumps({"assistant_message": text}).encode("utf-8")
        log_debug("Delegating TTS to Claude hook (parity)")
        subprocess.run(["python3", path], input=payload, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
        return True
    except Exception as e:
        log_debug(f"Claude TTS delegate failed: {e}")
        return True


def get_api_key() -> str | None:
    # Prefer environment
    api = os.environ.get('OPENAI_API_KEY')
    if api:
        return api
    # Fallback to Claude settings (kept locally on this machine)
    candidates = [
        os.path.expanduser('~/.claude/settings.local.json'),
        os.path.expanduser('~/.claude/.claude/settings.json'),
        os.path.expanduser('~/.claude/settings.json')
    ]
    for path in candidates:
        try:
            if os.path.exists(path):
                with open(path, 'r') as f:
                    settings = json.load(f)
                api = settings.get('env', {}).get('OPENAI_API_KEY')
                if api:
                    return api
        except Exception:
            continue
    return None


def get_voice() -> str:
    v = os.environ.get('CODEX_TTS_VOICE')
    if v:
        return v.strip()
    # Default Codex voice (calm/professional)
    return "ash"


def get_model(default_voice: str) -> str:
    m = os.environ.get('CODEX_TTS_MODEL')
    if m:
        return m.strip()
    # Default model for ash is tts-1
    return "tts-1"


def get_speed() -> float:
    s = os.environ.get('CODEX_TTS_SPEED')
    if s:
        try:
            return float(s)
        except Exception:
            pass
    return 1.0  # calmer and clearer by default


def _fallback_system_say(text: str) -> None:
    """Best-effort local speech using macOS 'say' as a fallback.

    This avoids total silence when API fails or API key is missing.
    """
    try:
        if not text or len(text) < 6:
            return
        rate = os.environ.get('CODEX_TTS_SAY_RATE')  # e.g., '220'
        voice = os.environ.get('CODEX_TTS_SAY_VOICE')  # e.g., 'Samantha'
        cmd = ['say']
        if voice:
            cmd += ['-v', voice]
        if rate:
            cmd += ['-r', rate]
        cmd.append(text)
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=60)
    except Exception as e:
        log_debug(f"Fallback say error: {e}")


def text_to_speech(text: str, api_key: str) -> None:
    """Convert text to speech using Kokoro-82M local TTS model.

    Replaced OpenAI TTS with Kokoro am_onyx voice for zero-cost, offline TTS.
    Model: prince-canuma/Kokoro-82M
    Voice: am_onyx (American English male, similar to OpenAI's onyx)

    Args:
        text: Text to convert to speech
        api_key: Unused (kept for API compatibility)
    """
    if not text or len(text) < 10:
        return

    try:
        # Stop any current playback to avoid overlap
        subprocess.run(['pkill', '-f', 'afplay'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        # Map OpenAI voice names to Kokoro voices
        voice_env = os.environ.get('CODEX_TTS_VOICE', 'onyx').lower()
        voice_mapping = {
            'onyx': 'am_onyx',
            'alloy': 'am_onyx',
            'echo': 'am_onyx',
            'fable': 'am_onyx',
            'nova': 'am_onyx',
            'shimmer': 'am_onyx',
            'ash': 'am_onyx'
        }
        kokoro_voice = voice_mapping.get(voice_env, 'am_onyx')

        # Get speed (clamp to Kokoro's valid range: 0.5-2.0)
        speed = get_speed()
        speed = max(0.5, min(2.0, speed))

        # Create output directory and change to it (Kokoro saves to CWD)
        output_dir = Path.home() / '.mlx_audio' / 'outputs'
        output_dir.mkdir(parents=True, exist_ok=True)

        # Generate unique filename
        file_prefix = f"codex_tts_{int(time.time())}"

        log_debug(f"Kokoro TTS: voice={kokoro_voice} speed={speed}")

        # Save current directory and change to output dir
        original_dir = Path.cwd()
        os.chdir(output_dir)

        try:
            # Generate audio with Kokoro (saves to current directory)
            generate_audio(
                text=text,
                model_path="prince-canuma/Kokoro-82M",
                voice=kokoro_voice,
                speed=speed,
                lang_code="a",  # American English
                file_prefix=file_prefix,
                audio_format="wav",
                sample_rate=24000,
                join_audio=True,
                verbose=False
            )
        finally:
            # Restore original directory
            os.chdir(original_dir)

        # Play the generated audio
        audio_path = output_dir / f"{file_prefix}.wav"
        if audio_path.exists():
            log_debug(f"Playing audio: {audio_path}")
            subprocess.run(['afplay', str(audio_path)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=90)
            # Cleanup
            try:
                audio_path.unlink()
            except Exception:
                pass
        else:
            raise FileNotFoundError(f"Kokoro audio not found: {audio_path}")

    except Exception as e:
        log_debug(f"Kokoro TTS error: {e}")
        # Fallback to macOS say if available
        _fallback_system_say(text)


def read_input() -> str:
    raw = sys.stdin.read()
    if not raw:
        return ""
    try:
        obj = json.loads(raw)
        # Preferred keys
        for k in ("assistant_message", "message", "text", "content"):
            if k in obj and isinstance(obj[k], str):
                return obj[k]
        return json.dumps(obj, ensure_ascii=False)
    except json.JSONDecodeError:
        return raw


def main() -> int:
    log_debug("Codex TTS start")
    api_key = get_api_key()
    if not api_key:
        log_debug("No OPENAI_API_KEY; using local 'say' fallback")

    full_text = read_input()
    if not full_text or len(full_text.strip()) < 20:
        log_debug("No substantial text")
        return 0

    log_debug(f"Input len={len(full_text)}")
    summary = create_conceptual_summary(full_text)
    log_debug(f"Summary len={len(summary)}")
    if summary:
        # Prefer delegating to Claude's TTS hook for exact parity
        if not delegate_tts_to_claude(summary):
            if api_key:
                log_debug("Requesting local TTS playback")
                text_to_speech(summary, api_key)
                log_debug("Playback finished")
            else:
                log_debug("Requesting fallback 'say' playback")
                _fallback_system_say(summary)
                log_debug("Fallback playback finished")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
