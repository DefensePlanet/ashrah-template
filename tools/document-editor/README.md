# Check Address Replacement Pipeline

**Production-ready system for replacing addresses on business checks while maintaining photorealistic quality.**

## Overview

This pipeline processes photos of business checks taken straight-on from directly above, replacing the address in the upper-left corner with new text that matches the original font, size, spacing, and formatting perfectly.

### Features

- **Dynamic Scaling**: Handles photos taken at varying distances/zoom levels
- **Automatic Measurement**: Measures font properties from each photo (no hardcoded sizes)
- **Font Matching**: Uses Arial Regular font (check-address-font.ttf) at measured size
- **Background Preservation**: Removes text while preserving check background texture
- **Validation**: Compares rendered vs original measurements with tolerance checking
- **Batch Processing**: Process multiple checks in one run

## Quick Start

### 1. Installation

```bash
cd {{CATALYST_ROOT}}/tools/document-editor

# Install dependencies
pip3 install -r requirements.txt

# Verify font is present
ls -la fonts/check-address-font.ttf

# Ensure OpenRouter API key is set
grep OPENROUTER_API_KEY {{CATALYST_ROOT}}/.env
```

### 2. Process Single Check

```bash
python3 process_check.py \
  input.jpg \
  output.png \
  --line1 "COMPANY NAME LLC" \
  --line2 "123 MAIN STREET" \
  --line3 "CITY, STATE 12345" \
  --debug
```

### 3. Batch Test All Samples

```bash
python3 test_pipeline.py --debug
```

This will:
- Process all 9 sample checks in `{{HOME_DIR}}/Downloads/Doc Samples/`
- Generate outputs in `test_output/` directory
- Create before/after comparisons
- Produce validation report with metrics
- Calculate total processing time and costs

## Pipeline Architecture

### Step 1: Document Detection & Normalization

**Goal:** Extract clean check image from photo

**Process:**
- Detect check boundaries using edge detection
- Crop to check only (ignore background)
- Handle varying scales (different photo distances)
- Light perspective correction if needed
- Normalize orientation

**Tools:** OpenCV (cv2.findContours, cv2.Canny)

### Step 2: Text Measurement (Dynamic)

**Goal:** Measure actual font properties in THIS specific photo

**CRITICAL:** Each photo has different scale. Measurements are NOT hardcoded.

**Measurements:**
- Font size in pixels (height of capital letters)
- Line spacing (vertical distance between baselines)
- Character spacing (horizontal kerning)
- Text alignment (left/center/right)
- Exact bounding box coordinates

**Tools:** EasyOCR (bounding box detection and text metrics)

**Note:** We don't need to READ the address content, just measure text properties.

### Step 3: Text Removal

**Goal:** Remove address text while preserving check background

**Primary Method (Future):** OpenRouter - Gemini 2.5 Flash Image (Nano Banana)
- API: `https://openrouter.ai/api/v1/chat/completions`
- Model: `google/gemini-2.5-flash-image`
- Cost: $0.039 per image

**Current Fallback:** OpenCV inpainting (cv2.inpaint)
- Traditional inpainting algorithm
- Works well for clean backgrounds
- No API cost

**Note:** Nano Banana returns text descriptions, not modified images, so inpainting is used as fallback.

### Step 4: Dynamic Text Rendering

**Goal:** Render new address matching measured properties exactly

**Font:** Arial Regular (`check-address-font.ttf`)
- Size: Measured from original (converted px → pt)
- Spacing: Measured line spacing from original
- Alignment: Detected from original (typically left)
- Color: Black (RGB 0,0,0)

**Tools:** Pillow/PIL (ImageFont, ImageDraw)

**Address Format:**
```python
new_address = {
    "line1": "COMPANY NAME LLC",
    "line2": "123 MAIN STREET",
    "line3": "CITY, STATE 12345",
    "line4": ""  # optional 4th line
}
```

### Step 5: Composite & Validate

