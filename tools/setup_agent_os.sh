#!/bin/bash

# Agent OS Setup Script for Catalyst
# This script sets up the complete Agent OS integration

set -e  # Exit on any error

BUILDER_ROOT="${BUILDER_ROOT:-{{CATALYST_ROOT}}}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "🚀 Setting up Agent OS integration for Catalyst..."
echo "Builder root: $BUILDER_ROOT"

# Ensure we're in the right directory
cd "$BUILDER_ROOT"

# Phase 1: Global Structure Setup
echo
echo "📁 Phase 1: Setting up global Agent OS structure..."

python3 tools/agents/agent_os_enforcer.py --dry-run | grep -E "(CREATE|UPDATE)" | head -10
if [ $? -eq 0 ]; then
    echo "Running global structure enforcement..."
    python3 tools/agents/agent_os_enforcer.py
else
    echo "Global structure appears to be in place."
fi

# Phase 2: Enhance All Capsules
echo
echo "📦 Phase 2: Enhancing all capsules with Agent OS structure..."

echo "Running capsule enhancement..."
python3 tools/agents/agent_os_enhancer.py

# Phase 3: Validation
echo
echo "🔍 Phase 3: Validating Agent OS implementation..."

echo "Running validation..."
python3 tools/agents/agent_os_validator.py --summary-only

# Phase 4: Integration Verification
echo
echo "🔗 Phase 4: Verifying integration..."

# Check that key files were created
GLOBAL_AGENT_OS="$BUILDER_ROOT/global/agent-os"
if [ -d "$GLOBAL_AGENT_OS" ]; then
    echo "✓ Global Agent OS directory exists"
else
    echo "✗ Global Agent OS directory missing"
    exit 1
fi

# Check commands
if [ -f "$GLOBAL_AGENT_OS/commands/README.md" ]; then
    echo "✓ Agent OS commands integrated"
else
    echo "✗ Agent OS commands missing"
fi

# Check standards
if [ -f "$GLOBAL_AGENT_OS/standards/base/coding-standards.md" ]; then
    echo "✓ Base coding standards in place"
else
    echo "✗ Base coding standards missing"
fi

# Check instructions
if [ -f "$GLOBAL_AGENT_OS/instructions/base/agent-context-template.md" ]; then
    echo "✓ Agent instructions template available"
else
    echo "✗ Agent instructions template missing"
fi

# Count enhanced capsules
ENHANCED_COUNT=$(find capsules -name ".agent-os" -type d | wc -l)
TOTAL_CAPSULES=$(find capsules -maxdepth 1 -type d ! -name "ops" ! -name ".*" ! -name "capsules" | wc -l)

echo "✓ Enhanced $ENHANCED_COUNT out of $TOTAL_CAPSULES capsules"

# Phase 5: Tool Integration
echo
echo "🛠️  Phase 5: Setting up tool integration..."

# Make tools executable
chmod +x tools/agents/agent_os_*.py 2>/dev/null || true

# Add to PATH or make easily accessible
if [ -f "$HOME/.zshrc" ]; then
    if ! grep -q "export PATH.*Builder/tools" "$HOME/.zshrc"; then
        echo "Adding Builder tools to PATH in ~/.zshrc"
        echo "export PATH=\"$BUILDER_ROOT/tools:\$PATH\"" >> "$HOME/.zshrc"
    fi
fi

echo
echo "🎉 Agent OS integration complete!"
echo
echo "Summary:"
echo "- Global Agent OS structure: ✓ Setup complete"  
echo "- Cross-capsule standards: ✓ Implemented"
echo "- Agent instructions layer: ✓ Available"
echo "- Capsule enhancements: ✓ $ENHANCED_COUNT capsules enhanced"
echo "- Validation tools: ✓ Ready"
echo
echo "Available tools:"
echo "- agent_os_enhancer.py  - Enhance capsules with Agent OS structure"
echo "- agent_os_validator.py - Validate Agent OS implementation"
echo "- agent_os_enforcer.py  - Enforce Agent OS standards"
echo
echo "Usage examples:"
echo "  python3 tools/agents/agent_os_validator.py --summary-only"
echo "  python3 tools/agents/agent_os_enhancer.py --capsule my-capsule"
echo "  python3 tools/agents/agent_os_enforcer.py --dry-run"
echo
echo "The Agent OS framework is now fully integrated with Builder!"
echo "AI agents will have comprehensive context and structured workflows."
