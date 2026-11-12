# Catalyst Portal Menu Bar

A native macOS menu bar app for visual control of Catalyst Portal services.

## Features

- **Real-time Service Monitoring**: Displays status of all portal services with live updates every 5 seconds
- **Core Services**: Always-on services (Caddy, Agent API, Bifrost, Claude Router)
- **Dev Services**: On-demand services (Vite Portal, Plasmic Backend, Plasmic Frontend) with idle timer
- **Quick Actions**: Start/stop services, view logs, open portal, PM2 monitor
- **Visual Status Indicators**:
  - ✅ Green: Running (online)
  - ❌ Red: Failed/Errored
  - ⚠️ Yellow: Restarting/Unstable (>5 restarts)
  - ⏸️ Gray: Stopped
  - 🔄 Spinner: Starting
- **Memory Usage**: Real-time memory consumption for each service
- **Idle Timer**: Progress bar showing dev services idle time (auto-shutdown at 30 min)

## Installation

### Prerequisites

- macOS 13.0 or later
- PM2 installed at `{{HOME_DIR}}/.npm-global/bin/pm2`
- Catalyst tools installed at `{{CATALYST_ROOT}}/tools/`
- Portal services configured in PM2

### Building from Source

```bash
cd {{CATALYST_ROOT}}/tools/CatalystPortalMenuBar

# Build Release version
xcodebuild -project CatalystPortalMenuBar.xcodeproj \
           -scheme CatalystPortalMenuBar \
           -configuration Release \
           build

# Copy to build directory (already done)
# Output: build/Release/CatalystPortalMenuBar.app
```

### Launch the App

```bash
# Open manually
open {{CATALYST_ROOT}}/tools/CatalystPortalMenuBar/build/Release/CatalystPortalMenuBar.app

# Or from anywhere (if in Applications folder)
open -a CatalystPortalMenuBar
```

## Auto-Launch on Login

### Method 1: System Settings (Recommended)

1. Open **System Settings** → **General** → **Login Items**
2. Click the **+** button under "Open at Login"
3. Navigate to and select:
   ```
   {{CATALYST_ROOT}}/tools/CatalystPortalMenuBar/build/Release/CatalystPortalMenuBar.app
   ```
4. Click **Add**

### Method 2: Create Launch Agent (Advanced)

Create a launch agent plist:

```bash
cat > ~/Library/LaunchAgents/com.builderos.portal-menu-bar.plist << 'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.builderos.portal-menu-bar</string>
    <key>ProgramArguments</key>
    <array>
        <string>{{CATALYST_ROOT}}/tools/CatalystPortalMenuBar/build/Release/CatalystPortalMenuBar.app/Contents/MacOS/CatalystPortalMenuBar</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <false/>
</dict>
</plist>
EOF

# Load the launch agent
launchctl load ~/Library/LaunchAgents/com.builderos.portal-menu-bar.plist
```

## Usage

### Menu Bar Icon

The menu bar icon shows overall service health:
- **Green Circle**: All core services running
- **Yellow Warning**: Some services down
- **Red X**: Core services failed
- **Gray Question**: Status unknown

Click the icon to open the dropdown menu.

### Dropdown Menu Sections

#### 1. Core Services
- Displays: Caddy (443), Agent API (8080), Bifrost Gateway (8083), Claude Router (3456)
- Shows: Status emoji, service name, port, memory usage
- Actions: Click ellipsis (•••) for Start/Stop/Restart/View Logs

#### 2. Dev Services (On-Demand)
- Displays: Vite Portal (5174), Plasmic Backend (3004), Plasmic Frontend (3003)
- Shows: Idle timer progress bar (30-minute auto-shutdown)
- Actions:
  - **Start Dev Services**: Starts all dev services
  - **Stop Dev Services**: Stops all dev services
  - Individual service actions via ellipsis menu

#### 3. Quick Actions
- **View All Logs**: Opens Terminal with `pm2 logs`
- **Open Portal**: Opens https://bldr.portal.localhost in browser
- **PM2 Monitor**: Opens Terminal with `pm2 monit`
- **Quit App**: Closes the menu bar app

### Keyboard Shortcuts

All Terminal windows opened by the app can use standard PM2 keyboard shortcuts:
- `Ctrl+C`: Stop log streaming
- `Cmd+K`: Clear Terminal

## Technical Details

