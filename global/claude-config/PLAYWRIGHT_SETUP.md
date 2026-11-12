# Playwright MCP Configuration for Claude Code

## Overview
Successfully configured Playwright MCP to work with Chromium and Brave browsers for Claude Code integration.

## ✅ Working Configurations

### 1. Chrome/Chromium Support
**MCP Server Configuration:**
```json
{
  "mcpServers": {
    "playwright": {
      "command": "node",
      "args": ["{{HOME_DIR}}/playwright-mcp/cli.js"],
      "env": {
        "PLAYWRIGHT_MCP_BROWSER": "chrome",
        "PLAYWRIGHT_MCP_HEADLESS": "false"
      }
    }
  }
}
```

**CLI Usage:**
```bash
# Chrome
node {{HOME_DIR}}/playwright-mcp/cli.js --browser chrome --config {{HOME_DIR}}/.claude/playwright-mcp-config.json

# Chromium
node {{HOME_DIR}}/playwright-mcp/cli.js --browser chromium --config {{HOME_DIR}}/.claude/playwright-mcp-config.json
```

### 2. Brave Browser Support
**MCP Server Configuration:**
```json
{
  "mcpServers": {
    "playwright-brave": {
      "command": "node",
      "args": [
        "{{HOME_DIR}}/playwright-mcp/cli.js",
        "--browser", "chromium",
        "--executable-path", "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser"
      ],
      "env": {
        "PLAYWRIGHT_MCP_BROWSER": "chromium",
        "PLAYWRIGHT_MCP_EXECUTABLE_PATH": "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser",
        "PLAYWRIGHT_MCP_HEADLESS": "false"
      }
    }
  }
}
```

**CLI Usage:**
```bash
node {{HOME_DIR}}/playwright-mcp/cli.js --browser chromium --executable-path "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser" --config {{HOME_DIR}}/.claude/playwright-brave-config.json
```

## 📁 Configuration Files

### Chrome/Chromium Config (`{{HOME_DIR}}/.claude/playwright-mcp-config.json`)
```json
{
  "browser": {
    "browserName": "chromium",
    "launchOptions": {
      "headless": false,
      "chromiumSandbox": true,
      "channel": "chrome"
    },
    "contextOptions": {
      "viewport": { "width": 1280, "height": 720 },
      "ignoreHTTPSErrors": false
    }
  },
  "network": {
    "allowedOrigins": [],
    "blockedOrigins": []
  },
  "server": {
    "port": 3000,
    "host": "localhost"
  },
  "outputDir": "/tmp/playwright-mcp-output",
  "saveTrace": true,
  "saveSession": false,
  "imageResponses": "allow"
}
```

### Brave Config (`{{HOME_DIR}}/.claude/playwright-brave-config.json`)
```json
{
  "browser": {
    "browserName": "chromium",
    "launchOptions": {
      "headless": false,
      "chromiumSandbox": true,
      "executablePath": "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser"
    },
    "contextOptions": {
      "viewport": { "width": 1280, "height": 720 },
      "ignoreHTTPSErrors": false
    }
  },
  "network": {
    "allowedOrigins": [],
    "blockedOrigins": []
  },
  "server": {
    "port": 3001,
    "host": "localhost"
  },
  "outputDir": "/tmp/playwright-mcp-brave-output",
  "saveTrace": true,
  "saveSession": false,
  "imageResponses": "allow"
}
```

## 🚀 Usage with Claude Code

### Environment Variables
```bash
# Chrome/Chromium
export PLAYWRIGHT_MCP_BROWSER=chrome
export PLAYWRIGHT_MCP_HEADLESS=false

# Brave Browser
export PLAYWRIGHT_MCP_BROWSER=chromium
export PLAYWRIGHT_MCP_EXECUTABLE_PATH="/Applications/Brave Browser.app/Contents/MacOS/Brave Browser"
export PLAYWRIGHT_MCP_HEADLESS=false
```

### Available CLI Options
- `--browser <browser>`: chrome, firefox, webkit, msedge, chromium
- `--executable-path <path>`: Custom browser executable path
- `--headless`: Run in headless mode
- `--config <path>`: Configuration file path
- `--device <device>`: Device emulation (e.g., "iPhone 15")
- `--viewport-size <size>`: Browser viewport (e.g., "1280,720")
- `--user-agent <ua>`: Custom user agent
- `--proxy-server <proxy>`: Proxy configuration
- `--save-trace`: Save Playwright traces
- `--save-session`: Save browser session

## ✅ Test Results
All configurations tested successfully:
- ✅ Chrome (Chromium): Started successfully
- ✅ Chromium: Started successfully  
- ✅ Brave Browser: Started successfully

## 🔧 Troubleshooting

### Common Issues
1. **Module not found**: Run `npm run build` in `{{HOME_DIR}}/playwright-mcp/`
2. **Browser not found**: Verify executable path for Brave
3. **Port conflicts**: Use different ports for multiple instances

### Verification
Run the test script to verify all configurations:
```bash
cd {{HOME_DIR}}/.claude && node test-playwright-browsers.js
```

## 📚 Additional Resources
- Playwright MCP Documentation: `{{HOME_DIR}}/playwright-mcp/README.md`
- Playwright Official Docs: https://playwright.dev
- MCP Protocol: https://modelcontextprotocol.com