/* eslint-disable no-console */
/**
 * React Grab Vite Plugin
 *
 * Bridges React Grab prompts to Claude Code CLI.
 * Only active in development mode.
 *
 * Receives:
 *   POST /api/grab-prompt
 *   { prompt: string, elementContext: { filePath, componentHierarchy, htmlSnippet } }
 *
 * Sends to Claude Code CLI and returns the response
 */
import { spawn, execSync, ChildProcess } from 'child_process'
import { writeFileSync, mkdirSync, existsSync, readdirSync, unlinkSync, readFileSync } from 'fs'
import { join, dirname } from 'path'
import { tmpdir, homedir } from 'os'
import { fileURLToPath } from 'url'
import { randomUUID } from 'crypto'

/**
 * Session storage for persistent conversations
 */
interface SessionMessage {
  role: 'user' | 'assistant'
  content: string
  timestamp: number
}

interface Session {
  id: string
  messages: SessionMessage[]
  createdAt: number
  lastActivity: number
  elementContext?: ElementContext
  claudeSessionId?: string // Claude CLI session ID for --resume
}

// In-memory session storage
const sessions: Map<string, Session> = new Map()

// Session cleanup interval (check every 5 minutes)
const SESSION_CLEANUP_INTERVAL = 5 * 60 * 1000
// Session TTL (12 hours)
const SESSION_TTL = 12 * 60 * 60 * 1000

/**
 * Create a new session
 */
function createSession(elementContext?: ElementContext): Session {
  const session: Session = {
    id: randomUUID(),
    messages: [],
    createdAt: Date.now(),
    lastActivity: Date.now(),
    elementContext,
  }
  sessions.set(session.id, session)
  return session
}

/**
 * Get a session by ID
 */
function getSession(id: string): Session | undefined {
  const session = sessions.get(id)
  if (session) {
    session.lastActivity = Date.now()
  }
  return session
}

/**
 * Add a message to a session
 */
function addMessageToSession(sessionId: string, role: 'user' | 'assistant', content: string) {
  const session = sessions.get(sessionId)
  if (session) {
    session.messages.push({
      role,
      content,
      timestamp: Date.now(),
    })
    session.lastActivity = Date.now()
  }
}

/**
 * Clean up old sessions
 */
function cleanupOldSessions(debug: boolean) {
  const now = Date.now()
  let cleaned = 0
  for (const [id, session] of sessions) {
    if (now - session.lastActivity > SESSION_TTL) {
      sessions.delete(id)
      cleaned++
    }
  }
  if (debug && cleaned > 0) {
    console.log(`[react-grab-vite] Cleaned up ${cleaned} old sessions`)
  }
}

// Start session cleanup interval
let cleanupInterval: ReturnType<typeof setInterval> | null = null

function startSessionCleanup(debug: boolean) {
  if (cleanupInterval) return
  cleanupInterval = setInterval(() => cleanupOldSessions(debug), SESSION_CLEANUP_INTERVAL)
}

/**
 * Parse Claude CLI stream-json output
 * Format: newline-delimited JSON objects
 */
interface StreamJsonMessage {
  type: 'content_block_delta' | 'content_block_start' | 'message_start' | 'message_delta' | 'message_stop' | 'error'
  delta?: {
    type?: string
    text?: string
  }
  content_block?: {
    type: string
    text?: string
  }
  message?: {
    id?: string
  }
  error?: {
    message: string
  }
}

function parseStreamJson(chunk: string): StreamJsonMessage[] {
  const messages: StreamJsonMessage[] = []
  const lines = chunk.split('\n').filter(line => line.trim())

  for (const line of lines) {
    try {
      const parsed = JSON.parse(line)
      messages.push(parsed)
    } catch {
      // Skip non-JSON lines
    }
  }

  return messages
}

/**
 * Get the directory where react-grab is installed (for update checking)
 */
function getPackageRoot(): string {
  const moduleDir = getModuleDir()
  // Module dir is typically dist/, so go up one level
  const packageRoot = join(moduleDir, '..')
  if (existsSync(join(packageRoot, 'package.json'))) {
    return packageRoot
  }
  return moduleDir
}

/**
 * Check if a directory is a git repository
 */
function isGitRepo(dir: string): boolean {
  return existsSync(join(dir, '.git'))
}

/**
 * Get local git commit hash
 */
function getLocalCommit(repoDir: string): string | null {
  try {
    const result = execSync('git rev-parse HEAD', {
      cwd: repoDir,
      encoding: 'utf-8',
      stdio: ['pipe', 'pipe', 'pipe'],
    })
    return result.trim()
  } catch {
    return null
  }
}

/**
 * Get remote git commit hash (latest on origin/main)
 */
