# iOS Testing Framework - Quick Reference Card

**🚀 One-page cheat sheet for the Catalyst iOS Testing Framework**

---

## 📦 Initial Setup (One-Time)

```bash
# Setup testing framework for your iOS project
~/Catalyst/tools/setup_ios_testing.sh MyApp.xcodeproj MyApp com.example.MyApp

# Add Pulse network monitoring (optional)
~/Catalyst/tools/add_pulse_to_app.sh MyApp/MyApp.swift

# Capture baseline screenshots
cd testing && ./scripts/capture-baseline.sh

# Commit baselines
git add baseline-screenshots/ && git commit -m "Add baseline screenshots"
```

---

## 🧪 Running Tests

### Quick Commands

```bash
cd testing

# Minimal (6 configs, ~5 min)
./scripts/run-matrix-tests.sh minimal

# Accessibility (40 configs, ~20 min)
./scripts/run-matrix-tests.sh accessibility

# Network (8 configs, ~12 min)
./scripts/run-matrix-tests.sh network

# Comprehensive (54 configs, ~45 min)
./scripts/run-matrix-tests.sh comprehensive

# Full pipeline (matrix + visual + network)
./scripts/run-comprehensive-pipeline.sh
```

### Visual Regression

```bash
cd testing

# Capture current state
./scripts/capture-current.sh

# Compare with baseline
./scripts/run-visual-diff.sh

# View results
open test-results/visual-diff-*/report.html
```

### Network Analysis

```bash
cd testing

# Analyze network performance
./scripts/analyze-network.sh

# View report
open test-results/network-analysis-*.html
```

---

## 🛠️ Direct Tool Usage

### Screenshot Diffing

```bash
# Single comparison
python3 ~/Catalyst/tools/screenshot_diff.py baseline.png current.png -o diff/

# Batch mode
python3 ~/Catalyst/tools/screenshot_diff.py --batch baseline/ current/ -o results/

# Custom threshold (2%)
python3 ~/Catalyst/tools/screenshot_diff.py baseline.png current.png -t 0.02
```

### Test Matrix

```bash
# Use preset
ruby ~/Catalyst/tools/ios_test_matrix.rb run --preset minimal \
  --project MyApp.xcodeproj --scheme MyApp

# Generate config
ruby ~/Catalyst/tools/ios_test_matrix.rb generate-config -o custom.json

# List presets
ruby ~/Catalyst/tools/ios_test_matrix.rb list-configs
```

### Network Export

```bash
# Export all logs
ruby ~/Catalyst/tools/pulse_log_export.rb export --app-id com.example.MyApp

# Analyze performance
ruby ~/Catalyst/tools/pulse_log_export.rb analyze --app-id com.example.MyApp

# Filter errors (4xx/5xx)
ruby ~/Catalyst/tools/pulse_log_export.rb filter --app-id com.example.MyApp --status 400-599

# List apps
ruby ~/Catalyst/tools/pulse_log_export.rb list-apps
```

---

## 🔄 CI/CD Setup

### GitHub Actions

```bash
cp ~/Catalyst/templates/ci-cd/ios-testing-github-actions.yml \
   .github/workflows/ios-testing.yml
```

### GitLab CI

```bash
cp ~/Catalyst/templates/ci-cd/ios-testing-gitlab-ci.yml .gitlab-ci.yml
```

### Bitbucket

```bash
cp ~/Catalyst/templates/ci-cd/ios-testing-bitbucket-pipelines.yml \
   bitbucket-pipelines.yml
```

### CircleCI

```bash
mkdir -p .circleci
cp ~/Catalyst/templates/ci-cd/ios-testing-circleci-config.yml \
   .circleci/config.yml
```

### Jenkins

```bash
cp ~/Catalyst/templates/ci-cd/ios-testing-Jenkinsfile Jenkinsfile
```

---

## 📊 Test Matrix Presets

| Preset | Configs | Time | Use Case |
|--------|---------|------|----------|
| **minimal** | 6 | 5-10 min | Daily dev, PRs |
| **accessibility** | 40 | 15-25 min | WCAG compliance |
| **network** | 8 | 10-15 min | Network testing |
| **comprehensive** | 54 | 30-60 min | Pre-release |

---

## 📁 Directory Structure

```
testing/
├── README.md                          # Quick reference
├── PULSE_SETUP.md                     # Network monitoring guide
├── baseline-screenshots/              # Reference images
├── current-screenshots/               # Current state
├── test-results/                      # Test output
├── configs/
│   ├── minimal.json
│   ├── accessibility.json
│   ├── network.json
│   └── comprehensive.json
└── scripts/
    ├── capture-baseline.sh
    ├── capture-current.sh
    ├── run-visual-diff.sh
    ├── run-matrix-tests.sh
    ├── analyze-network.sh
    └── run-comprehensive-pipeline.sh
```

