# Advanced iOS Testing Framework

**Complete Integration: Screenshot Diffing + Test Matrix + Network Analysis**

## Overview

Catalyst provides three powerful tools that work together to create a comprehensive iOS testing framework:

1. **screenshot_diff.py** - Visual regression testing via automated screenshot comparison
2. **ios_test_matrix.rb** - Comprehensive test automation across configuration matrices
3. **pulse_log_export.rb** - Network log extraction and analysis from Pulse

These tools integrate seamlessly with:
- **xcodebuildmcp** (58 MCP tools for Xcode operations)
- **simulator_control.rb** (20+ simulator manipulation commands)
- **Pulse Network Logger** (network monitoring framework)
- **SwiftUI Debug Overlays** (5 in-app debugging tools)

---

## Tool Capabilities

### 1. Screenshot Diffing Tool

**File:** `{{CATALYST_ROOT}}/tools/screenshot_diff.py`

**Purpose:** Automate visual regression testing by comparing screenshots pixel-by-pixel.

**Key Features:**
- Pixel-level difference calculation with antialiasing tolerance
- Multiple visual diff outputs (red highlights, side-by-side, overlay)
- Batch processing for entire screenshot directories
- HTML reports with visual comparisons
- Configurable thresholds (default: 1% difference tolerance)
- JSON output for CI/CD integration

**Usage:**

```bash
# Single screenshot comparison
python3 tools/screenshot_diff.py baseline.png current.png -o diff-output/

# Batch mode - compare entire directories
python3 tools/screenshot_diff.py --batch baseline-screenshots/ current-screenshots/ -o results/

# Custom threshold (0.5% tolerance)
python3 tools/screenshot_diff.py baseline.png current.png -t 0.005 -o diff/

# JSON output for automation
python3 tools/screenshot_diff.py baseline.png current.png -f json > diff.json
```

**Output:**
- `diff.png` - Red highlights on differences
- `side-by-side.png` - Baseline vs current side-by-side
- `overlay.png` - Overlay comparison
- `report.html` - Visual diff report with metrics

---

### 2. Test Matrix Automation

**File:** `{{CATALYST_ROOT}}/tools/ios_test_matrix.rb`

**Purpose:** Run comprehensive tests across all combinations of device configurations.

**Key Features:**
- Automatic test combination generation (appearance × text_size × network × location × accessibility)
- Environment setup/teardown via simulator_control.rb
- Sequential or parallel execution
- Screenshot capture for each configuration
- HTML/JSON reports with pass/fail results
- Predefined test configurations (minimal, accessibility, network, comprehensive)

**Configuration Format:**

```json
{
  "name": "My Test Matrix",
  "project_path": "/path/to/MyApp.xcodeproj",
  "scheme": "MyApp",
  "simulator": "iPhone 16",
  "matrix": {
    "appearance": ["light", "dark"],
    "text_size": ["L", "XL", "XXL", "AccessibilityXL"],
    "network": ["wifi", "3g", "off"],
    "location": [
      {"name": "SF", "lat": 37.7749, "lon": -122.4194},
      {"name": "NYC", "lat": 40.7128, "lon": -74.0060}
    ],
    "accessibility": [
      {"reduce_motion": true},
      {"increase_contrast": true}
    ]
  },
  "test_command": "xcodebuild test -scheme MyApp -destination 'platform=iOS Simulator,name=iPhone 16'",
  "screenshot_screens": ["HomeView", "SettingsView"],
  "output_dir": "./test-results"
}
```

**Usage:**

```bash
# Generate configuration template
ruby tools/ios_test_matrix.rb generate-config --output test-config.json

# Run test matrix
ruby tools/ios_test_matrix.rb run --config test-config.json

# Use predefined configuration
ruby tools/ios_test_matrix.rb run --preset accessibility --project MyApp.xcodeproj --scheme MyApp

# List available presets
ruby tools/ios_test_matrix.rb list-configs
```

**Predefined Configurations:**
- **minimal** - Light/dark × 3 text sizes (6 combinations)
- **accessibility** - All accessibility features (18 combinations)
- **network** - All network conditions (5 combinations)
- **comprehensive** - Full matrix test (120+ combinations)

---

### 3. Network Log Export

**File:** `{{CATALYST_ROOT}}/tools/pulse_log_export.rb`

