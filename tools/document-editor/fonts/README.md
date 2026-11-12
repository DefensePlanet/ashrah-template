# Business Check Fonts

## Font Identification

**Primary Font:** Arial (Regular weight)
**Source:** `/System/Library/Fonts/Supplemental/Arial.ttf`

## Font Files

- `check-address-font.ttf` - Arial Regular (755 KB) - **PRIMARY**
- `check-address-font-bold.ttf` - Arial Bold (749 KB) - Backup/optional

## Usage

### Address Block Rendering

Business check addresses use **Arial Regular** at approximately **10-11pt** size.

**Example addresses from samples:**
```
MID INCENTIVES, LLC

Silo Savings LLC
304 N 460 E
Vineyard, UT 84059

URBAN BARGAINS, LLC
1945 E ROSEMEADE PKWY STE 1122
CARROLLTON, TX 75007-2637

VIVAGOODS LLC
1000 MAIN ST STE 2300
HOUSTON, TX 77002-6353
```

### Python/Pillow Usage

```python
from PIL import ImageFont

# Load font
font = ImageFont.truetype(
    "{{CATALYST_ROOT}}/tools/document-editor/fonts/check-address-font.ttf",
    size=11  # 10-11pt typical for check addresses
)

# Render text
draw.text((x, y), "COMPANY NAME\nADDRESS LINE 1\nCITY, STATE ZIP", fill='black', font=font)
```

## Font Characteristics

- **Type:** Sans-serif
- **Style:** Clean, professional, high readability
- **Weight:** Regular (400)
- **Spacing:** Proportional (not monospace)
- **License:** System font (macOS included)

## Verification

Run test script to verify font rendering:
```bash
python3 {{CATALYST_ROOT}}/tools/document-editor/test_font_render.py
```

Output: `{{CATALYST_ROOT}}/tools/document-editor/test_render.png`

Compare to samples: `{{HOME_DIR}}/Downloads/Doc Samples/`

## Notes

- Font size on checks appears to be 10-11pt
- Line spacing: ~15px at 11pt
- All uppercase or mixed case (depends on check template)
- No special kerning or tracking adjustments needed
- Standard Arial renders identically to check samples
