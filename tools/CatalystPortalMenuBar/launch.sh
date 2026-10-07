#!/bin/bash
# Catalyst Portal Menu Bar - Launch Script

APP_PATH="{{CATALYST_ROOT}}/tools/CatalystPortalMenuBar/build/Release/CatalystPortalMenuBar.app"

# Check if app exists
if [ ! -d "$APP_PATH" ]; then
    echo "❌ App not found at: $APP_PATH"
    echo "Run: xcodebuild -project CatalystPortalMenuBar.xcodeproj -scheme CatalystPortalMenuBar -configuration Release build"
    exit 1
fi

# Check if already running
if pgrep -f "CatalystPortalMenuBar.app" > /dev/null; then
    echo "✅ Catalyst Portal Menu Bar is already running"
    echo "Look for the icon in your menu bar (top-right)"
    exit 0
fi

# Launch the app
echo "🚀 Launching Catalyst Portal Menu Bar..."
open -a "$APP_PATH"

# Wait and verify
sleep 2
if pgrep -f "CatalystPortalMenuBar.app" > /dev/null; then
    echo "✅ App launched successfully!"
    echo "Look for the icon in your menu bar (top-right)"
else
    echo "❌ Failed to launch app"
    echo "Try running manually: open -a \"$APP_PATH\""
    exit 1
fi