**Purpose:** Extract and analyze network logs from Pulse LoggerStore for debugging and performance analysis.

**Key Features:**
- Export logs in multiple formats (JSON, CSV, text, HTML)
- Advanced filtering (status code, URL pattern, HTTP method, time range)
- Analysis reports (request counts, error rates, performance stats)
- Identify slow requests (>1s) and failures
- Request/response metrics (size, duration, status)
- Integration with test matrix for network testing

**Usage:**

```bash
# Export all logs
ruby tools/pulse_log_export.rb export --app-id com.example.MyApp --format json

# Generate analysis report
ruby tools/pulse_log_export.rb analyze --app-id com.example.MyApp --output report.html

# Filter errors only (4xx/5xx)
ruby tools/pulse_log_export.rb filter --app-id com.example.MyApp --status 400-599 --output errors.json

# Filter by URL pattern
ruby tools/pulse_log_export.rb filter --app-id com.example.MyApp --url-pattern "api.example.com" --format csv

# Filter by method and time range
ruby tools/pulse_log_export.rb filter --app-id com.example.MyApp --method POST --since "2024-01-01T00:00:00Z"

# List installed apps
ruby tools/pulse_log_export.rb list-apps
```

**Analysis Metrics:**
- Total requests, success rate, error rate
- Average response time
- Data sent/received
- HTTP method distribution
- Status code distribution
- Top hosts
- Slow requests (>1s)
- Error details

---

## Integration Workflows

### Workflow 1: Visual Regression Testing

**Scenario:** Ensure UI changes don't break existing screens

**Steps:**

1. **Capture baseline screenshots** (first time only):
```bash
# Build and run app
cd ~/Catalyst/catalyst-mobile
ruby ~/Catalyst/tools/xcode_project_tool.rb build-run

# Capture baseline screenshots
ruby ~/Catalyst/tools/xcode_project_tool.rb take-screenshots --output baseline-screenshots/
```

2. **Make UI changes** to your app

3. **Capture new screenshots**:
```bash
ruby ~/Catalyst/tools/xcode_project_tool.rb build-run
ruby ~/Catalyst/tools/xcode_project_tool.rb take-screenshots --output current-screenshots/
```

4. **Run diff analysis**:
```bash
python3 ~/Catalyst/tools/screenshot_diff.py --batch \
  baseline-screenshots/ \
  current-screenshots/ \
  -o screenshot-diff-results/
```

5. **Review report**:
```bash
open screenshot-diff-results/report.html
```

**Result:** Visual diff report highlighting any UI changes with red overlays and side-by-side comparisons.

---

### Workflow 2: Comprehensive Matrix Testing

**Scenario:** Test app across all device configurations (accessibility, network, appearance)

**Steps:**

1. **Create test configuration**:
```json
{
  "name": "Comprehensive Test",
  "project_path": "{{CATALYST_ROOT}}/catalyst-mobile/CatalystMobile.xcodeproj",
  "scheme": "CatalystMobile",
  "simulator": "iPhone 16",
  "matrix": {
    "appearance": ["light", "dark"],
    "text_size": ["L", "AccessibilityXL"],
    "network": ["wifi", "3g"],
    "accessibility": [
      {},
      {"reduce_motion": true}
    ]
  },
  "screenshot_screens": ["Home", "Settings"],
  "output_dir": "./matrix-test-results"
}
```

2. **Run test matrix**:
```bash
ruby ~/Catalyst/tools/ios_test_matrix.rb run --config test-config.json
```

3. **Review results**:
```bash
open matrix-test-results/report.html
```

**Result:** 16 test combinations (2 appearance × 2 text × 2 network × 2 accessibility), with screenshots and pass/fail results.

---

### Workflow 3: Network Performance Testing

**Scenario:** Debug slow API calls and network errors

**Steps:**

1. **Setup Pulse in Xcode project** (one-time):
```bash
ruby ~/Catalyst/tools/xcode_project_tool.rb add-package \
  --url "https://github.com/kean/Pulse" \
  --product "Pulse"
```

2. **Run app with network conditions**:
```bash
# Throttle to 3G speeds
ruby ~/Catalyst/tools/simulator_control.rb network-throttle \
  --simulator "iPhone 16" \
  --profile 3g

# Run app
ruby ~/Catalyst/tools/xcode_project_tool.rb build-run
```