---

## 🎯 Common Workflows

### Daily Development

```bash
cd testing
./scripts/run-matrix-tests.sh minimal
./scripts/run-visual-diff.sh
open test-results/minimal/report.html
```

### Before PR

```bash
cd testing
./scripts/run-matrix-tests.sh accessibility
./scripts/run-visual-diff.sh
# Review any visual diffs, update baselines if intentional
```

### Network Debugging

```bash
cd testing
./scripts/run-matrix-tests.sh network
./scripts/analyze-network.sh
open test-results/network-analysis-*.html
```

### Pre-Release

```bash
cd testing
./scripts/run-comprehensive-pipeline.sh
open test-results/pipeline-*/matrix-results/report.html
```

---

## 🔧 Updating Baselines

```bash
cd testing

# Capture new baselines
./scripts/capture-baseline.sh

# Review changes
./scripts/run-visual-diff.sh
open test-results/visual-diff-*/report.html

# If approved, commit
git add baseline-screenshots/
git commit -m "Update baselines for [reason]"
git push
```

---

## 📚 Documentation Locations

| Document | Path |
|----------|------|
| **Complete Setup** | `~/Catalyst/docs/IOS_TESTING_COMPLETE_SETUP.md` |
| **Advanced Guide** | `~/Catalyst/docs/ADVANCED_IOS_TESTING.md` |
| **CI/CD Guide** | `~/Catalyst/docs/IOS_TESTING_CICD_GUIDE.md` |
| **Quick Reference** | `~/Catalyst/docs/IOS_TESTING_QUICK_REFERENCE.md` *(this file)* |
| **Project README** | `testing/README.md` *(after setup)* |
| **Pulse Setup** | `testing/PULSE_SETUP.md` *(after setup)* |

---

## 🛠️ Tool Help

```bash
# Setup script help
~/Catalyst/tools/setup_ios_testing.sh

# Screenshot diff help
python3 ~/Catalyst/tools/screenshot_diff.py --help

# Test matrix help
ruby ~/Catalyst/tools/ios_test_matrix.rb --help

# Network export help
ruby ~/Catalyst/tools/pulse_log_export.rb --help

# Pulse integration help
~/Catalyst/tools/add_pulse_to_app.sh
```

---

## 🚨 Troubleshooting

### No booted simulator

```bash
xcrun simctl boot "iPhone 16"
sleep 10
```

### Dependencies not installed

```bash
pip3 install Pillow numpy
gem install json
```

### Baseline not found

```bash
cd testing && ./scripts/capture-baseline.sh
git add baseline-screenshots/ && git commit -m "Add baselines"
```

### Pulse database not found

```bash
# Verify Pulse is integrated
cat testing/PULSE_SETUP.md

# Run app and make network requests first
```

---

## ⚡ Performance

| Operation | Time | Output Size |
|-----------|------|-------------|
| Screenshot diff (single) | 1-2s | ~500KB |
| Screenshot diff (batch 50) | 30-60s | ~25MB |
| Minimal matrix | 5-10min | ~50MB |
| Accessibility matrix | 15-25min | ~200MB |
| Network matrix | 10-15min | ~80MB |
| Comprehensive matrix | 30-60min | ~300MB |
| Network analysis | 2-3s | ~500KB |
| Full pipeline | 30-60min | ~350MB |

---

## ✅ Checklist for New Projects

- [ ] Run setup_ios_testing.sh
- [ ] Add Pulse (optional)
- [ ] Capture baselines
- [ ] Run minimal tests
- [ ] Setup CI/CD
- [ ] Document custom configs

---

## 💡 Tips

**Best Practices:**
- Run `minimal` daily for fast feedback
- Run `accessibility` weekly for compliance
- Run `comprehensive` before releases
- Update baselines after approved UI changes
- Archive test results for history

**CI/CD Strategy:**
- Feature branches: minimal preset
- Main/develop: comprehensive preset
- Scheduled: nightly comprehensive tests
- PR validation: minimal + visual regression

**Visual Regression:**
- Consistent status bar: Use simulator_control.rb
- Threshold tuning: Start with 1%, adjust as needed
- Baseline updates: Always review diffs first
- Git LFS: Consider for large baseline sets

---

*iOS Testing Framework Quick Reference - Catalyst*
*Print this page for instant access to all commands*
