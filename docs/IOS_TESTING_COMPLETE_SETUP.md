# iOS Testing Framework - Complete Setup Guide

**🎯 Everything you need to set up comprehensive iOS testing in minutes**

## What You Get

The Catalyst iOS Testing Framework provides three powerful tools that work together:

1. **📸 screenshot_diff.py** - Automated visual regression testing
2. **🧪 ios_test_matrix.rb** - Comprehensive test automation across device configurations
3. **🌐 pulse_log_export.rb** - Network log extraction and analysis

**Plus:**
- ✅ One-command setup for any iOS project
- ✅ Ready-to-use CI/CD templates for 5 platforms
- ✅ Automatic Pulse integration
- ✅ Pre-configured test matrix presets
- ✅ Complete testing pipelines

---

## 🚀 Quick Start (5 Minutes)

### Step 1: Setup Testing Framework

```bash
# Navigate to your iOS project
cd /path/to/your/MyApp.xcodeproj/..

# Run setup (one command!)
~/Catalyst/tools/setup_ios_testing.sh \
  MyApp.xcodeproj \
  MyApp \
  com.example.MyApp
```

This creates complete testing infrastructure:
- `testing/` directory with scripts and configs
- Test matrix presets (minimal, accessibility, network, comprehensive)
- Baseline screenshot scripts
- Network analysis tools
- CI/CD workflow templates

**What gets created:**
```
MyApp/
├── MyApp.xcodeproj
└── testing/
    ├── README.md                          # Quick reference guide
    ├── PULSE_SETUP.md                     # Network monitoring setup
    ├── baseline-screenshots/              # Reference screenshots
    ├── current-screenshots/               # Current state screenshots
    ├── test-results/                      # Test output
    ├── configs/
    │   ├── minimal.json                   # 6 combinations
    │   ├── accessibility.json             # 40 combinations
    │   ├── network.json                   # 8 combinations
    │   └── comprehensive.json             # 54 combinations
    └── scripts/
        ├── capture-baseline.sh            # Create baseline
        ├── capture-current.sh             # Capture current state
        ├── run-visual-diff.sh             # Compare screenshots
        ├── run-matrix-tests.sh            # Run test matrix
        ├── analyze-network.sh             # Network analysis
        └── run-comprehensive-pipeline.sh  # Full pipeline
```

### Step 2: Add Network Monitoring (Optional)

```bash
# Automatic Pulse integration
~/Catalyst/tools/add_pulse_to_app.sh MyApp/MyApp.swift
```

Or follow the guide:
```bash
cat testing/PULSE_SETUP.md
```

### Step 3: Capture Baseline Screenshots

```bash
cd testing
./scripts/capture-baseline.sh
```

Commit baselines to git:
```bash
git add baseline-screenshots/
git commit -m "Add baseline screenshots for visual regression testing"
```

### Step 4: Run Your First Test

```bash
cd testing

# Quick validation (6 configurations, ~5 minutes)
./scripts/run-matrix-tests.sh minimal

# View results
open test-results/minimal/report.html
```

### Step 5: Setup CI/CD (Optional)

```bash
# Copy your preferred CI/CD template
cp ~/.../templates/ci-cd/ios-testing-github-actions.yml \
   .github/workflows/ios-testing.yml

# Customize and commit
git add .github/workflows/ios-testing.yml
git commit -m "Add iOS testing CI workflow"
git push
```

**Done!** Your iOS project now has comprehensive automated testing.

---

## 📊 Testing Workflows

### Workflow 1: Quick Validation (Daily Development)

**Use Case:** Fast feedback after code changes

```bash
cd testing

# Run minimal tests (6 configurations)
./scripts/run-matrix-tests.sh minimal

# Check for visual regressions
./scripts/run-visual-diff.sh

# View results
open test-results/minimal/report.html
```

**Time:** ~5-10 minutes
**Configurations:** 6 (Light/Dark × 3 text sizes)

---

### Workflow 2: Accessibility Compliance

**Use Case:** Validate accessibility support

```bash
cd testing

# Run accessibility test matrix (40 configurations)
./scripts/run-matrix-tests.sh accessibility

# View results
open test-results/accessibility/report.html
```