3. **Export network logs**:
```bash
ruby ~/Catalyst/tools/pulse_log_export.rb analyze \
  --app-id com.example.MyApp \
  --output network-analysis.html
```

4. **Review slow requests**:
```bash
open network-analysis.html
```

**Result:** Detailed analysis showing slow requests (>1s), error rates, and request timing metrics.

---

### Workflow 4: Complete Testing Pipeline

**Scenario:** Full automated testing workflow combining all three tools

**Complete Pipeline:**

```bash
#!/bin/bash
# comprehensive-test-pipeline.sh

APP_ID="com.example.MyApp"
PROJECT_PATH="$HOME/Catalyst/my-app/MyApp.xcodeproj"
SCHEME="MyApp"
SIMULATOR="iPhone 16"
OUTPUT_DIR="./test-results-$(date +%Y%m%d-%H%M%S)"

echo "🚀 Starting Comprehensive iOS Test Pipeline"
echo "=============================================="
echo

# Step 1: Run test matrix
echo "📊 Step 1: Running test matrix..."
ruby ~/Catalyst/tools/ios_test_matrix.rb run \
  --preset comprehensive \
  --project "$PROJECT_PATH" \
  --scheme "$SCHEME" \
  --simulator "$SIMULATOR" \
  --output "$OUTPUT_DIR/matrix-results"

# Step 2: Visual regression testing
echo "🖼️  Step 2: Running visual regression tests..."
if [ -d "baseline-screenshots" ]; then
  python3 ~/Catalyst/tools/screenshot_diff.py --batch \
    baseline-screenshots/ \
    "$OUTPUT_DIR/matrix-results/screenshots" \
    -o "$OUTPUT_DIR/visual-diff"
else
  echo "⚠️  No baseline screenshots found. Creating baseline..."
  cp -r "$OUTPUT_DIR/matrix-results/screenshots" baseline-screenshots
fi

# Step 3: Network analysis
echo "🌐 Step 3: Analyzing network logs..."
ruby ~/Catalyst/tools/pulse_log_export.rb analyze \
  --app-id "$APP_ID" \
  --output "$OUTPUT_DIR/network-analysis.html"

# Step 4: Generate summary report
echo "📄 Step 4: Generating summary report..."
cat > "$OUTPUT_DIR/SUMMARY.md" << EOF
# Test Results Summary
Generated: $(date)

## Test Matrix Results
- Configuration: Comprehensive
- Results: $OUTPUT_DIR/matrix-results/report.html

## Visual Regression Results
- Diff Report: $OUTPUT_DIR/visual-diff/report.html
- Baseline: baseline-screenshots/
- Current: $OUTPUT_DIR/matrix-results/screenshots/

## Network Analysis
- Report: $OUTPUT_DIR/network-analysis.html

## Quick Links
- [Matrix Results](matrix-results/report.html)
- [Visual Diff](visual-diff/report.html)
- [Network Analysis](network-analysis.html)
EOF

echo
echo "✅ Pipeline complete!"
echo "📊 Results: $OUTPUT_DIR"
echo "📄 Summary: $OUTPUT_DIR/SUMMARY.md"
echo
echo "Open reports:"
echo "  open $OUTPUT_DIR/matrix-results/report.html"
echo "  open $OUTPUT_DIR/visual-diff/report.html"
echo "  open $OUTPUT_DIR/network-analysis.html"
```

**Usage:**
```bash
chmod +x comprehensive-test-pipeline.sh
./comprehensive-test-pipeline.sh
```

---

## Mobile Dev Agent Integration

The Mobile Dev agent has direct access to all three tools for comprehensive iOS testing workflows.

### Agent Commands

**Visual Regression Testing:**
```
"Run visual regression tests comparing baseline to current screenshots"
→ Mobile Dev uses screenshot_diff.py to generate visual diff report

"The UI changed unexpectedly - show me what's different"
→ Mobile Dev runs screenshot diff and opens report
```

**Matrix Testing:**
```
"Test the app in dark mode with large text"
→ Mobile Dev creates matrix config and runs ios_test_matrix.rb

"Run accessibility compliance tests"
→ Mobile Dev uses 'accessibility' preset

"Test the app under poor network conditions"
→ Mobile Dev uses 'network' preset with 3G throttling
```

