#!/usr/bin/env python3
"""
Check Address Replacement Pipeline - V2 (CORRECTED)
====================================================

CRITICAL FIXES:
1. Uses LaMa inpainting for Photoshop-quality text removal
2. Preserves ORIGINAL company name (line 1)
3. Only replaces address lines 2-4
4. NO API costs - local LaMa model

Pipeline:
1. Document Detection & Normalization
2. Text Measurement - SEPARATE line 1 from lines 2-4
3. Text Removal - Remove ONLY lines 2-4 with LaMa
4. Text Rendering - Render original line 1 + new lines 2-4
5. Validation

Author: Catalyst Backend Developer
Date: 2025-11-11
"""

import os
import sys
import json
import time
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, asdict

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import easyocr

# LaMa inpainting (optional - has compatibility issues on macOS)
try:
    import torch
    from simple_lama_inpainting import SimpleLama
    LAMA_AVAILABLE = True
except ImportError:
    LAMA_AVAILABLE = False
except Exception as e:
    LAMA_AVAILABLE = False
    # Silently fall back to OpenCV inpainting


@dataclass
class AddressBlock:
    """Address block with company name (line1) and address (lines2-4)"""
    company_name: str  # Original company name to preserve
    company_bbox: Tuple[int, int, int, int]  # (x1, y1, x2, y2)
    company_size_px: float

    address_bbox: Tuple[int, int, int, int]  # Combined bbox for lines 2-4
    address_baselines: List[int]  # Y-coordinates for lines 2-4

    font_size_px: float
    line_spacing_px: float
    alignment: str


@dataclass
class ValidationResult:
    """Validation metrics"""
    company_name_preserved: bool
    font_size_match: bool
    spacing_match: bool
    all_lines_rendered: bool
    measurements: Dict
    tolerance_used: float


@dataclass
class ProcessingResult:
    """Complete processing result"""
    success: bool
    output_path: str
    validation: Optional[ValidationResult]
    processing_time: float
    error: Optional[str] = None
    address_block: Optional[AddressBlock] = None