function getRemoteCommit(repoDir: string): string | null {
  try {
    // Fetch latest refs without downloading objects
    execSync('git fetch --quiet origin main 2>/dev/null || git fetch --quiet origin master 2>/dev/null', {
      cwd: repoDir,
      encoding: 'utf-8',
      stdio: ['pipe', 'pipe', 'pipe'],
      shell: '/bin/sh',
    })

    // Get the remote HEAD
    const result = execSync('git rev-parse origin/main 2>/dev/null || git rev-parse origin/master 2>/dev/null', {
      cwd: repoDir,
      encoding: 'utf-8',
      stdio: ['pipe', 'pipe', 'pipe'],
      shell: '/bin/sh',
    })
    return result.trim()
  } catch {
    return null
  }
}

/**
 * Get short commit hash for display
 */
function shortCommit(commit: string | null): string {
  return commit ? commit.slice(0, 7) : 'unknown'
}

/**
 * Pull latest changes from remote
 */
function pullUpdates(repoDir: string): { success: boolean; message: string } {
  try {
    const result = execSync('git pull --ff-only origin main 2>/dev/null || git pull --ff-only origin master 2>/dev/null', {
      cwd: repoDir,
      encoding: 'utf-8',
      stdio: ['pipe', 'pipe', 'pipe'],
      shell: '/bin/sh',
    })
    return { success: true, message: result.trim() }
  } catch (err) {
    const error = err as Error
    return { success: false, message: error.message }
  }
}

/**
 * Rebuild the package after pulling updates
 */
function rebuildPackage(repoDir: string): { success: boolean; message: string } {
  try {
    console.log('[react-grab] Rebuilding after update...')
    execSync('npm run build', {
      cwd: repoDir,
      encoding: 'utf-8',
      stdio: ['pipe', 'pipe', 'pipe'],
    })
    return { success: true, message: 'Build complete' }
  } catch (err) {
    const error = err as Error
    return { success: false, message: error.message }
  }
}

/**
 * Check for updates and optionally auto-update
 */
async function checkForUpdates(autoUpdate: boolean, debug: boolean): Promise<void> {
  const packageRoot = getPackageRoot()

  if (!isGitRepo(packageRoot)) {
    if (debug) {
      console.log('[react-grab] Not a git repo, skipping update check')
    }
    return
  }

  const localCommit = getLocalCommit(packageRoot)
  if (!localCommit) {
    if (debug) {
      console.log('[react-grab] Could not get local commit, skipping update check')
    }
    return
  }

  console.log('[react-grab] Checking for updates...')

  const remoteCommit = getRemoteCommit(packageRoot)
  if (!remoteCommit) {
    if (debug) {
      console.log('[react-grab] Could not fetch remote commit')
    }
    return
  }

  if (localCommit === remoteCommit) {
    console.log(`[react-grab] ✓ Up to date (${shortCommit(localCommit)})`)
    return
  }

  // Update available!
  console.log(`[react-grab] ⬆ Update available: ${shortCommit(localCommit)} → ${shortCommit(remoteCommit)}`)

  if (autoUpdate) {
    console.log('[react-grab] Auto-updating...')
    const pullResult = pullUpdates(packageRoot)

    if (pullResult.success) {
      console.log('[react-grab] ✓ Updated successfully')

      // Rebuild the package
      const buildResult = rebuildPackage(packageRoot)
      if (buildResult.success) {
        console.log('[react-grab] ✓ Rebuild complete')
        console.log('[react-grab] ⚠ Restart your dev server to use the new version')
      } else {
        console.warn('[react-grab] ⚠ Rebuild failed:', buildResult.message)
        console.warn('[react-grab] Run manually: cd', packageRoot, '&& npm run build')
      }
    } else {
      console.warn('[react-grab] ⚠ Auto-update failed:', pullResult.message)
      console.warn('[react-grab] Run manually: cd', packageRoot, '&& git pull')
    }
  } else {
    // Just notify
    console.log('[react-grab] To update, run:')
    console.log(`  cd ${packageRoot} && git pull && npm run build`)
  }
}

/**
 * Auto-detect AI CLI path (Claude Code or Cursor)
 * Checks common installation locations
 */
function detectCliPath(): string | undefined {
  const home = homedir()
  const candidates = [
    // Claude Code paths (primary - check first)
    join(home, '.local/bin/claude'),
    '/usr/local/bin/claude',
    // Cursor paths (fallback)
    join(home, '.local/bin/cursor'),
    '/usr/local/bin/cursor',
  ]

  for (const candidate of candidates) {
    if (existsSync(candidate)) {
      return candidate
    }
  }

  return undefined
}

/**
 * Minimal HTTP types for Vite middleware without coupling to specific versions.
 */
interface MinimalRequest {
  url?: string
  method?: string
  [Symbol.asyncIterator](): AsyncIterator<Buffer>
}

interface MinimalResponse {
  statusCode: number
  setHeader(name: string, value: string): void
  write(chunk: string): boolean
  end(body?: string): void
}

