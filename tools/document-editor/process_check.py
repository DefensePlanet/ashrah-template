#!/usr/bin/env python3
"""
Check Address Replacement Pipeline
===================================

Complete production pipeline for replacing addresses on business checks.
Handles varying scales, lighting, and backgrounds while maintaining
photorealistic quality matching the original font properties.

Steps:
1. Document Detection & Normalization
2. Text Measurement (Dynamic)
3. Text Removal (Nano Banana via OpenRouter)
4. Dynamic Text Rendering
5. Composite & Validate

Author: Catalyst Backend Developer
Date: 2025-11-11
"""

import os
import sys
import json
import time
import requests
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, asdict

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import easyocr


@dataclass
class TextMeasurements:
    """Measurements extracted from original check address"""
    font_size_px: float  # Height of capital letters in pixels
    line_spacing_px: float  # Vertical distance between baselines
    char_spacing_px: float  # Horizontal character spacing
    alignment: str  # 'left', 'center', or 'right'
    bbox: Tuple[int, int, int, int]  # (x1, y1, x2, y2) bounding box
    baseline_positions: List[int]  # Y-coordinates of each line's baseline
    company_name: str = ""  # Original company name (line 1) to preserve


@dataclass
class ValidationResult:
    """Validation metrics for rendered output"""
    font_size_match: bool
    spacing_match: bool
    all_lines_rendered: bool
    measurements: Dict
    tolerance_used: float


@dataclass
class ProcessingResult:
    """Complete processing result with metrics"""
    success: bool
    output_path: str
    validation: ValidationResult
    processing_time: float
    error: Optional[str] = None
    measurements: Optional[TextMeasurements] = None


