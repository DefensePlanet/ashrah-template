# @catalyst/react-grab

AI-powered element selection and modification tool for React applications. Click any element, send a prompt to your AI assistant with full component context. A customized tool merging features from the original [React Grab](https://github.com/user/react-grab) repository and [Cleo.build](https://cleo.build) AI element selection tool.

## Features

- **Zero Configuration** - Just add the Vite plugin, browser UI auto-injects
- **No Chrome Extension Required** - Works automatically in dev mode
- **Element Selection** - Click on any element with crosshairs targeting
- **Component Labels** - See React component names as you hover
- **Multi-Element Selection** - Shift+click or drag a selection box
- **Tree Navigation** - Use arrow keys to navigate the component hierarchy
- **AI Prompt Panel** - Send modification requests to Claude Code CLI
- **Conversation Mode** - Maintain context across multiple requests
- **Screenshot Support** - Attach screenshots for visual context
- **Copy to Clipboard** - Copy element info (component name, file path, HTML)
- **Export to JSON** - Export selected elements for external tools

## Quick Start (Auto-Injection)

The simplest way to use react-grab - just add the plugin:

### 1. Add the Vite Plugin

```typescript
// vite.config.ts
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { reactGrabVitePlugin } from '@catalyst/react-grab/vite'

export default defineConfig({
  plugins: [
    react(),
    reactGrabVitePlugin(), // That's it! Browser UI auto-injects
  ],
})
```

### 2. Run Your Dev Server

```bash
npm run dev
```

That's it! React Grab will automatically appear in the bottom-right corner of your app. No Chrome extension, no manual imports needed.

## Activation

1. **Click the cursor button** in the bottom-right corner (dark when inactive, orange when active)
2. **Click on any element** to open the prompt panel
3. Or use **Cmd+Shift+Z** (Mac) / **Ctrl+Shift+Z** (Windows/Linux) when hovering over an element

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Cmd/Ctrl + Shift + Z` | Toggle grab mode while hovering |
| `Escape` | Exit grab mode / Close prompt panel |
| `Shift + Click` | Add element to multi-selection |
| `Click + Drag` | Box select multiple elements |
| `↑` / `↓` | Navigate to parent/child in component tree |
| `←` / `→` | Navigate to previous/next sibling |
| `Enter` | Submit prompt (when panel is open) |
| `Cmd/Ctrl + E` | Show export panel |

## How It Works

### Auto-Injection (Default)

1. **Vite Plugin** uses `transformIndexHtml` to inject the browser UI script
2. **Browser UI** (~61KB minified) renders toolbar and selection overlay
3. **Element Selection** extracts React component info via React DevTools fiber
4. **API Endpoint** (`/api/grab-prompt`) receives selections
5. **Claude Code CLI** gets full context and makes requested modifications

### API Endpoints

The Vite plugin provides these dev server endpoints:

- `POST /api/grab-prompt` - Send single prompt
- `POST /api/grab-conversation` - Send prompt with conversation continuity
- `POST /api/grab-cleanup` - Clean up temp files on browser close

## Configuration

### Vite Plugin Options

```typescript
reactGrabVitePlugin({
  // Path to your project (for Claude CLI context)
  projectPath: process.cwd(),

  // Path to Claude CLI (auto-detected from ~/.local/bin/claude or /usr/local/bin/claude)
  claudePath: '/path/to/claude',

  // Enable debug logging
  debug: false,

  // Disable auto-injection (if you want manual control)
  disableAutoInject: false,
})
```

### Environment Variable Configuration

```bash
# In your .env.local file:

# For Claude Code users (default):
# No configuration needed, or explicitly set:
REACT_GRAB_CLI_PATH=/Users/yourname/.local/bin/claude

# For Cursor users:
REACT_GRAB_CLI_PATH=/path/to/cursor

# For other AI CLI tools:
REACT_GRAB_CLI_PATH=/path/to/your/ai-cli
```

**Priority order:**
1. `claudePath` option in vite.config.ts
2. `REACT_GRAB_CLI_PATH` environment variable
3. Auto-detect from `~/.local/bin/claude` or `/usr/local/bin/claude`

## Manual Import (Alternative)

If you disable auto-injection, you can manually import the browser plugin:

```typescript
// In your main entry file
import { registerReactGrabPlugin } from '@catalyst/react-grab'

if (import.meta.env.DEV) {
  registerReactGrabPlugin({
    apiEndpoint: '/api/grab-prompt',
    debug: false,
  })
}
```

## Catalyst Integration

For Catalyst projects, you can use the shared config:

```typescript
// vite.config.ts
import { defineCatalystConfig } from '@catalyst/vite-config'

export default defineCatalystConfig({
  // Your custom config here - react-grab included automatically
})
```

## Development

```bash
# Build the package (produces all bundles)
npm run build

# Watch mode for development
npm run dev
```

### Build Outputs

```
dist/
├── index.js/.mjs          # Browser plugin (for manual import)
├── vite-plugin.js/.mjs    # Vite plugin with transformIndexHtml
├── browser-bundle.global.js  # Auto-injected IIFE bundle (~61KB)
└── cli.js/.mjs            # CLI tool (optional)
```

## Architecture

```
@catalyst/react-grab/
├── src/
│   ├── index.ts              # Browser plugin exports
│   ├── react-grab-plugin.ts  # Main browser UI (~2700 lines)
│   ├── styles.ts             # CSS styles for the UI
│   ├── vite-plugin.ts        # Vite plugin with transformIndexHtml
│   ├── browser-bundle.ts     # IIFE wrapper for auto-injection
│   └── cli.ts                # CLI tool (optional)
└── dist/                     # Built output (CJS + ESM + IIFE)
```

## Requirements

- Vite 5.0+
- React application (detects React via DevTools hook or fiber)
- Claude Code CLI installed (or other AI CLI)

## Credits

- Original [React Grab](https://github.com/user/react-grab) repository
- [Cleo.build](https://cleo.build) AI element selection patterns
- Catalyst integration for Claude Code CLI

## License

MIT