/**
 * Minimal Vite Plugin interface to avoid version coupling.
 * This matches the essential shape needed by Vite plugins.
 */
interface VitePlugin {
  name: string
  apply?: 'build' | 'serve'
  configureServer?: (server: {
    middlewares: {
      use: (handler: (req: MinimalRequest, res: MinimalResponse, next: () => void) => void | Promise<void>) => void
    }
  }) => void
  transformIndexHtml?: (html: string) => string | { html: string; tags: Array<{ tag: string; attrs?: Record<string, string>; children?: string; injectTo?: 'head' | 'body' | 'head-prepend' | 'body-prepend' }> }
}

/**
 * Get the directory containing this module (works for both ESM and CJS)
 */
function getModuleDir(): string {
  // Try ESM approach first
  try {
    if (typeof import.meta !== 'undefined' && import.meta.url) {
      return dirname(fileURLToPath(import.meta.url))
    }
  } catch {
    // Fall through to __dirname approach
  }
  // CJS fallback
  if (typeof __dirname !== 'undefined') {
    return __dirname
  }
  // Last resort - use current working directory
  return process.cwd()
}

/**
 * Load the browser bundle for injection
 * Falls back to inline bundle if file not found
 */
function loadBrowserBundle(debug: boolean): string | null {
  const moduleDir = getModuleDir()

  // Try to find the browser bundle in various locations
  const bundlePaths = [
    join(moduleDir, 'browser-bundle.global.js'),             // Same dir as vite-plugin (after build)
    join(moduleDir, '..', 'dist', 'browser-bundle.global.js'), // From src to dist
    join(moduleDir, 'browser-bundle.iife.js'),               // Alternative IIFE naming
  ]

  for (const bundlePath of bundlePaths) {
    if (existsSync(bundlePath)) {
      if (debug) {
        console.log(`[react-grab-vite] Loaded browser bundle from: ${bundlePath}`)
      }
      return readFileSync(bundlePath, 'utf-8')
    }
  }

  console.warn('[react-grab-vite] Browser bundle not found. Run `npm run build` in react-grab package.')
  console.warn('[react-grab-vite] Searched paths:', bundlePaths)
  return null
}

export interface ReactGrabVitePluginConfig {
  /** Path to the project directory (used as working directory for AI CLI) */
  projectPath?: string
  /** Path to Claude CLI executable (default: {{HOME_DIR}}/.local/bin/claude) */
  claudePath?: string
  /** Enable debug logging (default: false) */
  debug?: boolean
  /** Disable automatic browser script injection (default: false) */
  disableAutoInject?: boolean
  /** Automatically update react-grab when new version is available (default: true) */
  autoUpdate?: boolean
  /** Skip update check entirely (default: false) */
  skipUpdateCheck?: boolean
}

interface ElementContext {
  filePath?: string
  componentHierarchy?: string[]
  htmlSnippet?: string
  lineNumber?: number
  // Enhanced identification fields
  textContent?: string
  siblingPosition?: {
    index: number
    total: number
    siblingTexts?: string[]
  }
  parentContext?: {
    tagName: string
    textContent?: string
    htmlSnippet?: string
  }
  uniqueIdentifiers?: {
    id?: string
    dataTestId?: string
    dataAttributes?: Record<string, string>
    className?: string
    key?: string
  }
}

interface Screenshot {
  dataUrl: string
  name: string
}

interface GrabPromptRequest {
  prompt: string
  elementContext?: ElementContext
  screenshots?: Screenshot[]
}

/**
 * Save base64 data URL to a temporary file
 */
function saveScreenshotToTemp(dataUrl: string, name: string, index: number): string {
  const tempDir = join(tmpdir(), 'react-grab-screenshots')
  if (!existsSync(tempDir)) {
    mkdirSync(tempDir, { recursive: true })
  }

  // Extract base64 data from data URL
  const matches = dataUrl.match(/^data:image\/(\w+);base64,(.+)$/)
  if (!matches) {
    throw new Error('Invalid screenshot data URL')
  }

  const extension = matches[1]
  const base64Data = matches[2]
  const buffer = Buffer.from(base64Data, 'base64')

  const filename = `screenshot-${Date.now()}-${index}.${extension}`
  const filepath = join(tempDir, filename)

  writeFileSync(filepath, buffer)
  return filepath
}

/**
 * Format the user's prompt with element context for the AI
 */
