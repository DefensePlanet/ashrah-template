# iOS Testing CI/CD Integration Guide

**Complete CI/CD Setup for Advanced iOS Testing Framework**

## Overview

This guide shows how to integrate the Catalyst Advanced iOS Testing Framework (screenshot diffing, test matrix automation, network analysis) into various CI/CD platforms.

**Supported Platforms:**
- ✅ GitHub Actions
- ✅ GitLab CI/CD
- ✅ Bitbucket Pipelines
- ✅ CircleCI
- ✅ Jenkins

---

## Prerequisites

### 1. iOS Testing Framework Setup

First, set up the testing framework for your project:

```bash
# Navigate to your project
cd /path/to/your/ios-project

# Run setup script
~/Catalyst/tools/setup_ios_testing.sh \
  MyApp.xcodeproj \
  MyApp \
  com.example.MyApp
```

This creates:
- `testing/` directory with scripts and configs
- Test matrix presets (minimal, accessibility, network, comprehensive)
- Baseline screenshot capture scripts
- Network analysis tools

### 2. Pulse Integration (Optional but Recommended)

Add Pulse network monitoring to your app:

```bash
# Add Pulse package via Xcode or use helper script
~/Catalyst/tools/add_pulse_to_app.sh MyApp/MyApp.swift
```

### 3. Baseline Screenshots

Capture baseline screenshots for visual regression testing:

```bash
cd testing
./scripts/capture-baseline.sh
```

Commit baseline screenshots to your repository:

```bash
git add baseline-screenshots/
git commit -m "Add baseline screenshots for visual regression testing"
```

---

## Platform-Specific Setup

### GitHub Actions

**Template Location:** `{{CATALYST_ROOT}}/templates/ci-cd/ios-testing-github-actions.yml`

**Setup:**

1. **Copy workflow file:**
```bash
mkdir -p .github/workflows
cp ~/Catalyst/templates/ci-cd/ios-testing-github-actions.yml \
   .github/workflows/ios-testing.yml
```

2. **Customize variables:**
```yaml
env:
  SCHEME: "YourScheme"           # Your Xcode scheme
  BUNDLE_ID: "com.your.app"      # Your bundle identifier
  SIMULATOR: "iPhone 16"         # Target simulator
```

3. **Commit and push:**
```bash
git add .github/workflows/ios-testing.yml
git commit -m "Add iOS testing CI workflow"
git push
```

**Workflow Features:**
- ✅ Automatic on push/PR to main/develop
- ✅ Runs minimal test matrix (fast feedback)
- ✅ Visual regression detection
- ✅ Network analysis
- ✅ Uploads test artifacts
- ✅ Posts results as PR comments
- ✅ Fails if visual regressions detected

**Customization:**

```yaml
# Run comprehensive tests on main branch only
- name: Run Test Matrix
  run: |
    cd testing
    if [ "${{ github.ref }}" == "refs/heads/main" ]; then
      ./scripts/run-matrix-tests.sh comprehensive
    else
      ./scripts/run-matrix-tests.sh minimal
    fi
```

---

### GitLab CI/CD

**Template Location:** `{{CATALYST_ROOT}}/templates/ci-cd/ios-testing-gitlab-ci.yml`

**Setup:**

1. **Copy configuration:**
```bash
cp ~/Catalyst/templates/ci-cd/ios-testing-gitlab-ci.yml \
   .gitlab-ci.yml
```

2. **Customize variables:**
```yaml
variables:
  SCHEME: "YourScheme"
  BUNDLE_ID: "com.your.app"
  SIMULATOR: "iPhone 16"
```

3. **Configure GitLab Runner:**

Ensure you have a macOS runner with tag `macos`:

```yaml
# .gitlab-ci.yml
tags:
  - macos
```

4. **Commit and push:**
```bash
git add .gitlab-ci.yml
git commit -m "Add iOS testing CI pipeline"
git push
```

