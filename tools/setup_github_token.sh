#!/bin/bash

# GitHub Token Setup for Catalyst MCP
# Usage: ./setup_github_token.sh <your_github_token>

if [ $# -eq 0 ]; then
    echo "Usage: $0 <github_token>"
    echo "Example: $0 ghp_xxxxxxxxxxxxxxxxxxxx"
    exit 1
fi

TOKEN=$1

# Add to shell profile for persistence
SHELL_PROFILE=""
if [ -f ~/.zshrc ]; then
    SHELL_PROFILE=~/.zshrc
elif [ -f ~/.bashrc ]; then
    SHELL_PROFILE=~/.bashrc
elif [ -f ~/.bash_profile ]; then
    SHELL_PROFILE=~/.bash_profile
fi

if [ -n "$SHELL_PROFILE" ]; then
    # Check if GITHUB_TOKEN is already in the profile
    if ! grep -q "export GITHUB_TOKEN=" "$SHELL_PROFILE"; then
        echo "" >> "$SHELL_PROFILE"
        echo "# GitHub Token for Catalyst MCP" >> "$SHELL_PROFILE"
        echo "export GITHUB_TOKEN=\"$TOKEN\"" >> "$SHELL_PROFILE"
        echo "✅ Added GITHUB_TOKEN to $SHELL_PROFILE"
    else
        # Update existing token
        sed -i.bak "s/export GITHUB_TOKEN=.*/export GITHUB_TOKEN=\"$TOKEN\"/" "$SHELL_PROFILE"
        echo "✅ Updated GITHUB_TOKEN in $SHELL_PROFILE"
    fi
fi

# Set for current session
export GITHUB_TOKEN="$TOKEN"
echo "✅ GITHUB_TOKEN set for current session"

# Verify token works
echo "🔍 Verifying token..."
if curl -s -H "Authorization: Bearer $TOKEN" https://api.github.com/user | grep -q "login"; then
    echo "✅ GitHub token is valid!"
    
    # Test the MCP server
    echo "🧪 Testing GitHub MCP server..."
    timeout 10 docker run --rm -e "GITHUB_PERSONAL_ACCESS_TOKEN=$TOKEN" ghcr.io/github/github-mcp-server:latest --help 2>/dev/null
    if [ $? -eq 0 ]; then
        echo "✅ GitHub MCP server is ready!"
    else
        echo "⚠️  GitHub MCP server needs Docker image pull (will happen automatically)"
    fi
else
    echo "❌ GitHub token verification failed. Please check the token."
    exit 1
fi

echo ""
echo "🚀 Setup complete! Restart your shell or Claude Code to use the new token."
echo "   Source your profile: source $SHELL_PROFILE"