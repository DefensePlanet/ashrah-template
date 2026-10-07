#!/bin/bash
# Bootstrap a fresh Mac for Catalyst + {{ORCHESTRATOR_NAME}} (Claude Code).
# Paste into Terminal on the new Mac. Prompts: your Mac password (Homebrew), GitHub login in the browser, Claude login in the browser.
set -e

if ! command -v brew >/dev/null 2>&1; then
  /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
fi
eval "$(/opt/homebrew/bin/brew shellenv)"

brew install gh git
brew install --cask claude-code

gh auth status >/dev/null 2>&1 || gh auth login -h github.com -p https -w
# the repo is being renamed catalyst-os -> {{ORCHESTRATOR_NAME_LOWER}} (Oct 2026); take whichever exists
if [ ! -d ~/catalyst-os ]; then
  if gh repo view {{GITHUB_USER}}/{{ORCHESTRATOR_NAME_LOWER}} >/dev/null 2>&1; then
    gh repo clone {{GITHUB_USER}}/{{ORCHESTRATOR_NAME_LOWER}} ~/catalyst-os
  else
    gh repo clone {{GITHUB_USER}}/catalyst-os ~/catalyst-os
  fi
fi

grep -q 'alias {{ORCHESTRATOR_NAME_LOWER}}=' ~/.zshrc 2>/dev/null || cat >> ~/.zshrc <<'EOF'

eval "$(/opt/homebrew/bin/brew shellenv)"
# Launch Catalyst with {{ORCHESTRATOR_NAME}}
alias {{ORCHESTRATOR_NAME_LOWER}}='cd ~/catalyst-os && claude'
EOF

# {{ORCHESTRATOR_NAME}}'s memory + settings arrive separately as ~/Downloads/{{ORCHESTRATOR_NAME_LOWER}}-bundle.tgz (AirDrop from the Pro)
[ -f ~/Downloads/{{ORCHESTRATOR_NAME_LOWER}}-bundle.tgz ] && tar -xzf ~/Downloads/{{ORCHESTRATOR_NAME_LOWER}}-bundle.tgz -C ~ && echo "{{ORCHESTRATOR_NAME}} bundle installed"

echo
echo "Done. Close this Terminal window, open a new one, and type:  {{ORCHESTRATOR_NAME_LOWER}}"