**Pipeline Stages:**
1. **setup** - Install dependencies
2. **build** - Build app
3. **test** - Run test matrix (minimal for MRs, comprehensive for main)
4. **analyze** - Network analysis
5. **report** - Generate summary, check for regressions

**Artifacts:**
- Test results stored for 1 week (MRs) or 1 month (main)
- JUnit XML reports for GitLab test summary
- Visual diff reports
- Network analysis HTML reports

---

### Bitbucket Pipelines

**Template Location:** `{{CATALYST_ROOT}}/templates/ci-cd/ios-testing-bitbucket-pipelines.yml`

**Setup:**

1. **Copy configuration:**
```bash
cp ~/Catalyst/templates/ci-cd/ios-testing-bitbucket-pipelines.yml \
   bitbucket-pipelines.yml
```

2. **Update scheme/bundle ID:**
```yaml
- xcodebuild build
    -scheme YourScheme
    -destination 'platform=iOS Simulator,name=iPhone 16'
```

3. **Enable Pipelines:**
- Go to Repository Settings → Pipelines → Settings
- Enable Pipelines
- Select runner: macOS

4. **Commit and push:**
```bash
git add bitbucket-pipelines.yml
git commit -m "Add iOS testing pipeline"
git push
```

**Pipeline Configurations:**

**Default (all branches):**
- Build & Test (Minimal)
- Visual regression
- Network analysis

**Main branch:**
- Comprehensive testing
- Full pipeline validation

**Pull requests:**
- Quick validation (minimal tests)

**Custom pipelines:**
```bash
# Run accessibility tests manually
# Pipelines → Run custom → accessibility-test

# Run network tests manually
# Pipelines → Run custom → network-test
```

---

### CircleCI

**Template Location:** `{{CATALYST_ROOT}}/templates/ci-cd/ios-testing-circleci-config.yml`

**Setup:**

1. **Copy configuration:**
```bash
mkdir -p .circleci
cp ~/Catalyst/templates/ci-cd/ios-testing-circleci-config.yml \
   .circleci/config.yml
```

2. **Configure parameters:**
```yaml
parameters:
  scheme:
    type: string
    default: "YourScheme"
  bundle-id:
    type: string
    default: "com.your.app"
```

3. **Enable project in CircleCI:**
- Go to CircleCI dashboard
- Add Project
- Select your repository

4. **Commit and push:**
```bash
git add .circleci/config.yml
git commit -m "Add CircleCI iOS testing"
git push
```

**Workflows:**

**test-and-deploy:**
- Runs on every push
- build → test-minimal → visual-regression → network-analysis
- Comprehensive tests run on main/develop branches only

**nightly:**
- Scheduled cron job (midnight daily)
- Runs comprehensive tests on main branch
- Useful for catching regressions over time

**Jobs:**
- `build` - Compile app, cache dependencies
- `test-minimal` - Quick validation (6 configurations)
- `test-comprehensive` - Full matrix (120+ configurations)
- `visual-regression` - Compare screenshots, fail on regressions
- `network-analysis` - Analyze Pulse logs

---

### Jenkins

**Template Location:** `{{CATALYST_ROOT}}/templates/ci-cd/ios-testing-Jenkinsfile`

**Setup:**

1. **Copy Jenkinsfile:**
```bash
cp ~/Catalyst/templates/ci-cd/ios-testing-Jenkinsfile \
   Jenkinsfile
```

2. **Customize environment:**
```groovy
environment {
    SCHEME = 'YourScheme'
    BUNDLE_ID = 'com.your.app'
    SIMULATOR = 'iPhone 16'
}
```

3. **Configure Jenkins:**
- Create new Pipeline job
- Pipeline → Definition: "Pipeline script from SCM"
- SCM: Git
- Repository URL: your-repo-url
- Script Path: Jenkinsfile

4. **Install Jenkins plugins:**
- HTML Publisher Plugin (for reports)
- Git Plugin
- Pipeline Plugin

5. **Configure macOS node:**
```groovy
agent {
    label 'macos'  // Ensure you have macOS node with this label
}
```