**Time:** ~15-25 minutes
**Configurations:** 40 (2 appearance × 5 text sizes × 4 accessibility features)

**Tests:**
- Dynamic Type support (5 text sizes including AccessibilityXXXL)
- Reduce Motion compatibility
- Increase Contrast support
- Bold Text rendering
- All combinations in light/dark mode

---

### Workflow 3: Network Resilience Testing

**Use Case:** Test app under poor network conditions

```bash
cd testing

# Run network test matrix (8 configurations)
./scripts/run-matrix-tests.sh network

# Analyze network logs
./scripts/analyze-network.sh

# View results
open test-results/network/report.html
open test-results/network-analysis-*.html
```

**Time:** ~10-15 minutes
**Configurations:** 8 (Light/Dark × WiFi/3G/Edge/Offline)

**Network Conditions:**
- WiFi (normal speed)
- 3G (throttled to 1.6 Mbps down, 768 Kbps up)
- Edge (throttled to 240 Kbps down, 200 Kbps up)
- Offline (no connectivity)

---

### Workflow 4: Complete Testing Pipeline

**Use Case:** Pre-release validation

```bash
cd testing

# Run everything at once
./scripts/run-comprehensive-pipeline.sh

# This runs:
# 1. Comprehensive test matrix (54 configurations)
# 2. Visual regression testing
# 3. Network analysis
# 4. Generates unified report
```

**Time:** ~30-60 minutes
**Configurations:** 54+ (2 appearance × 3 text sizes × 3 network × 3 accessibility)

**Output:**
```
test-results/pipeline-[timestamp]/
├── matrix-results/
│   ├── report.html                    # Test matrix report
│   └── screenshots/                   # All configuration screenshots
├── visual-diff/
│   ├── report.html                    # Visual regression report
│   ├── diff.png                       # Highlighted differences
│   ├── side-by-side.png               # Comparison view
│   └── overlay.png                    # Overlay comparison
├── network-analysis-*.html            # Network performance report
└── SUMMARY.md                         # Quick summary
```

---

## 🎯 Test Matrix Presets

### Minimal (Fast Feedback)

**Configurations:** 6
**Time:** ~5-10 minutes
**Use:** Daily development, PR validation

**Matrix:**
- Appearance: Light, Dark
- Text Size: L, XL, XXL

**Command:**
```bash
./scripts/run-matrix-tests.sh minimal
```

---

### Accessibility (Compliance)

**Configurations:** 40
**Time:** ~15-25 minutes
**Use:** Accessibility audits, WCAG compliance

**Matrix:**
- Appearance: Light, Dark
- Text Size: L, XL, XXL, AccessibilityXL, AccessibilityXXXL
- Accessibility: Normal, Reduce Motion, Increase Contrast, Bold Text

**Command:**
```bash
./scripts/run-matrix-tests.sh accessibility
```

---

### Network (Resilience)

**Configurations:** 8
**Time:** ~10-15 minutes
**Use:** Network testing, offline scenarios

**Matrix:**
- Appearance: Light, Dark
- Network: WiFi, 3G, Edge, Offline

**Command:**
```bash
./scripts/run-matrix-tests.sh network
```

---

### Comprehensive (Full Validation)

**Configurations:** 54
**Time:** ~30-60 minutes
**Use:** Pre-release testing, major updates

**Matrix:**
- Appearance: Light, Dark
- Text Size: L, XL, AccessibilityXL
- Network: WiFi, 3G, Offline
- Accessibility: Normal, Reduce Motion, Increase Contrast

**Command:**
```bash
./scripts/run-matrix-tests.sh comprehensive
```

---

## 🔧 Individual Tools

### Screenshot Diffing

**Purpose:** Detect visual regressions automatically