### Technology Stack
- **Language**: Swift 6.0
- **Frameworks**: SwiftUI, AppKit, Combine
- **Minimum macOS**: 13.0 (Ventura)
- **Architecture**: arm64 (Apple Silicon)

### Project Structure
```
CatalystPortalMenuBar/
├── CatalystPortalMenuBar.xcodeproj   # Xcode project (linked files)
├── CatalystPortalMenuBar/
│   ├── CatalystPortalMenuBarApp.swift  # App entry point
│   ├── MenuBarController.swift          # Menu bar management
│   ├── StatusBarView.swift              # Dropdown menu UI
│   ├── PM2Manager.swift                 # PM2 integration
│   ├── ServiceStatus.swift              # Data models
│   ├── IdleTimerView.swift              # Idle timer UI
│   ├── Info.plist                       # App configuration
│   └── Assets.xcassets/                 # App icons
├── build/
│   └── Release/
│       └── CatalystPortalMenuBar.app   # Built application
└── README.md
```

### PM2 Integration

The app executes PM2 commands at `{{HOME_DIR}}/.npm-global/bin/pm2`:

**Status Query:**
```bash
pm2 jlist
```

**Service Control:**
```bash
pm2 start <service-name>
pm2 stop <service-name>
pm2 restart <service-name>
```

**Dev Services (via builderos CLI):**
```bash
{{CATALYST_ROOT}}/tools/builderos start-dev
{{CATALYST_ROOT}}/tools/builderos stop-dev
```

**Idle Timer:**
Reads last activity from: `/tmp/builderos/dev-services-last-activity`

### Memory Usage

- **App Memory**: < 50 MB RAM
- **CPU Usage**: < 1% (during 5-second polling)
- **Performance**: Lightweight polling with minimal system impact

## Troubleshooting

### App Won't Launch
```bash
# Check if app exists
ls -la {{CATALYST_ROOT}}/tools/CatalystPortalMenuBar/build/Release/CatalystPortalMenuBar.app

# Check for running instances
ps aux | grep CatalystPortalMenuBar | grep -v grep

# Kill existing instances
killall CatalystPortalMenuBar
```

### Services Not Showing
```bash
# Verify PM2 is installed
which pm2
# Should output: {{HOME_DIR}}/.npm-global/bin/pm2

# Check PM2 services manually
pm2 jlist
pm2 status
```

### Menu Bar Icon Missing
- The app runs as a menu bar-only app (no dock icon)
- Look for the icon in the top-right menu bar
- If not visible, check Activity Monitor for running process

### Logs Not Opening
- Ensure Terminal.app has permissions
- Check System Settings → Privacy & Security → Automation
- Allow CatalystPortalMenuBar to control Terminal

### Dev Services Idle Timer Not Working
```bash
# Check if idle timer file exists
cat /tmp/builderos/dev-services-last-activity

# If missing, create manually (Phase 2 should create this)
mkdir -p /tmp/builderos
date +%s > /tmp/builderos/dev-services-last-activity
```

## Development

### Rebuilding
```bash
cd {{CATALYST_ROOT}}/tools/CatalystPortalMenuBar

# Clean build
xcodebuild -project CatalystPortalMenuBar.xcodeproj \
           -scheme CatalystPortalMenuBar \
           -configuration Release \
           clean build

# Copy to build directory
rm -rf build/Release/CatalystPortalMenuBar.app
cp -R ~/Library/Developer/Xcode/DerivedData/CatalystPortalMenuBar-*/Build/Products/Release/CatalystPortalMenuBar.app \
   build/Release/
```

### Modifying the App
All source files are **linked** (not copied) in the Xcode project. You can edit in:
- Xcode
- Cursor
- Any text editor

Changes sync immediately across all editors.

### Adding Features
1. Edit Swift files in `CatalystPortalMenuBar/` directory
2. Rebuild with `xcodebuild`
3. Relaunch the app

## Phase 3 Integration

This menu bar app is **Phase 3** of the Catalyst Portal orchestration:

- **Phase 1**: Core services auto-start via PM2 on login
- **Phase 2**: Dev services on-demand with auto-shutdown
- **Phase 3**: Visual control and monitoring (this app)

See Phase 1 & 2 documentation for full portal setup.

## License

Part of Catalyst internal tools.

## Support

For issues or feature requests, contact the Catalyst team.

---

**Version**: 1.0
**Build Date**: 2025-11-06
**Minimum macOS**: 13.0 (Ventura)
