#!/usr/bin/env python3
"""
Example Usage of Check Address Replacement Pipeline
====================================================

Simple examples showing how to use the pipeline in different scenarios.
"""

from process_check import CheckProcessor
import json


def example_1_basic():
    """Example 1: Basic single check processing"""
    print("="*60)
    print("Example 1: Basic Single Check Processing")
    print("="*60)

    processor = CheckProcessor()

    result = processor.process_check(
        input_image_path="{{HOME_DIR}}/Downloads/Doc Samples/uuid=13E331A1-7934-4184-A8F9-B41979AD76A0&code=001&library=3&type=1&mode=1&loc=true&cap=true.jpeg",
        new_address={
            "line1": "ACME CORPORATION",
            "line2": "456 BUSINESS PARK DR",
            "line3": "SAN FRANCISCO, CA 94105",
            "line4": ""
        },
        output_path="example_output_1.png"
    )

    if result['success']:
        print(f"✅ Success!")
        print(f"   Output: {result['output_path']}")
        print(f"   Time: {result['processing_time']:.1f}s")
        print(f"   Font match: {'✓' if result['validation']['font_size_match'] else '✗'}")
        print(f"   Spacing match: {'✓' if result['validation']['spacing_match'] else '✗'}")
    else:
        print(f"❌ Failed: {result['error']}")

    print()


def example_2_with_config():
    """Example 2: Using custom configuration"""
    print("="*60)
    print("Example 2: With Custom Configuration")
    print("="*60)

    # Load processor with custom config
    processor = CheckProcessor(config_path="config.json")

    # Enable debug mode temporarily
    processor.config['debug'] = True

    result = processor.process_check(
        input_image_path="{{HOME_DIR}}/Downloads/Doc Samples/uuid=2652109B-A43D-407B-8DCC-7B55D41DA407&code=001&library=3&type=1&mode=1&loc=true&cap=true.jpeg",
        new_address={
            "line1": "STARTUP VENTURES LLC",
            "line2": "100 INNOVATION BLVD STE 500",
            "line3": "AUSTIN, TX 78701",
            "line4": ""
        },
        output_path="example_output_2.png"
    )

    print(f"Result: {'✅ Success' if result['success'] else '❌ Failed'}")
    print()


def example_3_batch_processing():
    """Example 3: Process multiple checks programmatically"""
    print("="*60)
    print("Example 3: Batch Processing Multiple Checks")
    print("="*60)

    processor = CheckProcessor()

    # List of checks to process
    checks = [
        {
            "input": "{{HOME_DIR}}/Downloads/Doc Samples/uuid=13E331A1-7934-4184-A8F9-B41979AD76A0&code=001&library=3&type=1&mode=1&loc=true&cap=true.jpeg",
            "output": "batch_output_1.png",
            "address": {
                "line1": "COMPANY ONE LLC",
                "line2": "111 FIRST STREET",
                "line3": "NEW YORK, NY 10001"
            }
        },
        {
            "input": "{{HOME_DIR}}/Downloads/Doc Samples/uuid=2652109B-A43D-407B-8DCC-7B55D41DA407&code=001&library=3&type=1&mode=1&loc=true&cap=true.jpeg",
            "output": "batch_output_2.png",
            "address": {
                "line1": "COMPANY TWO INC",
                "line2": "222 SECOND AVENUE",
                "line3": "LOS ANGELES, CA 90001"
            }
        }
    ]

    results = []
    for i, check in enumerate(checks, 1):
        print(f"\nProcessing check {i}/{len(checks)}...")

        result = processor.process_check(
            input_image_path=check['input'],
            new_address=check['address'],
            output_path=check['output']
        )

        results.append(result)

        if result['success']:
            print(f"  ✅ {result['output_path']} ({result['processing_time']:.1f}s)")
        else:
            print(f"  ❌ Failed: {result['error']}")

    # Summary
    successful = sum(1 for r in results if r['success'])
    print(f"\n📊 Batch complete: {successful}/{len(checks)} successful")
    print()