function formatPromptForAI(request: GrabPromptRequest, screenshotPaths: string[] = []): string {
  const { prompt, elementContext } = request

  let formattedPrompt = prompt

  if (elementContext) {
    const contextParts: string[] = []

    // IMPORTANT: Start with the most distinguishing information
    // This helps Claude identify the EXACT element, not similar siblings

    // 1. Text content - most human-readable identifier
    if (elementContext.textContent) {
      contextParts.push(`**Selected Element Text:** "${elementContext.textContent}"`)
    }

    // 2. Parent context - crucial for disambiguating sibling elements
    if (elementContext.parentContext?.textContent) {
      contextParts.push(`**Parent Container Text:** "${elementContext.parentContext.textContent}"`)
    }

    // 3. Sibling position - explicit disambiguation
    if (elementContext.siblingPosition) {
      const { index, total, siblingTexts } = elementContext.siblingPosition
      contextParts.push(`**Position:** Element ${index} of ${total} similar siblings`)
      if (siblingTexts?.length) {
        contextParts.push(`**Sibling Context:** ${siblingTexts.join(' | ')}`)
      }
    }

    // 4. Unique identifiers
    if (elementContext.uniqueIdentifiers) {
      const ids = elementContext.uniqueIdentifiers
      const idParts: string[] = []
      if (ids.id) idParts.push(`id="${ids.id}"`)
      if (ids.dataTestId) idParts.push(`data-testid="${ids.dataTestId}"`)
      if (ids.key) idParts.push(`key="${ids.key}"`)
      if (ids.dataAttributes) {
        Object.entries(ids.dataAttributes).forEach(([k, v]) => {
          idParts.push(`${k}="${v}"`)
        })
      }
      if (idParts.length > 0) {
        contextParts.push(`**Unique Identifiers:** ${idParts.join(', ')}`)
      }
    }

    // 5. File and component info
    if (elementContext.filePath) {
      const lineInfo = elementContext.lineNumber ? `:${elementContext.lineNumber}` : ''
      contextParts.push(`**File:** \`${elementContext.filePath}${lineInfo}\``)
    }

    if (elementContext.componentHierarchy?.length) {
      contextParts.push(
        `**Component Hierarchy:** ${elementContext.componentHierarchy.join(' > ')}`
      )
    }

    // 6. HTML snippet (for reference)
    if (elementContext.htmlSnippet) {
      const snippet =
        elementContext.htmlSnippet.length > 500
          ? elementContext.htmlSnippet.slice(0, 500) + '...'
          : elementContext.htmlSnippet
      contextParts.push(`**Element HTML:**\n\`\`\`html\n${snippet}\n\`\`\``)
    }

    // 7. Screenshots
    if (screenshotPaths.length > 0) {
      contextParts.push(`**Attached Screenshots:** ${screenshotPaths.length} image(s)`)
      screenshotPaths.forEach((path, i) => {
        contextParts.push(`- Screenshot ${i + 1}: \`${path}\``)
      })
    }

    if (contextParts.length > 0) {
      // Add explicit instruction to target ONLY this specific element
      formattedPrompt = `## Selected Element Context

${contextParts.join('\n')}

---

**IMPORTANT:** Apply changes ONLY to this specific element, not to similar sibling elements. Use the text content, parent context, and position information above to identify the exact element.

**User Request:** ${prompt}`
    }
  }

  return formattedPrompt
}

/**
 * Queue prompt for Claude CLI execution (fire-and-forget pattern)
 * Returns immediately with success, Claude CLI runs in background
 */
function queueClaudeCLI(
  prompt: string,
  projectPath: string,
  claudePath: string,
  debug: boolean
): { success: boolean; message: string } {
  // Use -p for print mode (non-interactive)
  const args = ['-p', prompt, '--add-dir', projectPath]

  if (debug) {
    console.log('[react-grab-vite] Queuing Claude CLI execution...')
    console.log(`[react-grab-vite] Working directory: ${projectPath}`)
    console.log(`[react-grab-vite] Prompt: ${prompt.slice(0, 100)}...`)
  }

  try {
    // Spawn detached process that runs independently
    const child = spawn(claudePath, args, {
      cwd: projectPath,
      env: {
        ...process.env,
        HOME: process.env.HOME || homedir(),
        TERM: 'dumb',
      },
      stdio: ['ignore', 'pipe', 'pipe'],
      detached: true, // Run independently of parent
    })

    // Log output for debugging but don't wait for it
    if (debug) {
      child.stdout?.on('data', (data) => {
        console.log('[react-grab-vite] Claude:', data.toString().slice(0, 200))
      })

      child.stderr?.on('data', (data) => {
        console.error('[react-grab-vite] Claude stderr:', data.toString())
      })

      child.on('close', (code) => {
        console.log(`[react-grab-vite] Claude CLI completed with code ${code}`)
      })
    }

    child.on('error', (err) => {
      console.error('[react-grab-vite] Claude CLI error:', err.message)
    })

    // Unref to allow Vite to exit even if Claude is still running
    child.unref()

    return {
      success: true,
      message: 'Request sent to Claude Code. Check your terminal for the response.',
    }
  } catch (err) {
    const error = err as Error
    console.error('[react-grab-vite] Failed to start Claude CLI:', error.message)
    return {
      success: false,
      message: `Failed to start Claude CLI: ${error.message}`,
    }
  }
}