**Usage:**
```bash
# Single comparison
python3 ~/Catalyst/tools/screenshot_diff.py \
  baseline.png current.png -o diff/

# Batch mode (compare directories)
python3 ~/Catalyst/tools/screenshot_diff.py --batch \
  baseline-screenshots/ \
  current-screenshots/ \
  -o visual-diff-results/

# Custom threshold (2% tolerance)
python3 ~/Catalyst/tools/screenshot_diff.py \
  baseline.png current.png -t 0.02

# JSON output (for automation)
python3 ~/Catalyst/tools/screenshot_diff.py \
  baseline.png current.png -f json > diff.json
```

**Output:**
- `diff.png` - Red highlights on differences
- `side-by-side.png` - Baseline vs current comparison
- `overlay.png` - Overlay comparison
- `report.html` - Interactive visual diff report

---

### Test Matrix Automation

**Purpose:** Run tests across all device configurations

**Usage:**
```bash
# Use preset
ruby ~/Catalyst/tools/ios_test_matrix.rb run \
  --preset minimal \
  --project MyApp.xcodeproj \
  --scheme MyApp

# Use custom config
ruby ~/Catalyst/tools/ios_test_matrix.rb run \
  --config custom-config.json

# Generate config template
ruby ~/Catalyst/tools/ios_test_matrix.rb generate-config \
  --output my-config.json

# List available presets
ruby ~/Catalyst/tools/ios_test_matrix.rb list-configs
```

**Custom Configuration:**
```json
{
  "name": "Custom Test",
  "project_path": "/path/to/MyApp.xcodeproj",
  "scheme": "MyApp",
  "simulator": "iPhone 16",
  "matrix": {
    "appearance": ["light", "dark"],
    "text_size": ["L", "XXL"],
    "network": ["wifi", "off"]
  },
  "output_dir": "./custom-results"
}
```

---

### Network Log Export

**Purpose:** Analyze network performance from Pulse logs

**Usage:**
```bash
# Export all logs
ruby ~/Catalyst/tools/pulse_log_export.rb export \
  --app-id com.example.MyApp \
  --format json

# Generate analysis report
ruby ~/Catalyst/tools/pulse_log_export.rb analyze \
  --app-id com.example.MyApp \
  --output network-report.html

# Filter errors only (4xx/5xx)
ruby ~/Catalyst/tools/pulse_log_export.rb filter \
  --app-id com.example.MyApp \
  --status 400-599 \
  --output errors.json

# Filter by URL pattern
ruby ~/Catalyst/tools/pulse_log_export.rb filter \
  --app-id com.example.MyApp \
  --url-pattern "api.example.com" \
  --format csv

# Filter by method and time
ruby ~/Catalyst/tools/pulse_log_export.rb filter \
  --app-id com.example.MyApp \
  --method POST \
  --since "2024-01-01T00:00:00Z"

# List installed apps
ruby ~/Catalyst/tools/pulse_log_export.rb list-apps
```

**Analysis Report Includes:**
- Total requests, success rate, error rate
- Average response time
- Data sent/received
- HTTP method distribution
- Status code breakdown
- Slow requests (>1s)
- Error details with URLs

---

## 🔄 CI/CD Integration

Pre-configured templates for 5 platforms:

### GitHub Actions

```bash
cp ~/Catalyst/templates/ci-cd/ios-testing-github-actions.yml \
   .github/workflows/ios-testing.yml
```

**Features:**
- ✅ Runs on push/PR to main/develop
- ✅ Minimal tests for PRs, comprehensive for main
- ✅ Visual regression detection
- ✅ Network analysis
- ✅ Uploads artifacts
- ✅ Posts PR comments

---

### GitLab CI/CD

```bash
cp ~/Catalyst/templates/ci-cd/ios-testing-gitlab-ci.yml \
   .gitlab-ci.yml
```

**Stages:**
1. setup - Install dependencies
2. build - Compile app
3. test - Run test matrix
4. analyze - Network analysis
5. report - Generate summary

---

### Bitbucket Pipelines

```bash
cp ~/Catalyst/templates/ci-cd/ios-testing-bitbucket-pipelines.yml \
   bitbucket-pipelines.yml
```

**Pipelines:**
- default - Build & test (minimal)
- main - Comprehensive testing
- pull-requests - Quick validation
- custom - Accessibility/network tests

---

### CircleCI

