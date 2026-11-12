#!/usr/bin/env python3
"""
Create white menu bar icon from Catalyst app icon.
Preserves the original alpha channel while making foreground pure white.
"""

from PIL import Image
import numpy as np
import sys

def create_white_icon(source_path, output_16, output_32):
    """Convert icon to white version with preserved alpha."""
    print(f"Loading source icon: {source_path}")

    # Load source icon and convert to RGBA
    img = Image.open(source_path).convert('RGBA')
    data = np.array(img)

    print(f"Source image size: {img.size}")
    print(f"Source image mode: {img.mode}")

    # Get alpha channel
    alpha = data[:, :, 3]

    # Create white image with original alpha
    white_icon = np.zeros_like(data)
    white_icon[:, :, 0] = 255  # R - white
    white_icon[:, :, 1] = 255  # G - white
    white_icon[:, :, 2] = 255  # B - white
    white_icon[:, :, 3] = alpha  # Keep original alpha for anti-aliasing

    # Convert back to PIL Image
    result = Image.fromarray(white_icon, 'RGBA')

    # Create 16x16 version
    icon_16 = result.resize((16, 16), Image.Resampling.LANCZOS)
    icon_16.save(output_16, 'PNG')
    print(f"✅ Created: {output_16}")

    # Create 32x32 version (for @2x)
    icon_32 = result.resize((32, 32), Image.Resampling.LANCZOS)
    icon_32.save(output_32, 'PNG')
    print(f"✅ Created: {output_32}")

    print("\n✅ White icons created successfully!")
    print("Icons are pure white (#FFFFFF) with original alpha channel preserved.")

if __name__ == "__main__":
    source = "{{CATALYST_ROOT}}/capsules/catalyst-mobile/src/Assets.xcassets/AppIcon.appiconset/icon-80.png"
    output_dir = "{{CATALYST_ROOT}}/tools/CatalystPortalMenuBar/CatalystPortalMenuBar/Assets.xcassets/StatusIcon.imageset"

    create_white_icon(
        source,
        f"{output_dir}/StatusIcon-16.png",
        f"{output_dir}/StatusIcon-32.png"
    )
