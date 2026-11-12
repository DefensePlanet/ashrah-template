#!/bin/bash
"""
Setup MCP Auto-Update Service - Creates launchd service for automatic MCP updates
Similar to iOS/macOS automatic app updates
"""

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BUILDER_ROOT="{{CATALYST_ROOT}}"
PLIST_FILE="{{HOME_DIR}}/Library/LaunchAgents/com.builder.mcp-auto-updater.plist"

echo "Setting up MCP Auto-Update Service..."

# Create LaunchAgent plist
cat > "$PLIST_FILE" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.builder.mcp-auto-updater</string>
    
    <key>ProgramArguments</key>
    <array>
        <string>/usr/bin/python3</string>
        <string>${BUILDER_ROOT}/tools/mcp_auto_updater.py</string>
    </array>
    
    <key>WorkingDirectory</key>
    <string>${BUILDER_ROOT}</string>
    
    <key>StartInterval</key>
    <integer>604800</integer> <!-- 1 week -->
    
    <key>RunAtLoad</key>
    <true/>
    
    <key>StandardOutPath</key>
    <string>${BUILDER_ROOT}/logs/mcp_auto_updater.out.log</string>
    
    <key>StandardErrorPath</key>
    <string>${BUILDER_ROOT}/logs/mcp_auto_updater.err.log</string>
    
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/usr/local/bin:/usr/bin:/bin:/opt/homebrew/bin</string>
        <key>NODE_PATH</key>
        <string>/usr/local/lib/node_modules</string>
    </dict>
    
    <key>ProcessType</key>
    <string>Background</string>
    
    <key>LowPriorityIO</key>
    <true/>
    
    <key>Nice</key>
    <integer>10</integer>
</dict>
</plist>
EOF

# Create log directory
mkdir -p "${BUILDER_ROOT}/logs"

# Load the service
launchctl unload "$PLIST_FILE" 2>/dev/null || true
launchctl load "$PLIST_FILE"

if [ $? -eq 0 ]; then
    echo "✅ MCP Auto-Update Service installed successfully"
    echo "   - Service: com.builder.mcp-auto-updater"
    echo "   - Frequency: Weekly"
    echo "   - Logs: ${BUILDER_ROOT}/logs/mcp_auto_updater.*.log"
    echo ""
    echo "Service commands:"
    echo "  Start:  launchctl start com.builder.mcp-auto-updater"
    echo "  Stop:   launchctl stop com.builder.mcp-auto-updater"
    echo "  Status: launchctl list | grep mcp-auto-updater"
    echo "  Logs:   tail -f ${BUILDER_ROOT}/logs/mcp_auto_updater.out.log"
else
    echo "❌ Failed to install MCP Auto-Update Service"
    exit 1
fi

# Install required Python dependencies
echo "Installing Python dependencies..."
pip3 install --user requests semver

echo ""
echo "MCP Auto-Update Service is now running automatically weekly."
echo "It will check GitHub repositories and NPM packages for updates and apply them automatically."