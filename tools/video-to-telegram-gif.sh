#!/bin/bash
# Convert video to high-quality silent MP4 for Telegram (auto-plays like GIF)
# Usage: video-to-telegram-gif.sh input.mp4 [output.mp4] [scale]

set -e

INPUT="$1"
OUTPUT="${2:-${INPUT%.*}_telegram.mp4}"
SCALE="${3:-720}"  # Default to 720p width, maintains aspect ratio

if [ -z "$INPUT" ]; then
    echo "Usage: video-to-telegram-gif.sh <input> [output] [scale_width]"
    echo ""
    echo "Examples:"
    echo "  video-to-telegram-gif.sh video.mp4                    # Output: video_telegram.mp4"
    echo "  video-to-telegram-gif.sh video.mp4 output.mp4         # Custom output name"
    echo "  video-to-telegram-gif.sh video.mp4 output.mp4 480     # 480p width"
    echo ""
    echo "Scale presets:"
    echo "  480  - Good for most GIF-like content"
    echo "  720  - High quality (default)"
    echo "  1080 - Maximum quality (larger file)"
    exit 1
fi

if [ ! -f "$INPUT" ]; then
    echo "Error: Input file '$INPUT' not found"
    exit 1
fi

echo "Converting: $INPUT"
echo "Output: $OUTPUT"
echo "Scale: ${SCALE}p width"
echo ""

ffmpeg -i "$INPUT" \
    -an \
    -c:v libx264 \
    -preset slow \
    -crf 18 \
    -pix_fmt yuv420p \
    -movflags +faststart \
    -vf "scale=${SCALE}:-2" \
    -y \
    "$OUTPUT"

# Get file sizes
INPUT_SIZE=$(du -h "$INPUT" | cut -f1)
OUTPUT_SIZE=$(du -h "$OUTPUT" | cut -f1)

echo ""
echo "Done!"
echo "Input:  $INPUT_SIZE"
echo "Output: $OUTPUT_SIZE"
echo ""
echo "File ready for Telegram: $OUTPUT"