6. **Commit and push:**
```bash
git add Jenkinsfile
git commit -m "Add Jenkins iOS testing pipeline"
git push
```

**Pipeline Parameters:**

Run pipeline with parameters:
- **TEST_PRESET**: minimal | accessibility | network | comprehensive
- **RUN_VISUAL_REGRESSION**: Enable/disable visual regression tests
- **RUN_NETWORK_ANALYSIS**: Enable/disable network analysis

**Stages:**
1. Setup - Install dependencies
2. Boot Simulator - Start iOS Simulator
3. Build - Compile app with xcodebuild
4. Test Matrix - Run selected preset
5. Visual Regression - Compare screenshots
6. Network Analysis - Analyze Pulse logs
7. Generate Summary - Create test report

**Reports:**
- Test Matrix Report (HTML)
- Visual Regression Report (HTML)
- Network Analysis Report (HTML)
- Archived artifacts for historical reference

---

## Common Configuration Patterns

### 1. Branch-Specific Testing

**Run minimal tests on feature branches, comprehensive on main:**

**GitHub Actions:**
```yaml
- name: Select Test Preset
  id: preset
  run: |
    if [[ "${{ github.ref }}" == "refs/heads/main" ]]; then
      echo "preset=comprehensive" >> $GITHUB_OUTPUT
    else
      echo "preset=minimal" >> $GITHUB_OUTPUT
    fi

- name: Run Tests
  run: |
    cd testing
    ./scripts/run-matrix-tests.sh ${{ steps.preset.outputs.preset }}
```

**GitLab CI:**
```yaml
test:minimal:
  only:
    - merge_requests
    - branches
  except:
    - main

test:comprehensive:
  only:
    - main
```

### 2. Visual Regression Failure Handling

**Fail pipeline if visual regressions exceed threshold:**

```bash
# In any CI platform
if [ -f testing/test-results/visual-diff-*/diff-results.json ]; then
  DIFF_COUNT=$(cat testing/test-results/visual-diff-*/diff-results.json | jq '.different')
  THRESHOLD=3  # Allow up to 3 minor differences

  if [ "$DIFF_COUNT" -gt "$THRESHOLD" ]; then
    echo "❌ $DIFF_COUNT visual regressions detected (threshold: $THRESHOLD)"
    exit 1
  else
    echo "✅ $DIFF_COUNT visual differences within threshold"
  fi
fi
```

### 3. Scheduled Comprehensive Testing

**Run full tests nightly:**

**GitHub Actions:**
```yaml
on:
  schedule:
    - cron: '0 0 * * *'  # Midnight UTC
  push:
    branches: [main]
```

**GitLab CI:**
```yaml
test:comprehensive:scheduled:
  only:
    - schedules
  script:
    - cd testing
    - ./scripts/run-comprehensive-pipeline.sh
```

**CircleCI:**
```yaml
workflows:
  nightly:
    triggers:
      - schedule:
          cron: "0 0 * * *"
          filters:
            branches:
              only: main
```

### 4. Parallel Test Execution

**Run multiple test configurations in parallel:**

**GitHub Actions:**
```yaml
strategy:
  matrix:
    preset: [minimal, accessibility, network]

steps:
  - name: Run ${{ matrix.preset }} tests
    run: |
      cd testing
      ./scripts/run-matrix-tests.sh ${{ matrix.preset }}
```

**GitLab CI:**
```yaml
.test_template: &test_template
  stage: test
  script:
    - cd testing
    - ./scripts/run-matrix-tests.sh $TEST_PRESET

test:minimal:
  <<: *test_template
  variables:
    TEST_PRESET: minimal

test:accessibility:
  <<: *test_template
  variables:
    TEST_PRESET: accessibility

test:network:
  <<: *test_template
  variables:
    TEST_PRESET: network
```

### 5. Artifact Retention

**Store test results for different durations:**

**GitHub Actions:**
```yaml
- uses: actions/upload-artifact@v3
  with:
    name: test-results-${{ github.sha }}
    path: testing/test-results/
    retention-days: 30  # Keep for 30 days
```

