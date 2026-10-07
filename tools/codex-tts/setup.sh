#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

echo "=== Kokoro TTS Setup for Claude Code ==="
echo ""
echo "This sets up local, zero-cost text-to-speech for Claude Code responses"
echo "using the Kokoro-82M model on Apple Silicon."
echo ""

# 1. Check platform
if [[ "$(uname -s)" != "Darwin" ]]; then
    echo "ERROR: Kokoro TTS requires macOS (uses afplay for audio playback)"
    exit 1
fi

if [[ "$(uname -m)" != "arm64" ]]; then
    echo "ERROR: Kokoro TTS requires Apple Silicon (M1/M2/M3/M4) for the MLX framework"
    exit 1
fi

# 2. Find Python 3.11+
PYTHON=""
for candidate in \
    "/Library/Frameworks/Python.framework/Versions/3.11/bin/python3" \
    "/Library/Frameworks/Python.framework/Versions/3.12/bin/python3" \
    "/Library/Frameworks/Python.framework/Versions/3.13/bin/python3" \
    "/opt/homebrew/bin/python3" \
    "python3"; do
    if command -v "$candidate" &>/dev/null; then
        version=$("$candidate" -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>/dev/null || echo "0.0")
        major=$(echo "$version" | cut -d. -f1)
        minor=$(echo "$version" | cut -d. -f2)
        if [ "$major" -ge 3 ] && [ "$minor" -ge 11 ]; then
            PYTHON="$candidate"
            echo "Found Python $version at $candidate"
            break
        fi
    fi
done

if [ -z "$PYTHON" ]; then
    echo "ERROR: Python 3.11+ required."
    echo "Install from https://www.python.org/downloads/"
    exit 1
fi

# 3. Install dependencies
echo ""
echo "Installing Python dependencies..."
"$PYTHON" -m pip install -r "$SCRIPT_DIR/requirements.txt" --quiet
echo "Dependencies installed."

# 4. Create output directories
mkdir -p "$HOME/.mlx_audio/outputs"
mkdir -p "$HOME/.claude"
echo "Output directories created."

# 5. Pre-download Kokoro-82M model
echo ""
echo "Pre-downloading Kokoro-82M model (~160MB, one-time)..."
"$PYTHON" -c "
from mlx_audio.tts.utils import load_model
load_model(model_path='prince-canuma/Kokoro-82M')
print('Model cached successfully.')
" 2>/dev/null || {
    echo "NOTE: Model will download on first TTS request instead (requires internet)."
}

# 6. Summary
echo ""
echo "=== Setup Complete ==="
echo ""
echo "To enable voice summaries, use /voice in Claude Code."
echo ""
echo "How it works:"
echo "  - After each Claude Code response, the <tts-summary> tag is extracted"
echo "  - Text is sent to a local Kokoro TTS server (auto-starts on first use)"
echo "  - Audio plays through your Mac speakers via afplay"
echo ""
echo "Manual controls:"
echo "  Start server:  $SCRIPT_DIR/tts-server-ctl.sh start"
echo "  Stop server:   $SCRIPT_DIR/tts-server-ctl.sh stop"
echo "  Server status: $SCRIPT_DIR/tts-server-ctl.sh status"
echo ""
echo "Model: prince-canuma/Kokoro-82M | Voice: am_onyx | Cost: \$0"