/**
 * Queue prompt for Claude CLI with conversation continuity
 * Uses --continue flag to maintain session context
 */
function queueClaudeCLIConversation(
  prompt: string,
  projectPath: string,
  claudePath: string,
  debug: boolean,
  sessionId?: string | null
): { success: boolean; message: string; sessionId?: string } {
  // Use --continue to continue the most recent conversation in this project
  // If no session exists yet, Claude will start a new one
  const args = sessionId
    ? ['--resume', sessionId, '-p', prompt, '--add-dir', projectPath]
    : ['-c', '-p', prompt, '--add-dir', projectPath] // -c = --continue

  if (debug) {
    console.log('[react-grab-vite] Queuing Claude CLI conversation...')
    console.log(`[react-grab-vite] Working directory: ${projectPath}`)
    console.log(`[react-grab-vite] Session: ${sessionId || 'continue most recent'}`)
    console.log(`[react-grab-vite] Prompt: ${prompt.slice(0, 100)}...`)
  }

  try {
    // Spawn detached process that runs independently
    const child = spawn(claudePath, args, {
      cwd: projectPath,
      env: {
        ...process.env,
        HOME: process.env.HOME || homedir(),
        TERM: 'dumb',
      },
      stdio: ['ignore', 'pipe', 'pipe'],
      detached: true,
    })

    // Log output for debugging but don't wait for it
    if (debug) {
      child.stdout?.on('data', (data) => {
        console.log('[react-grab-vite] Claude:', data.toString().slice(0, 200))
      })

      child.stderr?.on('data', (data) => {
        console.error('[react-grab-vite] Claude stderr:', data.toString())
      })

      child.on('close', (code) => {
        console.log(`[react-grab-vite] Claude CLI conversation completed with code ${code}`)
      })
    }

    child.on('error', (err) => {
      console.error('[react-grab-vite] Claude CLI error:', err.message)
    })

    child.unref()

    return {
      success: true,
      message: 'Message sent. Conversation continues in Claude Code.',
      sessionId: sessionId || undefined,
    }
  } catch (err) {
    const error = err as Error
    console.error('[react-grab-vite] Failed to start Claude CLI conversation:', error.message)
    return {
      success: false,
      message: `Failed to start Claude CLI: ${error.message}`,
    }
  }
}

/**
 * Spawn Claude CLI with streaming output
 * Returns the child process for streaming response handling
 */
function spawnStreamingClaude(
  prompt: string,
  projectPath: string,
  claudePath: string,
  debug: boolean,
  claudeSessionId?: string | null
): ChildProcess {
  // Build args for streaming mode
  const args: string[] = []

  // Session handling
  if (claudeSessionId) {
    args.push('--resume', claudeSessionId)
  } else {
    args.push('-c') // --continue for new session in same project
  }

  // Add prompt
  args.push('-p', prompt)

  // Add streaming output format
  args.push('--output-format', 'stream-json')

  // Add project directory
  args.push('--add-dir', projectPath)

  if (debug) {
    console.log('[react-grab-vite] Spawning streaming Claude CLI...')
    console.log(`[react-grab-vite] Args: ${args.join(' ')}`)
  }

  const child = spawn(claudePath, args, {
    cwd: projectPath,
    env: {
      ...process.env,
      HOME: process.env.HOME || homedir(),
      TERM: 'dumb',
    },
    stdio: ['ignore', 'pipe', 'pipe'],
    // NOT detached - we need to capture output
  })

  return child
}

/**
 * Create the React Grab Vite plugin
 *
 * This plugin does two things:
 * 1. Auto-injects the React Grab browser UI via transformIndexHtml (no manual import needed)
 * 2. Provides API endpoints for Claude CLI communication
 *
 * Just add the plugin to your vite.config.ts and run `npm run dev` - react-grab works automatically.
 */