```bash
mkdir -p .circleci
cp ~/Catalyst/templates/ci-cd/ios-testing-circleci-config.yml \
   .circleci/config.yml
```

**Workflows:**
- test-and-deploy - Every push
- nightly - Scheduled comprehensive tests

---

### Jenkins

```bash
cp ~/Catalyst/templates/ci-cd/ios-testing-Jenkinsfile \
   Jenkinsfile
```

**Parameters:**
- TEST_PRESET - minimal/accessibility/network/comprehensive
- RUN_VISUAL_REGRESSION - Enable/disable
- RUN_NETWORK_ANALYSIS - Enable/disable

---

## 📚 Documentation

Complete documentation available:

1. **ADVANCED_IOS_TESTING.md** - Complete testing framework guide
   - All tool capabilities
   - Integration workflows
   - Troubleshooting
   - Best practices

2. **IOS_TESTING_CICD_GUIDE.md** - CI/CD integration guide
   - Platform-specific setup
   - Configuration patterns
   - Performance optimization
   - Security best practices

3. **Testing README** (in your project)
   - Quick reference
   - Script usage
   - Directory structure
   - Common commands

**Locations:**
```bash
# Framework documentation
cat ~/Catalyst/docs/ADVANCED_IOS_TESTING.md

# CI/CD guide
cat ~/Catalyst/docs/IOS_TESTING_CICD_GUIDE.md

# Project-specific guide (after setup)
cat testing/README.md

# Pulse setup guide (after setup)
cat testing/PULSE_SETUP.md
```

---

## 🛠️ Helper Scripts

### Setup Script

Configures complete testing framework for any iOS project:

```bash
~/Catalyst/tools/setup_ios_testing.sh \
  <project_path> \
  <scheme> \
  <bundle_id>
```

**What it creates:**
- Testing directory structure
- Test matrix configurations (4 presets)
- Testing scripts (6 automated scripts)
- CI/CD workflow templates
- Documentation (README, Pulse setup)

---

### Pulse Integration Script

Automatically adds Pulse network monitoring to iOS apps:

```bash
~/Catalyst/tools/add_pulse_to_app.sh MyApp/MyApp.swift
```

**What it adds:**
- Import Pulse framework
- Automatic URLSession monitoring
- 3-finger tap gesture for logs
- DEBUG-only (zero production overhead)

---

## 🎯 Common Use Cases

### Use Case 1: Daily Development

**Scenario:** Just finished coding, want quick feedback

```bash
cd testing

# Quick test (5 minutes)
./scripts/run-matrix-tests.sh minimal

# Check for visual breaks
./scripts/run-visual-diff.sh

# View results
open test-results/minimal/report.html
```

---

### Use Case 2: Before Pull Request

**Scenario:** Ready to create PR, want to catch issues

```bash
cd testing

# Run accessibility + visual regression
./scripts/run-matrix-tests.sh accessibility
./scripts/run-visual-diff.sh

# If diffs found, review carefully
open test-results/visual-diff-*/report.html

# Update baselines if changes are intentional
./scripts/capture-baseline.sh
git add baseline-screenshots/
git commit -m "Update baselines for [feature]"
```

---

### Use Case 3: Network Bug Investigation

**Scenario:** Users reporting network issues, need to debug

```bash
cd testing

# Test under poor network conditions
./scripts/run-matrix-tests.sh network

# Analyze network logs
./scripts/analyze-network.sh

# Review slow requests and errors
open test-results/network-analysis-*.html

# Export specific errors
ruby ~/Catalyst/tools/pulse_log_export.rb filter \
  --app-id com.example.MyApp \
  --status 400-599 \
  --output errors.json
```

---

### Use Case 4: Pre-Release Validation

**Scenario:** About to release, need full validation

```bash
cd testing

# Run everything
./scripts/run-comprehensive-pipeline.sh

# Review all reports
open test-results/pipeline-*/matrix-results/report.html
open test-results/pipeline-*/visual-diff/report.html
open test-results/network-analysis-*.html

# If all pass, ready to release!
```

---

## ⚡ Performance Metrics