**GitLab CI:**
```yaml
artifacts:
  paths:
    - testing/test-results/
  expire_in: 1 month  # Main branch
  # OR
  expire_in: 1 week   # Feature branches
```

---

## Performance Optimization

### 1. Caching Dependencies

**Cache pip and gem packages:**

**GitHub Actions:**
```yaml
- uses: actions/cache@v3
  with:
    path: |
      ~/.cache/pip
      ~/.gem
    key: ${{ runner.os }}-deps-${{ hashFiles('**/Pipfile.lock', '**/Gemfile.lock') }}
```

**GitLab CI:**
```yaml
cache:
  paths:
    - ~/.cache/pip
    - ~/.gem
```

### 2. Incremental Builds

**Use xcodebuild's build cache:**

```bash
xcodebuild build \
  -scheme MyApp \
  -destination 'platform=iOS Simulator,name=iPhone 16' \
  -derivedDataPath ./build/DerivedData \
  -UseModernBuildSystem=YES
```

### 3. Simulator Boot Optimization

**Boot simulator before build:**

```bash
# Start simulator boot in background
xcrun simctl boot "iPhone 16" &
BOOT_PID=$!

# Build app while simulator boots
xcodebuild build -scheme MyApp ...

# Wait for simulator to finish booting
wait $BOOT_PID
```

### 4. Parallel Screenshot Capture

**Capture screenshots in parallel (if testing multiple simulators):**

```bash
# Example: Test on iPhone 16 and iPad Pro simultaneously
xcrun simctl boot "iPhone 16" &
xcrun simctl boot "iPad Pro (12.9-inch)" &
wait

# Run tests in parallel
./scripts/run-matrix-tests.sh minimal --simulator "iPhone 16" &
./scripts/run-matrix-tests.sh minimal --simulator "iPad Pro (12.9-inch)" &
wait
```

---

## Troubleshooting

### Problem: "No booted simulators found"

**Solution:**
```yaml
# Ensure simulator boots successfully
- name: Boot Simulator
  run: |
    xcrun simctl boot "iPhone 16" || true
    sleep 10

    # Verify simulator is booted
    xcrun simctl list devices | grep Booted
```

### Problem: "Dependencies not installed"

**Solution:**
```yaml
# Use absolute paths and check Python/Ruby versions
- name: Install Dependencies
  run: |
    which python3
    which gem
    python3 --version
    gem --version

    pip3 install Pillow numpy
    gem install json
```

### Problem: "Visual diff fails with 'baseline not found'"

**Solution:**

1. Ensure baseline screenshots are committed:
```bash
git add testing/baseline-screenshots/
git commit -m "Add baseline screenshots"
```

2. Or create baselines in CI first run:
```yaml
- name: Setup Baselines
  run: |
    cd testing
    if [ ! -d baseline-screenshots ] || [ -z "$(ls -A baseline-screenshots)" ]; then
      echo "Creating baseline screenshots"
      ./scripts/capture-baseline.sh
      git config user.email "ci@example.com"
      git config user.name "CI Bot"
      git add baseline-screenshots/
      git commit -m "Create baseline screenshots [skip ci]"
      git push
    fi
```

### Problem: "Pulse database not found"

**Solution:**

1. Verify Pulse is integrated (check PULSE_SETUP.md)
2. Ensure app makes network requests during tests
3. Skip network analysis if no Pulse:
```bash
./scripts/analyze-network.sh || true
```

### Problem: "Tests timeout on CI"

**Solution:**

1. Use minimal preset for PRs:
```yaml
# Only run comprehensive on main branch
if: github.ref == 'refs/heads/main'
run: ./scripts/run-matrix-tests.sh comprehensive

# Use minimal for PRs
if: github.event_name == 'pull_request'
run: ./scripts/run-matrix-tests.sh minimal
```

2. Increase timeout:
```yaml
- name: Run Tests
  timeout-minutes: 30  # Default is 360 (6 hours)
```

### Problem: "Artifacts not uploading"

