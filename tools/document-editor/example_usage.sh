#!/bin/bash
# Example usage of the document text replacement pipeline

cd "$(dirname "$0")"

echo "🔧 Document Text Replacement Pipeline - Example Usage"
echo ""

# Check if test document exists
if [ ! -f "tests/sample_documents/test_document.jpg" ]; then
    echo "📝 Creating test document..."
    python3 tests/create_test_image.py
    echo ""
fi

echo "🎨 Processing document (MVP mode - OpenCV)..."
python3 src/process_document.py \
    --input tests/sample_documents/test_document.jpg \
    --output output/example_result.jpg \
    --new-text "123 New Street\nNew York, NY 10001\nUnited States"

echo ""
echo "✅ Done! Opening result..."
open output/example_result.jpg

echo ""
echo "💡 To use your own document:"
echo "   1. Place your image in tests/sample_documents/"
echo "   2. Run: python3 src/process_document.py --input tests/sample_documents/YOUR_FILE.jpg --output output/result.jpg --new-text 'Your text here'"
echo ""
echo "🚀 To use high-quality API mode, add --use-api flag"