export function reactGrabVitePlugin(userConfig?: ReactGrabVitePluginConfig): VitePlugin {
  // Resolve configuration with defaults
  // Priority: config option > REACT_GRAB_CLI_PATH env var > auto-detect
  const projectPath = userConfig?.projectPath || process.cwd()
  const claudePath = userConfig?.claudePath || process.env.REACT_GRAB_CLI_PATH || detectCliPath()
  const debug = userConfig?.debug || false
  const disableAutoInject = userConfig?.disableAutoInject || false
  const autoUpdate = userConfig?.autoUpdate !== false // default: true
  const skipUpdateCheck = userConfig?.skipUpdateCheck || false

  if (!claudePath) {
    console.warn('[react-grab-vite] No AI CLI found. Set claudePath in config or REACT_GRAB_CLI_PATH env var.')
  }

  // Check for updates (async, non-blocking)
  if (!skipUpdateCheck) {
    checkForUpdates(autoUpdate, debug).catch((err) => {
      if (debug) {
        console.warn('[react-grab] Update check failed:', err.message)
      }
    })
  }

  // Load browser bundle for injection (only in dev mode)
  let browserBundle: string | null = null
  if (!disableAutoInject) {
    browserBundle = loadBrowserBundle(debug)
  }

  // Start session cleanup
  startSessionCleanup(debug)

  // Log project path during development
  console.log(`[react-grab-vite] Working directory: ${projectPath}`)
  if (browserBundle) {
    console.log(`[react-grab-vite] Browser UI will be auto-injected (${Math.round(browserBundle.length / 1024)}KB)`)
  }

  return {
    name: 'react-grab-vite-plugin',
    apply: 'serve', // Only active during dev server

    // Auto-inject browser script into HTML
    transformIndexHtml(html) {
      if (!browserBundle || disableAutoInject) {
        return html
      }

      if (debug) {
        console.log('[react-grab-vite] Injecting browser bundle into HTML')
      }

      // Inject script before </body> tag
      // The script is wrapped in an IIFE to avoid polluting global scope
      const scriptTag = `
<!-- React Grab - Auto-injected by @catalyst/react-grab -->
<script>
(function() {
  // Only run in development mode
  if (location.hostname !== 'localhost' && location.hostname !== '127.0.0.1') {
    return;
  }
${browserBundle}
})();
</script>
`
      // Insert before closing body tag
      if (html.includes('</body>')) {
        return html.replace('</body>', `${scriptTag}</body>`)
      }

      // Fallback: append to end
      return html + scriptTag
    },

    configureServer(server) {
      server.middlewares.use(async (req, res, next) => {
        // Handle /api/grab-prompt
        if (req.url !== '/api/grab-prompt' || req.method !== 'POST') {
          return next()
        }

        if (debug) {
          console.log('[react-grab-vite] Received grab-prompt request')
        }

        // Read request body
        let body = ''
        for await (const chunk of req) {
          body += chunk
        }

        let request: GrabPromptRequest
        try {
          request = JSON.parse(body)
        } catch {
          res.statusCode = 400
          res.setHeader('Content-Type', 'application/json')
          res.end(JSON.stringify({ error: 'Invalid JSON body' }))
          return
        }

        if (!request.prompt?.trim()) {
          res.statusCode = 400
          res.setHeader('Content-Type', 'application/json')
          res.end(JSON.stringify({ error: 'Prompt is required' }))
          return
        }

        if (!claudePath) {
          res.statusCode = 500
          res.setHeader('Content-Type', 'application/json')
          res.end(JSON.stringify({ error: 'No AI CLI found. Install Claude Code or Cursor, or set claudePath in config.' }))
          return
        }

        // Format the prompt with context
        const formattedPrompt = formatPromptForAI(request)

        if (debug) {
          console.log('[react-grab-vite] Formatted prompt:')
          console.log(formattedPrompt.slice(0, 200) + (formattedPrompt.length > 200 ? '...' : ''))
        }

        // Queue Claude CLI execution (fire-and-forget)
        const result = queueClaudeCLI(formattedPrompt, projectPath, claudePath, debug)

        res.statusCode = result.success ? 200 : 500
        res.setHeader('Content-Type', 'application/json')
        res.end(
          JSON.stringify({
            success: result.success,
            message: result.message,
            projectPath: projectPath,
          })
        )
      })

      // Handle /api/grab-conversation (for expanded panel with session continuity)
      server.middlewares.use(async (req, res, next) => {
        if (req.url !== '/api/grab-conversation' || req.method !== 'POST') {
          return next()
        }

        if (debug) {
          console.log('[react-grab-vite] Received grab-conversation request')
        }

        // Read request body
        let body = ''
        for await (const chunk of req) {
          body += chunk
        }

        let request: GrabPromptRequest & { sessionId?: string }
        try {
          request = JSON.parse(body)
        } catch {
          res.statusCode = 400
          res.setHeader('Content-Type', 'application/json')
          res.end(JSON.stringify({ error: 'Invalid JSON body' }))
          return
        }

        if (!request.prompt?.trim()) {
          res.statusCode = 400
          res.setHeader('Content-Type', 'application/json')
          res.end(JSON.stringify({ error: 'Prompt is required' }))
          return
        }

        if (!claudePath) {
          res.statusCode = 500
          res.setHeader('Content-Type', 'application/json')
          res.end(JSON.stringify({ error: 'No AI CLI found. Install Claude Code or Cursor, or set claudePath in config.' }))
          return
        }

        // Process screenshots if any
        let screenshotPaths: string[] = []
        if (request.screenshots && request.screenshots.length > 0) {
          try {
            screenshotPaths = request.screenshots.map((screenshot, index) =>
              saveScreenshotToTemp(screenshot.dataUrl, screenshot.name, index)
            )
            if (debug) {
              console.log(`[react-grab-vite] Saved ${screenshotPaths.length} screenshots`)
            }
          } catch (err) {
            console.error('[react-grab-vite] Failed to save screenshots:', err)
          }
        }

        // Format the prompt with context and screenshot paths
        const formattedPrompt = formatPromptForAI(request, screenshotPaths)

        if (debug) {
          console.log('[react-grab-vite] Conversation prompt:')
          console.log(formattedPrompt.slice(0, 200) + (formattedPrompt.length > 200 ? '...' : ''))
          console.log(`[react-grab-vite] Session ID: ${request.sessionId || 'none (will continue)'}`)
        }

        // Queue Claude CLI with conversation continuity
        const result = queueClaudeCLIConversation(
          formattedPrompt,
          projectPath,
          claudePath,
          debug,
          request.sessionId
        )

        res.statusCode = result.success ? 200 : 500
        res.setHeader('Content-Type', 'application/json')
        res.end(
          JSON.stringify({
            success: result.success,
            message: result.message,
            projectPath: projectPath,
            sessionId: result.sessionId,
          })
        )
      })

      // Handle /api/grab-chat (streaming SSE endpoint)
      server.middlewares.use(async (req, res, next) => {
        if (req.url !== '/api/grab-chat' || req.method !== 'POST') {
          return next()
        }

        if (debug) {
          console.log('[react-grab-vite] Received streaming chat request')
        }

        // Read request body
        let body = ''
        for await (const chunk of req) {
          body += chunk
        }

        let request: { prompt: string; elementContext?: ElementContext; sessionId?: string; screenshots?: Screenshot[] }
        try {
          request = JSON.parse(body)
        } catch {
          res.statusCode = 400
          res.setHeader('Content-Type', 'application/json')
          res.end(JSON.stringify({ error: 'Invalid JSON body' }))
          return
        }

        if (!request.prompt?.trim()) {
          res.statusCode = 400
          res.setHeader('Content-Type', 'application/json')
          res.end(JSON.stringify({ error: 'Prompt is required' }))
          return
        }

        if (!claudePath) {
          res.statusCode = 500
          res.setHeader('Content-Type', 'application/json')
          res.end(JSON.stringify({ error: 'No AI CLI found. Install Claude Code or Cursor, or set claudePath in config.' }))
          return
        }

        // Get or create session
        let session: Session
        if (request.sessionId) {
          const existingSession = getSession(request.sessionId)
          if (existingSession) {
            session = existingSession
          } else {
            session = createSession(request.elementContext)
          }
        } else {
          session = createSession(request.elementContext)
        }

        // Process screenshots if any
        let screenshotPaths: string[] = []
        if (request.screenshots && request.screenshots.length > 0) {
          try {
            screenshotPaths = request.screenshots.map((screenshot, index) =>
              saveScreenshotToTemp(screenshot.dataUrl, screenshot.name, index)
            )
          } catch (err) {
            console.error('[react-grab-vite] Failed to save screenshots:', err)
          }
        }

        // Format the prompt with context
        const formattedPrompt = formatPromptForAI({
          prompt: request.prompt,
          elementContext: request.elementContext,
          screenshots: request.screenshots,
        }, screenshotPaths)

        // Add user message to session
        addMessageToSession(session.id, 'user', request.prompt)

        // Set up SSE response
        res.statusCode = 200
        res.setHeader('Content-Type', 'text/event-stream')
        res.setHeader('Cache-Control', 'no-cache')
        res.setHeader('Connection', 'keep-alive')
        res.setHeader('X-Accel-Buffering', 'no')

        // Send initial event with session ID
        res.write(`data: ${JSON.stringify({ type: 'session', sessionId: session.id })}\n\n`)

        // Spawn Claude CLI with streaming
        const child = spawnStreamingClaude(
          formattedPrompt,
          projectPath,
          claudePath,
          debug,
          session.claudeSessionId
        )

        let fullResponse = ''
        let buffer = ''

        child.stdout?.on('data', (data: Buffer) => {
          const chunk = data.toString()
          buffer += chunk

          // Process complete lines
          const lines = buffer.split('\n')
          buffer = lines.pop() || '' // Keep incomplete line in buffer

          for (const line of lines) {
            if (!line.trim()) continue

            try {
              const parsed = JSON.parse(line)

              // Handle different message types from Claude stream-json
              if (parsed.type === 'content_block_delta' && parsed.delta?.text) {
                fullResponse += parsed.delta.text
                res.write(`data: ${JSON.stringify({
                  type: 'delta',
                  text: parsed.delta.text,
                  fullText: fullResponse
                })}\n\n`)
              } else if (parsed.type === 'message_start' && parsed.message?.id) {
                // Store Claude's session ID for future continuity
                session.claudeSessionId = parsed.message.id
                res.write(`data: ${JSON.stringify({
                  type: 'message_start',
                  claudeSessionId: parsed.message.id
                })}\n\n`)
              } else if (parsed.type === 'message_stop') {
                // Message complete
                res.write(`data: ${JSON.stringify({
                  type: 'message_stop',
                  fullText: fullResponse
                })}\n\n`)
              } else if (parsed.type === 'error') {
                res.write(`data: ${JSON.stringify({
                  type: 'error',
                  error: parsed.error?.message || 'Unknown error'
                })}\n\n`)
              }
            } catch {
              // Non-JSON output (e.g., plain text from Claude)
              if (line.trim()) {
                fullResponse += line + '\n'
                res.write(`data: ${JSON.stringify({
                  type: 'text',
                  text: line,
                  fullText: fullResponse
                })}\n\n`)
              }
            }
          }
        })

        child.stderr?.on('data', (data: Buffer) => {
          const errorText = data.toString()
          if (debug) {
            console.error('[react-grab-vite] Claude stderr:', errorText)
          }
          res.write(`data: ${JSON.stringify({
            type: 'error',
            error: errorText
          })}\n\n`)
        })

        child.on('close', (code) => {
          if (debug) {
            console.log(`[react-grab-vite] Claude CLI streaming completed with code ${code}`)
          }

          // Process any remaining buffer
          if (buffer.trim()) {
            try {
              const parsed = JSON.parse(buffer)
              if (parsed.delta?.text) {
                fullResponse += parsed.delta.text
              }
            } catch {
              if (buffer.trim()) {
                fullResponse += buffer
              }
            }
          }

          // Add assistant response to session
          if (fullResponse.trim()) {
            addMessageToSession(session.id, 'assistant', fullResponse.trim())
          }

          // Send final done event
          res.write(`data: ${JSON.stringify({
            type: 'done',
            sessionId: session.id,
            fullText: fullResponse.trim(),
            success: code === 0
          })}\n\n`)
          res.end()
        })

        child.on('error', (err) => {
          console.error('[react-grab-vite] Claude CLI error:', err.message)
          res.write(`data: ${JSON.stringify({
            type: 'error',
            error: err.message
          })}\n\n`)
          res.end()
        })
      })

      // Handle /api/grab-session/:id (get session history)
      server.middlewares.use(async (req, res, next) => {
        const sessionMatch = req.url?.match(/^\/api\/grab-session\/([a-f0-9-]+)$/)
        if (!sessionMatch || req.method !== 'GET') {
          return next()
        }

        const sessionId = sessionMatch[1]
        const session = getSession(sessionId)

        if (!session) {
          res.statusCode = 404
          res.setHeader('Content-Type', 'application/json')
          res.end(JSON.stringify({ error: 'Session not found' }))
          return
        }

        res.statusCode = 200
        res.setHeader('Content-Type', 'application/json')
        res.end(JSON.stringify({
          id: session.id,
          messages: session.messages,
          createdAt: session.createdAt,
          lastActivity: session.lastActivity,
          elementContext: session.elementContext,
        }))
      })

      // Handle /api/grab-cleanup (cleanup when browser closes)
      server.middlewares.use(async (req, res, next) => {
        if (req.url !== '/api/grab-cleanup' || req.method !== 'POST') {
          return next()
        }

        if (debug) {
          console.log('[react-grab-vite] Received cleanup request (browser closing)')
        }

        // Read request body for optional session cleanup
        let body = ''
        for await (const chunk of req) {
          body += chunk
        }

        let request: { sessionId?: string } = {}
        try {
          if (body) {
            request = JSON.parse(body)
          }
        } catch {
          // Ignore parse errors
        }

        // Clean up specific session if provided
        if (request.sessionId) {
          sessions.delete(request.sessionId)
          if (debug) {
            console.log(`[react-grab-vite] Cleaned up session ${request.sessionId}`)
          }
        }

        // Clean up screenshot temp directory
        const tempDir = join(tmpdir(), 'react-grab-screenshots')
        try {
          if (existsSync(tempDir)) {
            const files = readdirSync(tempDir)
            for (const file of files) {
              unlinkSync(join(tempDir, file))
            }
            if (debug) {
              console.log(`[react-grab-vite] Cleaned up ${files.length} temp files`)
            }
          }
        } catch (err) {
          console.error('[react-grab-vite] Cleanup error:', err)
        }

        console.log('[react-grab-vite] Session cleanup complete')

        res.statusCode = 200
        res.setHeader('Content-Type', 'application/json')
        res.end(JSON.stringify({ success: true, message: 'Cleanup complete' }))
      })
    },
  }
}

// Default export for convenience
export default reactGrabVitePlugin