def example_4_error_handling():
    """Example 4: Proper error handling"""
    print("="*60)
    print("Example 4: Error Handling")
    print("="*60)

    processor = CheckProcessor()

    # Try to process a non-existent file
    result = processor.process_check(
        input_image_path="nonexistent_check.jpg",
        new_address={
            "line1": "TEST COMPANY",
            "line2": "123 TEST ST",
            "line3": "TEST CITY, XX 00000"
        },
        output_path="error_output.png"
    )

    if not result['success']:
        print(f"Expected error caught: {result['error']}")
        print(f"Processing time before failure: {result['processing_time']:.3f}s")
    else:
        print("Unexpected success!")

    print()


def example_5_validation_analysis():
    """Example 5: Analyzing validation results"""
    print("="*60)
    print("Example 5: Validation Analysis")
    print("="*60)

    processor = CheckProcessor()

    result = processor.process_check(
        input_image_path="{{HOME_DIR}}/Downloads/Doc Samples/uuid=963AD8EA-68E8-4114-9362-235AD4B4AAE4&code=001&library=3&type=1&mode=1&loc=true&cap=true.jpeg",
        new_address={
            "line1": "QUALITY CHECK LLC",
            "line2": "999 VALIDATION WAY",
            "line3": "TESTVILLE, TX 12345",
            "line4": ""
        },
        output_path="example_output_validation.png"
    )

    if result['success']:
        val = result['validation']
        measurements = val['measurements']

        print("Validation Results:")
        print(f"  Tolerance: ±{val['tolerance_used']*100}%")
        print()

        print("Font Size:")
        print(f"  Original: {measurements['original_font_size']:.1f}px")
        print(f"  Rendered: {measurements['rendered_font_size']:.1f}px")
        print(f"  Difference: {measurements['font_size_diff_pct']:.1f}%")
        print(f"  Match: {'✓ PASS' if val['font_size_match'] else '✗ FAIL'}")
        print()

        print("Line Spacing:")
        print(f"  Original: {measurements['original_line_spacing']:.1f}px")
        print(f"  Rendered: {measurements['rendered_line_spacing']:.1f}px")
        print(f"  Difference: {measurements['spacing_diff_pct']:.1f}%")
        print(f"  Match: {'✓ PASS' if val['spacing_match'] else '✗ FAIL'}")
        print()

        print("Lines Rendered:")
        print(f"  Expected: {measurements['expected_lines']}")
        print(f"  Detected: {measurements['detected_lines']}")
        print(f"  Match: {'✓ PASS' if val['all_lines_rendered'] else '✗ FAIL'}")

    print()


def example_6_json_export():
    """Example 6: Export results as JSON for automation"""
    print("="*60)
    print("Example 6: JSON Export for Automation")
    print("="*60)

    processor = CheckProcessor()

    result = processor.process_check(
        input_image_path="{{HOME_DIR}}/Downloads/Doc Samples/uuid=C2A2337F-C745-464E-A18A-2A5D1419DBAE&code=001&library=3&type=1&mode=1&loc=true&cap=true.jpeg",
        new_address={
            "line1": "AUTOMATION SYSTEMS INC",
            "line2": "777 API DRIVE",
            "line3": "SILICON VALLEY, CA 94025"
        },
        output_path="example_output_json.png"
    )

    # Save results as JSON
    with open("example_result.json", "w") as f:
        json.dump(result, f, indent=2)

    print("Results saved to example_result.json")
    print()
    print("Sample JSON output:")
    print(json.dumps({
        "success": result['success'],
        "output_path": result['output_path'],
        "processing_time": f"{result['processing_time']:.2f}s",
        "validation_summary": {
            "font_match": result['validation']['font_size_match'] if result['success'] else None,
            "spacing_match": result['validation']['spacing_match'] if result['success'] else None
        }
    }, indent=2))

    print()


def main():
    """Run all examples"""
    print("\n")
    print("="*60)
    print("CHECK ADDRESS REPLACEMENT - USAGE EXAMPLES")
    print("="*60)
    print()

    # Run examples
    example_1_basic()
    # example_2_with_config()  # Commented out - verbose debug output
    # example_3_batch_processing()  # Commented out - takes time
    # example_4_error_handling()
    example_5_validation_analysis()
    example_6_json_export()

    print("="*60)
    print("All examples complete!")
    print("="*60)
    print()


if __name__ == '__main__':
    main()