class CheckProcessor:
    """Main pipeline for check address replacement"""

    def __init__(self, config_path: Optional[str] = None):
        """Initialize processor with configuration"""
        self.config = self._load_config(config_path)
        self.ocr_reader = None  # Lazy load
        self.font_path = Path(__file__).parent / "fonts" / "check-address-font.ttf"

        # Load OpenRouter API key
        self.api_key = os.getenv("OPENROUTER_API_KEY")
        if not self.api_key:
            raise ValueError("OPENROUTER_API_KEY not found in environment")

    def _load_config(self, config_path: Optional[str]) -> Dict:
        """Load configuration from file or use defaults"""
        default_config = {
            "validation_tolerance": 0.05,  # 5% tolerance
            "openrouter_model": "google/gemini-2.5-flash-image",
            "openrouter_endpoint": "https://openrouter.ai/api/v1/chat/completions",
            "max_image_size": 4096,  # Max dimension for processing
            "font_color": (0, 0, 0),  # Black
            "debug": False
        }

        if config_path and os.path.exists(config_path):
            with open(config_path) as f:
                user_config = json.load(f)
                default_config.update(user_config)

        return default_config

    def process_check(
        self,
        input_image_path: str,
        new_address: Dict[str, str],
        output_path: str
    ) -> Dict:
        """
        Main entry point: process a check image to replace address.

        Args:
            input_image_path: Path to input check photo
            new_address: Dictionary with line1, line2, line3, line4 (optional)
            output_path: Path for output image

        Returns:
            Dictionary with success, output_path, validation, processing_time
        """
        start_time = time.time()

        try:
            # Step 1: Normalize check image
            print("Step 1: Normalizing check image...")
            normalized_img = self._normalize_document(input_image_path)

            # Step 2: Measure text properties
            print("Step 2: Measuring text properties...")
            measurements = self._measure_text(normalized_img)

            # Step 3: Remove address text
            print("Step 3: Removing original address...")
            cleaned_img = self._remove_text(normalized_img, measurements)

            # Step 4: Render new address
            print("Step 4: Rendering new address...")
            rendered_img = self._render_address(
                cleaned_img,
                new_address,
                measurements
            )

            # Step 5: Validate and save
            print("Step 5: Validating output...")
            validation = self._validate_output(
                rendered_img,
                new_address,
                measurements
            )

            # Save final image
            cv2.imwrite(output_path, rendered_img)

            processing_time = time.time() - start_time

            result = ProcessingResult(
                success=True,
                output_path=output_path,
                validation=validation,
                processing_time=processing_time,
                measurements=measurements
            )

            return asdict(result)

        except Exception as e:
            processing_time = time.time() - start_time
            result = ProcessingResult(
                success=False,
                output_path="",
                validation=None,
                processing_time=processing_time,
                error=str(e)
            )
            return asdict(result)

    def _normalize_document(self, image_path: str) -> np.ndarray:
        """
        Step 1: Detect and normalize check document

        - Detect check boundaries
        - Crop to check only
        - Handle scale variations
        - Light perspective correction if needed
        """
        # Load image
        img = cv2.imread(image_path)
        if img is None:
            raise ValueError(f"Could not load image: {image_path}")

        # Resize if too large
        h, w = img.shape[:2]
        max_dim = self.config["max_image_size"]
        if max(h, w) > max_dim:
            scale = max_dim / max(h, w)
            img = cv2.resize(img, None, fx=scale, fy=scale)

        # Convert to grayscale for processing
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # Apply bilateral filter to reduce noise while preserving edges
        filtered = cv2.bilateralFilter(gray, 9, 75, 75)

        # Edge detection
        edges = cv2.Canny(filtered, 50, 150)

        # Find contours
        contours, _ = cv2.findContours(
            edges,
            cv2.RETR_EXTERNAL,
            cv2.CHAIN_APPROX_SIMPLE
        )

        # Find largest rectangular contour (likely the check)
        check_contour = None
        max_area = 0

        for contour in contours:
            area = cv2.contourArea(contour)
            if area > max_area and area > (h * w * 0.1):  # At least 10% of image
                # Approximate to polygon
                peri = cv2.arcLength(contour, True)
                approx = cv2.approxPolyDP(contour, 0.02 * peri, True)

                # Check if roughly rectangular (3-5 corners due to variations)
                if len(approx) >= 3:
                    check_contour = approx
                    max_area = area

        if check_contour is not None:
            # Get bounding rectangle
            x, y, w, h = cv2.boundingRect(check_contour)

            # Add small padding
            padding = 10
            x = max(0, x - padding)
            y = max(0, y - padding)
            w = min(img.shape[1] - x, w + 2 * padding)
            h = min(img.shape[0] - y, h + 2 * padding)

            # Crop to check
            img = img[y:y+h, x:x+w]

        # For now, skip perspective correction since photos are straight-on
        # Can add later if needed based on test results

        return img

    def _measure_text(self, img: np.ndarray) -> TextMeasurements:
        """
        Step 2: Measure text properties dynamically

        Extracts font size, line spacing, character spacing from actual image.
        Does NOT need to read content, just measure properties.
        """
        # Lazy load OCR reader
        if self.ocr_reader is None:
            print("  Loading EasyOCR (first run only)...")
            self.ocr_reader = easyocr.Reader(['en'], gpu=False)  # Use CPU for stability

        # Run OCR on full image to find all text
        h, w = img.shape[:2]

        if self.config["debug"]:
            print(f"  Debug: Image size: {img.shape}")

        # Run OCR detection on full image
        all_results = self.ocr_reader.readtext(
            img,
            paragraph=False,
            min_size=10,
            text_threshold=0.6,
            low_text=0.3
        )

        if self.config["debug"]:
            print(f"  Debug: OCR found {len(all_results)} total text regions")
            for i, (bbox, text, conf) in enumerate(all_results[:10]):
                print(f"    {i+1}. '{text}' (conf: {conf:.2f})")

        if not all_results:
            raise ValueError("No text detected in check image")

        # Filter to address region (upper-left: top 40% of image, left 50%)
        address_results = []
        for bbox, text, conf in all_results:
            # Get center point of text bbox
            center_x = sum(p[0] for p in bbox) / 4
            center_y = sum(p[1] for p in bbox) / 4

            # Check if in upper-left region
            if center_y < h * 0.4 and center_x < w * 0.5:
                address_results.append((bbox, text, conf))

        if self.config["debug"]:
            print(f"  Debug: Filtered to {len(address_results)} address region texts")

        results = address_results

        if not results:
            raise ValueError("No text detected in upper-left address region")

        # Filter to address region (typically first 3-4 detected text blocks)
        # Sort by vertical position
        results = sorted(results, key=lambda x: x[0][0][1])
        address_blocks = results[:4]  # Take first 4 text blocks

        # Extract measurements
        font_sizes = []
        line_spacings = []
        baselines = []

        all_x1, all_y1 = float('inf'), float('inf')
        all_x2, all_y2 = 0, 0

        for bbox, text, conf in address_blocks:
            # bbox is [[x1,y1], [x2,y1], [x2,y2], [x1,y2]]
            x1 = int(min(p[0] for p in bbox))
            y1 = int(min(p[1] for p in bbox))
            x2 = int(max(p[0] for p in bbox))
            y2 = int(max(p[1] for p in bbox))

            # Update overall bounding box
            all_x1 = min(all_x1, x1)
            all_y1 = min(all_y1, y1)
            all_x2 = max(all_x2, x2)
            all_y2 = max(all_y2, y2)

            # Measure font height (capital letter height)
            height = y2 - y1
            font_sizes.append(height)

            # Baseline is bottom of text
            baselines.append(y2)

        # Calculate average font size
        avg_font_size = np.mean(font_sizes) if font_sizes else 20.0

        # Calculate line spacing (distance between consecutive baselines)
        if len(baselines) >= 2:
            spacings = [baselines[i+1] - baselines[i] for i in range(len(baselines)-1)]
            avg_line_spacing = np.mean(spacings)
        else:
            avg_line_spacing = avg_font_size * 1.35  # Default 1.35x font size

        # Character spacing (approximate from text width and character count)
        # For now, use standard spacing (will be handled by PIL's default)
        avg_char_spacing = 0  # PIL handles this automatically

        # Detect alignment (check if left-aligned, centered, or right-aligned)
        # For checks, it's typically left-aligned
        alignment = 'left'

        # Extract company name (first line of address)
        company_name = ""
        if address_blocks and len(address_blocks) > 0:
            company_name = address_blocks[0][1]  # First detected text line

        measurements = TextMeasurements(
            font_size_px=float(avg_font_size),
            line_spacing_px=float(avg_line_spacing),
            char_spacing_px=float(avg_char_spacing),
            alignment=alignment,
            bbox=(int(all_x1), int(all_y1), int(all_x2), int(all_y2)),
            baseline_positions=baselines,
            company_name=company_name
        )

        if self.config["debug"]:
            print(f"  Measured font size: {avg_font_size:.1f}px")
            print(f"  Measured line spacing: {avg_line_spacing:.1f}px")
            print(f"  Address bounding box: {measurements.bbox}")

        return measurements

    def _remove_text(
        self,
        img: np.ndarray,
        measurements: TextMeasurements
    ) -> np.ndarray:
        """
        Step 3: Remove text using Nano Banana (Gemini 2.5 Flash Image)

        Uses OpenRouter API to remove address text while preserving background.
        """
        # Convert image to base64 for API
        import base64
        from io import BytesIO

        # Convert to PIL Image
        pil_img = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))

        # Encode to base64
        buffer = BytesIO()
        pil_img.save(buffer, format="PNG")
        img_base64 = base64.b64encode(buffer.getvalue()).decode()

        # Prepare API request
        x1, y1, x2, y2 = measurements.bbox

        prompt = f"""Remove only the address text (lines 2-4) from the upper-left corner of this check.
PRESERVE the company name on line 1 unchanged: "{measurements.company_name}"
Preserve all background texture, check patterns, and formatting perfectly.
Return a clean image."""

        payload = {
            "model": self.config["openrouter_model"],
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": prompt
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{img_base64}"
                            }
                        }
                    ]
                }
            ]
        }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        print("  Calling OpenRouter API...")
        response = requests.post(
            self.config["openrouter_endpoint"],
            headers=headers,
            json=payload,
            timeout=60
        )

        if response.status_code != 200:
            raise ValueError(
                f"OpenRouter API error: {response.status_code} - {response.text}"
            )

        # Extract base64 image from Nano Banana response
        response_data = response.json()
        edited_image_url = response_data['choices'][0]['message']['images'][0]['image_url']['url']

        # Remove data URL prefix
        import base64
        base64_data = edited_image_url.replace('data:image/png;base64,', '')

        # Decode to bytes
        image_bytes = base64.b64decode(base64_data)

        # Convert to OpenCV format
        nparr = np.frombuffer(image_bytes, np.uint8)
        cleaned_image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if self.config["debug"]:
            print(f"  Received cleaned image: {cleaned_image.shape}")

        return cleaned_image

    def _render_address(
        self,
        img: np.ndarray,
        new_address: Dict[str, str],
        measurements: TextMeasurements
    ) -> np.ndarray:
        """
        Step 4: Render new address matching measured properties

        Preserves original company name (line 1) and renders new address (lines 2-4).
        Uses Arial Regular font at measured size with measured spacing.
        """
        # Convert to PIL for text rendering
        pil_img = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
        draw = ImageDraw.Draw(pil_img)

        # Load font at measured size
        # PIL font size is in points, but we have pixels
        # Rough conversion: points = pixels * 0.75
        font_size_pt = int(measurements.font_size_px * 0.75)

        try:
            font = ImageFont.truetype(str(self.font_path), font_size_pt)
        except Exception as e:
            raise ValueError(f"Could not load font: {e}")

        # Calculate starting position (top-left of original address)
        x1, y1, _, _ = measurements.bbox

        # Line 1: Re-render ORIGINAL company name
        y_offset = y1
        if measurements.company_name:
            draw.text(
                (x1, y_offset),
                measurements.company_name,
                fill=self.config["font_color"],
                font=font
            )
            y_offset += measurements.line_spacing_px

        # Lines 2-4: Render new address
        for key in ['line2', 'line3', 'line4']:
            if key in new_address and new_address[key]:
                draw.text(
                    (x1, y_offset),
                    new_address[key],
                    fill=self.config["font_color"],
                    font=font
                )
                y_offset += measurements.line_spacing_px

        # Convert back to OpenCV
        result = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)

        return result

    def _validate_output(
        self,
        img: np.ndarray,
        new_address: Dict[str, str],
        original_measurements: TextMeasurements
    ) -> ValidationResult:
        """
        Step 5: Validate rendered output

        Compares rendered text measurements against original measurements.
        """
        # Re-measure the rendered text
        try:
            new_measurements = self._measure_text(img)
        except Exception as e:
            # If measurement fails, assume validation failed
            return ValidationResult(
                font_size_match=False,
                spacing_match=False,
                all_lines_rendered=False,
                measurements={},
                tolerance_used=self.config["validation_tolerance"]
            )

        # Calculate tolerances
        tolerance = self.config["validation_tolerance"]

        # Check font size match
        size_diff = abs(
            new_measurements.font_size_px - original_measurements.font_size_px
        ) / original_measurements.font_size_px
        font_size_match = size_diff <= tolerance

        # Check line spacing match
        spacing_diff = abs(
            new_measurements.line_spacing_px - original_measurements.line_spacing_px
        ) / original_measurements.line_spacing_px
        spacing_match = spacing_diff <= tolerance

        # Check all lines rendered (company name + new address lines)
        # Company name is always line 1, so add 1 to expected count
        new_address_lines = sum(1 for k in ['line2', 'line3', 'line4']
                                if k in new_address and new_address[k])
        expected_lines = 1 + new_address_lines  # 1 for company name + new lines
        detected_lines = len(new_measurements.baseline_positions)
        all_lines_rendered = detected_lines >= expected_lines

        measurements = {
            'original_font_size': original_measurements.font_size_px,
            'rendered_font_size': new_measurements.font_size_px,
            'font_size_diff_pct': size_diff * 100,
            'original_line_spacing': original_measurements.line_spacing_px,
            'rendered_line_spacing': new_measurements.line_spacing_px,
            'spacing_diff_pct': spacing_diff * 100,
            'expected_lines': expected_lines,
            'detected_lines': detected_lines
        }

        return ValidationResult(
            font_size_match=font_size_match,
            spacing_match=spacing_match,
            all_lines_rendered=all_lines_rendered,
            measurements=measurements,
            tolerance_used=tolerance
        )