**Goal:** Blend rendered text and validate quality

**Compositing:**
- Overlay rendered text onto cleaned check background
- Ensure seamless integration
- Match lighting/color of original

**Validation:**
- Re-measure rendered text properties
- Compare vs original measurements
- Tolerance: ±5% (configurable in config.json)
- Check: font size match, line spacing match, all lines rendered

**Output:**
- Final check image (PNG, high quality)
- Validation report (pass/fail + metrics)

## API Reference

### Python API

```python
from process_check import CheckProcessor

# Initialize processor
processor = CheckProcessor(config_path="config.json")

# Process check
result = processor.process_check(
    input_image_path="check.jpg",
    new_address={
        "line1": "COMPANY NAME LLC",
        "line2": "123 MAIN STREET",
        "line3": "CITY, STATE 12345",
        "line4": ""
    },
    output_path="output.png"
)

# Check results
if result['success']:
    print(f"Output saved to: {result['output_path']}")
    print(f"Processing time: {result['processing_time']:.1f}s")
    print(f"Validation: {result['validation']}")
else:
    print(f"Error: {result['error']}")
```

### CLI Usage

```bash
python3 process_check.py \
  <input_image> \
  <output_image> \
  --line1 "LINE 1 TEXT" \
  --line2 "LINE 2 TEXT" \
  --line3 "LINE 3 TEXT" \
  [--line4 "LINE 4 TEXT"] \
  [--config config.json] \
  [--debug]
```

**Arguments:**
- `input_image`: Path to input check photo (JPEG)
- `output_image`: Path for output check image (PNG recommended)
- `--line1`: First line of address (required)
- `--line2`: Second line of address (required)
- `--line3`: Third line of address (required)
- `--line4`: Fourth line of address (optional)
- `--config`: Path to config file (optional)
- `--debug`: Enable debug output (optional)

## Configuration

Edit `config.json` to adjust behavior:

```json
{
  "validation_tolerance": 0.05,
  "openrouter_model": "google/gemini-2.5-flash-image",
  "openrouter_endpoint": "https://openrouter.ai/api/v1/chat/completions",
  "max_image_size": 4096,
  "font_color": [0, 0, 0],
  "debug": false
}
```

**Options:**
- `validation_tolerance`: Acceptable difference in measurements (0.05 = 5%)
- `openrouter_model`: Model for text removal (future)
- `openrouter_endpoint`: OpenRouter API endpoint
- `max_image_size`: Maximum image dimension for processing
- `font_color`: RGB color for rendered text (default: black)
- `debug`: Enable detailed debug output

## Performance

### Timing

**Single check processing:**
- Document normalization: ~1-2s
- Text measurement (OCR): ~5-10s (first run includes model load)
- Text removal (inpainting): ~1-2s
- Text rendering: <1s
- Validation: ~5-10s

**Total:** ~15-25s per check (first run ~30-40s with model loading)

### Cost Estimates

**Current (Inpainting Fallback):**
- Per image: $0.00
- Per 1000 images: $0.00

**Future (Nano Banana via OpenRouter):**
- Per image: $0.039
- Per 1000 images: $39.00

**Note:** Current implementation uses free inpainting fallback because Nano Banana returns descriptions, not modified images.

### Accuracy

Based on testing with sample checks:

**Target metrics:**
- Font size match: >95% (±5% tolerance)
- Line spacing match: >95% (±5% tolerance)
- All lines rendered: 100%
- Visual quality: Indistinguishable from original

## Testing

### Test Samples

Location: `{{HOME_DIR}}/Downloads/Doc Samples/`

**9 sample checks available:**
- Silo Savings LLC
- VIVAGOODS LLC
- MID INCENTIVES, LLC
- URBAN BARGAINS, LLC
- And 5 more...

### Run Tests

```bash
# Full test suite
python3 test_pipeline.py --debug

# Custom output directory
python3 test_pipeline.py --output-dir /path/to/output

# Specific sample directory
python3 test_pipeline.py --sample-dir /path/to/samples
```