**Network Analysis:**
```
"Show me all failed API requests"
→ Mobile Dev uses pulse_log_export.rb filter --status 400-599

"Which API calls are slow?"
→ Mobile Dev runs analyze command and shows slow requests

"Export network logs for debugging"
→ Mobile Dev exports logs in requested format
```

**Complete Pipeline:**
```
"Run comprehensive tests and show me the results"
→ Mobile Dev runs full pipeline (matrix + visual diff + network analysis)
→ Generates unified report with all results
```

---

## Tool Combinations

### Combination 1: Matrix Testing + Screenshot Diffing

**Use Case:** Validate UI across all configurations while detecting visual regressions

**Flow:**
1. `ios_test_matrix.rb` generates screenshots for each configuration
2. `screenshot_diff.py` compares each configuration's screenshots to baseline
3. Combined report shows which configurations have visual regressions

**Implementation:**
```bash
# Run matrix with screenshots
ruby ios_test_matrix.rb run --config test-config.json

# For each configuration's screenshots, run diff
for config_dir in matrix-results/screenshots/*; do
  config_name=$(basename "$config_dir")
  python3 screenshot_diff.py --batch \
    "baseline-screenshots/$config_name" \
    "$config_dir" \
    -o "diff-results/$config_name"
done
```

### Combination 2: Matrix Testing + Network Analysis

**Use Case:** Test network behavior under different conditions

**Flow:**
1. `ios_test_matrix.rb` runs tests with different network conditions (WiFi, 3G, offline)
2. `pulse_log_export.rb` extracts network logs for each condition
3. Compare performance across network conditions

**Implementation:**
```bash
# Test with 3G network
ruby simulator_control.rb network-throttle --profile 3g
ruby ios_test_matrix.rb run --preset network
ruby pulse_log_export.rb analyze --app-id com.example.app --output 3g-analysis.html

# Test with WiFi
ruby simulator_control.rb network-throttle --profile wifi
ruby ios_test_matrix.rb run --preset network
ruby pulse_log_export.rb analyze --app-id com.example.app --output wifi-analysis.html

# Compare results
diff 3g-analysis.html wifi-analysis.html
```

### Combination 3: All Three Tools

**Use Case:** Complete testing coverage (UI + functionality + network)

**Flow:**
1. `ios_test_matrix.rb` runs comprehensive tests across all configurations
2. `screenshot_diff.py` validates visual consistency
3. `pulse_log_export.rb` analyzes network performance
4. Unified report with all metrics

**Result:** Complete picture of app health across all dimensions.

---

## Best Practices

### Screenshot Diffing

✅ **DO:**
- Create baseline screenshots in production-ready state
- Use consistent simulator and status bar settings
- Review diffs carefully (some changes are intentional)
- Update baselines when UI changes are approved
- Use threshold wisely (1% default catches real issues without false positives)

❌ **DON'T:**
- Compare screenshots from different simulators
- Ignore small diffs (they compound over time)
- Use inconsistent status bar or time
- Skip baseline updates after intentional changes

**Tip:** Use `simulator_control.rb override-status-bar` for consistent status bar in screenshots.

### Test Matrix

✅ **DO:**
- Start with minimal preset, expand to comprehensive
- Use predefined presets for common scenarios
- Screenshot key screens only (not every view)
- Run regularly (daily or per PR)
- Review HTML reports for patterns

❌ **DON'T:**
- Run comprehensive matrix on every code change (too slow)
- Screenshot every single view (increases runtime)
- Ignore failed configurations
- Run without simulator prepared (wait for boot)

**Tip:** Use `--preset minimal` for quick validation, `--preset comprehensive` for release testing.

### Network Analysis

✅ **DO:**
- Export logs after test runs
- Filter by status code to find errors
- Review slow requests (>1s threshold)
- Compare network performance across conditions
- Archive logs for debugging later

❌ **DON'T:**
- Export logs before running tests (empty database)
- Ignore 4xx errors (client issues)
- Forget to test offline scenarios
- Skip network throttling tests

**Tip:** Run network analysis after each test matrix run to correlate failures with network issues.

---

## Troubleshooting

### Screenshot Diffing Issues

**Problem:** "Image dimensions don't match"
- **Cause:** Different simulators or orientations
- **Solution:** Use same simulator for baseline and current screenshots