**Solution:**

Verify paths exist before upload:
```yaml
- name: Upload Test Results
  if: always()
  uses: actions/upload-artifact@v3
  with:
    name: test-results
    path: testing/test-results/
    if-no-files-found: warn  # Don't fail if no results
```

---

## Best Practices

### 1. Test Strategy by Branch

**Feature branches:**
- ✅ Minimal preset (fast feedback)
- ✅ Visual regression (catch UI breaks)
- ⏭️ Skip comprehensive tests (too slow)

**Main/develop branches:**
- ✅ Comprehensive preset (full validation)
- ✅ All analysis tools enabled
- ✅ Archive results long-term

**Release branches:**
- ✅ Comprehensive + accessibility
- ✅ Multiple simulators/devices
- ✅ Performance benchmarks

### 2. Baseline Management

**When to update baselines:**
- ✅ Approved UI changes
- ✅ Design system updates
- ✅ iOS version upgrades

**How to update:**
```bash
# Capture new baselines locally
cd testing
./scripts/capture-baseline.sh

# Review changes
./scripts/run-visual-diff.sh
open test-results/visual-diff-*/report.html

# If approved, commit new baselines
git add baseline-screenshots/
git commit -m "Update baseline screenshots for [reason]"
git push
```

### 3. Notification Strategy

**GitHub Actions - Slack notifications:**
```yaml
- name: Notify Slack on Failure
  if: failure()
  uses: slackapi/slack-github-action@v1
  with:
    payload: |
      {
        "text": "iOS Tests Failed - ${{ github.repository }}",
        "blocks": [
          {
            "type": "section",
            "text": {
              "type": "mrkdwn",
              "text": "❌ *iOS Testing Pipeline Failed*\n*Branch:* ${{ github.ref }}\n*Commit:* ${{ github.sha }}"
            }
          }
        ]
      }
  env:
    SLACK_WEBHOOK_URL: ${{ secrets.SLACK_WEBHOOK }}
```

### 4. Security

**Protect sensitive data:**
```yaml
# Never log credentials
- name: Analyze Network
  env:
    BUNDLE_ID: ${{ secrets.APP_BUNDLE_ID }}  # Use secrets
  run: |
    # Don't echo $BUNDLE_ID
    ruby tools/pulse_log_export.rb analyze --app-id "$BUNDLE_ID"
```

**Use environment protection:**
- GitHub: Settings → Environments → Required reviewers
- GitLab: Settings → CI/CD → Protected environments
- Jenkins: Folder-level credentials

---

## Summary

All iOS Testing Framework tools are CI/CD ready:

| Platform | Template | Key Features |
|----------|----------|--------------|
| **GitHub Actions** | `ios-testing-github-actions.yml` | PR comments, artifact storage, branch protection |
| **GitLab CI** | `ios-testing-gitlab-ci.yml` | Pipeline stages, scheduled jobs, merge request integration |
| **Bitbucket** | `ios-testing-bitbucket-pipelines.yml` | Custom pipelines, branch-specific configs |
| **CircleCI** | `ios-testing-circleci-config.yml` | Workflows, scheduled cron, artifact storage |
| **Jenkins** | `ios-testing-Jenkinsfile` | HTML reports, parameterized builds, post-build actions |

**Next Steps:**

1. Choose your CI/CD platform
2. Copy appropriate template from `{{CATALYST_ROOT}}/templates/ci-cd/`
3. Customize scheme, bundle ID, and simulator
4. Commit configuration file
5. Push to repository
6. Watch tests run automatically!

**Documentation:**
- Testing Framework: `{{CATALYST_ROOT}}/docs/ADVANCED_IOS_TESTING.md`
- Setup Script: `{{CATALYST_ROOT}}/tools/setup_ios_testing.sh`
- Pulse Integration: `{{CATALYST_ROOT}}/tools/add_pulse_to_app.sh`

---

*iOS Testing CI/CD Integration Guide - Catalyst*
*All CI/CD templates ready for immediate use*