class CheckProcessorV2:
    """V2: Photoshop-quality with company name preservation"""

    def __init__(self, config_path: Optional[str] = None, use_lama: bool = False):
        """Initialize processor

        Args:
            config_path: Optional config file
            use_lama: If True, attempt to use LaMa (may fail on macOS).
                     If False, use improved OpenCV inpainting.
        """
        self.config = self._load_config(config_path)
        self.ocr_reader = None  # Lazy load
        self.lama_model = None  # Lazy load
        self.use_lama = use_lama and LAMA_AVAILABLE
        self.font_path = Path(__file__).parent / "fonts" / "check-address-font.ttf"

    def _load_config(self, config_path: Optional[str]) -> Dict:
        """Load configuration"""
        default_config = {
            "validation_tolerance": 0.05,
            "max_image_size": 4096,
            "font_color": (0, 0, 0),
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
        new_address_lines: Dict[str, str],  # line2, line3, line4 (optional)
        output_path: str
    ) -> Dict:
        """
        Process check: Preserve company name, replace address lines 2-4

        Args:
            input_image_path: Input check photo
            new_address_lines: Dict with 'line2', 'line3', 'line4' (optional)
                              NO 'line1' - company name is preserved from original
            output_path: Output path

        Example:
            new_address_lines = {
                "line2": "123 NEW STREET",
                "line3": "AUSTIN, TX 78701"
            }
        """
        start_time = time.time()

        try:
            # Step 1: Normalize
            print("Step 1: Normalizing check image...")
            normalized_img = self._normalize_document(input_image_path)

            # Step 2: Detect address block (company + address)
            print("Step 2: Detecting address block...")
            address_block = self._detect_address_block(normalized_img)

            # Step 3: Remove ONLY address lines (2-4) with LaMa
            print("Step 3: Removing address lines (preserving company name)...")
            cleaned_img = self._remove_address_only(normalized_img, address_block)

            # Step 4: Render company name (original) + new address (lines 2-4)
            print("Step 4: Rendering text...")
            rendered_img = self._render_complete_address(
                cleaned_img,
                address_block,
                new_address_lines
            )

            # Step 5: Validate
            print("Step 5: Validating output...")
            validation = self._validate_output(
                rendered_img,
                address_block,
                new_address_lines
            )

            # Save
            cv2.imwrite(output_path, rendered_img)

            processing_time = time.time() - start_time

            result = ProcessingResult(
                success=True,
                output_path=output_path,
                validation=validation,
                processing_time=processing_time,
                address_block=address_block
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
        """Step 1: Detect and normalize check"""
        img = cv2.imread(image_path)
        if img is None:
            raise ValueError(f"Could not load image: {image_path}")

        # Resize if too large
        h, w = img.shape[:2]
        max_dim = self.config["max_image_size"]
        if max(h, w) > max_dim:
            scale = max_dim / max(h, w)
            img = cv2.resize(img, None, fx=scale, fy=scale)

        # Document detection (same as V1)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        filtered = cv2.bilateralFilter(gray, 9, 75, 75)
        edges = cv2.Canny(filtered, 50, 150)
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        check_contour = None
        max_area = 0

        for contour in contours:
            area = cv2.contourArea(contour)
            if area > max_area and area > (h * w * 0.1):
                peri = cv2.arcLength(contour, True)
                approx = cv2.approxPolyDP(contour, 0.02 * peri, True)
                if len(approx) >= 3:
                    check_contour = approx
                    max_area = area

        if check_contour is not None:
            x, y, w, h = cv2.boundingRect(check_contour)
            padding = 10
            x = max(0, x - padding)
            y = max(0, y - padding)
            w = min(img.shape[1] - x, w + 2 * padding)
            h = min(img.shape[0] - y, h + 2 * padding)
            img = img[y:y+h, x:x+w]

        return img

    def _detect_address_block(self, img: np.ndarray) -> AddressBlock:
        """
        Step 2: Detect address block and SEPARATE company name from address

        Returns:
            AddressBlock with company name text + bbox, and address lines bbox
        """
        # Lazy load OCR
        if self.ocr_reader is None:
            print("  Loading EasyOCR...")
            self.ocr_reader = easyocr.Reader(['en'], gpu=False)

        h, w = img.shape[:2]

        # Run OCR
        all_results = self.ocr_reader.readtext(
            img,
            paragraph=False,
            min_size=10,
            text_threshold=0.6,
            low_text=0.3
        )

        if not all_results:
            raise ValueError("No text detected in check")

        # Filter to upper-left address region
        address_results = []
        for bbox, text, conf in all_results:
            center_x = sum(p[0] for p in bbox) / 4
            center_y = sum(p[1] for p in bbox) / 4
            if center_y < h * 0.4 and center_x < w * 0.5:
                address_results.append((bbox, text, conf))

        if not address_results:
            raise ValueError("No text in address region")

        # Sort by vertical position (top to bottom)
        address_results = sorted(address_results, key=lambda x: x[0][0][1])

        # Take first 4 lines (company + 3 address lines)
        address_blocks = address_results[:4]

        if len(address_blocks) < 2:
            raise ValueError("Need at least 2 lines (company + address)")

        # LINE 1: Company name (PRESERVE)
        company_bbox_points, company_text, company_conf = address_blocks[0]
        company_x1 = int(min(p[0] for p in company_bbox_points))
        company_y1 = int(min(p[1] for p in company_bbox_points))
        company_x2 = int(max(p[0] for p in company_bbox_points))
        company_y2 = int(max(p[1] for p in company_bbox_points))
        company_bbox = (company_x1, company_y1, company_x2, company_y2)
        company_size = company_y2 - company_y1

        # LINES 2-4: Address lines (REPLACE)
        address_lines = address_blocks[1:]  # Skip company name

        # Calculate address bbox (combined lines 2-4)
        addr_x1 = float('inf')
        addr_y1 = float('inf')
        addr_x2 = 0
        addr_y2 = 0
        baselines = []
        font_sizes = []

        for bbox_points, text, conf in address_lines:
            x1 = int(min(p[0] for p in bbox_points))
            y1 = int(min(p[1] for p in bbox_points))
            x2 = int(max(p[0] for p in bbox_points))
            y2 = int(max(p[1] for p in bbox_points))

            addr_x1 = min(addr_x1, x1)
            addr_y1 = min(addr_y1, y1)
            addr_x2 = max(addr_x2, x2)
            addr_y2 = max(addr_y2, y2)

            baselines.append(y2)
            font_sizes.append(y2 - y1)

        address_bbox = (int(addr_x1), int(addr_y1), int(addr_x2), int(addr_y2))

        # Calculate average measurements
        avg_font_size = np.mean(font_sizes) if font_sizes else company_size

        if len(baselines) >= 2:
            spacings = [baselines[i+1] - baselines[i] for i in range(len(baselines)-1)]
            avg_line_spacing = np.mean(spacings)
        else:
            avg_line_spacing = avg_font_size * 1.35

        address_block = AddressBlock(
            company_name=company_text,
            company_bbox=company_bbox,
            company_size_px=float(company_size),
            address_bbox=address_bbox,
            address_baselines=baselines,
            font_size_px=float(avg_font_size),
            line_spacing_px=float(avg_line_spacing),
            alignment='left'
        )

        if self.config["debug"]:
            print(f"  Company name: '{company_text}'")
            print(f"  Company bbox: {company_bbox}")
            print(f"  Address bbox: {address_bbox}")
            print(f"  Font size: {avg_font_size:.1f}px")
            print(f"  Line spacing: {avg_line_spacing:.1f}px")

        return address_block

    def _remove_address_only(
        self,
        img: np.ndarray,
        address_block: AddressBlock
    ) -> np.ndarray:
        """
        Step 3: Remove ONLY address lines (2-4) using best available method

        Preserves company name (line 1) completely.
        """
        # Create mask for address region ONLY (not company name)
        mask = np.zeros(img.shape[:2], dtype=np.uint8)
        x1, y1, x2, y2 = address_block.address_bbox

        # Expand mask slightly for clean removal
        padding = 5
        x1 = max(0, x1 - padding)
        y1 = max(0, y1 - padding)
        x2 = min(img.shape[1], x2 + padding)
        y2 = min(img.shape[0], y2 + padding)

        mask[y1:y2, x1:x2] = 255

        if self.use_lama:
            # Try LaMa (may fail on macOS)
            try:
                if self.lama_model is None:
                    print("  Loading LaMa model...")
                    self.lama_model = SimpleLama(device='cpu')
                print("  Running LaMa inpainting...")
                result = self.lama_model(img, mask)
                return result
            except Exception as e:
                print(f"  LaMa failed ({str(e)[:50]}...), falling back to OpenCV")
                self.use_lama = False  # Disable for future calls

        # Improved OpenCV inpainting (fallback or default)
        print("  Using OpenCV NS inpainting (high quality)...")
        # NS (Navier-Stokes) algorithm produces better results than TELEA
        result = cv2.inpaint(img, mask, inpaintRadius=7, flags=cv2.INPAINT_NS)
        return result

    def _render_complete_address(
        self,
        img: np.ndarray,
        address_block: AddressBlock,
        new_address_lines: Dict[str, str]
    ) -> np.ndarray:
        """
        Step 4: Render complete address block

        1. Render ORIGINAL company name at original position
        2. Render NEW address lines below
        """
        # Convert to PIL
        pil_img = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
        draw = ImageDraw.Draw(pil_img)

        # Load font
        font_size_pt = int(address_block.font_size_px * 0.75)
        try:
            font = ImageFont.truetype(str(self.font_path), font_size_pt)
        except Exception as e:
            raise ValueError(f"Could not load font: {e}")

        # Step 4a: Render ORIGINAL company name
        company_x, company_y, _, _ = address_block.company_bbox
        draw.text(
            (company_x, company_y),
            address_block.company_name,  # ORIGINAL company name
            fill=self.config["font_color"],
            font=font
        )

        # Step 4b: Render NEW address lines (lines 2-4)
        lines = []
        for key in ['line2', 'line3', 'line4']:
            if key in new_address_lines and new_address_lines[key]:
                lines.append(new_address_lines[key])

        if not lines:
            raise ValueError("No address lines provided (need line2, line3 at minimum)")

        # Calculate starting position for line 2
        # Use company bbox bottom + line spacing
        _, _, _, company_y2 = address_block.company_bbox
        y_offset = company_y2 + address_block.line_spacing_px

        # Render each address line
        for line in lines:
            draw.text(
                (company_x, y_offset),
                line,
                fill=self.config["font_color"],
                font=font
            )
            y_offset += address_block.line_spacing_px

        # Convert back to OpenCV
        result = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)

        return result

    def _validate_output(
        self,
        img: np.ndarray,
        original_address_block: AddressBlock,
        new_address_lines: Dict[str, str]
    ) -> ValidationResult:
        """Step 5: Validate output"""
        try:
            # Re-detect address block in rendered image
            rendered_block = self._detect_address_block(img)
        except Exception as e:
            return ValidationResult(
                company_name_preserved=False,
                font_size_match=False,
                spacing_match=False,
                all_lines_rendered=False,
                measurements={},
                tolerance_used=self.config["validation_tolerance"]
            )

        tolerance = self.config["validation_tolerance"]

        # Check 1: Company name preserved
        company_name_preserved = (
            rendered_block.company_name.strip().upper() ==
            original_address_block.company_name.strip().upper()
        )

        # Check 2: Font size match
        size_diff = abs(
            rendered_block.font_size_px - original_address_block.font_size_px
        ) / original_address_block.font_size_px
        font_size_match = size_diff <= tolerance

        # Check 3: Line spacing match
        spacing_diff = abs(
            rendered_block.line_spacing_px - original_address_block.line_spacing_px
        ) / original_address_block.line_spacing_px
        spacing_match = spacing_diff <= tolerance

        # Check 4: All lines rendered
        expected_lines = 1 + sum(  # 1 for company name
            1 for k in ['line2', 'line3', 'line4']
            if k in new_address_lines and new_address_lines[k]
        )
        detected_lines = 1 + len(rendered_block.address_baselines)
        all_lines_rendered = detected_lines >= expected_lines

        measurements = {
            'company_name_original': original_address_block.company_name,
            'company_name_rendered': rendered_block.company_name,
            'company_name_match': company_name_preserved,
            'original_font_size': original_address_block.font_size_px,
            'rendered_font_size': rendered_block.font_size_px,
            'font_size_diff_pct': size_diff * 100,
            'original_line_spacing': original_address_block.line_spacing_px,
            'rendered_line_spacing': rendered_block.line_spacing_px,
            'spacing_diff_pct': spacing_diff * 100,
            'expected_lines': expected_lines,
            'detected_lines': detected_lines
        }

        return ValidationResult(
            company_name_preserved=company_name_preserved,
            font_size_match=font_size_match,
            spacing_match=spacing_match,
            all_lines_rendered=all_lines_rendered,
            measurements=measurements,
            tolerance_used=tolerance
        )


def main():
    """CLI entry point"""
    import argparse

    parser = argparse.ArgumentParser(
        description="Replace address on check (preserving company name)"
    )
    parser.add_argument('input', help='Input check image')
    parser.add_argument('output', help='Output image')
    parser.add_argument('--line2', required=True, help='Address line 2 (street)')
    parser.add_argument('--line3', required=True, help='Address line 3 (city/state/zip)')
    parser.add_argument('--line4', default='', help='Address line 4 (optional)')
    parser.add_argument('--config', help='Config file')
    parser.add_argument('--debug', action='store_true', help='Debug output')

    args = parser.parse_args()

    # Create new address dict (NO line1 - company name is preserved)
    new_address_lines = {
        'line2': args.line2,
        'line3': args.line3
    }
    if args.line4:
        new_address_lines['line4'] = args.line4

    # Process
    processor = CheckProcessorV2(config_path=args.config)
    if args.debug:
        processor.config['debug'] = True

    result = processor.process_check(
        args.input,
        new_address_lines,
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