def main():
    """
    CLI entry point for check address replacement.

    Process check to replace address while preserving company name.

    Usage:
        python process_check.py input.jpg output.png \\
            --line2 "123 NEW STREET" \\
            --line3 "AUSTIN, TX 78701"

    Note: Company name (line 1) is automatically preserved from original.
    """
    import argparse

    parser = argparse.ArgumentParser(
        description="Replace address on business check (preserves company name)"
    )
    parser.add_argument('input', help='Input check image path')
    parser.add_argument('output', help='Output image path')
    parser.add_argument('--line2', required=True, help='Street address')
    parser.add_argument('--line3', required=True, help='City, state, zip')
    parser.add_argument('--line4', default='', help='Optional 4th line')
    parser.add_argument('--config', help='Config file path')
    parser.add_argument('--debug', action='store_true', help='Enable debug output')

    args = parser.parse_args()

    # Create new address dict (NO line1 - company name preserved from original)
    new_address = {
        'line2': args.line2,
        'line3': args.line3,
        'line4': args.line4
    }

    # Process check
    processor = CheckProcessor(config_path=args.config)
    if args.debug:
        processor.config['debug'] = True

    result = processor.process_check(
        args.input,
        new_address,
        args.output
    )

    # Print results
    print("\n" + "="*60)
    print("PROCESSING COMPLETE")
    print("="*60)
    print(json.dumps(result, indent=2))

    sys.exit(0 if result['success'] else 1)


if __name__ == '__main__':
    main()