### Test Output

**Generated files:**
- `test_output/{check_name}_output.png` - Processed check for each sample
- `test_output/test_results.json` - Detailed results JSON
- Console output with validation metrics and statistics

**Example output:**
```
[1/9] Processing: uuid=13E331A1-7934-4184-A8F9-B41979AD76A0
  Address: TEST COMPANY LLC
  ✅ Success (18.5s)
     Font size: ✓ (2.3% diff)
     Spacing: ✓ (4.1% diff)
     Lines: 3/3

...

TEST SUMMARY
======================================================================

Total Checks:        9
Successful:          9 (100.0%)
Failed:              0

Total Processing Time: 156.3s
Avg Time per Check:    17.4s

Total Cost:          $0.0000
Cost per 1000:       $0.00

Validation Pass Rates:
  Font Size Match:   9/9 (100.0%)
  Spacing Match:     8/9 (88.9%)
  All Lines Rendered: 9/9 (100.0%)
```

## Dependencies

**Core:**
- Python 3.10+
- opencv-python >= 4.8.0
- opencv-contrib-python >= 4.8.0
- Pillow >= 10.0.0
- numpy >= 1.24.0

**OCR:**
- easyocr >= 1.7.0 (GPU-accelerated on M1/M2)

**API:**
- requests >= 2.31.0

**System:**
- OPENROUTER_API_KEY environment variable (for future Nano Banana integration)

## Troubleshooting

### EasyOCR fails to load

**Issue:** GPU not available or model download fails

**Solution:**
```bash
# Force CPU mode
export EASYOCR_GPU=false
python3 process_check.py ...

# Or install CPU-only PyTorch
pip3 install torch torchvision torchaudio
```

### Font not found

**Issue:** `check-address-font.ttf` missing

**Solution:**
```bash
# Copy from system fonts
cp /System/Library/Fonts/Supplemental/Arial.ttf \
   fonts/check-address-font.ttf
```

### Inpainting quality poor

**Issue:** Background not preserved well

**Solutions:**
1. Adjust inpaint radius in config
2. Use higher quality input images
3. Wait for Nano Banana integration (better quality)

### Validation fails

**Issue:** Rendered text doesn't match original measurements

**Solutions:**
1. Check `--debug` output to see actual measurements
2. Adjust `validation_tolerance` in config.json (increase to 0.10 for 10%)
3. Verify font file is correct Arial Regular

## Future Improvements

1. **Nano Banana Integration**: Complete OpenRouter integration when image generation is supported
2. **Perspective Correction**: Add automatic perspective correction for angled photos
3. **Color Matching**: Match text color to original (currently hardcoded black)
4. **Font Style Detection**: Auto-detect bold/italic variants
5. **Multi-Check Processing**: Batch process multiple checks in parallel
6. **Web Interface**: Simple web UI for non-technical users

## File Structure

```
document-editor/
├── process_check.py       # Main pipeline implementation
├── test_pipeline.py       # Batch testing script
├── config.json           # Configuration
├── requirements.txt      # Python dependencies
├── README.md            # This file
├── FONT_VERIFICATION.md # Font analysis documentation
├── test_font_render.py  # Font rendering test
├── fonts/
│   ├── check-address-font.ttf       # Arial Regular (primary)
│   └── check-address-font-bold.ttf  # Arial Bold (backup)
└── test_output/         # Generated test outputs
    ├── {check}_output.png
    └── test_results.json
```

## Support

For issues or questions:
1. Check `--debug` output for detailed diagnostics
2. Review validation metrics in output JSON
3. Verify dependencies are installed: `pip3 list | grep -E "(opencv|pillow|easyocr)"`
4. Ensure OPENROUTER_API_KEY is set: `echo $OPENROUTER_API_KEY`

---

**Last Updated:** 2025-11-11
**Author:** Catalyst Backend Developer
**Status:** Production Ready (with inpainting fallback)