**Problem:** "Too many false positives"
- **Cause:** Threshold too strict
- **Solution:** Increase threshold with `-t 0.02` (2%)

**Problem:** Dependencies not installed
- **Solution:** `pip3 install Pillow numpy`

### Test Matrix Issues

**Problem:** "No booted simulators found"
- **Solution:** Boot simulator first: `xcrun simctl boot "iPhone 16"`

**Problem:** Tests timing out
- **Cause:** Comprehensive matrix too large
- **Solution:** Use smaller preset or reduce matrix dimensions

**Problem:** Environment setup failing
- **Cause:** simulator_control.rb not accessible
- **Solution:** Verify simulator_control.rb is in tools/ directory

### Network Log Issues

**Problem:** "Pulse database not found"
- **Cause:** Pulse not integrated or no network requests made
- **Solution:** Add Pulse package, run app and make network requests

**Problem:** "Could not find app container"
- **Cause:** App not installed or wrong bundle ID
- **Solution:** Verify app is installed with `ruby pulse_log_export.rb list-apps`

**Problem:** Empty logs
- **Cause:** No network requests made yet
- **Solution:** Run app and trigger network activity first

---

## Performance Metrics

### Screenshot Diffing
- **Single comparison:** 1-2 seconds
- **Batch mode (50 screenshots):** 30-60 seconds
- **Output size:** ~500KB per diff set

### Test Matrix
- **Minimal preset (6 configs):** 5-10 minutes
- **Accessibility preset (18 configs):** 15-25 minutes
- **Comprehensive preset (120+ configs):** 1-2 hours

### Network Analysis
- **Export 100 requests:** 1-2 seconds
- **Analysis report:** 2-3 seconds
- **HTML generation:** 3-5 seconds

---

## CI/CD Integration

### GitHub Actions Example

```yaml
name: iOS Testing Pipeline

on: [push, pull_request]

jobs:
  test:
    runs-on: macos-latest
    steps:
      - uses: actions/checkout@v3

      - name: Setup Dependencies
        run: |
          pip3 install Pillow numpy
          gem install json

      - name: Boot Simulator
        run: |
          xcrun simctl boot "iPhone 16" || true
          sleep 10

      - name: Run Test Matrix
        run: |
          ruby tools/ios_test_matrix.rb run \
            --preset accessibility \
            --project MyApp.xcodeproj \
            --scheme MyApp \
            --output test-results/

      - name: Visual Regression Tests
        run: |
          python3 tools/screenshot_diff.py --batch \
            baseline-screenshots/ \
            test-results/screenshots/ \
            -o visual-diff/ \
            -f json > diff-results.json

      - name: Network Analysis
        run: |
          ruby tools/pulse_log_export.rb analyze \
            --app-id com.example.MyApp \
            --output network-analysis.json

      - name: Upload Results
        uses: actions/upload-artifact@v3
        with:
          name: test-results
          path: |
            test-results/
            visual-diff/
            network-analysis.json

      - name: Check for Failures
        run: |
          # Fail if visual regressions detected
          if [ $(jq '.different' diff-results.json) -gt 0 ]; then
            echo "❌ Visual regressions detected"
            exit 1
          fi
```

---

## Summary

The Advanced iOS Testing Framework provides three powerful tools that work together:

1. **screenshot_diff.py** - Automated visual regression testing
2. **ios_test_matrix.rb** - Comprehensive configuration matrix testing
3. **pulse_log_export.rb** - Network log analysis

**Key Benefits:**
- ✅ Complete test coverage (UI + functionality + network)
- ✅ Automated visual regression detection
- ✅ Accessibility compliance validation
- ✅ Network performance analysis
- ✅ CI/CD integration ready
- ✅ Mobile Dev agent integration

**Next Steps:**
1. Add Pulse to your iOS project
2. Create baseline screenshots
3. Configure test matrix
4. Run comprehensive test pipeline
5. Review reports and fix issues

For individual tool documentation:
- Screenshot Diffing: Run `python3 tools/screenshot_diff.py --help`
- Test Matrix: Run `ruby tools/ios_test_matrix.rb --help`
- Network Analysis: Run `ruby tools/pulse_log_export.rb --help`

---

*Advanced iOS Testing Framework - Catalyst*
*Mobile Dev Agent: Use these tools for comprehensive iOS testing workflows*