| Tool | Operation | Time | Output |
|------|-----------|------|--------|
| **screenshot_diff.py** | Single comparison | 1-2s | ~500KB |
| **screenshot_diff.py** | Batch (50 images) | 30-60s | ~25MB |
| **ios_test_matrix.rb** | Minimal (6 configs) | 5-10min | ~50MB |
| **ios_test_matrix.rb** | Accessibility (40 configs) | 15-25min | ~200MB |
| **ios_test_matrix.rb** | Comprehensive (54 configs) | 30-60min | ~300MB |
| **pulse_log_export.rb** | Export 100 requests | 1-2s | ~1MB |
| **pulse_log_export.rb** | Analysis report | 2-3s | ~500KB |
| **Comprehensive Pipeline** | Full run | 30-60min | ~350MB |

---

## ✅ Checklist for New Projects

### Initial Setup

- [ ] Run setup_ios_testing.sh with your project details
- [ ] Review testing/README.md
- [ ] Add Pulse network monitoring (optional)
- [ ] Capture baseline screenshots
- [ ] Commit baselines to git

### First Test Run

- [ ] Run minimal test matrix
- [ ] Verify all tests pass
- [ ] Review test report
- [ ] Check screenshot quality

### CI/CD Setup

- [ ] Choose CI/CD platform
- [ ] Copy appropriate template
- [ ] Customize scheme/bundle ID
- [ ] Test pipeline on feature branch
- [ ] Enable for main branch

### Regular Testing

- [ ] Run minimal tests daily
- [ ] Run accessibility tests weekly
- [ ] Run comprehensive tests before releases
- [ ] Update baselines when UI changes
- [ ] Archive test results

---

## 🚨 Troubleshooting

### "No booted simulators found"

```bash
# Boot simulator manually
xcrun simctl boot "iPhone 16"
sleep 10

# Verify
xcrun simctl list devices | grep Booted
```

### "Dependencies not installed"

```bash
# Install Python packages
pip3 install Pillow numpy

# Install Ruby gems
gem install json

# Verify
python3 -c "import PIL; import numpy"
ruby -e "require 'json'"
```

### "Baseline screenshots not found"

```bash
# Create baselines
cd testing
./scripts/capture-baseline.sh

# Commit
git add baseline-screenshots/
git commit -m "Add baseline screenshots"
```

### "Pulse database not found"

```bash
# Verify Pulse is integrated
cat testing/PULSE_SETUP.md

# Ensure app makes network requests
# Run app and trigger network activity

# Skip network analysis if no Pulse
./scripts/analyze-network.sh || true
```

---

## 📞 Support

**Documentation:**
- Complete guide: `~/Catalyst/docs/ADVANCED_IOS_TESTING.md`
- CI/CD guide: `~/Catalyst/docs/IOS_TESTING_CICD_GUIDE.md`
- Mobile Dev agent: `~/.claude/agents/mobile-dev.md`

**Tools:**
- Setup script: `~/Catalyst/tools/setup_ios_testing.sh --help`
- Screenshot diff: `python3 ~/Catalyst/tools/screenshot_diff.py --help`
- Test matrix: `ruby ~/Catalyst/tools/ios_test_matrix.rb --help`
- Network export: `ruby ~/Catalyst/tools/pulse_log_export.rb --help`

**Examples:**
- See testing/README.md (created after setup)
- See testing/PULSE_SETUP.md (created after setup)

---

## Summary

You now have a complete iOS testing framework with:

✅ **Automated visual regression testing** - Catch UI breaks automatically
✅ **Comprehensive test matrices** - Test all device configurations
✅ **Network performance analysis** - Debug API issues
✅ **One-command setup** - Works with any iOS project
✅ **CI/CD ready** - Templates for 5 platforms
✅ **Zero production overhead** - All tools are DEBUG-only

**Get started in 5 minutes:**
```bash
~/Catalyst/tools/setup_ios_testing.sh MyApp.xcodeproj MyApp com.example.MyApp
cd testing
./scripts/capture-baseline.sh
./scripts/run-matrix-tests.sh minimal
open test-results/minimal/report.html
```

---

*iOS Testing Framework - Catalyst*
*Complete, automated, production-ready*
